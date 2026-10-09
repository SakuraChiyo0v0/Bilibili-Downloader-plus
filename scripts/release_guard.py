"""公开发行不自动重建或覆盖；允许首次构建与草稿修复。"""

from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen
import argparse
import json
import os


def is_published(repository: str, tag: str, token: str = "") -> bool:
    request = Request(
        f"https://api.github.com/repos/{repository}/releases/tags/{quote(tag, safe = '')}",
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "Bilibili-Downloader-plus-release-guard"},
    )
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urlopen(request, timeout = 30) as response:
            release = json.load(response)
    except HTTPError as error:
        if error.code == 404:
            return False
        raise
    if not isinstance(release, dict) or not isinstance(release.get("draft"), bool):
        raise ValueError("Invalid GitHub release response")
    return not release["draft"]


def main():
    parser = argparse.ArgumentParser(description = __doc__)
    parser.add_argument("tag")
    parser.add_argument("--repository", default = os.environ.get("GITHUB_REPOSITORY", "SakuraChiyo0v0/Bilibili-Downloader-plus"))
    parser.add_argument("--github-output", type = Path)
    args = parser.parse_args()
    published = is_published(args.repository, args.tag, os.environ.get("GH_TOKEN", ""))
    value = f"SHOULD_BUILD={str(not published).lower()}\n"
    if args.github_output:
        with args.github_output.open("a", encoding = "utf-8") as stream:
            stream.write(value)
    print("Release is already public; skip rebuilding published assets." if published else "New or draft release; build allowed.")
    print(value, end = "")


if __name__ == "__main__":
    main()
