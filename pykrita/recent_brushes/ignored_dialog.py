try:
    from PyQt6.QtWidgets import (QAbstractItemView, QDialog, QHBoxLayout, QListWidget,
                                 QPushButton, QVBoxLayout)
except ImportError:
    from PyQt5.QtWidgets import (QAbstractItemView, QDialog, QHBoxLayout, QListWidget,
                                 QPushButton, QVBoxLayout)

DIALOG_TITLE = "Ignored brushes"
RESTORE_LABEL = "Restore"
CLOSE_LABEL = "Close"


class IgnoredBrushesDialog(QDialog):

    def __init__(self, tracker, parent=None):
        super().__init__(parent)
        self.setWindowTitle(DIALOG_TITLE)
        self._tracker = tracker
        self._list = QListWidget()
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._restore_button = QPushButton(RESTORE_LABEL)
        self._close_button = QPushButton(CLOSE_LABEL)

        self._list.itemSelectionChanged.connect(self._update_restore_button)
        self._restore_button.clicked.connect(self._on_restore)
        self._close_button.clicked.connect(self.accept)

        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(self._restore_button)
        buttons.addWidget(self._close_button)
        layout = QVBoxLayout(self)
        layout.addWidget(self._list)
        layout.addLayout(buttons)

        self._reload()

    def names(self):
        return [self._list.item(row).text() for row in range(self._list.count())]

    def _reload(self):
        self._list.clear()
        for name in self._tracker.ignored_names():
            self._list.addItem(name)
        self._update_restore_button()

    def _update_restore_button(self):
        self._restore_button.setEnabled(bool(self._list.selectedItems()))

    def _on_restore(self):
        selected = self._list.selectedItems()
        if not selected:
            return
        self._tracker.restore(selected[0].text())
        self._reload()
