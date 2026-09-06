from .qt import QtWidgets

DIALOG_TITLE = "Ignored brushes"
RESTORE_LABEL = "Restore"
CLOSE_LABEL = "Close"


class IgnoredBrushesDialog(QtWidgets.QDialog):

    def __init__(self, tracker, parent=None):
        super().__init__(parent)
        self.setWindowTitle(DIALOG_TITLE)
        self._tracker = tracker
        self._list = QtWidgets.QListWidget()
        self._list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self._restore_button = QtWidgets.QPushButton(RESTORE_LABEL)
        self._close_button = QtWidgets.QPushButton(CLOSE_LABEL)

        self._list.itemSelectionChanged.connect(self._update_restore_button)
        self._restore_button.clicked.connect(self._on_restore)
        self._close_button.clicked.connect(self.accept)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(self._restore_button)
        buttons.addWidget(self._close_button)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self._list)
        layout.addLayout(buttons)

        self._reload()

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
