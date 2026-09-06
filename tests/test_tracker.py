import json
import time

from fakes import FakePreset, FakeView, FakeWindow


def _saved(tracker):
    return tracker.module.History.load(str(tracker.path))


def test_tick_records_the_active_preset(tracker):
    tracker.krita.window = FakeWindow(FakeView(FakePreset("Ink-2")))

    tracker._tick()

    assert tracker.names() == ["Ink-2"]
    assert _saved(tracker).names(time.time()) == ["Ink-2"]


def test_tick_emits_changed_once_per_new_preset(tracker):
    counter = {"count": 0}
    tracker.changed.connect(lambda: counter.__setitem__("count", counter["count"] + 1))

    tracker.krita.window = FakeWindow(FakeView(FakePreset("a")))
    tracker._tick()
    tracker._tick()
    tracker.krita.window = FakeWindow(FakeView(FakePreset("b")))
    tracker._tick()

    assert counter["count"] == 2
    assert tracker.names() == ["b", "a"]


def test_tick_without_window_does_nothing(tracker):
    tracker.krita.window = None

    tracker._tick()

    assert tracker.names() == []
    assert not tracker.path.exists()


def test_tick_without_view_does_nothing(tracker):
    tracker.krita.window = FakeWindow(None)

    tracker._tick()

    assert tracker.names() == []
    assert not tracker.path.exists()


def test_active_preset_returns_none_without_a_window_instead_of_raising(tracker):
    tracker.krita.window = None

    assert tracker._active_preset() is None


def test_active_preset_returns_none_without_a_view_instead_of_raising(tracker):
    tracker.krita.window = FakeWindow(view=None)

    assert tracker._active_preset() is None


def test_tick_with_no_preset_does_nothing(tracker):
    tracker.krita.window = FakeWindow(FakeView(None))

    tracker._tick()

    assert tracker.names() == []
    assert not tracker.path.exists()


def test_tick_swallows_api_errors(tracker):
    class ExplodingView:
        def currentBrushPreset(self):
            raise RuntimeError("krita exploded")

    tracker.krita.window = FakeWindow(ExplodingView())

    tracker._tick()

    assert tracker.names() == []


def test_timer_runs_only_while_a_docker_is_visible(tracker):
    assert not tracker._timer.isActive()

    docker_a = object()
    docker_b = object()

    tracker.attach_viewer(docker_a)
    tracker.attach_viewer(docker_b)
    assert tracker._timer.isActive()

    tracker.detach_viewer(docker_a)
    assert tracker._timer.isActive()

    tracker.detach_viewer(docker_b)
    assert not tracker._timer.isActive()


def test_detaching_a_viewer_twice_does_not_block_the_next_stop(tracker):
    docker_a = object()
    docker_b = object()
    tracker.attach_viewer(docker_a)
    tracker.attach_viewer(docker_b)
    tracker.detach_viewer(docker_a)
    tracker.detach_viewer(docker_b)

    tracker.detach_viewer(docker_b)
    tracker.attach_viewer(docker_a)
    assert tracker._timer.isActive()

    tracker.detach_viewer(docker_a)
    assert not tracker._timer.isActive()


def test_clear_brings_the_current_preset_back(tracker):
    tracker.krita.window = FakeWindow(FakeView(FakePreset("a")))
    tracker._tick()
    assert tracker.names() == ["a"]

    tracker.clear()
    assert tracker.names() == []

    tracker._tick()
    assert tracker.names() == ["a"]


def test_setup_loads_the_saved_history(tracker):
    history = tracker.module.History()
    history.touch("z", time.time())
    history.save(str(tracker.path))

    tracker.setup()

    assert tracker.names() == ["z"]


def test_set_limit_persists_and_hides_the_lower_ranked(tracker):
    tracker.krita.window = FakeWindow(FakeView(FakePreset("a")))
    tracker._tick()
    tracker.krita.window = FakeWindow(FakeView(FakePreset("b")))
    tracker._tick()

    tracker.set_limit(1)

    assert tracker.names() == ["b"]
    assert _saved(tracker).names(time.time()) == ["b"]
    assert _saved(tracker).limit == 1


def test_a_tick_before_setup_does_not_overwrite_the_saved_file(tracker):
    now = time.time()
    history = tracker.module.History()
    history.touch("old2", now - 2)
    history.touch("old1", now - 1)
    history.save(str(tracker.path))

    tracker.krita.window = FakeWindow(FakeView(FakePreset("new")))
    tracker._tick()

    assert _saved(tracker).names(time.time()) == ["new", "old1", "old2"]


def test_set_limit_before_setup_does_not_overwrite_the_saved_file(tracker):
    now = time.time()
    history = tracker.module.History()
    history.touch("old2", now - 2)
    history.touch("old1", now - 1)
    history.save(str(tracker.path))

    tracker.set_limit(5)

    assert _saved(tracker).names(time.time()) == ["old1", "old2"]


def test_setup_does_not_replace_an_already_loaded_history_with_the_file(tracker):
    tracker.krita.window = FakeWindow(FakeView(FakePreset("a")))
    tracker._tick()
    assert tracker.names() == ["a"]

    stale = tracker.module.History()
    stale.touch("other", time.time())
    stale.save(str(tracker.path))

    tracker.setup()
    assert tracker.names() == ["a"]

    tracker._tick()
    assert tracker.names() == ["a"]


def test_application_closing_stops_the_timer(tracker):
    tracker.setup()
    tracker.attach_viewer(object())
    assert tracker._timer.isActive()

    tracker.notifier.applicationClosing.emit()

    assert not tracker._timer.isActive()


def test_polling_gives_up_after_repeated_errors(tracker):
    class ExplodingView:
        def currentBrushPreset(self):
            raise RuntimeError("krita exploded")

    tracker.krita.window = FakeWindow(ExplodingView())
    tracker.attach_viewer(object())
    assert tracker._timer.isActive()

    limit = tracker.module.MAX_CONSECUTIVE_ERRORS
    for _ in range(limit):
        tracker._tick()

    assert not tracker._timer.isActive()
    assert len(tracker.logged) == 2


def test_names_loads_lazily_before_setup(tracker):
    history = tracker.module.History(limit=7)
    history.touch("z", time.time())
    history.save(str(tracker.path))

    assert tracker.names() == ["z"]


def test_limit_loads_lazily_before_setup(tracker):
    history = tracker.module.History(limit=7)
    history.touch("z", time.time())
    history.save(str(tracker.path))

    assert tracker.limit == 7


def test_detach_viewer_key_survives_a_timer_destroyed_before_it(tracker):
    viewer = object()
    tracker.attach_viewer(viewer)

    class ExplodingTimer:
        def stop(self):
            raise RuntimeError("wrapped C/C++ object of type QTimer has been deleted")

    tracker._timer = ExplodingTimer()

    tracker.detach_viewer_key(id(viewer))


def test_reattaching_a_viewer_retries_polling_after_it_gave_up(tracker):
    class ExplodingView:
        def currentBrushPreset(self):
            raise RuntimeError("krita exploded")

    tracker.krita.window = FakeWindow(ExplodingView())
    tracker.attach_viewer(object())
    assert tracker._timer.isActive()

    limit = tracker.module.MAX_CONSECUTIVE_ERRORS
    for _ in range(limit):
        tracker._tick()

    assert not tracker._timer.isActive()
    assert tracker._errors == limit

    tracker.attach_viewer(object())

    assert tracker._timer.isActive()
    assert tracker._errors == 0


def test_tick_touches_with_the_current_clock(tracker, monkeypatch):
    frozen = 1_700_000_000.0
    monkeypatch.setattr(tracker.module.time, "time", lambda: frozen)
    tracker.krita.window = FakeWindow(FakeView(FakePreset("a")))

    tracker._tick()

    entries = json.loads(tracker.path.read_text(encoding="utf-8"))["entries"]
    assert entries["a"] == {"score": 1.0, "last_used": frozen}


def test_ignore_persists_and_emits_changed(tracker):
    tracker.krita.window = FakeWindow(FakeView(FakePreset("a")))
    tracker._tick()
    emitted = []
    tracker.changed.connect(lambda: emitted.append(True))

    tracker.ignore("a")

    assert emitted == [True]
    assert tracker.names() == []
    assert tracker.ignored_names() == ["a"]
    assert _saved(tracker).names(time.time()) == []
    assert _saved(tracker).ignored_names() == ["a"]


def test_restore_persists_and_emits_changed(tracker):
    tracker.ignore("a")
    emitted = []
    tracker.changed.connect(lambda: emitted.append(True))

    tracker.restore("a")

    assert emitted == [True]
    assert tracker.ignored_names() == []
    assert _saved(tracker).ignored_names() == []


def test_polling_an_ignored_preset_writes_and_emits_nothing(tracker):
    tracker.ignore("Eraser")
    written_before = tracker.path.read_text(encoding="utf-8")
    emitted = []
    tracker.changed.connect(lambda: emitted.append(True))
    tracker.krita.window = FakeWindow(FakeView(FakePreset("Eraser")))

    tracker._tick()
    tracker._tick()

    assert tracker.names() == []
    assert emitted == []
    assert tracker.path.read_text(encoding="utf-8") == written_before


def test_ignoring_the_active_preset_records_it_again_once_restored(tracker):
    tracker.krita.window = FakeWindow(FakeView(FakePreset("a")))
    tracker._tick()
    assert tracker.names() == ["a"]

    tracker.ignore("a")
    tracker._tick()
    assert tracker.names() == []

    tracker.restore("a")
    tracker._tick()
    assert tracker.names() == ["a"]


def test_ignored_names_loads_lazily_before_setup(tracker):
    history = tracker.module.History()
    history.ignore("z")
    history.save(str(tracker.path))

    assert tracker.ignored_names() == ["z"]


def test_ignore_before_setup_does_not_overwrite_the_saved_file(tracker):
    history = tracker.module.History()
    history.touch("old", time.time())
    history.save(str(tracker.path))

    tracker.ignore("eraser")

    assert _saved(tracker).names(time.time()) == ["old"]
    assert _saved(tracker).ignored_names() == ["eraser"]


def test_restore_before_setup_does_not_overwrite_the_saved_file(tracker):
    history = tracker.module.History()
    history.touch("old", time.time())
    history.ignore("eraser")
    history.save(str(tracker.path))

    tracker.restore("eraser")

    assert _saved(tracker).names(time.time()) == ["old"]
    assert _saved(tracker).ignored_names() == []


def test_names_ranks_with_the_current_clock(tracker, monkeypatch):
    frozen = 1_700_000_000.0
    week = 7 * 24 * 3600.0
    history = tracker.module.History()
    for _ in range(3):
        history.touch("often", frozen - 2 * week)          # 3 x 0.25 = 0.75 at frozen
    history.touch("lately", frozen - 600)                  # 1 x 4 = 4 at frozen
    history.save(str(tracker.path))
    monkeypatch.setattr(tracker.module.time, "time", lambda: frozen)

    assert tracker.names() == ["lately", "often"]


def test_get_tracker_returns_the_same_instance(tracker):
    tracker.module._TRACKER = None

    first = tracker.module.get_tracker()
    second = tracker.module.get_tracker()

    assert first is second


def test_a_failed_save_is_logged_instead_of_escaping_the_caller(tracker, monkeypatch):
    def explode(self, path):
        raise OSError("disk full")

    monkeypatch.setattr(tracker.module.History, "save", explode)
    emitted = []
    tracker.changed.connect(lambda: emitted.append(True))

    tracker.ignore("Eraser")

    assert tracker.ignored_names() == ["Eraser"]
    assert emitted == [True]
    assert tracker.logged == ["recent_brushes: could not save the history: OSError('disk full')"]
