"""增强入口使用上游控件、选项和任务生命周期的离线回归。"""
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QApplication, QWidget
from qfluentwidgets import ConfigItem

from util.common.config import APPConfig, config
from util.common.enum import ConventionType, CoverType, DownloadStatus, StorageType
from util.common.runtime import runtime


@pytest.fixture(scope = "module")
def app():
    instance = QApplication.instance() or QApplication([])
    import res.resources_rc  # noqa: F401
    return instance


@pytest.fixture(autouse = True)
def restore_config(monkeypatch):
    items = [item for item in vars(APPConfig).values() if isinstance(item, ConfigItem)]
    values = [(item, deepcopy(config.get(item))) for item in items]
    download_state = vars(runtime.download).copy()
    naming_state = deepcopy(vars(runtime.naming))
    monkeypatch.setattr(config, "save", lambda: None)
    from util.thread.pool import GlobalThreadPoolTask
    monkeypatch.setattr(GlobalThreadPoolTask, "run_func", lambda *args, **kwargs: None)
    yield
    for item, value in values:
        config.set(item, value, save = False)
    vars(runtime.download).update(download_state)
    vars(runtime.naming).update(naming_state)


def test_audio_cover_uses_upstream_cleanup_toggle(app):
    from gui.component.setting.card import CoverSettingCard
    config.set(config.download_cover, True)
    config.set(config.cover_type, CoverType.JPG)
    config.set(config.attach_cover, False)
    config.set(config.attach_cover_audio, True)
    card = CoverSettingCard()
    assert card.delete_cover_after_attach_group.isEnabled()
    card.delete_cover_after_attach_switch.setChecked(True)
    assert config.get(config.delete_cover_after_attach) is True
    card.attach_cover_audio_switch.setChecked(False)
    assert not card.delete_cover_after_attach_group.isEnabled()
    assert config.get(config.delete_cover_after_attach) is False
    card.attach_cover_audio_switch.setChecked(True)
    card.type_choice.setCurrentIndex(card.type_choice.findData(CoverType.AVIF))
    assert not card.attach_cover_audio_switch.isChecked()
    assert not card.attach_cover_audio_group.isEnabled()


def test_sync_options_work_without_preview_and_restore_source_rules(app, monkeypatch):
    from gui.dialog.download_options.dialog import DownloadOptionsDialog
    from util.parse.preview.info import PreviewerInfo
    from util.sync.options import capture_download_options, scoped_download_options

    monkeypatch.setattr(PreviewerInfo, "video_quality_choice_data", {})
    monkeypatch.setattr(PreviewerInfo, "audio_quality_choice_data", {})
    custom = {"id": "sync-rule", "name": "Sync", "type": 40, "rule": "{leaf_title}", "default": False}
    config.set(config.naming_rule_list, deepcopy(config.get(config.naming_rule_list)) + [custom])
    parent = QWidget()
    parent.parse_interface = SimpleNamespace(download_options_dialog_opened = False)
    original_quality = runtime.download.audio_quality_id
    options = capture_download_options()
    options.update({"audio_quality_id": 30251, "naming_rule_ids": {"40": "sync-rule"}})
    with scoped_download_options(options):
        dialog = DownloadOptionsDialog(parent, {ConventionType.FAVORITE}, sync_mode = True)
        assert dialog.media_settings_page.media_info_card.audio_quality_id == 30251
        assert dialog.media_settings_page.media_info_card.video_quality_widget.choice.count() > 0
        assert dialog.media_settings_page.media_info_card.audio_quality_widget.custom_btn.isHidden()
        assert dialog.download_settings_page.show_dialog_card.isHidden()
        assert dialog.download_settings_page.naming_convention_card.rule_ids == {ConventionType.FAVORITE: "sync-rule"}
        assert parent.parse_interface.download_options_dialog_opened is True
        dialog.close()
    assert runtime.download.audio_quality_id == original_quality
    assert parent.parse_interface.download_options_dialog_opened is False


def test_storage_card_keeps_upstream_download_path(app):
    from gui.component.setting.storage_card import StorageSettingCard
    config.set(config.storage_type, StorageType.LOCAL)
    config.set(config.download_path, "D:/downloads")
    config.set(config.local_temp_path, "D:/cache")
    parent = QWidget()
    card = StorageSettingCard(parent)
    assert not card.path_group.isEnabled()
    card.storage_type_choice.setCurrentIndex(card.storage_type_choice.findData(StorageType.WEBDAV))
    assert card.path_group.isEnabled()
    assert card._cache_path() == "D:/cache"
    assert config.get(config.download_path) == "D:/downloads"


def test_initial_sync_keeps_selected_items_pending_until_task_creation(app, monkeypatch):
    from gui.interface.parse import ParseInterface
    from util.sync.manager import sync_manager
    from util.sync import parser

    selected = {"bvid": "BV_selected", "cid": 1}
    unselected = {"bvid": "BV_baseline", "cid": 2}
    source = SimpleNamespace(sync_id = "source")
    add = Mock(return_value = source)
    queue = Mock(return_value = True)
    monkeypatch.setattr(sync_manager, "add_or_update_source", add)
    monkeypatch.setattr(sync_manager, "download_initial", queue)
    monkeypatch.setattr(parser, "detect_sync_source_type", lambda *_: "collection")
    parse_list = SimpleNamespace(
        get_checked_items = lambda **_: [selected],
        get_all_items = lambda: [SimpleNamespace(to_dict = lambda: selected), SimpleNamespace(to_dict = lambda: unselected)],
        _model = SimpleNamespace(root_node = SimpleNamespace(count = lambda: 0)),
    )
    page = SimpleNamespace(parse_list = parse_list, url_box = SimpleNamespace(text = lambda: "https://bilibili.com/list/1"), parser_category_name = "COLLECTION_LIST", tr = lambda text: text)
    ParseInterface.on_download_and_sync(page)
    assert add.call_args.kwargs["episodes"] == [unselected]
    queue.assert_called_once_with("source", [selected])


def test_uploading_task_cannot_be_cancelled_or_start_next_merge(app, monkeypatch):
    from gui.component.download_list.model import DownloadListModel
    from util.download.task.manager import task_manager
    uploading = SimpleNamespace(Basic = SimpleNamespace(task_id = "upload"), Download = SimpleNamespace(status = DownloadStatus.UPLOADING))
    queued = SimpleNamespace(Basic = SimpleNamespace(task_id = "queued"), Download = SimpleNamespace(status = DownloadStatus.FFMPEG_QUEUED))
    model = DownloadListModel([uploading, queued])
    cancel = Mock()
    start = Mock()
    monkeypatch.setattr(task_manager, "cancel_async", cancel)
    monkeypatch.setattr(model, "togglePauseResume", start)
    model.cancelDownload(uploading)
    model.manageConcurrentMerges()
    cancel.assert_not_called()
    start.assert_not_called()


def test_webdav_test_closes_connection_after_failure(app, monkeypatch):
    from gui.dialog.setting.webdav import WebDAVTestWorker, StorageProviderFactory
    provider = Mock()
    provider.test_connection.side_effect = RuntimeError("offline")
    monkeypatch.setattr(StorageProviderFactory, "create_webdav", lambda **_: provider)
    errors = []
    worker = WebDAVTestWorker("https://example.test", "", "", "/", True)
    worker.error.connect(errors.append)
    worker.run()
    assert errors == ["offline"]
    provider.close.assert_called_once()
