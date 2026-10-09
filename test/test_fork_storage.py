"""上传必须以任务存储快照为准，失败/取消保留文件，并参与上游线程生命周期。"""
from types import SimpleNamespace
from unittest.mock import Mock
from threading import Event

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


def make_task(tmp_path, *names):
    from util.download.task.info import TaskInfo
    task = TaskInfo()
    task.File.download_path = str(tmp_path)
    task.File.relative_files = list(names)
    task.Options.storage_type = "webdav"
    task.Options.cleanup_after_upload = True
    return task


class Provider:
    def __init__(self, deltas=(), fail=False):
        self.deltas = deltas
        self.fail = fail
        self.closed = 0
        self.calls = []

    def upload(self, local, remote, progress_callback):
        self.calls.append((local, remote))
        for delta in self.deltas:
            progress_callback(delta)
        if self.fail:
            raise RuntimeError("upload failed")

    def close(self):
        self.closed += 1


def run_worker(app, task, provider):
    from util.storage.upload_worker import UploadWorker
    worker = UploadWorker(task, provider)
    result = SimpleNamespace(success=[], error=[], progress=[], finished=[])
    worker.success.connect(lambda: result.success.append(True))
    worker.error.connect(result.error.append)
    worker.progress.connect(lambda n, total: result.progress.append((n, total)))
    worker.finished.connect(lambda: result.finished.append(True))
    worker.start()
    assert worker.wait(3000)
    app.processEvents()
    return result


def test_factory_uses_task_storage_even_after_global_switch(monkeypatch):
    from util.storage import factory
    from util.common.enum import StorageType, ProxyMode
    settings = {"storage_type": StorageType.LOCAL, "proxy_mode": ProxyMode.DISABLED,
                "webdav_url": "https://example.test", "webdav_username": "", "webdav_password": "",
                "webdav_base_path": "/", "webdav_verify_ssl": True}
    config = SimpleNamespace(**{key: key for key in settings}, get=lambda key: settings[key])
    monkeypatch.setattr(factory, "config", config)
    monkeypatch.setattr(factory, "Proxy", lambda: SimpleNamespace(get_proxies=lambda: None))
    remote = Mock()
    monkeypatch.setattr(factory, "WebDAVStorageProvider", remote)
    assert factory.StorageProviderFactory.create_from_config(StorageType.WEBDAV) is remote.return_value
    remote.assert_called_once()
    with pytest.raises(ValueError):
        factory.StorageProviderFactory.create_from_config("unknown")


def test_cumulative_progress_and_finished_signal(app, tmp_path):
    (tmp_path / "media.mp3").write_bytes(b"123456")
    (tmp_path / "lyrics.lrc").write_bytes(b"123456")
    task = make_task(tmp_path, "media.mp3")
    task.File.additional_files = ["lyrics.lrc", "media.mp3"]
    provider = Provider(deltas=[2, 2, 2])
    result = run_worker(app, task, provider)
    assert [n for n, _ in result.progress] == [0, 2, 4, 6, 6, 8, 10, 12, 12]
    assert {total for _, total in result.progress} == {12}
    assert result.success == result.finished == [True]
    assert result.error == []
    assert provider.closed == 1
    assert len(provider.calls) == 2


@pytest.mark.parametrize("names", [[], ["missing.mp3"], ["existing.mp3", "missing.lrc"]])
def test_missing_files_never_report_success_and_always_close(app, tmp_path, names):
    (tmp_path / "existing.mp3").write_bytes(b"source")
    provider = Provider()
    result = run_worker(app, make_task(tmp_path, *names), provider)
    assert result.success == []
    assert len(result.error) == 1
    assert result.finished == [True]
    assert provider.closed == 1
    assert provider.calls == []
    assert (tmp_path / "existing.mp3").exists()


def test_cancellation_during_last_upload_suppresses_success(app, tmp_path):
    from util.storage.upload_worker import UploadWorker
    (tmp_path / "media.mp3").write_bytes(b"source")
    entered, release = Event(), Event()
    provider = Provider()
    def upload(*args, **kwargs):
        entered.set()
        assert release.wait(3)
    provider.upload = upload
    worker = UploadWorker(make_task(tmp_path, "media.mp3"), provider)
    successes = []
    worker.success.connect(lambda: successes.append(True))
    worker.start()
    try:
        assert entered.wait(3)
        assert not worker.stop(0)
    finally:
        release.set()
        assert worker.wait(3000)
    app.processEvents()
    assert successes == []
    assert provider.closed == 1
    assert (tmp_path / "media.mp3").exists()


def test_upload_retry_skips_media_processing_and_failure_keeps_local(app, tmp_path, monkeypatch):
    from util.download.downloader import merger as module
    from util.common.enum import DownloadStatus
    (tmp_path / "finished.mp3").write_bytes(b"complete")
    task = make_task(tmp_path, "finished.mp3")
    task.File.upload_pending = True
    manager = SimpleNamespace(update=Mock(), mark_as_completed=Mock())
    monkeypatch.setattr(module, "task_manager", manager)
    monkeypatch.setattr(module, "signal_bus", Mock())
    provider = Provider(fail=True)
    monkeypatch.setattr(module.StorageProviderFactory, "create_from_config", lambda storage: provider)
    merger = module.Merger(task)
    monkeypatch.setattr(merger, "merge_video_audio", Mock(side_effect=AssertionError("must not merge")))
    merger.start()
    assert merger._upload_worker.wait(3000)
    app.processEvents()
    assert task.File.upload_pending
    assert task.Download.status == DownloadStatus.FFMPEG_FAILED
    assert (tmp_path / "finished.mp3").exists()
    manager.mark_as_completed.assert_not_called()
    manager.update.assert_called_once_with(task, wait=True)
    assert merger.stop()


def test_upload_success_respects_task_cleanup_snapshot(app, tmp_path, monkeypatch):
    from util.download.downloader import merger as module
    (tmp_path / "finished.mp3").write_bytes(b"complete")
    task = make_task(tmp_path, "finished.mp3")
    task.Options.cleanup_after_upload = False
    task.File.upload_pending = True
    manager = SimpleNamespace(update=Mock(), mark_as_completed=Mock())
    monkeypatch.setattr(module, "task_manager", manager)
    monkeypatch.setattr(module, "signal_bus", Mock())
    monkeypatch.setattr(module.StorageProviderFactory, "create_from_config", lambda storage: Provider())
    merger = module.Merger(task)
    merger.start()
    assert merger._upload_worker.wait(3000)
    app.processEvents()
    assert (tmp_path / "finished.mp3").exists()
    assert not task.File.upload_pending
    manager.mark_as_completed.assert_called_once_with(task, wait=True)
    assert merger.stop()


def test_cleanup_failure_after_partial_delete_does_not_retry_upload(app, tmp_path, monkeypatch):
    from util.download.downloader import merger as module
    from util.common.enum import DownloadStatus
    for name in ("one.mp3", "two.lrc"):
        (tmp_path / name).write_bytes(b"uploaded")
    task = make_task(tmp_path, "one.mp3", "two.lrc")
    task.File.upload_pending = True
    manager = SimpleNamespace(update=Mock(), mark_as_completed=Mock())
    bus = Mock()
    monkeypatch.setattr(module, "task_manager", manager)
    monkeypatch.setattr(module, "signal_bus", bus)
    def partial_remove(cwd, *names):
        (cwd / names[0]).unlink()
        raise PermissionError("second file locked")
    monkeypatch.setattr(module, "safe_remove", partial_remove)
    merger = module.Merger(task)
    merger.on_upload_success()
    assert not (tmp_path / "one.mp3").exists()
    assert (tmp_path / "two.lrc").exists()
    assert not task.File.upload_pending
    assert task.Download.status == DownloadStatus.COMPLETED
    manager.mark_as_completed.assert_called_once_with(task, wait=True)
    bus.toast.show_long_message.emit.assert_called_once()


def test_provider_close_failure_after_uploaded_does_not_retry(app, tmp_path):
    (tmp_path / "media.mp3").write_bytes(b"source")
    provider = Provider()
    provider.close = Mock(side_effect=RuntimeError("close failed"))
    result = run_worker(app, make_task(tmp_path, "media.mp3"), provider)
    assert result.success == [True]
    assert result.error == []
    assert result.finished == [True]


def test_stopped_merger_keeps_upload_thread_alive_until_it_finishes(app, tmp_path, monkeypatch):
    from util.download.downloader import merger as module
    from PySide6.QtCore import QObject
    (tmp_path / "finished.mp3").write_bytes(b"complete")
    task = make_task(tmp_path, "finished.mp3")
    task.File.upload_pending = True
    manager = SimpleNamespace(update=Mock(), mark_as_completed=Mock())
    monkeypatch.setattr(module, "task_manager", manager)
    monkeypatch.setattr(module, "signal_bus", Mock())
    entered, release = Event(), Event()
    provider = Provider()
    def upload(*args, **kwargs):
        entered.set()
        assert release.wait(3)
    provider.upload = upload
    monkeypatch.setattr(module.StorageProviderFactory, "create_from_config", lambda storage: provider)
    parent = QObject()
    merger = module.Merger(task, parent=parent)
    merger.start()
    worker = merger._upload_worker
    try:
        assert entered.wait(3)
        assert not merger.stop(0)
        merger.detach()
        assert merger.parent() is None
        assert merger in module._detached_mergers
    finally:
        release.set()
        assert worker.wait(3000)
    app.processEvents()
    assert merger not in module._detached_mergers
    assert (tmp_path / "finished.mp3").exists()
    manager.mark_as_completed.assert_not_called()


def test_attachment_only_task_uploads_without_media(app, tmp_path, monkeypatch):
    from util.download.downloader import merger as module
    from util.common.enum import DownloadType
    (tmp_path / "cover.jpg").write_bytes(b"cover")
    task = make_task(tmp_path)
    task.File.additional_files = ["cover.jpg"]
    task.Download.type = DownloadType.COVER
    task.Options.cleanup_after_upload = False
    manager = SimpleNamespace(update=Mock(), mark_as_completed=Mock())
    monkeypatch.setattr(module, "task_manager", manager)
    monkeypatch.setattr(module, "signal_bus", Mock())
    provider = Provider()
    monkeypatch.setattr(module.StorageProviderFactory, "create_from_config", lambda storage: provider)
    merger = module.Merger(task)
    merger.start()
    assert merger._upload_worker.wait(3000)
    app.processEvents()
    assert [local.name for local, _ in provider.calls] == ["cover.jpg"]
    manager.mark_as_completed.assert_called_once_with(task, wait=True)
    assert (tmp_path / "cover.jpg").exists()
    assert merger.stop()


def test_webdav_connection_test_uses_same_proxy_mode_as_upload(monkeypatch):
    from util.storage import factory
    from util.common.enum import ProxyMode
    settings = {"proxy_mode": ProxyMode.SYSTEM, "webdav_url": "https://example.test", "webdav_username": "",
                "webdav_password": "", "webdav_base_path": "/"}
    monkeypatch.setattr(factory, "config", SimpleNamespace(**{key: key for key in settings}, get=lambda key: settings[key]))
    monkeypatch.setattr(factory, "Proxy", lambda: SimpleNamespace(get_proxies=lambda: None))
    provider = Mock()
    monkeypatch.setattr(factory, "WebDAVStorageProvider", provider)
    factory.StorageProviderFactory.create_webdav()
    assert provider.call_args.kwargs["trust_env"] is True
    factory.StorageProviderFactory.create_webdav(proxies={"https": "http://proxy.test:8080"})
    assert provider.call_args.kwargs["proxies"] == {"https": "http://proxy.test:8080"}
    assert provider.call_args.kwargs["trust_env"] is False
