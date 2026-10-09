from copy import deepcopy
from threading import Event, RLock
from uuid import uuid4
import logging

from PySide6.QtCore import QObject, QTimer

from ..common.enum import DuplicateDownloadResolution
from ..common.signal_bus import signal_bus
from ..common.timestamp import get_timestamp_ms
from ..download.task.manager import task_manager
from ..parse.episode.tree import EpisodeData
from ..thread.pool import GlobalThreadPoolTask
from .db import SyncDatabase
from .info import SyncSourceInfo
from .options import capture_download_options, normalize_options
from .parser import SyncSourceParser, calc_episode_key

logger = logging.getLogger(__name__)


class SyncManager(QObject):
    def __init__(self, parent = None):
        super().__init__(parent)
        self.db_manager = SyncDatabase()
        self.source_map = {source.sync_id: source for source in self.db_manager.query_sources()}
        self._lock = RLock()
        self.checking_sources: dict[str, Event] = {}
        self.started = False
        self._closing = False
        self.timer = QTimer(self)
        self.timer.setInterval(30 * 60 * 1000)
        self.timer.timeout.connect(self.check_all)
        signal_bus.sync.check_source.connect(self.check_source)
        signal_bus.sync.check_all.connect(self.check_all)

    def start(self):
        if self.started or self._closing:
            return
        self.started = True
        self.timer.start()
        QTimer.singleShot(15 * 1000, self.check_all)

    def shutdown(self):
        self.timer.stop()
        with self._lock:
            self._closing = True
            for cancelled in self.checking_sources.values():
                cancelled.set()

    def sources(self):
        with self._lock:
            return list(self.source_map.values())

    def add_or_update_source(self, title: str, url: str, source_type: str, episodes: list[dict], options: dict = None):
        if not source_type:
            raise ValueError("Unsupported sync source")
        with self._lock:
            source = self._find_source_by_url(url)
            known_item_ids = self._calc_known_item_ids(episodes)
            now = get_timestamp_ms()
            if source:
                self._cancel_check(source.sync_id)
                source.title = title or source.title
                source.source_type = source_type
                source.known_item_ids = sorted(set(source.known_item_ids) | set(known_item_ids))
                source.options = normalize_options(options if options is not None else source.options or capture_download_options())
                source.updated_time = now
                self.db_manager.update_source(source)
                signal_bus.sync.source_updated.emit(source)
            else:
                source = SyncSourceInfo(
                    sync_id = str(uuid4()), title = title, url = url, source_type = source_type,
                    enabled = True, created_time = now, updated_time = now,
                    known_item_ids = known_item_ids,
                    options = normalize_options(options if options is not None else capture_download_options()),
                )
                self.db_manager.add_source(source)
                self.source_map[source.sync_id] = source
                signal_bus.sync.source_added.emit(source)
            return source

    def update_source_options(self, sync_id: str, options: dict = None):
        with self._lock:
            source = self.source_map.get(sync_id)
            if not source:
                return
            self._cancel_check(sync_id)
            source.options = normalize_options(options if options is not None else capture_download_options())
            source.updated_time = get_timestamp_ms()
            self.db_manager.update_source(source)
            signal_bus.sync.source_updated.emit(source)

    def set_enabled(self, sync_id: str, enabled: bool):
        with self._lock:
            source = self.source_map.get(sync_id)
            if not source:
                return
            if not enabled:
                self._cancel_check(sync_id)
            source.enabled = enabled
            source.updated_time = get_timestamp_ms()
            self.db_manager.update_source(source)
            signal_bus.sync.source_updated.emit(source)

    def delete_source(self, sync_id: str):
        with self._lock:
            if sync_id not in self.source_map:
                return
            self._cancel_check(sync_id)
            self.db_manager.delete_source(sync_id)
            self.source_map.pop(sync_id)
            signal_bus.sync.source_removed.emit(sync_id)

    def _cancel_check(self, sync_id: str):
        cancelled = self.checking_sources.get(sync_id)
        if cancelled:
            cancelled.set()

    def check_all(self):
        for source in self.sources():
            if source.enabled:
                self.check_source(source.sync_id)

    def check_source(self, sync_id: str):
        return self._schedule_check(sync_id)

    def download_initial(self, sync_id: str, episodes: list[dict]):
        """首次勾选下载也走同一条确认路径；失败条目留给下轮同步重试。"""
        return self._schedule_check(sync_id, deepcopy(episodes))

    def _schedule_check(self, sync_id: str, initial_episodes = None):
        with self._lock:
            source = self.source_map.get(sync_id)
            if self._closing or not source or not source.enabled or sync_id in self.checking_sources:
                return False
            cancelled = Event()
            self.checking_sources[sync_id] = cancelled
        try:
            GlobalThreadPoolTask.run_func(self._check_source_worker, sync_id, cancelled, initial_episodes)
        except Exception:
            with self._lock:
                self.checking_sources.pop(sync_id, None)
            raise
        return True

    def _check_source_worker(self, sync_id: str, cancelled: Event, initial_episodes = None):
        with self._lock:
            source = self.source_map.get(sync_id)
            if source is None:
                self.checking_sources.pop(sync_id, None)
                return
            saved_options = deepcopy(source.options)
            options = normalize_options(saved_options)
            known_ids = set(source.known_item_ids)
            url = source.url
        now = get_timestamp_ms()
        confirmed_ids = set()
        created_count = 0
        error_message = ""
        parsed = {}

        def can_continue():
            with self._lock:
                return not self._closing and not cancelled.is_set() and self.source_map.get(sync_id) is source and source.enabled

        try:
            # 同步解析和界面解析共享 EpisodeData；遵循上游的解析作用域避免互相清缓存。
            with EpisodeData.parsing(clear_cache = False):
                if not can_continue():
                    return
                parsed = SyncSourceParser().parse(url) if initial_episodes is None else {"episodes": initial_episodes}
                new_episodes = []
                item_indices = {}
                seen_entries = set()
                for episode in parsed["episodes"]:
                    item_id = calc_episode_key(episode)
                    entry_id = (item_id, episode.get("cid"), episode.get("ep_id"), episode.get("sid"))
                    if item_id not in known_ids and entry_id not in seen_entries:
                        # 同一个稿件可有多个已解析分 P；全部创建成功才确认稿件，不能只取第一 P。
                        seen_entries.add(entry_id)
                        item_indices.setdefault(item_id, []).append(len(new_episodes))
                        new_episodes.append(episode)
                if not can_continue():
                    return
                if new_episodes:
                    options["duplicate_resolution"] = DuplicateDownloadResolution.SKIP
                    result = task_manager.create(new_episodes, options = options, wait = True, should_continue = can_continue)
                    confirmed_ids = {item_id for item_id, indices in item_indices.items() if all(index in result.confirmed_indices for index in indices)}
                    created_count = result.created_count
                    error_message = "; ".join(dict.fromkeys(result.errors.values()))
        except Exception as error:
            logger.exception("Sync check failed: %s", source.title)
            error_message = str(error)
        finally:
            with self._lock:
                # 删除后的工作线程不能重新写入或再次向 UI 发送该源。
                if self.source_map.get(sync_id) is source:
                    source.known_item_ids = sorted(set(source.known_item_ids) | confirmed_ids)
                    if source.options == saved_options:
                        for key in ("global_starting_number", "current_starting_number"):
                            if key in options:
                                source.options[key] = options[key]
                    source.title = parsed.get("title") or source.title
                    source.source_type = parsed.get("source_type") or source.source_type
                    source.last_added_count = created_count
                    source.last_error = error_message or ("同步已取消" if cancelled.is_set() or self._closing else "")
                    source.last_checked_time = now
                    if not source.last_error:
                        source.last_success_time = now
                    source.updated_time = get_timestamp_ms()
                    try:
                        self.db_manager.update_source(source)
                        signal_bus.sync.source_updated.emit(source)
                    except Exception:
                        logger.exception("保存同步源失败: %s", sync_id)
                if self.checking_sources.get(sync_id) is cancelled:
                    self.checking_sources.pop(sync_id, None)

    def _find_source_by_url(self, url: str):
        return next((source for source in self.source_map.values() if source.url == url), None)

    def _calc_known_item_ids(self, episodes: list[dict]):
        return sorted({calc_episode_key(episode) for episode in episodes})


sync_manager = SyncManager()
