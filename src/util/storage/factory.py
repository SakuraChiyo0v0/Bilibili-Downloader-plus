from ..common.config import config
from ..common.enum import StorageType
from ..network.proxy import Proxy

from .provider import StorageProvider
from .local import LocalStorageProvider
from .webdav import WebDAVStorageProvider


class StorageProviderFactory:
    @staticmethod
    def create_from_config() -> StorageProvider:
        storage_type = config.get(config.storage_type)

        if storage_type == StorageType.WEBDAV:
            return WebDAVStorageProvider(
                url=config.get(config.webdav_url),
                username=config.get(config.webdav_username),
                password=config.get(config.webdav_password),
                base_path=config.get(config.webdav_base_path),
                verify_ssl=config.get(config.webdav_verify_ssl),
                proxies=Proxy().get_proxies() if config.get(config.proxy_enabled) else None,
            )

        return LocalStorageProvider()

    @staticmethod
    def create_webdav(url: str = None, username: str = None, password: str = None,
                      base_path: str = None, verify_ssl: bool = True,
                      proxies: dict | None = None) -> WebDAVStorageProvider:
        return WebDAVStorageProvider(
            url=url if url is not None else config.get(config.webdav_url),
            username=username if username is not None else config.get(config.webdav_username),
            password=password if password is not None else config.get(config.webdav_password),
            base_path=base_path if base_path is not None else config.get(config.webdav_base_path),
            verify_ssl=verify_ssl,
            proxies=proxies,
        )
