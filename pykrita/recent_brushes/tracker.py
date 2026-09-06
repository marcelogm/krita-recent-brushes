"""Records which brush preset is active.

Krita has no signal for "the current preset changed", so while a docker is
visible this polls the active view a few times per second and touches the
history whenever the preset name differs from the last one seen.
"""

import os
import time

from krita import Extension, Krita, qDebug

from .history import History
from .qt import QtCore

POLL_INTERVAL_MS = 300
MAX_CONSECUTIVE_ERRORS = 20
KRITA_DATA_DIR = "~/.local/share/krita"
HISTORY_FILE_NAME = "recent_brushes_history.json"


def history_path():
    return os.path.join(os.path.expanduser(KRITA_DATA_DIR), HISTORY_FILE_NAME)


class RecentBrushesTracker(Extension):

    changed = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._path = history_path()
        self.history = History()
        self._loaded = False
        self._last_name = None
        self._last_error = None
        self._errors = 0
        self._viewers = set()
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(POLL_INTERVAL_MS)
        self._timer.timeout.connect(self.tick)

    def setup(self):
        self._ensure_loaded()
        self._stop_timer_on_shutdown()
        self.changed.emit()

    def createActions(self, window):
        pass

    @property
    def limit(self):
        self._ensure_loaded()
        return self.history.limit

    def names(self):
        self._ensure_loaded()
        return self.history.names(time.time())

    def is_polling(self):
        return self._timer.isActive()

    def tick(self):
        try:
            self._record_active_preset()
        except Exception as error:
            self._note_error(error)
            return
        self._forget_errors()

    def attach_viewer(self, viewer):
        self._viewers.add(id(viewer))
        self._forget_errors()
        if not self._timer.isActive():
            self._timer.start()

    def detach_viewer(self, viewer):
        self.detach_viewer_key(id(viewer))

    def detach_viewer_key(self, key):
        self._viewers.discard(key)
        if not self._viewers:
            self._stop_timer_even_if_already_destroyed()

    def set_limit(self, limit):
        self._ensure_loaded()
        self.history.set_limit(limit)
        self._persist()

    def clear(self):
        self._ensure_loaded()
        self.history.clear()
        self._last_name = None
        self._persist()

    def ignored_names(self):
        self._ensure_loaded()
        return self.history.ignored_names()

    def ignore(self, name):
        self._ensure_loaded()
        self.history.ignore(name)
        if name == self._last_name:
            self._last_name = None
        self._persist()

    def restore(self, name):
        self._ensure_loaded()
        self.history.restore(name)
        self._persist()

    def _persist(self):
        try:
            self.history.save(self._path)
        except Exception as error:
            qDebug("recent_brushes: could not save the history: {!r}".format(error))
        self.changed.emit()

    def _ensure_loaded(self):
        if self._loaded:
            return
        self.history = History.load(self._path)
        self._loaded = True

    def _stop_timer_on_shutdown(self):
        notifier = Krita.instance().notifier()
        if notifier is not None:
            notifier.applicationClosing.connect(self._timer.stop)

    def _stop_timer_even_if_already_destroyed(self):
        try:
            self._timer.stop()
        except RuntimeError:
            pass

    def _active_preset(self):
        window = Krita.instance().activeWindow()
        if window is None:
            return None
        view = window.activeView()
        if view is None:
            return None
        return view.currentBrushPreset()

    def _record_active_preset(self):
        self._ensure_loaded()
        preset = self._active_preset()
        if preset is None:
            return
        name = preset.name()
        if not name or name == self._last_name:
            return
        if not self.history.touch(name, time.time()):
            return
        self._last_name = name
        self._persist()

    def _forget_errors(self):
        self._errors = 0
        self._last_error = None

    def _note_error(self, error):
        self._log_unless_repeated(repr(error))
        self._errors += 1
        if self._errors >= MAX_CONSECUTIVE_ERRORS:
            self._give_up_polling()

    def _log_unless_repeated(self, message):
        if message == self._last_error:
            return
        self._last_error = message
        qDebug("recent_brushes: polling error: " + message)

    def _give_up_polling(self):
        self._timer.stop()
        qDebug("recent_brushes: polling stopped after {} consecutive errors"
               .format(self._errors))


_TRACKER = None


def get_tracker():
    global _TRACKER
    if _TRACKER is None:
        _TRACKER = RecentBrushesTracker(Krita.instance())
    return _TRACKER
