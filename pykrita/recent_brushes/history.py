import json
import math
import os
import tempfile
from dataclasses import dataclass

DEFAULT_LIMIT = 20
MAX_LIMIT = 100
SORT_SMART = "smart"
SORT_RECENT = "recent"
SORTS = (SORT_SMART, SORT_RECENT)
DEFAULT_SORT = SORT_SMART
BACKUP_SUFFIX = ".bak"
TEMPORARY_PREFIX = ".recent-brushes-"
TEMPORARY_SUFFIX = ".tmp"

HOUR = 3600.0
DAY = 24 * HOUR
WEEK = 7 * DAY
RECENCY_BUCKETS = ((HOUR, 4.0), (DAY, 2.0), (WEEK, 0.5))
OLDEST_FACTOR = 0.25

MAX_AGE = 10_000.0
AGING_KEEPS = 0.9
MIN_SCORE = 1.0


@dataclass
class Entry:
    score: float
    last_used: float


def recency_factor(age):
    for ceiling, factor in RECENCY_BUCKETS:
        if age < ceiling:
            return factor
    return OLDEST_FACTOR


def _frecency(entry, now):
    return entry.score * recency_factor(now - entry.last_used)


def _sane_limit(limit):
    try:
        return max(1, min(MAX_LIMIT, int(limit)))
    except (TypeError, ValueError, OverflowError):
        return DEFAULT_LIMIT


def _sane_sort(sort):
    return sort if sort in SORTS else DEFAULT_SORT


def _read_payload(path):
    with open(path, encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload.get("entries"), dict):
        raise ValueError("entries")
    if not isinstance(payload.get("ignored"), list):
        raise ValueError("ignored")
    return payload


def _is_finite_number(value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _entries_from(rows, ignored):
    entries = {}
    for name, row in rows.items():
        if not name or name in ignored or not isinstance(row, dict):
            continue
        score = row.get("score")
        last_used = row.get("last_used")
        if (_is_finite_number(score) and 0 < score <= MAX_AGE
                and _is_finite_number(last_used)):
            entries[name] = Entry(float(score), float(last_used))
    return entries


def _ignored_from(items):
    return {item for item in items if isinstance(item, str) and item}


def _write_beside_then_replace(path, payload):
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        dir=directory, prefix=TEMPORARY_PREFIX, suffix=TEMPORARY_SUFFIX)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)
        os.replace(temporary, path)
    except BaseException:
        _delete_if_present(temporary)
        raise


def _delete_if_present(path):
    if os.path.exists(path):
        os.remove(path)


def _quarantine_keeping_earlier_backup(path):
    try:
        backup = os.fspath(path) + BACKUP_SUFFIX
        if os.path.exists(backup):
            return
        os.replace(path, backup)
    except Exception:
        pass


class History:

    def __init__(self, limit=DEFAULT_LIMIT, sort=DEFAULT_SORT):
        self._limit = _sane_limit(limit)
        self._sort = _sane_sort(sort)
        self._entries = {}
        self._ignored = set()

    @property
    def limit(self):
        return self._limit

    @property
    def sort(self):
        return self._sort

    def names(self, now):
        by_name = sorted(self._entries.items())
        ranked = sorted(by_name, key=self._rank_key(now), reverse=True)
        return [name for name, _ in ranked[:self._limit]]

    def _rank_key(self, now):
        if self._sort == SORT_RECENT:
            return lambda item: item[1].last_used
        return lambda item: (_frecency(item[1], now), item[1].last_used)

    def touch(self, name, now):
        if not name or name in self._ignored:
            return False
        entry = self._entries.get(name)
        if entry is None:
            self._entries[name] = Entry(1.0, now)
        else:
            entry.score += 1.0
            entry.last_used = now
        self._age_if_needed()
        return True

    def _age_if_needed(self):
        total = sum(entry.score for entry in self._entries.values())
        if total <= MAX_AGE:
            return
        factor = AGING_KEEPS * MAX_AGE / total
        for entry in self._entries.values():
            entry.score *= factor
        self._entries = {name: entry for name, entry in self._entries.items()
                         if entry.score >= MIN_SCORE}

    def ignore(self, name):
        if not name:
            return
        self._ignored.add(name)
        self._entries.pop(name, None)

    def restore(self, name):
        self._ignored.discard(name)

    def ignored_names(self):
        return sorted(self._ignored)

    def set_limit(self, limit):
        self._limit = _sane_limit(limit)

    def set_sort(self, sort):
        self._sort = _sane_sort(sort)

    def clear(self):
        self._entries = {}

    def save(self, path):
        _write_beside_then_replace(os.fspath(path), {
            "limit": self._limit,
            "entries": {
                name: {"score": entry.score, "last_used": entry.last_used}
                for name, entry in self._entries.items()},
            "ignored": sorted(self._ignored),
        })

    @classmethod
    def load(cls, path):
        try:
            path = os.fspath(path)
            payload = _read_payload(path)
        except OSError:
            return cls()
        except Exception:
            _quarantine_keeping_earlier_backup(path)
            return cls()
        history = cls(payload.get("limit"))
        ignored = _ignored_from(payload["ignored"])
        history._ignored = ignored
        history._entries = _entries_from(payload["entries"], ignored)
        return history
