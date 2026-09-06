"""Everything needed to run the plugin outside Krita.

Importing this module registers two things in `sys.modules`:

- `recent_brushes`, pointing at `pykrita/recent_brushes` but skipping its
  `__init__.py`, which registers the plugin with Krita at import time;
- `krita`, a stub whose `Krita.instance()` returns whatever `FakeKrita` the
  current test installed through the `krita` fixture.
"""

import os
import sys
import types
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt6 import QtCore, QtGui, QtTest, QtWidgets
except ImportError:
    from PyQt5 import QtCore, QtGui, QtTest, QtWidgets

__all__ = ["QtCore", "QtGui", "QtTest", "QtWidgets"]

PLUGIN_DIR = Path(__file__).resolve().parent.parent / "pykrita" / "recent_brushes"


class FakePreset:
    def __init__(self, name, image=None):
        self._name = name
        self._image = QtGui.QImage() if image is None else image

    def name(self):
        return self._name

    def image(self):
        return self._image


class FakeView:
    def __init__(self, preset=None):
        self.preset = preset
        self.activated = []

    def currentBrushPreset(self):
        return self.preset

    def setCurrentBrushPreset(self, resource):
        self.activated.append(resource)


class FakeWindow:
    def __init__(self, view=None):
        self.view = view

    def activeView(self):
        return self.view


class FakeNotifier(QtCore.QObject):
    applicationClosing = QtCore.pyqtSignal()


class FakeKrita(QtCore.QObject):
    def __init__(self):
        super().__init__()
        self.window = None
        self.presets = {}
        self.notifier_object = FakeNotifier()
        self.icons_requested = []
        self.icons = {}

    def activeWindow(self):
        return self.window

    def resources(self, resource_type):
        assert resource_type == "preset"
        return self.presets

    def notifier(self):
        return self.notifier_object

    def icon(self, name):
        self.icons_requested.append(name)
        return self.icons.get(name, QtGui.QIcon())


current = types.SimpleNamespace(krita=None, logged=[])


def _krita_stub():
    stub = types.ModuleType("krita")
    stub.Extension = type("Extension", (QtCore.QObject,), {})
    stub.DockWidget = QtWidgets.QDockWidget
    stub.Krita = types.SimpleNamespace(instance=lambda: current.krita)
    stub.qDebug = lambda text: current.logged.append(text)
    return stub


def _plugin_package():
    package = types.ModuleType("recent_brushes")
    package.__path__ = [str(PLUGIN_DIR)]
    return package


sys.modules.setdefault("krita", _krita_stub())
sys.modules.setdefault("recent_brushes", _plugin_package())
