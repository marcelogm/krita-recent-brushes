import time

from fakes import FakePreset, FakeView, FakeWindow, QtCore, QtGui, QtTest


def _dialog_names(dialog):
    return [dialog._list.item(row).text() for row in range(dialog._list.count())]


def _model_names(env, docker):
    return [
        docker._model.item(i).data(env.docker_module.NAME_ROLE)
        for i in range(docker._model.rowCount())
    ]


def test_grid_follows_the_tracker_ranking(env):
    history = env.tracker_module.History()
    for tick in (1.0, 2.0, 3.0):
        history.touch("Often", tick)
    history.touch("Lately", 4.0)
    history.save(str(env.path))
    env.krita.presets = {
        "Often": FakePreset("Often"),
        "Lately": FakePreset("Lately"),
    }

    docker = env.docker_module.RecentBrushesDocker()

    assert _model_names(env, docker) == ["Often", "Lately"]


def test_grid_skips_names_without_matching_preset(env):
    history = env.tracker_module.History()
    history.touch("Old", 1.0)
    history.touch("New", 2.0)
    history.touch("Gone", 3.0)
    history.save(str(env.path))
    env.krita.presets = {
        "Old": FakePreset("Old"),
        "New": FakePreset("New"),
    }

    docker = env.docker_module.RecentBrushesDocker()

    assert _model_names(env, docker) == ["New", "Old"]
    assert env.logged == []


def test_spinbox_starts_at_saved_limit(env):
    history = env.tracker_module.History(limit=7)
    history.save(str(env.path))

    docker = env.docker_module.RecentBrushesDocker()

    assert docker._limit_box.value() == 7


def test_construction_does_not_write_the_limit_back_to_disk(env, monkeypatch):
    history = env.tracker_module.History(limit=7)
    history.save(str(env.path))
    save_calls = []
    original_save = env.tracker_module.History.save

    def spy_save(self, path):
        save_calls.append(path)
        return original_save(self, path)

    monkeypatch.setattr(env.tracker_module.History, "save", spy_save)

    env.docker_module.RecentBrushesDocker()

    assert save_calls == []


def test_changing_spinbox_calls_set_limit_and_hides_the_rest(env):
    history = env.tracker_module.History(limit=5)
    history.touch("a", 1.0)
    history.touch("b", 2.0)
    history.touch("c", 3.0)
    history.save(str(env.path))
    env.krita.presets = {name: FakePreset(name) for name in ("a", "b", "c")}
    docker = env.docker_module.RecentBrushesDocker()
    assert docker._model.rowCount() == 3

    docker._limit_box.setValue(2)

    assert _model_names(env, docker) == ["c", "b"]
    reloaded = env.tracker_module.History.load(str(env.path))
    assert reloaded.limit == 2
    assert reloaded.names(time.time()) == ["c", "b"]


def test_clicking_item_activates_preset(env):
    history = env.tracker_module.History()
    history.touch("Ink", 1.0)
    history.save(str(env.path))
    resource = FakePreset("Ink")
    env.krita.presets = {"Ink": resource}
    view = FakeView()
    env.krita.window = FakeWindow(view)
    docker = env.docker_module.RecentBrushesDocker()

    docker._on_clicked(docker._model.index(0, 0))

    assert view.activated == [resource]


def test_clicking_without_an_active_view_does_nothing_instead_of_raising(env):
    history = env.tracker_module.History()
    history.touch("Ink", 1.0)
    history.save(str(env.path))
    env.krita.presets = {"Ink": FakePreset("Ink")}
    env.krita.window = None
    docker = env.docker_module.RecentBrushesDocker()

    docker._on_clicked(docker._model.index(0, 0))


def test_clear_button_empties_grid_and_icon_cache(env):
    history = env.tracker_module.History()
    history.touch("Ink", 1.0)
    history.save(str(env.path))
    env.krita.presets = {"Ink": FakePreset("Ink")}
    docker = env.docker_module.RecentBrushesDocker()
    assert docker._model.rowCount() == 1
    assert docker._icons

    docker._on_clear()

    assert docker._model.rowCount() == 0
    assert docker._icons == {}


def test_show_hide_events_attach_detach_once(env):
    history = env.tracker_module.History()
    history.save(str(env.path))
    docker = env.docker_module.RecentBrushesDocker()
    tracker = env.tracker_module.get_tracker()
    calls = {"attach": 0, "detach": 0}
    real_attach = tracker.attach_viewer
    real_detach = tracker.detach_viewer

    def counting_attach(viewer):
        calls["attach"] += 1
        real_attach(viewer)

    def counting_detach(viewer):
        calls["detach"] += 1
        real_detach(viewer)

    tracker.attach_viewer = counting_attach
    tracker.detach_viewer = counting_detach

    docker.showEvent(QtGui.QShowEvent())
    docker.showEvent(QtGui.QShowEvent())
    assert calls == {"attach": 1, "detach": 0}

    docker.hideEvent(QtGui.QHideEvent())
    docker.hideEvent(QtGui.QHideEvent())
    assert calls == {"attach": 1, "detach": 1}


def test_typing_a_bigger_limit_does_not_truncate(env):
    names = [f"p{i}" for i in range(20)]
    history = env.tracker_module.History(limit=20)
    for tick, name in enumerate(reversed(names)):
        history.touch(name, float(tick))
    history.save(str(env.path))
    env.krita.presets = {name: FakePreset(name) for name in names}
    docker = env.docker_module.RecentBrushesDocker()
    assert docker._limit_box.value() == 20
    assert _model_names(env, docker) == names

    box = docker._limit_box
    box.show()
    box.setFocus()
    box.selectAll()
    QtTest.QTest.keyClicks(box, "50")
    QtTest.QTest.keyClick(box, QtCore.Qt.Key.Key_Enter)

    assert box.value() == 50
    assert _model_names(env, docker) == names
    reloaded = env.tracker_module.History.load(str(env.path))
    assert reloaded.names(time.time()) == names


def test_second_docker_picks_up_limit_changed_by_first(env):
    names = [f"p{i}" for i in range(20)]
    history = env.tracker_module.History(limit=20)
    for tick, name in enumerate(reversed(names)):
        history.touch(name, float(tick))
    history.save(str(env.path))
    env.krita.presets = {name: FakePreset(name) for name in names}

    docker_a = env.docker_module.RecentBrushesDocker()
    docker_b = env.docker_module.RecentBrushesDocker()
    assert docker_b._limit_box.value() == 20

    docker_a._limit_box.setValue(5)

    assert docker_b._limit_box.value() == 5
    assert docker_b._model.rowCount() == 5


def test_mirroring_the_limit_does_not_write_it_back(env):
    history = env.tracker_module.History(limit=20)
    history.save(str(env.path))
    docker = env.docker_module.RecentBrushesDocker()
    tracker = env.tracker_module.get_tracker()

    calls = []
    original_set_limit = tracker.set_limit

    def spy_set_limit(value):
        calls.append(value)
        return original_set_limit(value)

    tracker.set_limit = spy_set_limit

    tracker.set_limit(5)

    assert calls == [5]
    assert docker._limit_box.value() == 5


def test_icons_of_removed_names_are_pruned(env):
    history = env.tracker_module.History(limit=20)
    history.touch("a", 1.0)
    history.touch("b", 2.0)
    history.save(str(env.path))
    env.krita.presets = {"a": FakePreset("a"), "b": FakePreset("b")}
    docker = env.docker_module.RecentBrushesDocker()
    assert set(docker._icons) == {"a", "b"}

    env.tracker_module.get_tracker().set_limit(1)

    assert set(docker._icons) == {"b"}


def test_clicking_does_not_refetch_resources(env):
    history = env.tracker_module.History()
    history.touch("Ink", 1.0)
    history.save(str(env.path))
    resource = FakePreset("Ink")
    env.krita.presets = {"Ink": resource}
    view = FakeView()
    env.krita.window = FakeWindow(view)
    docker = env.docker_module.RecentBrushesDocker()

    calls = {"count": 0}
    original_resources = env.krita.resources

    def counting_resources(resource_type):
        calls["count"] += 1
        return original_resources(resource_type)

    env.krita.resources = counting_resources

    docker._on_clicked(docker._model.index(0, 0))

    assert calls["count"] == 0
    assert view.activated == [resource]


def test_null_image_preset_gets_fallback_icon(env):
    history = env.tracker_module.History()
    history.touch("Blank", 1.0)
    history.save(str(env.path))
    env.krita.presets = {"Blank": FakePreset("Blank", image=QtGui.QImage())}

    docker = env.docker_module.RecentBrushesDocker()

    icon = docker._model.item(0).icon()
    assert icon.isNull() is False


def test_refresh_logs_rebuild_errors_instead_of_raising(env, monkeypatch):
    history = env.tracker_module.History()
    history.save(str(env.path))
    docker = env.docker_module.RecentBrushesDocker()

    def exploding_rebuild():
        raise RuntimeError("boom")

    monkeypatch.setattr(docker, "_rebuild", exploding_rebuild)

    docker.refresh()

    assert env.logged == ["recent_brushes: error while drawing the docker: RuntimeError('boom')"]


def _docker_with(env, *names):
    history = env.tracker_module.History()
    for tick, name in enumerate(names):
        history.touch(name, float(tick + 1))
    history.save(str(env.path))
    env.krita.presets = {name: FakePreset(name) for name in names}
    return env.docker_module.RecentBrushesDocker()


def test_grid_asks_for_a_custom_context_menu(env):
    docker = _docker_with(env)

    assert docker._list.contextMenuPolicy() == QtCore.Qt.ContextMenuPolicy.CustomContextMenu


def test_context_menu_offers_to_ignore_the_brush(env):
    docker = _docker_with(env, "Ink")

    menu = docker._context_menu_for("Ink")

    assert [action.text() for action in menu.actions()] == ['Ignore "Ink"']


def test_ignoring_from_the_menu_removes_the_brush_and_its_icon(env):
    docker = _docker_with(env, "Ink", "Pencil")
    assert set(docker._icons) == {"Ink", "Pencil"}

    docker._context_menu_for("Ink").actions()[0].trigger()

    assert _model_names(env, docker) == ["Pencil"]
    assert set(docker._icons) == {"Pencil"}
    assert env.tracker_module.get_tracker().ignored_names() == ["Ink"]


def test_right_click_on_empty_space_opens_no_menu(env, monkeypatch):
    docker = _docker_with(env, "Ink")
    docker._list.resize(400, 400)
    built = []
    monkeypatch.setattr(docker, "_context_menu_for", lambda name: built.append(name))

    docker._on_context_menu(QtCore.QPoint(390, 390))

    assert built == []


class FakeMenu:
    def __init__(self, log):
        self.log = log

    def exec(self, point):
        self.log.append(("exec", point))

    def deleteLater(self):
        self.log.append("deleted")


def test_right_clicking_an_item_opens_and_then_discards_its_menu(env, monkeypatch):
    docker = _docker_with(env, "Ink")
    docker._list.resize(400, 400)
    log = []
    monkeypatch.setattr(docker, "_context_menu_for",
                        lambda name: (log.append(name), FakeMenu(log))[1])
    inside = docker._list.visualRect(docker._model.index(0, 0)).center()

    docker._list.customContextMenuRequested.emit(inside)

    assert log == ["Ink", ("exec", docker._list.viewport().mapToGlobal(inside)), "deleted"]


def _docker_ignoring(env, *names):
    history = env.tracker_module.History()
    for name in names:
        history.ignore(name)
    history.save(str(env.path))
    return env.docker_module.RecentBrushesDocker()


def test_ignored_button_shows_the_count(env):
    docker = _docker_ignoring(env, "b", "a")
    assert docker._ignored_button.toolTip() == "Ignored brushes (2)…"

    env.tracker_module.get_tracker().restore("a")

    assert docker._ignored_button.toolTip() == "Ignored brushes (1)…"


def test_ignored_button_opens_the_dialog_on_the_tracker(env, monkeypatch):
    docker = _docker_ignoring(env)
    opened = []

    class FakeDialog:
        def __init__(self, tracker, parent=None):
            opened.append((tracker, parent))

        def exec(self):
            opened.append("exec")

        def deleteLater(self):
            opened.append("deleted")

    monkeypatch.setattr(env.docker_module, "IgnoredBrushesDialog", FakeDialog)

    docker._ignored_button.click()

    assert opened == [(env.tracker_module.get_tracker(), docker), "exec", "deleted"]


def test_dialog_lists_the_ignored_names_alphabetically(env):
    _docker_ignoring(env, "b", "a")

    dialog = env.dialog_module.IgnoredBrushesDialog(env.tracker_module.get_tracker())

    assert _dialog_names(dialog) == ["a", "b"]


def test_dialog_restore_button_is_disabled_until_a_name_is_selected(env):
    _docker_ignoring(env, "a")
    dialog = env.dialog_module.IgnoredBrushesDialog(env.tracker_module.get_tracker())
    assert not dialog._restore_button.isEnabled()

    dialog._list.setCurrentRow(0)

    assert dialog._restore_button.isEnabled()


def test_restoring_from_the_dialog_puts_the_brush_back(env):
    docker = _docker_ignoring(env, "a", "b")
    tracker = env.tracker_module.get_tracker()
    dialog = env.dialog_module.IgnoredBrushesDialog(tracker)
    dialog._list.setCurrentRow(0)

    dialog._restore_button.click()

    assert _dialog_names(dialog) == ["b"]
    assert not dialog._restore_button.isEnabled()
    assert tracker.ignored_names() == ["b"]
    assert docker._ignored_button.toolTip() == "Ignored brushes (1)…"


def test_restore_with_nothing_selected_does_nothing(env):
    _docker_ignoring(env, "a")
    tracker = env.tracker_module.get_tracker()
    dialog = env.dialog_module.IgnoredBrushesDialog(tracker)

    dialog._on_restore()

    assert tracker.ignored_names() == ["a"]


def test_close_button_closes_the_dialog(env):
    _docker_ignoring(env, "a")
    dialog = env.dialog_module.IgnoredBrushesDialog(env.tracker_module.get_tracker())
    dialog.show()
    assert dialog.isVisible()

    dialog._close_button.click()

    assert not dialog.isVisible()


def test_context_menu_escapes_ampersands_in_the_brush_name(env):
    docker = _docker_with(env, "Ink & Wash")

    menu = docker._context_menu_for("Ink & Wash")
    menu.actions()[0].trigger()

    assert [action.text() for action in menu.actions()] == ['Ignore "Ink && Wash"']
    assert env.tracker_module.get_tracker().ignored_names() == ["Ink & Wash"]


def test_clicking_logs_activation_errors_instead_of_raising(env):
    class ExplodingView:
        def setCurrentBrushPreset(self, resource):
            raise RuntimeError("krita exploded")

    docker = _docker_with(env, "Ink")
    env.krita.window = FakeWindow(ExplodingView())

    docker._on_clicked(docker._model.index(0, 0))

    assert env.logged == ["recent_brushes: could not activate the preset: RuntimeError('krita exploded')"]


def test_action_buttons_are_icon_only_tool_buttons(env):
    docker = env.docker_module.RecentBrushesDocker()

    for button in (docker._ignored_button, docker._clear_button):
        assert isinstance(button, env.docker_module.QtWidgets.QToolButton)
        assert button.text() == ""
        assert button.icon().isNull() is False
    assert docker._clear_button.toolTip() == "Clear history"


def test_buttons_ask_krita_for_theme_icons_before_falling_back(env):
    env.docker_module.RecentBrushesDocker()

    assert "edit-clear" in env.krita.icons_requested
    assert "novisible" in env.krita.icons_requested
    assert "configure" in env.krita.icons_requested


def test_clicking_clear_button_empties_grid_and_icon_cache(env):
    history = env.tracker_module.History()
    history.touch("Ink", 1.0)
    history.save(str(env.path))
    env.krita.presets = {"Ink": FakePreset("Ink")}
    docker = env.docker_module.RecentBrushesDocker()
    assert docker._model.rowCount() == 1

    docker._clear_button.click()

    assert docker._model.rowCount() == 0
    assert docker._icons == {}
    assert env.tracker_module.History.load(str(env.path)).names(time.time()) == []


def test_settings_button_opens_a_menu_containing_the_limit_spinner(env):
    docker = env.docker_module.RecentBrushesDocker()
    button = docker._settings_button

    assert isinstance(button, env.docker_module.QtWidgets.QToolButton)
    assert button.toolTip() == "Settings"
    assert button.popupMode() == env.docker_module.QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup
    menu = button.menu()
    assert menu is not None
    actions = menu.actions()
    assert len(actions) == 1
    assert isinstance(actions[0], env.docker_module.QtWidgets.QWidgetAction)
    assert docker._limit_box in actions[0].defaultWidget().findChildren(
        env.docker_module.QtWidgets.QSpinBox)


def test_spinner_inside_the_menu_still_sets_the_limit(env):
    history = env.tracker_module.History(limit=5)
    history.touch("a", 1.0)
    history.touch("b", 2.0)
    history.save(str(env.path))
    env.krita.presets = {name: FakePreset(name) for name in ("a", "b")}
    docker = env.docker_module.RecentBrushesDocker()
    docker._settings_button.menu().show()

    docker._limit_box.setValue(1)

    assert _model_names(env, docker) == ["b"]
    assert env.tracker_module.History.load(str(env.path)).limit == 1
    docker._settings_button.menu().hide()
