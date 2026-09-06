from krita import DockWidget, Krita, qDebug

from .history import MAX_LIMIT
from .ignored_dialog import IgnoredBrushesDialog
from .qt import QtCore, QtGui, QtWidgets
from .tracker import get_tracker

TITLE = "Recent Brushes"
LIMIT_LABEL = "Max:"
CLEAR_TOOLTIP = "Clear history"
IGNORED_TOOLTIP = "Ignored brushes ({})…"
SETTINGS_TOOLTIP = "Settings"
NO_MENU_ARROW = "QToolButton::menu-indicator { image: none; }"
PRESET_RESOURCE_TYPE = "preset"
ICON_SIZE = 48
NAME_ROLE = QtCore.Qt.ItemDataRole.UserRole
IGNORE_ACTION_LABEL = 'Ignore "{}"'

CLEAR_ICONS = ("edit-clear", "deletelayer")
IGNORED_ICONS = ("novisible", "hidden")
SETTINGS_ICONS = ("configure",)
CLEAR_FALLBACK = QtWidgets.QStyle.StandardPixmap.SP_TrashIcon
IGNORED_FALLBACK = QtWidgets.QStyle.StandardPixmap.SP_DialogCancelButton
SETTINGS_FALLBACK = QtWidgets.QStyle.StandardPixmap.SP_FileDialogDetailedView


class RecentBrushesDocker(DockWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle(TITLE)
        self._tracker = get_tracker()
        self._icons = {}
        self._presets = {}
        self._attached = False
        self._limit_box = self._build_limit_box()
        self._ignored_button = self._build_tool_button(
            IGNORED_ICONS, IGNORED_FALLBACK, IGNORED_TOOLTIP.format(0), self._on_show_ignored)
        self._clear_button = self._build_tool_button(
            CLEAR_ICONS, CLEAR_FALLBACK, CLEAR_TOOLTIP, self._on_clear)
        self._settings_button = self._build_settings_button()
        self._model = QtGui.QStandardItemModel()
        self._list = self._build_grid()
        self.setWidget(self._build_body())
        self._tracker.changed.connect(self.refresh)
        self._detach_when_destroyed()
        self.refresh()

    def canvasChanged(self, canvas):
        pass

    def showEvent(self, event):
        super().showEvent(event)
        if not self._attached:
            self._attached = True
            self._tracker.attach_viewer(self)

    def hideEvent(self, event):
        super().hideEvent(event)
        if self._attached:
            self._attached = False
            self._tracker.detach_viewer(self)

    def refresh(self):
        try:
            self._rebuild()
        except Exception as error:
            qDebug("recent_brushes: error while drawing the docker: {!r}".format(error))

    def _build_limit_box(self):
        box = QtWidgets.QSpinBox()
        box.setRange(1, MAX_LIMIT)
        box.setKeyboardTracking(False)
        box.setValue(self._tracker.limit)
        box.valueChanged.connect(self._on_limit_changed)
        return box

    def _build_tool_button(self, icon_names, fallback, tooltip, on_click):
        button = QtWidgets.QToolButton()
        button.setAutoRaise(True)
        button.setIcon(self._theme_icon(icon_names, fallback))
        button.setToolTip(tooltip)
        button.clicked.connect(on_click)
        return button

    def _theme_icon(self, icon_names, fallback):
        for name in icon_names:
            icon = Krita.instance().icon(name)
            if not icon.isNull():
                return icon
        return self.style().standardIcon(fallback)

    def _build_settings_button(self):
        button = QtWidgets.QToolButton()
        button.setAutoRaise(True)
        button.setIcon(self._theme_icon(SETTINGS_ICONS, SETTINGS_FALLBACK))
        button.setToolTip(SETTINGS_TOOLTIP)
        button.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
        button.setStyleSheet(NO_MENU_ARROW)
        button.setMenu(self._build_settings_menu())
        return button

    def _build_settings_menu(self):
        row = QtWidgets.QWidget()
        row_layout = QtWidgets.QHBoxLayout(row)
        row_layout.addWidget(QtWidgets.QLabel(LIMIT_LABEL))
        row_layout.addWidget(self._limit_box)
        action = QtWidgets.QWidgetAction(self)
        action.setDefaultWidget(row)
        menu = QtWidgets.QMenu(self)
        menu.addAction(action)
        return menu

    def _build_grid(self):
        grid = QtWidgets.QListView()
        grid.setViewMode(QtWidgets.QListView.ViewMode.IconMode)
        grid.setMovement(QtWidgets.QListView.Movement.Static)
        grid.setResizeMode(QtWidgets.QListView.ResizeMode.Adjust)
        grid.setUniformItemSizes(True)
        grid.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        grid.setIconSize(QtCore.QSize(ICON_SIZE, ICON_SIZE))
        grid.setModel(self._model)
        grid.clicked.connect(self._on_clicked)
        grid.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        grid.customContextMenuRequested.connect(self._on_context_menu)
        return grid

    def _build_body(self):
        top_row = QtWidgets.QHBoxLayout()
        top_row.addStretch()
        top_row.addWidget(self._ignored_button)
        top_row.addWidget(self._clear_button)
        top_row.addWidget(self._settings_button)

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(top_row)
        layout.addWidget(self._list)
        body = QtWidgets.QWidget()
        body.setLayout(layout)
        return body

    def _detach_when_destroyed(self):
        tracker = self._tracker
        key = id(self)
        self.destroyed.connect(lambda *_: tracker.detach_viewer_key(key))

    def _rebuild(self):
        self._presets = Krita.instance().resources(PRESET_RESOURCE_TYPE)
        self._mirror_limit_from_tracker()
        self._ignored_button.setToolTip(
            IGNORED_TOOLTIP.format(len(self._tracker.ignored_names())))
        names = self._tracker.names()
        self._model.clear()
        for name in names:
            resource = self._presets.get(name)
            if resource is not None:
                self._model.appendRow(self._item_for(name, resource))
        self._drop_icons_outside(names)

    def _item_for(self, name, resource):
        item = QtGui.QStandardItem()
        item.setEditable(False)
        item.setToolTip(name)
        item.setData(name, NAME_ROLE)
        item.setIcon(self._icon_for(name, resource))
        return item

    def _drop_icons_outside(self, names):
        still_listed = set(names)
        self._icons = {name: icon for name, icon in self._icons.items()
                       if name in still_listed}

    def _mirror_limit_from_tracker(self):
        limit = self._tracker.limit
        if self._limit_box.value() == limit:
            return
        self._limit_box.blockSignals(True)
        self._limit_box.setValue(limit)
        self._limit_box.blockSignals(False)

    def _icon_for(self, name, resource):
        if name not in self._icons:
            self._icons[name] = self._render_icon(resource)
        return self._icons[name]

    def _render_icon(self, resource):
        image = resource.image()
        if image is None or image.isNull():
            return self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileIcon)
        return QtGui.QIcon(QtGui.QPixmap.fromImage(image).scaled(
            ICON_SIZE, ICON_SIZE,
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation))

    def _on_clicked(self, index):
        try:
            self._activate(index.data(NAME_ROLE))
        except Exception as error:
            qDebug("recent_brushes: could not activate the preset: {!r}".format(error))

    def _activate(self, name):
        resource = self._presets.get(name)
        window = Krita.instance().activeWindow()
        view = window.activeView() if window is not None else None
        if resource is None or view is None:
            return
        view.setCurrentBrushPreset(resource)

    def _on_context_menu(self, position):
        index = self._list.indexAt(position)
        if not index.isValid():
            return
        menu = self._context_menu_for(index.data(NAME_ROLE))
        menu.exec(self._list.viewport().mapToGlobal(position))
        menu.deleteLater()

    def _context_menu_for(self, name):
        menu = QtWidgets.QMenu(self._list)
        action = menu.addAction(IGNORE_ACTION_LABEL.format(name.replace("&", "&&")))
        action.triggered.connect(lambda *_: self._ignore(name))
        return menu

    def _ignore(self, name):
        self._icons.pop(name, None)
        self._tracker.ignore(name)

    def _on_limit_changed(self, value):
        self._tracker.set_limit(value)

    def _on_clear(self):
        self._icons.clear()
        self._tracker.clear()

    def _on_show_ignored(self):
        dialog = IgnoredBrushesDialog(self._tracker, self)
        dialog.exec()
        dialog.deleteLater()
