"""增强版版本标识；不导入配置或 GUI，供更新检查与构建脚本共用。"""

from dataclasses import dataclass
import re


FORK_REPOSITORY = "SakuraChiyo0v0/Bilibili-Downloader-plus"
FORK_REPOSITORY_URL = f"https://github.com/{FORK_REPOSITORY}"


_PLUS_VERSION = re.compile(
    r"v?(?P<base>[0-9]+\.[0-9]+\.[0-9]+)(?:-?rc(?P<preview>[1-9][0-9]*))?"
    r"\+plus\.(?P<revision>[1-9][0-9]*)"
)


@dataclass(frozen = True)
class PlusVersion:
    name: str
    base: str
    revision: int
    preview: int | None = None

    @property
    def sort_key(self):
        return (*map(int, self.base.split(".")), self.preview is None, self.preview or 0, self.revision)

    @property
    def rpm_release(self):
        prefix = "1" if self.preview is None else f"0.rc{self.preview}"
        return f"{prefix}.plus.{self.revision}"

    @property
    def debian_version(self):
        preview = f"~rc{self.preview}" if self.preview is not None else ""
        return f"{self.base}{preview}+plus.{self.revision}"


def parse_plus_version(value: str) -> PlusVersion:
    match = _PLUS_VERSION.fullmatch(value)
    if match is None:
        raise ValueError(f"Invalid Plus version: {value!r}; expected X.Y.Z+plus.N")
    return PlusVersion(
        name = value.removeprefix("v"),
        base = match["base"],
        revision = int(match["revision"]),
        preview = int(match["preview"]) if match["preview"] else None,
    )
