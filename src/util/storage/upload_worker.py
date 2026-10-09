from PySide6.QtCore import QThread, Signal

from pathlib import Path
from threading import Event
import logging

from ..download.task.info import TaskInfo
from .provider import StorageProvider

logger = logging.getLogger(__name__)


class UploadCancelled(Exception):
    pass


class UploadWorker(QThread):
    # Python 整数避免大于 2 GiB 的文件进度溢出 Qt 的 32 位 int。
    progress = Signal(object, object)
    success = Signal()
    error = Signal(str)

    def __init__(self, task_info: TaskInfo, provider: StorageProvider, parent=None):
        super().__init__(parent)
        self.task_info = task_info
        self.provider = provider
        self._cancelled = Event()

    def stop(self, timeout: int = 3000):
        self._cancelled.set()
        return self.wait(timeout)

    def _check_cancelled(self):
        if self._cancelled.is_set():
            raise UploadCancelled()

    def run(self):
        succeeded = False
        error_message = None
        try:
            self._check_cancelled()
            cwd = Path(self.task_info.File.download_path, self.task_info.File.folder)
            file_names = dict.fromkeys([
                *self.task_info.File.relative_files,
                *self.task_info.File.additional_files,
            ])
            if not file_names:
                raise FileNotFoundError("没有可上传的文件")

            files = []
            for name in file_names:
                local_path = cwd / name
                # 先校验全部文件，不能跳过缺失文件后报告整项成功并触发本地清理。
                if not local_path.is_file():
                    raise FileNotFoundError(f"上传文件不存在：{local_path}")
                remote_path = f"{self.task_info.File.folder}/{name}".replace("\\", "/")
                files.append((local_path, remote_path, local_path.stat().st_size))

            total = sum(size for _, _, size in files)
            uploaded = 0
            self.progress.emit(0, total)

            for local, remote, file_size in files:
                self._check_cancelled()
                transferred = 0

                def callback(delta: int):
                    nonlocal transferred
                    self._check_cancelled()
                    transferred = min(file_size, transferred + max(0, delta))
                    self.progress.emit(uploaded + transferred, total)

                self.provider.upload(local, remote, progress_callback=callback)
                self._check_cancelled()
                uploaded += file_size
                self.progress.emit(uploaded, total)

            succeeded = True
        except UploadCancelled:
            logger.debug("远程上传已取消，本地文件保留")
        except Exception as e:
            logger.exception("上传到远程存储失败")
            error_message = str(e)
        finally:
            try:
                self.provider.close()
            except Exception as e:
                logger.exception("关闭远程存储连接失败")
                # 全部 PUT 已成功时，连接释放失败不能使已上传任务重新上传。
                if not succeeded:
                    error_message = error_message or str(e)

        # QThread 自身负责发出 finished，即使预检失败、取消或 close 异常也能结束线程。
        if not self._cancelled.is_set():
            if error_message is not None:
                self.error.emit(error_message)
            elif succeeded:
                self.success.emit()
