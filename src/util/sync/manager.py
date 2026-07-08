from copy import deepcopy
from uuid import uuid4
import logging

from PySide6.QtCore import QObject, QTimer

from ..common.enum import NumberingType
from ..common.signal_bus import signal_bus
from ..common.timestamp import get_timestamp_ms
from ..download.task.manager import task_manager
from ..thread.pool import GlobalThreadPoolTask
from .db import SyncDatabase
from .info import SyncSourceInfo
from .options import capture_download_options
from .parser import SyncSourceParser, calc_episode_key

logger = logging.getLogger(__name__)


class SyncManager(QObject):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.db_manager = SyncDatabase()
        self.source_map: dict[str, SyncSourceInfo] = {
            source.sync_id: source for source in self.db_manager.query_sources()
        }
        self.checking_sources = set()
        self.started = False

        self.timer = QTimer(self)
        self.timer.setInterval(30 * 60 * 1000)
        self.timer.timeout.connect(self.check_all)

        signal_bus.sync.check_source.connect(self.check_source)
        signal_bus.sync.check_all.connect(self.check_all)

    def start(self):
        if self.started:
            return

        self.started = True
        self.timer.start()
        QTimer.singleShot(15 * 1000, self.check_all)

    def sources(self):
        return list(self.source_map.values())

    def add_or_update_source(self, title: str, url: str, source_type: str, episodes: list[dict], options: dict = None):
        if not source_type:
            raise ValueError("Unsupported sync source")

        existing = self._find_source_by_url(url)
        known_item_ids = self._calc_known_item_ids(episodes)
        now = get_timestamp_ms()

        if existing:
            source = existing
            source.title = title or source.title
            source.source_type = source_type or source.source_type
            source.known_item_ids = sorted(set(source.known_item_ids) | set(known_item_ids))
            source.options = deepcopy(options or source.options or capture_download_options())
            source.updated_time = now
            self.db_manager.update_source(source)
            signal_bus.sync.source_updated.emit(source)

            return source

        source = SyncSourceInfo(
            sync_id = str(uuid4()),
            title = title,
            url = url,
            source_type = source_type,
            enabled = True,
            created_time = now,
            updated_time = now,
            known_item_ids = known_item_ids,
            options = deepcopy(options or capture_download_options()),
        )

        self.source_map[source.sync_id] = source
        self.db_manager.add_source(source)
        signal_bus.sync.source_added.emit(source)

        return source

    def update_source_options(self, sync_id: str, options: dict = None):
        source = self.source_map.get(sync_id)

        if not source:
            return

        source.options = deepcopy(options or capture_download_options())
        source.updated_time = get_timestamp_ms()
        self.db_manager.update_source(source)
        signal_bus.sync.source_updated.emit(source)

    def set_enabled(self, sync_id: str, enabled: bool):
        source = self.source_map.get(sync_id)

        if not source:
            return

        source.enabled = enabled
        source.updated_time = get_timestamp_ms()
        self.db_manager.update_source(source)
        signal_bus.sync.source_updated.emit(source)

    def delete_source(self, sync_id: str):
        if sync_id not in self.source_map:
            return

        self.source_map.pop(sync_id)
        self.db_manager.delete_source(sync_id)
        signal_bus.sync.source_removed.emit(sync_id)

    def check_all(self):
        for source in self.sources():
            if source.enabled:
                self.check_source(source.sync_id)

    def check_source(self, sync_id: str):
        source = self.source_map.get(sync_id)

        if not source or not source.enabled or sync_id in self.checking_sources:
            return

        self.checking_sources.add(sync_id)
        GlobalThreadPoolTask.run_func(self._check_source_worker, sync_id)

    def _check_source_worker(self, sync_id: str):
        source = self.source_map.get(sync_id)

        if not source:
            self.checking_sources.discard(sync_id)
            return

        now = get_timestamp_ms()

        try:
            parsed = SyncSourceParser().parse(source.url)
            episodes = parsed["episodes"]
            known_ids = set(source.known_item_ids)
            new_episodes = []
            new_ids = []

            for episode in episodes:
                item_id = calc_episode_key(episode)

                if item_id not in known_ids:
                    known_ids.add(item_id)
                    new_ids.append(item_id)
                    new_episodes.append(episode)

            if new_episodes:
                options = deepcopy(source.options)
                options["skip_duplicate_prompt"] = True
                task_manager.create_with_options(new_episodes, options)
                self._advance_global_number(source, len(new_episodes))

            source.title = parsed.get("title") or source.title
            source.source_type = parsed.get("source_type") or source.source_type
            source.known_item_ids = sorted(known_ids)
            source.last_added_count = len(new_episodes)
            source.last_error = ""
            source.last_checked_time = now
            source.last_success_time = now
            source.updated_time = now

        except Exception as e:
            logger.exception("Sync check failed: %s", source.title)
            source.last_error = str(e)
            source.last_added_count = 0
            source.last_checked_time = now
            source.updated_time = now

        finally:
            self.db_manager.update_source(source)
            signal_bus.sync.source_updated.emit(source)
            self.checking_sources.discard(sync_id)

    def _advance_global_number(self, source: SyncSourceInfo, count: int):
        if count <= 0:
            return

        try:
            numbering_type = NumberingType(source.options.get("numbering_type"))
        except ValueError:
            return

        if numbering_type == NumberingType.CONTINUOUS:
            source.options["global_starting_number"] = source.options.get("global_starting_number", 1) + count

    def _find_source_by_url(self, url: str):
        for source in self.source_map.values():
            if source.url == url:
                return source

        return None

    def _calc_known_item_ids(self, episodes: list[dict]):
        return sorted({calc_episode_key(episode) for episode in episodes})


sync_manager = SyncManager()

