from util.common.enum import DownloadStatus
from util.download.task.info import TaskInfo
from util.download.task.query_worker import QueryWorker


def test_interrupted_upload_waits_for_explicit_retry():
    task = TaskInfo()
    task.Download.status = DownloadStatus.UPLOADING
    task.File.relative_files = ["finished.mp3"]
    task.File.upload_pending = True

    restored = QueryWorker().get_task_list([task])

    assert restored == [task]
    assert task.Download.status == DownloadStatus.FFMPEG_FAILED
    assert task.File.upload_pending is True
    assert task.File.relative_files == ["finished.mp3"]


def test_completed_upload_record_keeps_its_status():
    task = TaskInfo()
    task.Download.status = DownloadStatus.COMPLETED

    QueryWorker().get_task_list([task], update_status = False)

    assert task.Download.status == DownloadStatus.COMPLETED
