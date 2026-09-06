import json
import tempfile

import pytest

from recent_brushes.history import (DAY, DEFAULT_LIMIT, DEFAULT_SORT, HOUR, MAX_AGE,
                                    MAX_LIMIT, SORT_RECENT, SORT_SMART, WEEK, History,
                                    recency_factor)

NOW = 1_700_000_000.0
MINUTE = 60.0


# --- recency factor -------------------------------------------------------

def test_recency_factor_is_four_within_the_last_hour():
    assert recency_factor(0) == 4
    assert recency_factor(30 * MINUTE) == 4
    assert recency_factor(HOUR - 1) == 4


def test_recency_factor_is_two_within_the_last_day():
    assert recency_factor(HOUR) == 2
    assert recency_factor(DAY - 1) == 2


def test_recency_factor_is_a_half_within_the_last_week():
    assert recency_factor(DAY) == 0.5
    assert recency_factor(WEEK - 1) == 0.5


def test_recency_factor_is_a_quarter_beyond_a_week():
    assert recency_factor(WEEK) == 0.25
    assert recency_factor(400 * DAY) == 0.25


def test_negative_age_counts_as_the_freshest_bucket():
    assert recency_factor(-5 * MINUTE) == 4
    assert recency_factor(-2 * WEEK) == 4


# --- touch / names ----------------------------------------------------------

def test_names_of_an_empty_history_is_empty():
    assert History().names(NOW) == []


def test_touch_returns_true_when_it_records_a_use():
    assert History().touch("a", NOW) is True


def test_touch_of_blank_names_is_refused_and_records_nothing():
    history = History()
    history.touch("a", NOW)

    assert history.touch("", NOW) is False
    assert history.touch(None, NOW) is False
    assert history.names(NOW) == ["a"]


def test_names_returns_a_copy():
    history = History()
    history.touch("a", NOW)

    history.names(NOW).append("intruder")

    assert history.names(NOW) == ["a"]


def test_more_uses_rank_higher_within_the_same_bucket():
    history = History()
    history.touch("once", NOW - 3 * MINUTE)
    history.touch("twice", NOW - 5 * MINUTE)
    history.touch("twice", NOW - 4 * MINUTE)

    assert history.names(NOW) == ["twice", "once"]


def test_equal_frecency_ranks_the_more_recent_use_first():
    history = History()
    history.touch("older", NOW - 10 * MINUTE)
    history.touch("newer", NOW - 2 * MINUTE)

    assert history.names(NOW) == ["newer", "older"]


def test_a_fresh_brush_with_fewer_uses_outranks_an_older_one_with_more():
    history = History()
    for _ in range(3):
        history.touch("two-days", NOW - 2 * DAY)          # 3 x 0.5 = 1.5
    for _ in range(2):
        history.touch("half-hour", NOW - 30 * MINUTE)     # 2 x 4 = 8

    assert history.names(NOW) == ["half-hour", "two-days"]


def test_an_old_brush_needs_over_sixteen_times_the_uses_to_beat_a_fresh_one():
    history = History()
    for _ in range(17):
        history.touch("old", NOW - 2 * WEEK)              # 17 x 0.25 = 4.25
    history.touch("fresh", NOW - 30 * MINUTE)             # 1 x 4 = 4

    assert history.names(NOW) == ["old", "fresh"]


def test_fifteen_old_uses_are_not_enough_against_one_fresh_use():
    history = History()
    for _ in range(15):
        history.touch("old", NOW - 2 * WEEK)              # 15 x 0.25 = 3.75
    history.touch("fresh", NOW - 30 * MINUTE)             # 1 x 4 = 4

    assert history.names(NOW) == ["fresh", "old"]


def test_ranking_is_recomputed_for_the_now_it_is_asked_about():
    history = History()
    for _ in range(3):
        history.touch("fading", NOW - 50 * MINUTE)        # 3 x 4 = 12 now, 3 x 2 = 6 in 15 min
    for _ in range(2):
        history.touch("holding", NOW - 30 * MINUTE)       # 2 x 4 = 8 now, still 8 in 15 min

    assert history.names(NOW) == ["fading", "holding"]
    assert history.names(NOW + 15 * MINUTE) == ["holding", "fading"]


def test_a_use_in_the_future_still_ranks():
    history = History()
    history.touch("clock-skew", NOW + 2 * DAY)

    assert history.names(NOW) == ["clock-skew"]


# --- limit --------------------------------------------------------------------

def test_default_limit_is_twenty():
    assert DEFAULT_LIMIT == 20
    assert History().limit == 20


def _touch_in_order(history, names, start=NOW - 30 * MINUTE):
    for offset, name in enumerate(names):
        history.touch(name, start + offset * MINUTE)


def test_names_shows_only_the_top_limit_names():
    history = History(limit=3)
    _touch_in_order(history, ["a", "b", "c", "d"])

    assert history.names(NOW) == ["d", "c", "b"]


def test_a_smaller_limit_hides_names_without_forgetting_them():
    history = History(limit=10)
    _touch_in_order(history, ["a", "b", "c", "d"])

    history.set_limit(2)
    assert history.limit == 2
    assert history.names(NOW) == ["d", "c"]

    history.set_limit(10)
    assert history.names(NOW) == ["d", "c", "b", "a"]


def test_limit_is_never_below_one():
    history = History(limit=0)
    assert history.limit == 1

    history.set_limit(-5)
    assert history.limit == 1


def test_clamped_limit_is_the_one_actually_enforced():
    history = History(limit=0)

    history.touch("a", NOW - 2 * MINUTE)
    assert history.names(NOW) == ["a"]

    history.set_limit(-5)
    history.touch("b", NOW - MINUTE)
    assert history.names(NOW) == ["b"]


def test_unusable_limit_falls_back_to_default():
    assert History(limit=None).limit == DEFAULT_LIMIT
    assert History(limit="abc").limit == DEFAULT_LIMIT
    assert History(limit=float("inf")).limit == DEFAULT_LIMIT


def test_limit_is_capped_at_max():
    assert History(limit=10 ** 1000).limit == MAX_LIMIT
    assert History(limit=MAX_LIMIT + 1).limit == MAX_LIMIT


# --- sort mode ------------------------------------------------------------------

def test_default_sort_is_smart():
    assert DEFAULT_SORT == "smart"
    assert History().sort == "smart"


def test_sort_can_be_chosen_at_construction_and_changed_later():
    history = History(sort=SORT_RECENT)
    assert history.sort == "recent"

    history.set_sort(SORT_SMART)
    assert history.sort == "smart"


def test_unknown_sorts_fall_back_to_smart():
    assert History(sort="random").sort == "smart"
    assert History(sort=None).sort == "smart"
    assert History(sort=3).sort == "smart"
    assert History(sort=["recent"]).sort == "smart"

    history = History(sort=SORT_RECENT)
    history.set_sort("bogus")
    assert history.sort == "smart"


def test_recent_orders_by_last_use_and_ignores_the_score():
    history = History(sort=SORT_RECENT)
    for _ in range(5):
        history.touch("often", NOW - 10 * MINUTE)
    history.touch("lately", NOW - 2 * MINUTE)

    assert history.names(NOW) == ["lately", "often"]
    assert history.names(NOW + WEEK) == ["lately", "often"]


def test_smart_and_recent_disagree_on_the_same_entries():
    history = History()
    for _ in range(5):
        history.touch("often", NOW - 10 * MINUTE)
    history.touch("lately", NOW - 2 * MINUTE)

    assert history.names(NOW) == ["often", "lately"]
    history.set_sort(SORT_RECENT)
    assert history.names(NOW) == ["lately", "often"]


def test_recent_breaks_ties_alphabetically():
    history = History(sort=SORT_RECENT)
    history.touch("zeta", NOW)
    history.touch("alpha", NOW)
    history.touch("mid", NOW)

    assert history.names(NOW) == ["alpha", "mid", "zeta"]


def test_limit_applies_in_recent_mode():
    history = History(limit=2, sort=SORT_RECENT)
    _touch_in_order(history, ["a", "b", "c", "d"])

    assert history.names(NOW) == ["d", "c"]


# --- ignore / restore / clear -------------------------------------------------

def test_ignore_removes_the_name_from_the_ranking_and_lists_it():
    history = History()
    _touch_in_order(history, ["a", "eraser"])

    history.ignore("eraser")

    assert history.names(NOW) == ["a"]
    assert history.ignored_names() == ["eraser"]


def test_touch_of_an_ignored_name_is_refused():
    history = History()
    history.ignore("eraser")

    assert history.touch("eraser", NOW) is False
    assert history.names(NOW) == []


def test_ignore_of_blank_names_is_refused():
    history = History()

    history.ignore("")
    history.ignore(None)

    assert history.ignored_names() == []


def test_ignored_names_are_sorted_and_unique():
    history = History()
    history.ignore("b")
    history.ignore("a")
    history.ignore("b")

    assert history.ignored_names() == ["a", "b"]


def test_restore_forgets_the_name_and_a_later_touch_starts_from_one():
    history = History()
    for _ in range(3):
        history.touch("a", NOW - 30 * MINUTE)
    for _ in range(2):
        history.touch("b", NOW - 20 * MINUTE)

    history.ignore("a")
    history.restore("a")
    history.touch("a", NOW - MINUTE)

    assert history.ignored_names() == []
    assert history.names(NOW) == ["b", "a"]


def test_restore_of_an_unknown_name_is_a_no_op():
    history = History()
    history.ignore("a")

    history.restore("never ignored")

    assert history.ignored_names() == ["a"]


def test_clear_empties_the_ranking_but_keeps_limit_and_ignored():
    history = History(limit=7)
    _touch_in_order(history, ["a", "b"])
    history.ignore("eraser")

    history.clear()

    assert history.names(NOW) == []
    assert history.limit == 7
    assert history.ignored_names() == ["eraser"]


# --- persistence --------------------------------------------------------------

def test_save_then_load_round_trips_entries_ignored_and_limit(tmp_path):
    path = tmp_path / "history.json"
    history = History(limit=3)
    for _ in range(3):
        history.touch("often", NOW - 2 * DAY)
    history.touch("lately", NOW - 30 * MINUTE)
    history.ignore("eraser")

    history.save(path)
    loaded = History.load(path)

    assert loaded.names(NOW) == ["lately", "often"]
    assert loaded.names(NOW + WEEK) == ["often", "lately"]
    assert loaded.limit == 3
    assert loaded.ignored_names() == ["eraser"]


def test_saved_file_has_the_documented_shape(tmp_path):
    path = tmp_path / "history.json"
    history = History()
    history.touch("a", NOW)
    history.ignore("e")
    history.ignore("b")

    history.save(path)

    assert json.loads(path.read_text(encoding="utf-8")) == {
        "limit": 20,
        "entries": {"a": {"score": 1.0, "last_used": NOW}},
        "ignored": ["b", "e"],
    }


def test_touch_again_adds_one_and_moves_last_used(tmp_path):
    path = tmp_path / "history.json"
    history = History()
    history.touch("a", NOW - DAY)
    history.touch("a", NOW)

    history.save(path)

    entries = json.loads(path.read_text(encoding="utf-8"))["entries"]
    assert entries == {"a": {"score": 2.0, "last_used": NOW}}


def test_save_writes_unicode_names_as_utf8_bytes(tmp_path):
    path = tmp_path / "history.json"
    history = History()
    history.touch("Watercolour Brush — nº 3 ✨", NOW)
    history.ignore("Borracha — macia ✨")

    history.save(path)

    payload = json.loads(path.read_bytes().decode("utf-8"))
    assert list(payload["entries"]) == ["Watercolour Brush — nº 3 ✨"]
    assert payload["ignored"] == ["Borracha — macia ✨"]
    loaded = History.load(path)
    assert loaded.names(NOW) == ["Watercolour Brush — nº 3 ✨"]
    assert loaded.ignored_names() == ["Borracha — macia ✨"]


def test_save_leaves_no_temporary_file_behind(tmp_path):
    path = tmp_path / "history.json"
    history = History()
    history.touch("a", NOW)

    history.save(path)

    assert sorted(entry.name for entry in tmp_path.iterdir()) == ["history.json"]


def test_save_creates_missing_parent_directory(tmp_path):
    path = tmp_path / "sub" / "dir" / "history.json"
    history = History()
    history.touch("a", NOW)

    history.save(path)

    assert History.load(path).names(NOW) == ["a"]


def test_failed_save_keeps_the_previous_file_intact(tmp_path, monkeypatch):
    path = tmp_path / "history.json"
    saved = History()
    saved.touch("a", NOW)
    saved.save(path)

    def explode(*args, **kwargs):
        raise RuntimeError("disk full")

    monkeypatch.setattr("recent_brushes.history.json.dump", explode)
    saved.touch("b", NOW)
    with pytest.raises(RuntimeError):
        saved.save(path)

    assert History.load(path).names(NOW) == ["a"]
    assert sorted(entry.name for entry in tmp_path.iterdir()) == ["history.json"]


def test_save_writes_its_temporary_file_on_the_destination_filesystem(tmp_path, monkeypatch):
    path = tmp_path / "sub" / "history.json"
    directories = []
    real_mkstemp = tempfile.mkstemp

    def spy(*args, **kwargs):
        directories.append(kwargs["dir"])
        return real_mkstemp(*args, **kwargs)

    monkeypatch.setattr("recent_brushes.history.tempfile.mkstemp", spy)
    History().save(path)

    assert directories == [str(path.parent)]


def test_load_of_missing_file_returns_empty_history(tmp_path):
    loaded = History.load(tmp_path / "does-not-exist.json")

    assert loaded.names(NOW) == []
    assert loaded.ignored_names() == []
    assert loaded.limit == DEFAULT_LIMIT
    assert not (tmp_path / "does-not-exist.json.bak").exists()


def test_load_of_missing_file_never_attempts_a_quarantine(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr("recent_brushes.history.os.replace", lambda *args: calls.append(args))

    loaded = History.load(tmp_path / "does-not-exist.json")

    assert loaded.names(NOW) == []
    assert calls == []


def _make_path_unreadable_without_corrupting_it(path):
    path.mkdir()


def test_load_of_unreadable_path_leaves_it_alone(tmp_path):
    path = tmp_path / "history.json"
    _make_path_unreadable_without_corrupting_it(path)

    loaded = History.load(path)

    assert loaded.names(NOW) == []
    assert path.is_dir()
    assert not (tmp_path / "history.json.bak").exists()


def test_load_of_corrupt_file_returns_empty_history_and_quarantines(tmp_path):
    path = tmp_path / "history.json"
    path.write_text("{this is not json", encoding="utf-8")

    loaded = History.load(path)

    assert loaded.names(NOW) == []
    assert loaded.limit == DEFAULT_LIMIT
    assert (tmp_path / "history.json.bak").read_text(encoding="utf-8") == "{this is not json"
    assert not path.exists()


def test_load_of_null_payload_is_treated_as_corrupt(tmp_path):
    path = tmp_path / "history.json"
    path.write_text("null", encoding="utf-8")

    loaded = History.load(path)

    assert loaded.names(NOW) == []
    assert (tmp_path / "history.json.bak").read_text(encoding="utf-8") == "null"


def test_load_of_the_previous_names_list_format_is_treated_as_corrupt(tmp_path):
    path = tmp_path / "history.json"
    path.write_text('{"limit": 5, "names": ["a", "b"]}', encoding="utf-8")

    loaded = History.load(path)

    assert loaded.names(NOW) == []
    assert (tmp_path / "history.json.bak").exists()


def test_load_without_an_entries_dict_is_treated_as_corrupt(tmp_path):
    path = tmp_path / "history.json"
    path.write_text('{"limit": 5, "entries": [], "ignored": []}', encoding="utf-8")

    loaded = History.load(path)

    assert loaded.names(NOW) == []
    assert (tmp_path / "history.json.bak").exists()


def test_load_without_an_ignored_list_is_treated_as_corrupt(tmp_path):
    path = tmp_path / "history.json"
    path.write_text('{"limit": 5, "entries": {}, "ignored": "eraser"}', encoding="utf-8")

    loaded = History.load(path)

    assert loaded.names(NOW) == []
    assert (tmp_path / "history.json.bak").exists()


def test_load_of_a_valid_empty_file_does_not_quarantine(tmp_path):
    path = tmp_path / "history.json"
    path.write_text('{"limit": 5, "entries": {}, "ignored": []}', encoding="utf-8")

    loaded = History.load(path)

    assert loaded.names(NOW) == []
    assert loaded.limit == 5
    assert not (tmp_path / "history.json.bak").exists()


def test_load_without_limit_key_keeps_the_entries(tmp_path):
    path = tmp_path / "history.json"
    path.write_text(
        '{"entries": {"a": {"score": 1.0, "last_used": %r}}, "ignored": []}' % NOW,
        encoding="utf-8")

    loaded = History.load(path)

    assert loaded.names(NOW) == ["a"]
    assert loaded.limit == DEFAULT_LIMIT
    assert not (tmp_path / "history.json.bak").exists()


def test_quarantine_does_not_overwrite_an_earlier_backup(tmp_path):
    path = tmp_path / "history.json"
    backup = tmp_path / "history.json.bak"
    backup.write_text('{"limit": 20, "entries": {}, "ignored": ["saved earlier"]}', encoding="utf-8")
    path.write_text("{garbage", encoding="utf-8")

    History.load(path)

    assert backup.read_text(encoding="utf-8") == '{"limit": 20, "entries": {}, "ignored": ["saved earlier"]}'


# --- aging ---------------------------------------------------------------------

def test_aging_scales_scores_and_drops_the_ones_below_one(tmp_path):
    path = tmp_path / "history.json"
    history = History()
    for tick in range(int(MAX_AGE)):
        history.touch("workhorse", NOW - DAY + tick)

    history.touch("once", NOW)
    history.save(path)

    entries = json.loads(path.read_text(encoding="utf-8"))["entries"]
    assert entries["workhorse"]["score"] == pytest.approx(8999.1)   # 10000 x 0.9 x 10000 / 10001
    assert "once" not in entries
    assert history.names(NOW) == ["workhorse"]


def test_a_total_exactly_at_the_ceiling_does_not_age(tmp_path):
    path = tmp_path / "history.json"
    history = History()
    for tick in range(int(MAX_AGE) - 1):
        history.touch("workhorse", NOW - DAY + tick)

    history.touch("once", NOW)
    history.save(path)

    entries = json.loads(path.read_text(encoding="utf-8"))["entries"]
    assert entries["workhorse"]["score"] == MAX_AGE - 1
    assert entries["once"]["score"] == 1.0


def test_a_score_that_lands_exactly_on_the_floor_survives_aging(tmp_path):
    path = tmp_path / "history.json"
    path.write_text(
        '{"limit": 5, "entries": {"big": {"score": 9000, "last_used": 1},'
        ' "big2": {"score": 8997, "last_used": 1},'
        ' "edge": {"score": 2, "last_used": 1}}, "ignored": []}',
        encoding="utf-8")
    history = History.load(path)

    history.touch("new", NOW)                      # total 18000 -> factor exactly 0.5

    assert sorted(history.names(NOW)) == ["big", "big2", "edge"]


def test_a_score_just_under_the_floor_is_dropped_by_aging(tmp_path):
    path = tmp_path / "history.json"
    path.write_text(
        '{"limit": 5, "entries": {"big": {"score": 9000, "last_used": 1},'
        ' "big2": {"score": 8994, "last_used": 1},'
        ' "small": {"score": 1.9, "last_used": 1},'
        ' "edge": {"score": 2, "last_used": 1}}, "ignored": []}',
        encoding="utf-8")
    history = History.load(path)

    history.touch("new", NOW)                      # total 17998.9 -> factor ~0.5

    assert sorted(history.names(NOW)) == ["big", "big2", "edge"]


# --- tolerant reading -----------------------------------------------------------

def test_load_drops_malformed_entry_rows_and_keeps_the_valid_one(tmp_path):
    path = tmp_path / "history.json"
    path.write_text("""{
        "limit": 5,
        "entries": {
            "": {"score": 1, "last_used": 1},
            "not a dict": 5,
            "no score": {"last_used": 1},
            "no last_used": {"score": 1},
            "text score": {"score": "3", "last_used": 1},
            "bool score": {"score": true, "last_used": 1},
            "infinite score": {"score": Infinity, "last_used": 1},
            "zero score": {"score": 0, "last_used": 1},
            "negative score": {"score": -5, "last_used": 1},
            "impossible score": {"score": 10001, "last_used": 1},
            "nan last_used": {"score": 1, "last_used": NaN},
            "ok": {"score": 2, "last_used": 1}
        },
        "ignored": []
    }""", encoding="utf-8")

    loaded = History.load(path)

    assert loaded.names(NOW) == ["ok"]
    assert not (tmp_path / "history.json.bak").exists()


def test_load_drops_non_string_or_blank_ignored_items(tmp_path):
    path = tmp_path / "history.json"
    path.write_text('{"limit": 5, "entries": {}, "ignored": [7, null, "", "a", "a"]}',
                    encoding="utf-8")

    loaded = History.load(path)

    assert loaded.ignored_names() == ["a"]
    assert not (tmp_path / "history.json.bak").exists()


def test_load_drops_rows_with_integers_too_large_for_a_float(tmp_path):
    path = tmp_path / "history.json"
    huge = "1" + "0" * 400
    path.write_text(
        '{"limit": 5, "entries": {"huge score": {"score": %s, "last_used": 1},'
        ' "huge last_used": {"score": 1, "last_used": %s},'
        ' "ok": {"score": 1, "last_used": 1}}, "ignored": []}' % (huge, huge),
        encoding="utf-8")

    loaded = History.load(path)

    assert loaded.names(NOW) == ["ok"]
    assert not (tmp_path / "history.json.bak").exists()


def test_load_keeps_a_name_present_in_both_places_only_as_ignored(tmp_path):
    path = tmp_path / "history.json"
    path.write_text(
        '{"limit": 5, "entries": {"a": {"score": 3, "last_used": 1}}, "ignored": ["a"]}',
        encoding="utf-8")

    loaded = History.load(path)

    assert loaded.names(NOW) == []
    assert loaded.ignored_names() == ["a"]
    assert loaded.touch("a", NOW) is False


def test_load_keeps_a_score_exactly_at_the_ceiling(tmp_path):
    path = tmp_path / "history.json"
    path.write_text(
        '{"limit": 5, "entries": {"a": {"score": 10000, "last_used": 1}}, "ignored": []}',
        encoding="utf-8")

    loaded = History.load(path)

    assert loaded.names(NOW) == ["a"]


def test_load_keeps_scores_below_one_until_aging(tmp_path):
    path = tmp_path / "history.json"
    path.write_text(
        '{"limit": 5, "entries": {"a": {"score": 0.5, "last_used": 1}}, "ignored": []}',
        encoding="utf-8")

    loaded = History.load(path)

    assert loaded.names(NOW) == ["a"]
