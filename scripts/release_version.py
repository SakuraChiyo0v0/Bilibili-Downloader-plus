"""从发行标签生成平台版本，拒绝标签与源码不一致的构建。"""

from pathlib import Path
import argparse
import ast
import sys
import tomllib


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from util.common.version import parse_plus_version


def release_metadata(tag: str):
    version = parse_plus_version(tag)
    return {
        "VERSION": version.base,
        "VERSION_NAME": version.name,
        "IS_PRERELEASE": str(version.preview is not None).lower(),
        "RPM_RELEASE": version.rpm_release,
        "DEB_VERSION": version.debian_version,
    }


def validate_source_version(tag: str):
    expected = parse_plus_version(tag).name
    tree = ast.parse((ROOT / "src/util/common/config.py").read_text(encoding = "utf-8"))
    config_class = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "APPConfig")
    app_version = next(
        ast.literal_eval(node.value)
        for node in config_class.body if isinstance(node, ast.Assign)
        if any(isinstance(target, ast.Name) and target.id == "app_version" for target in node.targets)
    )
    project_version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding = "utf-8"))["project"]["version"]
    if expected != app_version or expected != project_version:
        raise ValueError(f"Release {expected} does not match source versions: app={app_version}, project={project_version}")


def main():
    parser = argparse.ArgumentParser(description = __doc__)
    parser.add_argument("tag")
    parser.add_argument("--github-output", type = Path)
    args = parser.parse_args()
    validate_source_version(args.tag)
    metadata = release_metadata(args.tag)
    output = "".join(f"{key}={value}\n" for key, value in metadata.items())
    if args.github_output:
        with args.github_output.open("a", encoding = "utf-8") as stream:
            stream.write(output)
    else:
        print(output, end = "")


if __name__ == "__main__":
    main()
