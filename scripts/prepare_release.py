"""验证完整发行资产集合，生成校验和与本版发布说明。"""

from pathlib import Path
import argparse
import hashlib
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from util.common.version import parse_plus_version


def expected_assets(version: str) -> set[str]:
    version = parse_plus_version(version).name
    prefix = f"Bili23-Downloader_{version}"
    names = {
        f"{prefix}_windows_x64.exe",
        f"{prefix}_windows_x64_portable.zip",
        f"{prefix}_windows_x64_for_win7.exe",
        f"{prefix}_macos_x86_64.dmg",
        f"{prefix}_macos_aarch64.dmg",
    }
    for arch, gnu_arch in (("amd64", "x86_64"), ("arm64", "aarch64")):
        names.update({
            f"{prefix}_linux_{arch}_portable.tar.gz",
            f"{prefix}_linux_{arch}.deb",
            f"{prefix}_linux_{gnu_arch}.rpm",
            f"{prefix}_linux_{gnu_arch}.AppImage",
        })
    return names


def prepare(artifacts: Path, version: str, notes: Path, windows_signed: bool):
    version = parse_plus_version(version).name
    expected = expected_assets(version)
    actual = {path.name for path in artifacts.iterdir() if path.name != "SHA256SUMS.txt"}
    if actual != expected:
        raise ValueError(f"Release asset mismatch: missing={sorted(expected - actual)}, unexpected={sorted(actual - expected)}")

    checksums = []
    for name in sorted(expected):
        path = artifacts / name
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f"Empty release asset: {name}")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        checksums.append(f"{digest.hexdigest()}  {name}\n")
    (artifacts / "SHA256SUMS.txt").write_text("".join(checksums), encoding = "utf-8")

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding = "utf-8")
    if not changelog.startswith(f"## {version}"):
        raise ValueError("CHANGELOG does not start with the release version")
    content = changelog.split("\n---", 1)[0].rstrip()
    signing = "Windows 启动器和安装包已按本仓库配置执行数字签名。" if windows_signed else (
        "**Windows 安装包与启动器未进行 Authenticode 数字签名。** "
        "本仓库没有配置签名证书，系统可能显示未知发布者提示；请通过本 Release 获取安装包并核对 SHA256。"
    )
    content += f"""

### 安装包与校验

- Windows：安装包、便携 ZIP，以及文件名含 `for_win7` 的兼容安装包。
- Linux：amd64／arm64 的便携包、DEB、RPM、AppImage。
- macOS：Intel 与 Apple Silicon 的 DMG；本次未执行 Apple 签名或公证。
- `SHA256SUMS.txt` 包含全部 13 个安装／便携产物的 SHA256。

{signing}

增强版使用方式与限制见 [本仓库 README](https://github.com/SakuraChiyo0v0/Bilibili-Downloader-plus#readme)。
本项目基于 [ScottSloan/Bili23-Downloader](https://github.com/ScottSloan/Bili23-Downloader) 独立维护，不向上游发起 PR。
"""
    notes.write_text(content, encoding = "utf-8")
    return checksums


def main():
    parser = argparse.ArgumentParser(description = __doc__)
    parser.add_argument("artifacts", type = Path)
    parser.add_argument("version")
    parser.add_argument("--notes", type = Path, default = Path("release-notes.md"))
    parser.add_argument("--windows-signed", choices = ("true", "false"), default = "false")
    args = parser.parse_args()
    checksums = prepare(args.artifacts, args.version, args.notes, args.windows_signed == "true")
    print(f"Validated {len(checksums)} release assets; SHA256SUMS.txt and {args.notes} generated.")


if __name__ == "__main__":
    main()
