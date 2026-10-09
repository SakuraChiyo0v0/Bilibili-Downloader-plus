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
            self.tr("Storage"),
            self.tr("Choose where downloaded files are stored"),
            parent
        )

        self.parent_window = parent_window

        # 存储方式
        self.storage_type_choice = SettingComboBox(
            config.storage_type,
            [self.tr("Local"), self.tr("WebDAV")],
            parent=self
        )

        # 路径选择（本地 = 保存路径，WebDAV = 缓存目录）
        self.download_path_card = PushSettingCard(
            self.tr("Choose folder"),
            FluentIcon.FOLDER,
            self.tr("Local Cache"),
            "",
            self
        )
        self.download_path_card.clicked.connect(self._on_change_path)

        # WebDAV 专属选项
        self.conflict_choice = SettingComboBox(
            config.webdav_conflict_resolution,
            [self.tr("Auto rename"), self.tr("Overwrite")],
            parent=self
        )
        self.cleanup_switch = SettingSwitchButton(config.cleanup_after_upload, parent=self)
        self.webdav_config_btn = PushButton(self.tr("Configure…"), self)
        self.webdav_config_btn.clicked.connect(self._on_configure_webdav)

        # 分组
        self.type_group = self.addGroup("", self.tr("Storage Type"), "", self.storage_type_choice)
        self.path_group = self.addGroup(FluentIcon.FOLDER, self.tr("Local Cache"), "", self.download_path_card)
        self.conflict_group = self.addGroup("", self.tr("File Conflict Resolution"), "", self.conflict_choice)
        self.cleanup_group = self.addGroup("", self.tr("Clean Up After Upload"), "", self.cleanup_switch)
        self.webdav_group = self.addGroup(ExtendedFluentIcon.SERVER, self.tr("WebDAV Server"), "", self.webdav_config_btn)

        # 信号
        self.diskSpaceReady.connect(self.on_disk_space_ready)
        self.filesystemTypeReady.connect(self.on_filesystem_type_ready)

        # 初始状态
        self._on_storage_type_changed(config.get(config.storage_type))
        self.storage_type_choice.currentIndexChanged.connect(
            lambda idx: self._on_storage_type_changed(self.storage_type_choice.itemData(idx))
        )

        QTimer.singleShot(0, self._refresh_disk_space)

    def _cache_path(self):
        return config.get(config.local_temp_path) or config.get(config.download_path)

    def _on_storage_type_changed(self, storage_type: StorageType):
        is_webdav = storage_type == StorageType.WEBDAV
        self.path_group.setContent(self.tr("Files are processed locally before being uploaded to WebDAV"))
        self.download_path_card.setContent(self._cache_path())
        self.path_group.setEnabled(is_webdav)
        self.conflict_group.setEnabled(is_webdav)
        self.cleanup_group.setEnabled(is_webdav)
        self.webdav_group.setEnabled(is_webdav)
        self._refresh_disk_space()

    def _on_change_path(self):
        path = Directory.browse_directory(self.parent_window, self.tr("Choose cache folder"), self._cache_path())
        if path:
            config.set(config.local_temp_path, path)
            self._refresh_disk_space(check_filesystem = True)

    def _refresh_disk_space(self, check_filesystem: bool = False):
        path = self._cache_path()

        def worker():
            self.diskSpaceReady.emit(path, Directory.calc_disk_space(path))
            if check_filesystem:
                self.filesystemTypeReady.emit(path, Directory.get_filesystem_type(path))

        GlobalThreadPoolTask.run_func(worker)

    def on_disk_space_ready(self, path: str, disk_space_info: dict = None):
        if path != self._cache_path():
            return

        if disk_space_info:
            self.download_path_card.setContent(
                self.tr("{path} ({free} available)").format(
                    path=path, free=disk_space_info.get("free")
                )
            )
        else:
            self.download_path_card.setContent(path)

    def on_filesystem_type_ready(self, path: str, filesystem_type: str):
        if path != self._cache_path() or filesystem_type is None:
            return

        if filesystem_type.upper() in ("FAT32", "EXFAT", "VFAT", "MSDOS", "FAT", "FAT16", "FAT12", "MS-DOS"):
            from ..dialog import MessageBox
            dialog = MessageBox(
                self.tr("The file system of the selected path does not support sparse files"),
                self.tr('The file system type of the currently selected cache path is {fs}, which does not support sparse files.\n\nIf you continue, please disable the "Preallocate file space" option. (Settings → Behavior → Download Handling)').format(fs=filesystem_type),
                self.parent_window
            )
            dialog.hideCancelButton()
            dialog.show()

    def _on_configure_webdav(self):
        from gui.dialog.setting.webdav import WebDAVDialog

        dialog = WebDAVDialog(self.parent_window)
        dialog.exec()
