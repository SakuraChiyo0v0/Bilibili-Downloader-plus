from PySide6.QtCore import Signal

from pathlib import Path
import logging

from ..download.task.info import TaskInfo
from ..thread.worker_base import WorkerBase

from .provider import StorageProvider

logger = logging.getLogger(__name__)


class UploadWorker(WorkerBase):
    progress = Signal(int, int)
    success = Signal()
    error = Signal(str)

    def __init__(self, task_info: TaskInfo, provider: StorageProvider, parent=None):
        super().__init__(parent)
        self.task_info = task_info
        self.provider = provider

    def run(self):
        cwd = Path(self.task_info.File.download_path, self.task_info.File.folder)

        # 合并 relative_files 和 additional_files
        file_names = list(self.task_info.File.relative_files)
        for name in self.task_info.File.additional_files:
            if name not in file_names:
                file_names.append(name)

        files = []
        for name in file_names:
            local_path = cwd / name
            if not local_path.exists():
                logger.warning("上传时本地文件不存在：%s", local_path)
                continue

            remote_path = f"{self.task_info.File.folder}/{name}".replace("\\", "/")
            files.append((local_path, remote_path))

        if not files:
            self.success.emit()
            return

        total = sum(local.stat().st_size for local, _ in files)
        uploaded = 0

        try:
            for local, remote in files:
                file_size = local.stat().st_size

                def make_callback(base: int):
                    def callback(delta: int):
                        self.progress.emit(base + delta, total)
                    return callback

                self.provider.upload(local, remote, progress_callback=make_callback(uploaded))
                uploaded += file_size

            self.success.emit()
        except Exception as e:
            logger.exception("上传到远程存储失败")
            self.error.emit(str(e))
        finally:
            self.provider.close()
            self.finished.emit()
