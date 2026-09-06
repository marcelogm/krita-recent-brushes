"""Krita 5.2 ships PyQt5; newer builds ship PyQt6. Import whichever is there."""

try:
    from PyQt6 import QtCore, QtGui, QtWidgets
except ImportError:
    from PyQt5 import QtCore, QtGui, QtWidgets

__all__ = ["QtCore", "QtGui", "QtWidgets"]
