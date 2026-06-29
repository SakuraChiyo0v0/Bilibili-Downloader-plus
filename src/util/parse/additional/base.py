from ...download.task.info import TaskInfo
from ..parser.base import ParserBase

from pathlib import Path
from typing import List

class AdditionalParserBase(ParserBase):
    def __init__(self, task_info: TaskInfo):
        super().__init__()

        self.task_info: TaskInfo = task_info

    def _write(self, contents: str | bytes, suffix: str, name: str = None, qualifier: List[str] = None):
        if isinstance(contents, str):
            mode = "w"
            encoding = "utf-8"

        elif isinstance(contents, bytes):
            mode = "wb"
            encoding = None

        if name is None:
            name = self.task_info.File.name

        if qualifier:
            name_parts = f"{name}.{'.'.join(qualifier)}"
        else:
            name_parts = name

        file_name = f"{name_parts}.{suffix}"
        path = self.__base_path / file_name
        path.parent.mkdir(parents = True, exist_ok = True)

        with open(path, mode, encoding = encoding) as f:
            f.write(contents)

        self._update_file_size(path)

        # 记录附加文件用于后续上传
        if file_name not in self.task_info.File.additional_files:
            self.task_info.File.additional_files.append(file_name)

    def _update_file_size(self, path: Path):
        if path.exists():
            self.task_info.Download.downloaded_size += path.stat().st_size
            self.task_info.Download.total_size += path.stat().st_size

    def _on_error(self, error_message: str):
        raise RuntimeError(error_message)
    
    @property
    def __base_path(self):
        return Path(self.task_info.File.download_path, self.task_info.File.folder)
