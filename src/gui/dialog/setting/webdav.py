from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import QGridLayout

from qfluentwidgets import SubtitleLabel, BodyLabel, LineEdit, PushButton, MessageBox, CheckBox

from gui.component.dialog import DialogBase

from util.common.config import config
from util.storage.factory import StorageProviderFactory
from util.thread.async_ import AsyncTask
from util.thread.worker_base import WorkerBase

import logging

logger = logging.getLogger(__name__)


class WebDAVTestWorker(WorkerBase):
    success = Signal()
    error = Signal(str)

    def __init__(self, url: str, username: str, password: str, base_path: str, verify_ssl: bool, parent=None):
        super().__init__(parent)
        self.url = url
        self.username = username
        self.password = password
        self.base_path = base_path
        self.verify_ssl = verify_ssl

    @Slot()
    def run(self):
        provider = None
        try:
            provider = StorageProviderFactory.create_webdav(
                url=self.url,
                username=self.username,
                password=self.password,
                base_path=self.base_path,
                verify_ssl=self.verify_ssl,
            )
            provider.test_connection()
            self.success.emit()
        except Exception as e:
            logger.error("WebDAV 连接测试失败: %s", str(e))
            self.error.emit(str(e))
        finally:
            if provider is not None:
                try:
                    provider.close()
                except Exception:
                    logger.exception("关闭 WebDAV 测试连接失败")
            self.finished.emit()


class WebDAVDialog(DialogBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_UI()

    def init_UI(self):
        self.caption_lab = SubtitleLabel(self.tr("Configure WebDAV Server"), self)

        url_lab = BodyLabel(self.tr("Server URL"), self)
        self.url_box = LineEdit(self)
        self.url_box.setPlaceholderText(self.tr("https://example.com/dav"))
        self.url_box.setText(config.get(config.webdav_url))

        username_lab = BodyLabel(self.tr("Username"), self)
        self.username_box = LineEdit(self)
        self.username_box.setPlaceholderText(self.tr("Optional"))
        self.username_box.setText(config.get(config.webdav_username))

        password_lab = BodyLabel(self.tr("Password"), self)
        self.password_box = LineEdit(self)
        self.password_box.setPlaceholderText(self.tr("Optional"))
        self.password_box.setText(config.get(config.webdav_password))
        self.password_box.setEchoMode(LineEdit.EchoMode.Password)

        base_path_lab = BodyLabel(self.tr("Remote Base Path"), self)
        self.base_path_box = LineEdit(self)
        self.base_path_box.setPlaceholderText(self.tr("/"))
        self.base_path_box.setText(config.get(config.webdav_base_path))

        self.verify_ssl_checkbox = CheckBox(self.tr("Verify SSL Certificate"))
        self.verify_ssl_checkbox.setChecked(config.get(config.webdav_verify_ssl))

        self.test_btn = PushButton(self.tr("Test Connection"), self)
        self.test_btn.setMaximumWidth(150)

        grid_layout = QGridLayout()
        grid_layout.addWidget(url_lab, 0, 0)
        grid_layout.addWidget(self.url_box, 1, 0)
        grid_layout.addWidget(username_lab, 2, 0)
        grid_layout.addWidget(self.username_box, 3, 0)
        grid_layout.addWidget(password_lab, 4, 0)
        grid_layout.addWidget(self.password_box, 5, 0)
        grid_layout.addWidget(base_path_lab, 6, 0)
        grid_layout.addWidget(self.base_path_box, 7, 0)

        self.viewLayout.addWidget(self.caption_lab)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addLayout(grid_layout)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(self.verify_ssl_checkbox)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(self.test_btn)

        self.widget.setMinimumWidth(500)

        self.test_btn.clicked.connect(self.on_test)

    def on_test(self):
        url = self.url_box.text().strip()
        if not url:
            dialog = MessageBox(
                self.tr("Invalid Configuration"),
                self.tr("Please enter the WebDAV server URL first."),
                self
            )
            dialog.hideCancelButton()
            dialog.exec()
            return

        self.set_test_btn_status(False)

        worker = WebDAVTestWorker(
            url=url,
            username=self.username_box.text(),
            password=self.password_box.text(),
            base_path=self.base_path_box.text(),
            verify_ssl=self.verify_ssl_checkbox.isChecked(),
        )
        worker.success.connect(self.on_test_success)
        worker.error.connect(self.on_test_error)
        AsyncTask.run(worker)

    @Slot()
    def on_test_success(self):
        self.set_test_btn_status(True)

        dialog = MessageBox(
            self.tr("Connection Successful"),
            self.tr("Successfully connected to the WebDAV server."),
            self
        )
        dialog.hideCancelButton()
        dialog.exec()

    @Slot(str)
    def on_test_error(self, error: str):
        logger.error("WebDAV 连接测试失败: %s", error)

        self.set_test_btn_status(True)

        dialog = MessageBox(
            self.tr("Connection Failed"),
            error,
            self
        )
        dialog.hideCancelButton()
        dialog.exec()

    def accept(self):
        config.set(config.webdav_url, self.url_box.text().strip())
        config.set(config.webdav_username, self.username_box.text())
        config.set(config.webdav_password, self.password_box.text())
        config.set(config.webdav_base_path, self.base_path_box.text().strip())
        config.set(config.webdav_verify_ssl, self.verify_ssl_checkbox.isChecked())

        return super().accept()

    def set_test_btn_status(self, enabled: bool):
        if enabled:
            self.test_btn.setEnabled(True)
            self.test_btn.setText(self.tr("Test Connection"))
        else:
            self.test_btn.setEnabled(False)
            self.test_btn.setText(self.tr("Testing…"))
