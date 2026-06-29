from PySide6.QtWidgets import QVBoxLayout, QLabel
from PySide6.QtCore import Signal

from qfluentwidgets import SwitchSettingCard, PushSettingCard, FluentIcon

from gui.component.setting import NumberSettingCard, DownloadFormatCard
from gui.component.widget import ScrollArea
from .card import NamingConventionCard

from util.common.icon import ExtendedFluentIcon
from util.common.config import config
from util.common.enum import StorageType
from util.common.io.directory import Directory
from util.thread.pool import GlobalThreadPoolTask


class _StorageAwarePathCard(PushSettingCard):
    diskSpaceReady = Signal(str, object)

    def __init__(self, parent_window, parent=None):
        super().__init__(
            self.tr("更改"),
            FluentIcon.FOLDER,
            "",
            "",
            parent
        )
        self.parent_window = parent_window
        self.diskSpaceReady.connect(self._on_disk_space)

        # 本地模式：直接作为保存位置
        # WebDAV 模式：作为缓存目录提示标签
        self._cache_label = QLabel(self)
        self._cache_label.setWordWrap(True)
        self._cache_label.setStyleSheet("font-size: 12px; color: gray; padding: 0 16px 8px 16px;")
        self._cache_label.hide()

        self.clicked.connect(self._on_click)
        self._refresh()
        self.storage_type = config.get(config.storage_type)

    def _refresh(self):
        st = config.get(config.storage_type)
        self.storage_type = st

        if st == StorageType.WEBDAV:
            url = config.get(config.webdav_url) or self.tr("未配置服务器地址")
            temp = config.get(config.local_temp_path) or config.get(config.download_path) or ""

            self.setTitle(self.tr("保存位置"))
            self.setContent(self.tr("WebDAV  —  {url}").format(url=url))
            self._cache_label.setText(
                self.tr("本地缓存: {path}").format(path=temp) if temp else self.tr("请先设置本地缓存目录")
            )
            self._cache_label.show()
            self.path = temp

        else:
            path = config.get(config.download_path) or ""
            self.setTitle(self.tr("保存位置"))
            self.setContent(path)
            self._cache_label.hide()
            self.path = path
            self._refresh_disk_space(path)

    def _refresh_disk_space(self, path: str):
        if config.get(config.storage_type) == StorageType.WEBDAV:
            return

        def worker():
            info = Directory.calc_disk_space(path)
            self.diskSpaceReady.emit(path, info)

        GlobalThreadPoolTask.run_func(worker)

    def _on_disk_space(self, path: str, info: dict = None):
        if info:
            self.setContent(self.tr("{path}  ({free} 可用)").format(path=path, free=info.get("free")))
        else:
            self.setContent(path)

    def _on_click(self):
        st = config.get(config.storage_type)
        if st == StorageType.WEBDAV:
            title = self.tr("选择本地缓存目录")
            config_key = config.local_temp_path
            default = config.get(config.local_temp_path) or config.get(config.download_path)
        else:
            title = self.tr("选择保存位置")
            config_key = config.download_path
            default = config.get(config.download_path)

        path = Directory.browse_directory(self.parent_window, title, default)
        if path:
            config.set(config_key, path)
            self._refresh()


class DownloadSettingsPage(ScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.options_dialog = parent

        self.init_UI()

    def init_UI(self):
        self.download_path_card = _StorageAwarePathCard(self.options_dialog, parent=self)
        self.download_format_card = DownloadFormatCard(parent=self)
        self.naming_convention_card = NamingConventionCard(self)
        self.show_dialog_card = SwitchSettingCard(
            ExtendedFluentIcon.OPTIONS,
            self.tr("Automatically show this dialog"),
            self.tr("Automatically show this dialog before downloading to customize settings"),
            config.show_download_options_dialog,
            self
        )
        self.numbering_settings_card = NumberSettingCard(self.options_dialog, self)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.download_path_card)
        main_layout.addWidget(self.download_path_card._cache_label)
        main_layout.addWidget(self.download_format_card)
        main_layout.addWidget(self.naming_convention_card)
        main_layout.addWidget(self.show_dialog_card)
        main_layout.addWidget(self.numbering_settings_card)

        main_layout.addStretch()

        self.setScrollLayout(main_layout)

    def on_save(self):
        config.set(config.download_path, self.download_path_card.path)
        config.target_naming_rule_id = self.naming_convention_card.rule_choice.currentData()
