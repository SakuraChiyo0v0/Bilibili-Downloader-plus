from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib

from packaging.version import Version
import pytest

from util.common.config import config
from util.common.version import parse_plus_version


ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize("older,newer", [
    ("2.20.0+plus.1", "2.20.0+plus.2"),
    ("2.20.0+plus.9", "2.20.0+plus.10"),
    ("2.20.0+plus.99", "2.21.0+plus.1"),
    ("2.21.0-rc1+plus.5", "2.21.0-rc2+plus.1"),
    ("2.21.0-rc9+plus.99", "2.21.0+plus.1"),
])
def test_plus_versions_order_numerically(older, newer):
    assert parse_plus_version(older).sort_key < parse_plus_version(newer).sort_key
    assert Version(older) < Version(newer)


@pytest.mark.parametrize("value", ["2.20.0", "2.20.0-plus.1", "2.20.0+plus.0", "2.20.0+plus.x", "2.20.0+plus.1\n", "2.20.0+other.1"])
def test_invalid_or_non_plus_versions_are_rejected(value):
    with pytest.raises(ValueError):
        parse_plus_version(value)


def test_source_and_package_versions_match():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding = "utf-8"))
    version = parse_plus_version(config.app_version)
    assert project["project"]["version"] == version.name
    assert config.app_comparable_version == version.base
    assert Version(version.name).is_prerelease == (version.preview is not None)
    setup = (ROOT / "assets/setup.iss").read_text(encoding = "utf-8")
    assert f'#define MyAppVersion "{version.base}"' in setup
    assert f'#define MyAppVersionName "{version.name}"' in setup


def test_release_cli_emits_platform_metadata(tmp_path):
    output = tmp_path / "github-output"
    output.write_text("EXISTING=value\n", encoding = "utf-8")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/release_version.py"), f"v{config.app_version}", "--github-output", str(output)],
        capture_output = True, text = True, timeout = 30,
    )
    assert result.returncode == 0, result.stderr
    data = dict(line.split("=", 1) for line in output.read_text(encoding = "utf-8").splitlines())
    version = parse_plus_version(config.app_version)
    assert data["EXISTING"] == "value"
    assert data["VERSION"] == version.base
    assert data["VERSION_NAME"] == config.app_version
    assert data["IS_PRERELEASE"] == str(version.preview is not None).lower()
    assert data["RPM_RELEASE"] == version.rpm_release
    assert data["DEB_VERSION"] == version.debian_version


def test_release_cli_rejects_mislabeled_source(tmp_path):
    output = tmp_path / "github-output"
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/release_version.py"), "v9.99.0+plus.1", "--github-output", str(output)],
        capture_output = True, text = True, timeout = 30,
    )
    assert result.returncode != 0
    assert "does not match source versions" in result.stderr
    assert not output.exists()


def test_preview_release_metadata_uses_numeric_base():
    spec = spec_from_file_location("plus_release_script", ROOT / "scripts/release_version.py")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.release_metadata("v2.21.0-rc2+plus.3") == {
        "VERSION": "2.21.0", "VERSION_NAME": "2.21.0-rc2+plus.3",
        "IS_PRERELEASE": "true", "RPM_RELEASE": "0.rc2.plus.3",
        "DEB_VERSION": "2.21.0~rc2+plus.3",
    }


@pytest.mark.skipif(shutil.which("cmake") is None, reason = "CMake is not installed")
@pytest.mark.parametrize("version", ["2.20.0+plus.1", "2.20.0-rc1+plus.2", "2.20.0"])
def test_real_cmake_keeps_suffix_out_of_numeric_resources(tmp_path, version):
    script = tmp_path / "version-test.cmake"
    script.write_text(
        f'set(CMAKE_CURRENT_BINARY_DIR "{tmp_path.as_posix()}")\n'
        f'set(PYSTAND_APP_VERSION "{version}")\n'
        f'include("{(ROOT / "launcher/version.cmake").as_posix()}")\n',
        encoding = "utf-8",
    )
    result = subprocess.run([shutil.which("cmake"), "-P", str(script)], capture_output = True, text = True, timeout = 30)
    assert result.returncode == 0, result.stderr
    header = (tmp_path / "version.h").read_text(encoding = "utf-8")
    assert "#define APP_VER_CSV 2,20,0,0" in header
    assert '#define APP_VER_STR "2.20.0.0"' in header
    assert f'#define APP_DISPLAY_VERSION "{version}"' in header
