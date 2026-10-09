from copy import deepcopy
from threading import Event
from unittest.mock import Mock

import pytest

from util.common.enum import ConventionType, DuplicateDownloadResolution, StorageType
from util.common._json import dumps, loads
from util.common.runtime import runtime
from util.download.task.manager import TaskCreationResult
from util.sync.info import SyncSourceInfo
from util.sync.manager import SyncManager
from util.sync.options import capture_download_options, normalize_options, scoped_download_options


@pytest.fixture
def sync(monkeypatch):
    import util.sync.manager as module
    database = Mock()
    database.query_sources.return_value = []
    monkeypatch.setattr(module, "SyncDatabase", lambda: database)
    monkeypatch.setattr(module, "signal_bus", Mock())
    monkeypatch.setattr(module, "task_manager", Mock())
    parser = Mock()
    parser.parse.return_value = {"episodes": [{"bvid": "old"}, {"bvid": "good"}, {"bvid": "bad"}]}
    monkeypatch.setattr(module, "SyncSourceParser", lambda: parser)
    manager = SyncManager()
    source = SyncSourceInfo(sync_id = "source", title = "源", url = "url", known_item_ids = ["video:old"], options = {"global_starting_number": 2})
    manager.source_map[source.sync_id] = source
    cancelled = Event()
    manager.checking_sources[source.sync_id] = cancelled
    yield manager, source, cancelled, module, parser
    manager.shutdown()


def test_only_confirmed_items_enter_sync_ledger(sync):
    manager, source, cancelled, module, _ = sync
    module.task_manager.create.return_value = TaskCreationResult(confirmed_indices = {0}, created_count = 1, errors = {1: "建任务失败"})
    manager._check_source_worker(source.sync_id, cancelled)
    assert source.known_item_ids == ["video:good", "video:old"]
    assert source.last_error == "建任务失败"
    assert source.last_added_count == 1
    assert source.last_success_time == 0
    call = module.task_manager.create.call_args
    assert call.kwargs["wait"] is True
    assert call.kwargs["options"]["duplicate_resolution"] == DuplicateDownloadResolution.SKIP
    assert source.sync_id not in manager.checking_sources


def test_confirmed_duplicate_is_known_without_added_count(sync):
    manager, source, cancelled, module, _ = sync
    module.task_manager.create.return_value = TaskCreationResult(confirmed_indices = {0, 1}, created_count = 0)
    manager._check_source_worker(source.sync_id, cancelled)
    assert source.known_item_ids == ["video:bad", "video:good", "video:old"]
    assert source.last_added_count == 0
    assert not source.last_error
    assert source.last_success_time


@pytest.mark.parametrize("action", ["delete", "disable", "shutdown"])
def test_source_cancelled_during_parse_cannot_create_tasks(sync, action):
    manager, source, cancelled, module, parser = sync
    def parse(url):
        if action == "delete":
            manager.delete_source(source.sync_id)
        elif action == "disable":
            manager.set_enabled(source.sync_id, False)
        else:
            manager.shutdown()
        return {"episodes": [{"bvid": "new"}]}
    parser.parse.side_effect = parse
    manager._check_source_worker(source.sync_id, cancelled)
    module.task_manager.create.assert_not_called()
    assert source.known_item_ids == ["video:old"]
    if action == "delete":
        manager.db_manager.update_source.assert_not_called()
        module.signal_bus.sync.source_updated.emit.assert_not_called()
    assert source.sync_id not in manager.checking_sources


def test_repeated_check_is_scheduled_only_once(sync, monkeypatch):
    manager, source, _, module, _ = sync
    manager.checking_sources.clear()
    dispatch = Mock()
    monkeypatch.setattr(module.GlobalThreadPoolTask, "run_func", dispatch)
    assert manager.check_source(source.sync_id)
    assert not manager.check_source(source.sync_id)
    dispatch.assert_called_once()


def test_initial_download_failure_remains_retryable(sync):
    manager, source, cancelled, module, parser = sync
    module.task_manager.create.return_value = TaskCreationResult(errors = {0: "disk full"})
    manager._check_source_worker(source.sync_id, cancelled, [{"bvid": "selected"}])
    parser.parse.assert_not_called()
    assert source.known_item_ids == ["video:old"]
    assert source.last_error == "disk full"


def test_all_selected_parts_are_created_before_marking_video_known(sync):
    from util.parse.episode.tree import Attribute
    manager, source, cancelled, module, _ = sync
    module.task_manager.create.return_value = TaskCreationResult(confirmed_indices = {0}, created_count = 1, errors = {1: "第二 P 失败"})
    episodes = [
        {"bvid": "selected", "cid": cid, "attribute": Attribute.VIDEO_BIT | Attribute.COLLECTION_BIT}
        for cid in (1, 2)
    ]
    manager._check_source_worker(source.sync_id, cancelled, episodes)
    assert len(module.task_manager.create.call_args.args[0]) == 2
    assert source.known_item_ids == ["video:old"]


def test_old_rule_map_serializes_and_context_restores_global_state():
    from util.common.config import config
    before = capture_download_options()
    old_path = config.get(config.download_path)
    old_temp = config.get(config.local_temp_path)
    old_runtime_rules = deepcopy(runtime.naming.target_rule_ids)
    options = normalize_options({
        "naming_rule_ids": {ConventionType.NORMAL: "removed-rule", "invalid": "ignore"},
        "cleanup_cover_after_attach": False,
        "download_path": "source-cache",
        "storage_type": StorageType.WEBDAV.value,
    })
    assert loads(dumps(options))["naming_rule_ids"] == {"11": "removed-rule"}
    with scoped_download_options(options):
        captured = capture_download_options()
        assert captured["download_path"] == "source-cache"
        assert captured["delete_cover_after_attach"] is False
        assert runtime.naming.target_rule_ids == {ConventionType.NORMAL: "removed-rule"}
        config.set(config.download_path, "edited-cache")
        assert capture_download_options()["download_path"] == "edited-cache"
    assert capture_download_options() == before
    assert config.get(config.download_path) == old_path
    assert config.get(config.local_temp_path) == old_temp
    assert runtime.naming.target_rule_ids == old_runtime_rules


def test_source_database_round_trip_with_migrated_options(tmp_path):
    from util.sync.db import SyncDatabase
    database = SyncDatabase.__new__(SyncDatabase)
    database.path = tmp_path / "sync.db"
    database.check_and_create_table()
    source = SyncSourceInfo(sync_id = "one", options = normalize_options({"naming_rule_ids": {11: "rule"}}))
    try:
        database.add_source(source)
        result = database.query_sources()
        assert len(result) == 1
        assert result[0].options["naming_rule_ids"] == {"11": "rule"}
    finally:
        database.close_connection()
