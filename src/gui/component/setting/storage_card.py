from PySide6.QtCore import QTimer, Signal

from qfluentwidgets import PushButton, FluentIcon, PushSettingCard

from .widget import SettingSwitchButton, SettingComboBox
from .card import ExpandGroupSettingCard

from util.common.config import config
from util.common.enum import StorageType
from util.common.icon import ExtendedFluentIcon
from util.common.io.directory import Directory
from util.thread.pool import GlobalThreadPoolTask


class StorageSettingCard(ExpandGroupSettingCard):
    diskSpaceReady = Signal(str, object)
    filesystemTypeReady = Signal(str, str)

    def __init__(self, parent_window, parent=None):
        super().__init__(
            ExtendedFluentIcon.SERVER,
            self.tr("保存位置"),
            self.tr("文件下载后的最终保存位置"),
            parent
        )

        self.parent_window = parent_window

        # 存储方式
        self.storage_type_choice = SettingComboBox(
            config.storage_type,
            [self.tr("本地"), self.tr("WebDAV")],
            parent=self
        )

        # 路径选择（本地 = 保存路径，WebDAV = 缓存目录）
        self.download_path_card = PushSettingCard(
            self.tr("更改"),
            FluentIcon.FOLDER,
            self.tr("保存路径"),
            "",
            self
        )
        self.download_path_card.clicked.connect(self._on_change_path)

        # WebDAV 专属选项
        self.conflict_choice = SettingComboBox(
            config.webdav_conflict_resolution,
            [self.tr("自动重命名"), self.tr("覆盖")],
            parent=self
        )
        self.cleanup_switch = SettingSwitchButton(config.cleanup_after_upload, parent=self)
        self.webdav_config_btn = PushButton(self.tr("配置…"), self)
        self.webdav_config_btn.clicked.connect(self._on_configure_webdav)

        # 分组
        self.type_group = self.addGroup("", self.tr("存储方式"), "", self.storage_type_choice)
        self.path_group = self.addGroup(FluentIcon.FOLDER, self.tr("保存路径"), "", self.download_path_card)
        self.conflict_group = self.addGroup("", self.tr("同名文件处理"), "", self.conflict_choice)
        self.cleanup_group = self.addGroup("", self.tr("上传后清理缓存"), "", self.cleanup_switch)
        self.webdav_group = self.addGroup(ExtendedFluentIcon.SERVER, self.tr("服务器"), "", self.webdav_config_btn)

        # 信号
        self.diskSpaceReady.connect(self.on_disk_space_ready)
        self.filesystemTypeReady.connect(self.on_filesystem_type_ready)

        # 初始状态
        self._on_storage_type_changed(config.get(config.storage_type))
        self.storage_type_choice.currentIndexChanged.connect(
            lambda idx: self._on_storage_type_changed(self.storage_type_choice.itemData(idx))
        )

        QTimer.singleShot(0, self._refresh_disk_space)

    def _on_storage_type_changed(self, storage_type: StorageType):
        is_webdav = storage_type == StorageType.WEBDAV

        if is_webdav:
            self.download_path_card.setTitle(self.tr("本地缓存"))
            self.path_group.setContent(self.tr("视频先下载到此目录，合并后再上传到 WebDAV"))
            path = config.get(config.local_temp_path) or config.get(config.download_path)
        else:
            self.download_path_card.setTitle(self.tr("保存路径"))
            self.path_group.setContent("")
            path = config.get(config.download_path)

        self.download_path_card.setContent(path)
        self._refresh_disk_space()

        self.conflict_group.setEnabled(is_webdav)
        self.cleanup_group.setEnabled(is_webdav)
        self.webdav_group.setEnabled(is_webdav)

    def _on_change_path(self):
        storage_type = config.get(config.storage_type)

        if storage_type == StorageType.WEBDAV:
            config_key = config.local_temp_path
            title = self.tr("选择本地缓存目录")
            default = config.get(config.local_temp_path) or config.get(config.download_path)
        else:
            config_key = config.download_path
            title = self.tr("选择保存位置")
            default = config.get(config.download_path)

        path = Directory.browse_directory(self.parent_window, title, default)

        if path:
            config.set(config_key, path)
            self.download_path_card.setContent(path)
            self._refresh_disk_space()

    def _refresh_disk_space(self):
        storage_type = config.get(config.storage_type)
        path = (
            config.get(config.local_temp_path) or config.get(config.download_path)
            if storage_type == StorageType.WEBDAV
            else config.get(config.download_path)
        )

        def worker():
            self.diskSpaceReady.emit(path, Directory.calc_disk_space(path))
            filesystem_type = Directory.get_filesystem_type(path)
            self.filesystemTypeReady.emit(path, filesystem_type)

        GlobalThreadPoolTask.run_func(worker)

    def on_disk_space_ready(self, path: str, disk_space_info: dict = None):
        if disk_space_info:
            self.download_path_card.setContent(
                self.tr("{path}  ({free} 可用)").format(
                    path=path, free=disk_space_info.get("free")
                )
            )
        else:
            self.download_path_card.setContent(path)

    def on_filesystem_type_ready(self, path: str, filesystem_type: str):
        if filesystem_type is None:
            return

        if filesystem_type.upper() in ("FAT32", "EXFAT", "VFAT", "MSDOS", "FAT", "FAT16", "FAT12", "MS-DOS"):
            from ..dialog import MessageBox
            dialog = MessageBox(
                self.tr("不支持的文件系统"),
                self.tr(
                    "当前分区文件系统为 {type}，不支持大于 4 GB 的文件。"
                    "请将保存位置更换为 NTFS 分区。"
                ).format(type=filesystem_type),
                self.parent_window
            )
            dialog.hideCancelButton()
            dialog.show()

    def _on_configure_webdav(self):
        from gui.dialog.setting.webdav import WebDAVDialog

        dialog = WebDAVDialog(self.parent_window)
        dialog.exec()
