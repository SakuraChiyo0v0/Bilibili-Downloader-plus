from ..common.config import config
from ..common.enum import StorageType, ProxyMode
from ..network.proxy import Proxy

from .provider import StorageProvider
from .local import LocalStorageProvider
from .webdav import WebDAVStorageProvider


class StorageProviderFactory:
    @staticmethod
    def create_from_config(storage_type: StorageType | str | None = None) -> StorageProvider:
        # 存储方式由任务固化；凭据仍只读取设置，不写入任务数据库。
        storage_type = StorageType(storage_type if storage_type is not None else config.get(config.storage_type))

        if storage_type == StorageType.WEBDAV:
            return WebDAVStorageProvider(
                url=config.get(config.webdav_url),
                username=config.get(config.webdav_username),
                password=config.get(config.webdav_password),
                base_path=config.get(config.webdav_base_path),
                verify_ssl=config.get(config.webdav_verify_ssl),
                proxies=Proxy().get_proxies(),
                trust_env=config.get(config.proxy_mode) == ProxyMode.SYSTEM,
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
            # 设置页的连接测试与实际上传使用同一代理模式。
            proxies=proxies if proxies is not None else Proxy().get_proxies(),
            trust_env=proxies is None and config.get(config.proxy_mode) == ProxyMode.SYSTEM,
        )
