from pathlib import Path
from typing import Callable

from .provider import StorageProvider


class LocalStorageProvider(StorageProvider):
    """本地存储 Provider，文件已经落在目标位置，无需上传。"""

    def upload(self, local_path: Path, remote_path: str,
               progress_callback: Callable[[int], None] | None = None) -> None:
        pass

    def exists(self, remote_path: str) -> bool:
        return False

    def mkdir(self, remote_path: str) -> None:
        pass
