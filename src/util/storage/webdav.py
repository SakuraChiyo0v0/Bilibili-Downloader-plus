from pathlib import Path
from typing import Callable
from urllib.parse import urljoin, quote

import httpx

from ..common.config import config
from ..common.enum import FileConflictResolution

from .provider import StorageProvider


class WebDAVStorageProvider(StorageProvider):
    def __init__(self, url: str, username: str = "", password: str = "",
                 base_path: str = "/", verify_ssl: bool = True,
                 proxies: dict | None = None, trust_env: bool = False):
        self.url = url.rstrip("/")
        self.base_path = self._normalize_path(base_path)

        auth = None
        if username or password:
            auth = (username, password)

        mounts = None
        if proxies:
            proxy_url = proxies.get("http") or proxies.get("https")
            if proxy_url:
                mounts = {
                    "http://": httpx.HTTPTransport(proxy=proxy_url, verify=verify_ssl),
                    "https://": httpx.HTTPTransport(proxy=proxy_url, verify=verify_ssl),
                }

        self._client = httpx.Client(
            auth=auth,
            verify=verify_ssl,
            mounts=mounts,
            trust_env=trust_env,
            follow_redirects=True,
            timeout=30,
        )

    def _normalize_path(self, path: str) -> str:
        path = path.replace("\\", "/")
        if not path.startswith("/"):
            path = "/" + path
        return path.rstrip("/")

    def _join_url(self, remote_path: str) -> str:
        remote_path = self._normalize_path(remote_path)
        full_path = f"{self.base_path}{remote_path}"
        return urljoin(self.url + "/", quote(full_path.lstrip("/")))

    def _request(self, method: str, remote_path: str, **kwargs):
        url = self._join_url(remote_path)
        response = self._client.request(method, url, **kwargs)
        return response

    def exists(self, remote_path: str) -> bool:
        try:
            response = self._request("PROPFIND", remote_path, headers={"Depth": "0"})
            if response.status_code == 207:
                return True
            if response.status_code == 404:
                return False
            response.raise_for_status()
            return False
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return False
            raise

    def mkdir(self, remote_path: str) -> None:
        remote_path = self._normalize_path(remote_path)
        parts = [p for p in remote_path.split("/") if p]

        current = ""
        for part in parts:
            current = f"{current}/{part}"
            try:
                response = self._request("MKCOL", current)
                # 201/200/204: 创建成功, 405: 已存在(标准), 409: 已存在(AList 等)
                if response.status_code not in (201, 200, 204, 405, 409):
                    response.raise_for_status()
            except httpx.HTTPStatusError as e:
                if e.response.status_code not in (405, 409):
                    raise

    def resolve_conflict(self, remote_path: str) -> str:
        resolution = config.get(config.webdav_conflict_resolution)
        if resolution == FileConflictResolution.OVERWRITE:
            return remote_path

        if not self.exists(remote_path):
            return remote_path

        # 自动重命名：name (1).ext
        remote_path = self._normalize_path(remote_path)
        parts = remote_path.split("/")
        name = parts[-1]
        parent = "/".join(parts[:-1])

        dot = name.rfind(".")
        if dot > 0:
            name_without_suffix = name[:dot]
            suffix = name[dot:]
        else:
            name_without_suffix = name
            suffix = ""

        n = 1
        max_attempts = 1000
        while n <= max_attempts:
            new_name = f"{name_without_suffix} ({n}){suffix}"
            new_path = f"{parent}/{new_name}" if parent else f"/{new_name}"
            if not self.exists(new_path):
                return new_path
            n += 1

        # 超过最大重试次数，直接用时间戳后缀
        import time
        new_name = f"{name_without_suffix}_{int(time.time())}{suffix}"
        return f"{parent}/{new_name}" if parent else f"/{new_name}"

    def upload(self, local_path: Path, remote_path: str,
               progress_callback: Callable[[int], None] | None = None) -> None:
        final_remote = self.resolve_conflict(remote_path)

        parent = final_remote.rsplit("/", 1)[0]
        if parent:
            self.mkdir(parent)

        def file_chunks():
            with open(local_path, "rb") as f:
                while True:
                    chunk = f.read(1024 * 1024)
                    if not chunk:
                        break
                    if progress_callback:
                        progress_callback(len(chunk))
                    yield chunk

        response = self._request("PUT", final_remote, content=file_chunks())
        response.raise_for_status()

    def test_connection(self) -> None:
        try:
            response = self._request("PROPFIND", "/", headers={"Depth": "0"})
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                raise RuntimeError("认证失败，请检查用户名和密码") from e
            raise

        if response.status_code not in (207, 200, 404):
            response.raise_for_status()

    def close(self) -> None:
        self._client.close()
