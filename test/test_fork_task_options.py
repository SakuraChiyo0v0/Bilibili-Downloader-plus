from concurrent.futures import ThreadPoolExecutor
from threading import Event, Lock
from unittest.mock import Mock

import pytest

from util.common.enum import NumberingType, StorageType, VideoContainer
from util.common.runtime import runtime
from util.download.task.info import TaskInfo
from util.download.task.manager import TaskManager
from util.parse.episode.tree import Attribute


def test_legacy_options_migrate_without_overwriting_new_snapshot():
    task = TaskInfo()
    task.from_dict({
        "File": {"storage_type": "webdav", "additional_files": ["cover.jpg"]},
        "Download": {"video_container": "mkv", "m4a_to_mp3": False, "attach_cover": -1,
                     "cleanup_cover_after_attach": True, "subtitle_language": {},
                     "danmaku_style": {"font": "旧样式"}, "auto_tag": True},
        "Options": {"auto_tag": False, "video_container": "mp4"},
    })
    assert task.Options.video_container == "mp4"
    assert task.Options.auto_tag is False
    assert task.Options.m4a_to_mp3 is False
    assert task.Options.attach_cover is None
    assert task.Options.subtitle_language is None
    assert task.Options.delete_cover_after_attach is True
    assert task.Options.danmaku_style == {"font": "旧样式"}
    assert task.Options.storage_type == "webdav"
    assert task.File.additional_files == ["cover.jpg"]
    restored = TaskInfo()
    restored.from_dict(task.to_dict())
    assert restored.to_dict() == task.to_dict()


def test_task_snapshot_has_fork_options_without_credentials():
    from util.download.task.options import snapshot
    data = snapshot({"storage_type": StorageType.WEBDAV, "cleanup_after_upload": False})
    assert data["storage_type"] == "webdav"
    assert data["cleanup_after_upload"] is False
    assert not any("password" in key or "username" in key for key in data)


def test_legacy_upstream_task_remains_local_when_global_storage_changes(monkeypatch):
    from util.common.config import config
    from util.download.task.options import resolve
    original_get = config.get
    monkeypatch.setattr(config, "get", lambda item: StorageType.WEBDAV if item is config.storage_type else original_get(item))
    task = TaskInfo()
    task.from_dict({"Basic": {"task_id": "upstream-old"}})
    assert resolve(task, "storage_type") == StorageType.LOCAL


@pytest.fixture
def manager(monkeypatch):
    import util.download.task.manager as module
    obj = TaskManager.__new__(TaskManager)
    obj._numbering_lock = Lock()
    obj._update_lock = Lock()
    obj._pending_updates = {}
    obj._update_flush_scheduled = False
    obj._update_executor = ThreadPoolExecutor(max_workers = 1)
    obj.db_manager = Mock()
    obj.db_manager.check_duplicate.return_value = False
    obj.db_manager.build_record.side_effect = lambda task: (task.Basic.task_id, task.to_dict())
    monkeypatch.setattr(module, "signal_bus", Mock())
    obj._signals = module.signal_bus
    def convert(episode, number, options):
        if episode.get("fail"):
            raise ValueError("创建失败")
        task = TaskInfo()
        task.Basic.task_id = episode["title"]
        task.Episode.number = number
        return task
    monkeypatch.setattr(obj, "_TaskManager__episode_info_to_task_info", convert)
    yield obj
    obj._update_executor.shutdown()


def source_options():
    return {"numbering_type": NumberingType.CONTINUOUS.value, "global_starting_number": 8}


def test_failed_creation_is_not_confirmed_and_number_is_rolled_back(manager):
    options = source_options()
    result = manager.create([{"title": "bad", "fail": True}, {"title": "good"}], options = options, wait = True)
    assert result.confirmed_indices == {1}
    assert result.errors == {0: "创建失败"}
    assert result.created_count == 1
    assert options["global_starting_number"] == 9
    assert manager.db_manager.add_task_records.call_args.args[0][0][1]["Episode"]["number"] == 8


def test_database_failure_does_not_confirm_or_publish_task(manager):
    manager.db_manager.add_task_records.side_effect = OSError("disk full")
    options = source_options()
    result = manager.create([{"title": "a"}], options = options, wait = True)
    assert not result.confirmed_indices
    assert result.errors
    assert options["global_starting_number"] == 8
    manager._signals.download.add_to_downloading_list.emit.assert_not_called()


def test_confirmation_waits_for_database_commit(manager):
    entered, release = Event(), Event()
    def persist(records):
        entered.set()
        assert release.wait(5)
    manager.db_manager.add_task_records.side_effect = persist
    with ThreadPoolExecutor(max_workers = 1) as pool:
        future = pool.submit(manager.create, [{"title": "a"}], options = source_options(), wait = True)
        try:
            assert entered.wait(5)
            assert not future.done()
            manager._signals.download.add_to_downloading_list.emit.assert_not_called()
        finally:
            release.set()
        assert future.result().confirmed_indices == {0}


def test_partial_reparse_failure_does_not_confirm_parent(manager, monkeypatch):
    from util.download.task.reparse_worker import ReparseWorker
    monkeypatch.setattr(ReparseWorker, "parse_episodes", lambda self: [{"title": "part1"}, {"title": "part2", "fail": True}])
    result = manager.create([{"title": "parent", "attribute": Attribute.NEED_PARSE_BIT}], options = source_options(), wait = True)
    assert not result.confirmed_indices
    assert result.created_count == 1
    assert result.errors[0] == "创建失败"


def test_reparse_duplicate_child_is_confirmed_without_another_task(manager, monkeypatch):
    from util.download.task.reparse_worker import ReparseWorker
    monkeypatch.setattr(ReparseWorker, "parse_episodes", lambda self: [{"title": "exists"}, {"title": "new"}])
    monkeypatch.setattr(manager, "_check_duplicate", lambda episode, options: episode["title"] == "exists")
    result = manager.create([{"title": "parent", "attribute": Attribute.NEED_PARSE_BIT}], options = source_options(), wait = True)
    assert result.confirmed_indices == {0}
    assert result.created_count == 1


def test_cancellation_after_build_prevents_storage(manager):
    checks = iter([True, False])
    options = source_options()
    result = manager.create([{"title": "a"}], options = options, wait = True, should_continue = lambda: next(checks))
    assert not result.confirmed_indices
    assert options["global_starting_number"] == 8
    manager.db_manager.add_task_records.assert_not_called()


def test_source_numbering_is_unique_and_does_not_change_runtime(manager):
    before = (runtime.naming.global_starting_number, runtime.naming.current_starting_number)
    options = source_options()
    with ThreadPoolExecutor(max_workers = 4) as pool:
        numbers = list(pool.map(lambda _: manager._TaskManager__reserve_number({}, options)[0], range(50)))
    assert sorted(numbers) == list(range(8, 58))
    assert (runtime.naming.global_starting_number, runtime.naming.current_starting_number) == before


def test_confirmed_update_propagates_disk_failure(manager):
    manager.db_manager.update_task_json_many.side_effect = OSError("disk full")
    with pytest.raises(OSError, match = "disk full"):
        manager.update(TaskInfo(), wait = True)


def test_task_creation_respects_saved_path_and_string_rule_keys(monkeypatch):
    from util.common.enum import ConventionType
    from util.common.naming_rules import load_rules
    from util.download.task.manager import cover_manager
    monkeypatch.setattr(cover_manager, "arrange_cover_id", lambda _: "")
    rule = next(rule for rule in load_rules() if rule["type"] == ConventionType.NORMAL)
    manager = TaskManager.__new__(TaskManager)
    task = manager._TaskManager__episode_info_to_task_info(
        {"title": "示例", "attribute": Attribute.VIDEO_BIT | Attribute.NORMAL_BIT}, 1,
        {"download_path": "source-cache", "storage_type": "webdav", "video_container": VideoContainer.MKV.value,
         "naming_rule_ids": {str(int(ConventionType.NORMAL)): rule["id"]}},
    )
    assert task.File.download_path == "source-cache"
    assert task.Naming.rule_id == rule["id"]
    assert task.Options.video_container == VideoContainer.MKV.value
