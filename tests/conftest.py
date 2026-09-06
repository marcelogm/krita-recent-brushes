import os
import types

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

try:
    from PyQt6.QtWidgets import QApplication, QDockWidget
except ImportError:
    from PyQt5.QtWidgets import QApplication, QDockWidget

from fakes import (forget_plugin_modules_imported_outside_monkeypatch,
                   import_plugin_modules, install_fake_krita)


@pytest.fixture(scope="session")
def qt_app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def tracker(qt_app, tmp_path, monkeypatch):
    logged = []
    fake_krita = install_fake_krita(monkeypatch, log_to=logged)
    module, = import_plugin_modules(monkeypatch, "tracker")
    path = tmp_path / "history.json"
    monkeypatch.setattr(module, "history_path", lambda: str(path))

    instance = module.RecentBrushesTracker()
    instance.krita = fake_krita
    instance.module = module
    instance.path = path
    instance.notifier = fake_krita.notifier_object
    instance.logged = logged
    yield instance

    forget_plugin_modules_imported_outside_monkeypatch()


@pytest.fixture
def env(qt_app, tmp_path, monkeypatch):
    logged = []
    fake_krita = install_fake_krita(monkeypatch, log_to=logged, dock_widget=QDockWidget)
    tracker_module, docker_module, dialog_module = import_plugin_modules(
        monkeypatch, "tracker", "docker", "ignored_dialog")
    path = tmp_path / "history.json"
    monkeypatch.setattr(tracker_module, "history_path", lambda: str(path))
    tracker_module._TRACKER = None

    yield types.SimpleNamespace(
        krita=fake_krita,
        tracker_module=tracker_module,
        docker_module=docker_module,
        dialog_module=dialog_module,
        path=path,
        logged=logged,
    )

    forget_plugin_modules_imported_outside_monkeypatch()
