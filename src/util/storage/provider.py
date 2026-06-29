from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable


class StorageProvider(ABC):
    @abstractmethod
    def upload(self, local_path: Path, remote_path: str,
               progress_callback: Callable[[int], None] | None = None) -> None:
        """将本地文件上传到 remote_path，progress_callback 接收每次成功写入的字节增量。"""

    @abstractmethod
    def exists(self, remote_path: str) -> bool:
        """检查远程路径是否已存在。"""

    @abstractmethod
    def mkdir(self, remote_path: str) -> None:
        """递归创建远程目录。"""

    def resolve_conflict(self, remote_path: str) -> str:
        """根据配置决定远程路径；子类可覆盖以支持冲突处理。"""
        return remote_path

    def test_connection(self) -> None:
        """设置页测试连接，失败时抛出异常。"""

    def close(self) -> None:
        """释放底层资源。"""
