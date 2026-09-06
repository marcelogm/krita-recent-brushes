import types

import pytest

import fakes
from fakes import FakeKrita, QtWidgets
from recent_brushes import docker, ignored_dialog, tracker as tracker_module


@pytest.fixture(scope="session")
def qt_app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture
def krita(qt_app, tmp_path, monkeypatch):
    """A fresh Krita, an empty log and no tracker singleton for each test."""
    fake = FakeKrita()
    monkeypatch.setattr(fakes.current, "krita", fake)
    monkeypatch.setattr(fakes.current, "logged", [])
    monkeypatch.setattr(tracker_module, "_TRACKER", None)
    monkeypatch.setattr(tracker_module, "history_path",
                        lambda: str(tmp_path / "history.json"))
    return fake


@pytest.fixture
def tracker(krita, tmp_path):
    instance = tracker_module.RecentBrushesTracker()
    instance.krita = krita
    instance.module = tracker_module
    instance.path = tmp_path / "history.json"
    instance.notifier = krita.notifier_object
    instance.logged = fakes.current.logged
    return instance


@pytest.fixture
def env(krita, tmp_path):
    return types.SimpleNamespace(
        krita=krita,
        tracker_module=tracker_module,
        docker_module=docker,
        dialog_module=ignored_dialog,
        path=tmp_path / "history.json",
        logged=fakes.current.logged,
    )
