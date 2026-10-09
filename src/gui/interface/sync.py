from copy import deepcopy
from datetime import datetime

from PySide6.QtCore import QSize, Signal, Slot
from PySide6.QtWidgets import QFrame, QHBoxLayout, QListWidgetItem, QVBoxLayout, QWidget

from qfluentwidgets import BodyLabel, FluentIcon, LineEdit, ListWidget, PrimaryPushButton, PushButton, SubtitleLabel, SwitchButton, TitleLabel

from gui.component.dialog import DialogBase
from gui.component.widget import ToolButton

from util.common.enum import ToastNotificationCategory, ConventionType
from util.common.icon import ExtendedFluentIcon
from util.common.signal_bus import signal_bus
from util.sync.info import SyncSourceInfo
from util.sync.manager import sync_manager
from util.sync.options import capture_download_options, scoped_download_options
from util.sync.parser import SyncSourceParser
from util.thread.async_ import AsyncTask
from util.thread.worker_base import WorkerBase


class ManualSyncAddWorker(WorkerBase):
    success = Signal(object)
    error = Signal(str)

    def __init__(self, url: str, options: dict, parent = None):
        super().__init__(parent)

        self.url = url
        self.options = deepcopy(options)

    @Slot()
    def run(self):
        try:
            parsed = SyncSourceParser().parse(self.url)
            self.success.emit(parsed)

        except Exception as e:
            self.error.emit(str(e))

        finally:
            self.finished.emit()


class AddSyncSourceDialog(DialogBase):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.url = ""
        self.options = capture_download_options()

        self.init_UI()

    def init_UI(self):
        self.caption_lab = SubtitleLabel(self.tr("Add Sync Source"), self)

        self.url_lab = BodyLabel(self.tr("Sync Source URL"), self)

        self.url_box = LineEdit(self)
        self.url_box.setPlaceholderText(self.tr("Paste favorites, collection, or bangumi link"))
        self.url_box.setClearButtonEnabled(True)

        self.options_btn = PushButton(FluentIcon.SETTING, self.tr("Edit download options"), self)

        self.viewLayout.addWidget(self.caption_lab)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(self.url_lab)
        self.viewLayout.addWidget(self.url_box)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(self.options_btn)

        self.widget.setMinimumWidth(560)

        self.yesButton.setText(self.tr("Add"))

        self.url_box.textChanged.connect(lambda _: self.url_box.setError(False))
        self.options_btn.clicked.connect(self.on_edit_options)

    def on_edit_options(self):
        from gui.dialog.download_options.dialog import DownloadOptionsDialog

        with scoped_download_options(self.options):
            dialog = DownloadOptionsDialog(
                self.parent(),
                type_ids = {ConventionType.FAVORITE, ConventionType.COLLECTION, ConventionType.BANGUMI},
                sync_mode = True
            )
            dialog.setWindowTitle(self.tr("Sync Download Options"))

            if not dialog.exec():
                return

            self.options = capture_download_options()

        self.show_top_toast_message(
            ToastNotificationCategory.SUCCESS,
            "",
            self.tr("Download options updated")
        )

    def accept(self):
        self.url = self.url_box.text().strip()

        is_valid = self.url != ""
        self.url_box.setError(not is_valid)

        if not is_valid:
            self.url_box.setFocus()
            self.show_top_toast_message(
                ToastNotificationCategory.ERROR,
                "",
                self.tr("Please enter a sync source URL")
            )
            return

        return super().accept()


class SyncSourceItem(QWidget):
    def __init__(self, source: SyncSourceInfo, parent = None):
        super().__init__(parent)

        self.source = source

        self.init_UI()

    def init_UI(self):
        self.title_label = BodyLabel(self.source.title or self.source.url, self)
        self.meta_label = BodyLabel(self._meta_text(), self)
        self.status_label = BodyLabel(self._status_text(), self)

        self.enabled_switch = SwitchButton(self)
        self.enabled_switch.setChecked(self.source.enabled)

        self.check_btn = ToolButton(ExtendedFluentIcon.RETRY, self)
        self.check_btn.setToolTip(self.tr("Check now"))

        self.options_btn = ToolButton(FluentIcon.SETTING, self)
        self.options_btn.setToolTip(self.tr("Edit download options"))

        self.delete_btn = ToolButton(FluentIcon.DELETE, self)
        self.delete_btn.setToolTip(self.tr("Delete"))

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.meta_label)
        text_layout.addWidget(self.status_label)

        action_layout = QHBoxLayout()
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.addWidget(self.enabled_switch)
        action_layout.addWidget(self.check_btn)
        action_layout.addWidget(self.options_btn)
        action_layout.addWidget(self.delete_btn)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 8, 12, 8)
        main_layout.addLayout(text_layout)
        main_layout.addStretch()
        main_layout.addLayout(action_layout)

        self.enabled_switch.checkedChanged.connect(lambda checked: sync_manager.set_enabled(self.source.sync_id, checked))
        self.check_btn.clicked.connect(lambda: signal_bus.sync.check_source.emit(self.source.sync_id))
        self.options_btn.clicked.connect(self.on_edit_options)
        self.delete_btn.clicked.connect(lambda: sync_manager.delete_source(self.source.sync_id))

    def on_edit_options(self):
        from gui.dialog.download_options.dialog import DownloadOptionsDialog

        main_window = self.window()
        new_options = None

        with scoped_download_options(self.source.options):
            type_ids = {
                "favlist": {ConventionType.FAVORITE},
                "collection": {ConventionType.COLLECTION},
                "bangumi": {ConventionType.BANGUMI},
            }.get(self.source.source_type, set())
            dialog = DownloadOptionsDialog(main_window, type_ids = type_ids, sync_mode = True)
            dialog.setWindowTitle(self.tr("Sync Download Options"))

            if not dialog.exec():
                return

            new_options = capture_download_options()

        sync_manager.update_source_options(self.source.sync_id, new_options)

        signal_bus.toast.show.emit(
            ToastNotificationCategory.SUCCESS,
            "",
            self.tr("Sync download options updated")
        )

    def _meta_text(self):
        source_type_map = {
            "favlist": self.tr("Favorites"),
            "collection": self.tr("Collection"),
            "bangumi": self.tr("Bangumi"),
        }

        item_count = len(self.source.known_item_ids)

        return self.tr("{source_type} | {item_count} known items").format(
            source_type = source_type_map.get(self.source.source_type, self.source.source_type),
            item_count = item_count
        )

    def _status_text(self):
        if self.source.last_error:
            return self.tr("Last check failed: {error}").format(error = self.source.last_error)

        if self.source.last_success_time:
            time_text = datetime.fromtimestamp(self.source.last_success_time / 1000).strftime("%Y-%m-%d %H:%M")

            return self.tr("Last checked: {time} | Added: {count}").format(
                time = time_text,
                count = self.source.last_added_count
            )

        return self.tr("Not checked yet")


class SyncInterface(QFrame):
    def __init__(self, parent = None):
        super().__init__(parent = parent)

        self.setObjectName("SyncInterface")

        self.init_UI()
        self.refresh_sources()

    def init_UI(self):
        self.title_label = TitleLabel(self.tr("Sync"), self)

        self.add_btn = PrimaryPushButton(FluentIcon.ADD, self.tr("Add Sync"), self)
        self.check_all_btn = PrimaryPushButton(ExtendedFluentIcon.RETRY, self.tr("Check All"), self)

        self.list_widget = ListWidget(self)
        self.list_widget.setSpacing(6)

        self.empty_label = BodyLabel(self.tr("No sync sources"), self)
        self.empty_label.setVisible(False)

        top_layout = QHBoxLayout()
        top_layout.addWidget(self.title_label)
        top_layout.addStretch()
        top_layout.addWidget(self.add_btn)
        top_layout.addWidget(self.check_all_btn)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 15, 25, 15)
        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.empty_label)
        main_layout.addWidget(self.list_widget)

        self.connect_signals()

    def connect_signals(self):
        self.add_btn.clicked.connect(self.on_add_source)
        self.check_all_btn.clicked.connect(lambda: signal_bus.sync.check_all.emit())
        signal_bus.sync.source_added.connect(lambda _: self.refresh_sources())
        signal_bus.sync.source_updated.connect(lambda _: self.refresh_sources())
        signal_bus.sync.source_removed.connect(lambda _: self.refresh_sources())

    def on_add_source(self):
        dialog = AddSyncSourceDialog(self.window())

        if not dialog.exec():
            return

        url = dialog.url
        options = deepcopy(dialog.options)

        self.set_add_btn_loading(True)

        self._pending_source = (url, options)
        worker = ManualSyncAddWorker(url, options)
        worker.success.connect(self.on_add_source_success)
        worker.error.connect(self.on_add_source_error)
        worker.finished.connect(self.on_add_source_finished)
        AsyncTask.run(worker)

    @Slot(object)
    def on_add_source_success(self, parsed: dict):
        url, options = self._pending_source
        episodes = parsed.get("episodes", [])
        try:
            sync_manager.add_or_update_source(
                title = parsed.get("title", ""), url = url,
                source_type = parsed.get("source_type", ""),
                episodes = episodes, options = options
            )
        except Exception as error:
            self.on_add_source_error(str(error))
            return

        signal_bus.toast.show.emit(
            ToastNotificationCategory.SUCCESS,
            "",
            self.tr("Sync source saved: {count} known items").format(count = len(episodes))
        )

    @Slot(str)
    def on_add_source_error(self, error: str):
        signal_bus.toast.show.emit(
            ToastNotificationCategory.ERROR,
            self.tr("Sync Failed"),
            self._friendly_sync_error(error)
        )

    @Slot()
    def on_add_source_finished(self):
        self.set_add_btn_loading(False)

    def _friendly_sync_error(self, error: str):
        lower_error = error.lower()

        if "invalid link" in lower_error:
            return self.tr("Invalid sync source URL")

        if "unsupported sync source" in lower_error or "only collection videos can be synced" in lower_error:
            return self.tr("This source does not support sync downloads")

        return error

    def set_add_btn_loading(self, loading: bool):
        self.add_btn.setEnabled(not loading)

        if loading:
            self.add_btn.setText(self.tr("Adding..."))

        else:
            self.add_btn.setText(self.tr("Add Sync"))

    def refresh_sources(self):
        self.list_widget.clear()

        sources = sync_manager.sources()
        self.empty_label.setVisible(len(sources) == 0)
        self.list_widget.setVisible(len(sources) > 0)

        for source in sources:
            item = QListWidgetItem()
            widget = SyncSourceItem(source, self.list_widget)
            item.setSizeHint(QSize(100, 86))
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)
