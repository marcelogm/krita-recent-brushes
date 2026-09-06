import importlib
import os
import sys
import types
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt6.QtCore import QObject, pyqtSignal
    from PyQt6.QtGui import QImage
except ImportError:
    from PyQt5.QtCore import QObject, pyqtSignal
    from PyQt5.QtGui import QImage

ROOT = Path(__file__).resolve().parent.parent
PLUGIN_PACKAGE = "recent_brushes"
PLUGIN_DIR = ROOT / "pykrita" / PLUGIN_PACKAGE
PLUGIN_MODULES = ("recent_brushes.docker", "recent_brushes.ignored_dialog",
                  "recent_brushes.tracker", "recent_brushes.history")


class FakePreset:
    def __init__(self, name, image=None):
        self._name = name
        self._image = QImage() if image is None else image

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


class FakeNotifier(QObject):
    applicationClosing = pyqtSignal()


class FakeKrita(QObject):
    def __init__(self):
        super().__init__()
        self.window = None
        self.presets = {}
        self.notifier_object = FakeNotifier()

    def activeWindow(self):
        return self.window

    def resources(self, resource_type):
        assert resource_type == "preset"
        return self.presets

    def notifier(self):
        return self.notifier_object


def install_fake_krita(monkeypatch, log_to=None, dock_widget=None):
    krita_stub = types.ModuleType("krita")
    krita_stub.Extension = type("Extension", (QObject,), {})
    fake_krita = FakeKrita()
    krita_stub.Krita = types.SimpleNamespace(instance=lambda: fake_krita)
    krita_stub.qDebug = (lambda text: None) if log_to is None else log_to.append
    if dock_widget is not None:
        krita_stub.DockWidget = dock_widget
    monkeypatch.setitem(sys.modules, "krita", krita_stub)
    return fake_krita


def _plugin_package():
    """A stand-in for the package whose __init__ imports `krita`."""
    package = types.ModuleType(PLUGIN_PACKAGE)
    package.__path__ = [str(PLUGIN_DIR)]
    return package


def install_plugin_package():
    sys.modules[PLUGIN_PACKAGE] = _plugin_package()


def import_plugin_modules(monkeypatch, *names):
    monkeypatch.setitem(sys.modules, PLUGIN_PACKAGE, _plugin_package())
    for module in PLUGIN_MODULES:
        monkeypatch.delitem(sys.modules, module, raising=False)
    return [importlib.import_module(PLUGIN_PACKAGE + "." + name) for name in names]


def forget_plugin_modules_imported_outside_monkeypatch():
    for module in PLUGIN_MODULES:
        sys.modules.pop(module, None)
