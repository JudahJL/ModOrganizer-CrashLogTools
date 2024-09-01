import os
from typing import List, Callable

from mobase import IPluginTool, VersionInfo, ReleaseType, PluginRequirementFactory

try:
    from PyQt6.QtCore import *
    from PyQt6.QtGui import *
    from PyQt6.QtWidgets import *

    SortOrder = Qt.SortOrder
    SelectionMode = QAbstractItemView.SelectionMode
    ContextMenuPolicy = Qt.ContextMenuPolicy
    StandardButton = QDialogButtonBox.StandardButton
    Orientation = Qt.Orientation
except ImportError:
    from PyQt5.QtCore import *
    from PyQt5.QtGui import *
    from PyQt5.QtWidgets import *

    SortOrder = Qt
    SelectionMode = QAbstractItemView
    ContextMenuPolicy = Qt
    StandardButton = QDialogButtonBox
    Orientation = Qt

from . import crashlogs


class CrashLogViewer(IPluginTool):

    def __init__(self):
        super().__init__()

    def name(self) -> str:
        return "Crash Log Viewer"

    def version(self) -> "VersionInfo":
        return VersionInfo(1, 0, 0, 0, ReleaseType.FINAL)

    def description(self) -> str:
        return "Lists crash logs"

    def author(self) -> str:
        return "Parapets, edited by Miss Corruption"

    def requirements(self) -> List["IPluginRequirement"]:
        return [PluginRequirementFactory.gameDependency(crashlogs.supported_games())]

    def settings(self) -> List["PluginSetting"]:
        return []

    def displayName(self) -> str:
        return "Crash Log Viewer"

    def tooltip(self) -> str:
        return "View crash logs"

    def icon(self) -> "QIcon":
        return QIcon()

    def init(self, organizer: "IOrganizer") -> bool:
        self.organizer = organizer
        organizer.onUserInterfaceInitialized(self.onUserInterfaceInitializedCallback)

        return True

    def display(self) -> None:
        self.dialog.show()

    def onUserInterfaceInitializedCallback(self, main_window: "QMainWindow"):
        game = self.organizer.managedGame().gameName()
        self.finder = crashlogs.get_finder(game)
        self.dialog = self.make_dialog(main_window)

    def make_dialog(self, main_window: "QMainWindow") -> "QDialog":
        log_dir = self.finder.log_directory

        source_model = QFileSystemModel()
        source_model.setRootPath(log_dir)

        proxy_model = FileFilterProxyModel()
        proxy_model.setSourceModel(source_model)
        proxy_model.setFilterWildcard(self.finder.filter)
        proxy_model.sort(0, SortOrder.DescendingOrder)

        dialog = QDialog(main_window)
        dialog.setWindowTitle("Crash Log Viewer")

        logs_list = QListView(dialog)
        logs_list.setModel(proxy_model)
        logs_list.setRootIndex(proxy_model.mapFromSource(source_model.index(log_dir)))
        logs_list.setDragEnabled(True)
        logs_list.setSelectionMode(SelectionMode.ExtendedSelection)

        def open_logs(index: "QModelIndex") -> None:
            source_index = proxy_model.mapToSource(index)
            os.startfile(source_model.filePath(source_index))

        def delete(index: "QModelIndex") -> None:
            source_index = proxy_model.mapToSource(index)
            QFile(source_model.filePath(source_index)).moveToTrash()

        def for_selected(
            action: Callable[["QModelIndex"], None]
        ) -> Callable[[bool], None]:
            def fn(checked: bool):
                for index in logs_list.selectedIndexes():
                    action(index)

            return fn

        open_action = QAction(logs_list.tr("&Open"), logs_list)
        open_action.triggered.connect(for_selected(open_logs))
        f = open_action.font()
        f.setBold(True)
        open_action.setFont(f)
        logs_list.addAction(open_action)

        delete_action = QAction(logs_list.tr("&Delete"), logs_list)
        delete_action.triggered.connect(for_selected(delete))
        logs_list.addAction(delete_action)
        logs_list.setContextMenuPolicy(ContextMenuPolicy.ActionsContextMenu)
        logs_list.activated.connect(open_logs)

        button_box = QDialogButtonBox(dialog)
        button_box.rejected.connect(dialog.reject)
        button_box.setOrientation(Orientation.Horizontal)
        button_box.setStandardButtons(StandardButton.Close)
        button_box.button(StandardButton.Close).setAutoDefault(False)

        layout = QVBoxLayout()
        layout.addWidget(logs_list)
        layout.addWidget(button_box)
        dialog.setLayout(layout)

        return dialog


class FileFilterProxyModel(QSortFilterProxyModel):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def filePath(self, index: "QModelIndex") -> str:
        return self.sourceModel().filePath(self.mapToSource(index))

    def filterAcceptsRow(self, source_row: int, source_parent: "QModelIndex") -> bool:
        source_model = self.sourceModel()
        if source_parent == source_model.index(source_model.rootPath()):
            return super().filterAcceptsRow(source_row, source_parent)
        return True
