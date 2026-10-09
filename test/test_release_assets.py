from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import hashlib

import pytest

from util.common.config import config

ROOT = Path(__file__).resolve().parent.parent
SPEC = spec_from_file_location("prepare_release", ROOT / "scripts/prepare_release.py")
MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
VERSION = config.app_version


def populate(tmp_path):
    artifacts = tmp_path / "assets"
    artifacts.mkdir()
    for name in MODULE.expected_assets(VERSION):
        (artifacts / name).write_bytes(name.encode())
    return artifacts


def test_checksums_cover_every_platform_and_notes_report_unsigned_build(tmp_path):
    artifacts = populate(tmp_path)
    notes = tmp_path / "notes.md"
    MODULE.prepare(artifacts, VERSION, notes, windows_signed = False)
    lines = (artifacts / "SHA256SUMS.txt").read_text(encoding = "utf-8").splitlines()
    assert len(lines) == 13
    for line in lines:
        digest, name = line.split("  ", 1)
        assert digest == hashlib.sha256((artifacts / name).read_bytes()).hexdigest()
    content = notes.read_text(encoding = "utf-8")
    assert "未进行 Authenticode" in content
    assert "\n## 上游 " not in content


@pytest.mark.parametrize("fault", ["missing", "unexpected", "empty"])
def test_incomplete_or_unexpected_assets_block_release_preparation(tmp_path, fault):
    artifacts = populate(tmp_path)
    asset = artifacts / sorted(MODULE.expected_assets(VERSION))[0]
    if fault == "missing":
        asset.unlink()
    elif fault == "empty":
        asset.write_bytes(b"")
    else:
        (artifacts / "private-config.json").write_text("{}")
    notes = tmp_path / "notes.md"
    with pytest.raises(ValueError):
        MODULE.prepare(artifacts, VERSION, notes, windows_signed = False)
    assert not notes.exists()
