"""fork 音频增强必须叠加在上游封装、失败恢复与完成落盘流程上。"""
import json
import shutil
import subprocess
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication


@pytest.fixture
def media(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    from util.common.enum import DownloadType
    from util.download.downloader import merger as module
    from util.download.task.info import TaskInfo
    from util.download.task.options import snapshot

    task = TaskInfo()
    task.Basic.task_id = "audio-test"
    task.File.download_path = str(tmp_path)
    task.File.name = "song"
    task.File.audio_file_ext = "m4a"
    task.Download.type = DownloadType.AUDIO
    task.Options.from_dict(snapshot({
        "storage_type": "local", "auto_tag": True, "write_video_url_tag": True,
        "attach_cover_audio": True, "delete_cover_after_attach": True,
        "cover_type": "jpg", "m4a_to_mp3": False,
    }))
    task.Episode.leaf_title = "测试标题"
    task.Episode.uploader = "作者"
    task.Episode.url = "https://www.bilibili.com/video/BV-test"
    manager = SimpleNamespace(update=Mock(), mark_as_completed=Mock())
    monkeypatch.setattr(module, "task_manager", manager)
    monkeypatch.setattr(module, "signal_bus", Mock())
    merger = module.Merger(task)
    yield app, module, merger, task, manager
    merger.stop()


def test_remux_retains_audio_tags_cover_and_cleans_registered_attachment(media, tmp_path, monkeypatch):
    _, _, merger, task, manager = media
    (tmp_path / merger.temp_audio_file_name).write_bytes(b"source")
    (tmp_path / "song.jpg").write_bytes(b"cover")
    task.File.additional_files = ["song.jpg", "song.lrc"]
    task.File.relative_files = [merger.temp_audio_file_name]
    captured = []
    monkeypatch.setattr(merger, "_start_ffmpeg", lambda cmd, cwd, callback: captured.append((cmd.build(), callback)))

    merger.start()
    argv, callback = captured[0]
    assert "copy" in argv
    assert "attached_pic" in argv
    assert "title=测试标题" in argv
    assert "artist=作者" in argv
    assert "comment=https://www.bilibili.com/video/BV-test" in argv
    (tmp_path / merger.temp_remux_audio_file_name).write_bytes(b"output")
    callback(0, "", "")

    assert (tmp_path / "song.m4a").read_bytes() == b"output"
    assert not (tmp_path / "song.jpg").exists()
    assert task.File.additional_files == ["song.lrc"]
    assert task.File.relative_files == ["song.m4a"]
    manager.mark_as_completed.assert_called_once_with(task, wait=True)


@pytest.mark.parametrize("ext", ["m4a", "flac"])
def test_conversion_does_not_change_source_extension_before_success(media, tmp_path, monkeypatch, ext):
    _, _, merger, task, _ = media
    task.File.audio_file_ext = ext
    task.Options.m4a_to_mp3 = True
    (tmp_path / merger.temp_audio_file_name).write_bytes(b"source")
    commands = []
    monkeypatch.setattr(merger, "_start_ffmpeg", lambda cmd, cwd, cb: commands.append(cmd.build()))
    merger.start()
    assert task.File.audio_file_ext == ext
    assert commands[0][-1] == "output_audio-test.mp3"
    assert (tmp_path / f"audio_audio-test.{ext}").exists()
    merger.on_merge_error(RuntimeError("failed"), "", "failed")
    assert task.File.audio_file_ext == ext
    assert (tmp_path / f"audio_audio-test.{ext}").exists()


def test_attachment_registration_is_unique_and_excludes_chapter(media, tmp_path):
    _, _, _, task, _ = media
    from util.parse.additional.base import AdditionalParserBase
    from util.parse.additional.chapter import ChapterParser

    parser = AdditionalParserBase(task)
    parser._write("one", "srt")
    parser._write("two", "srt")
    ChapterParser(task)._write_chapter_file(";FFMETADATA1")
    assert task.File.additional_files == ["song.srt"]


@pytest.mark.parametrize("ext", ["m4a", "flac", "mp3"])
def test_real_ffmpeg_preserves_tags_and_audio_cover(tmp_path, ext):
    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        pytest.skip("需要本机 ffmpeg/ffprobe")
    from util.ffmpeg.command import FFmpegCommand

    source = tmp_path / "source.m4a"
    subprocess.run([ffmpeg, "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=0.1",
                    "-c:a", "flac" if ext == "flac" else "aac", "-strict", "experimental",
                    "-movflags", "+frag_keyframe+empty_moov", "-f", "mp4", str(source)],
                   check=True, capture_output=True, timeout=20)
    cover = tmp_path / "cover.png"
    image = QImage(16, 16, QImage.Format.Format_RGB32)
    image.fill(0xff448899)
    assert image.save(str(cover))
    output = tmp_path / f"output.{ext}"
    make = FFmpegCommand.convert_m4a_to_mp3 if ext == "mp3" else FFmpegCommand.remux_audio
    argv = make(str(source), str(output), cover_path=str(cover), metadata={
        "title": "test-title", "artist": "test-artist", "video_url": "https://example.test/video"
    }).build()
    argv[0] = ffmpeg
    result = subprocess.run(argv, capture_output=True, timeout=20)
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    probe = subprocess.run([ffprobe, "-v", "error", "-show_format", "-show_streams", "-of", "json", str(output)],
                           capture_output=True, check=True, timeout=10)
    data = json.loads(probe.stdout)
    tags = {key.lower(): value for key, value in data["format"]["tags"].items()}
    assert tags["title"] == "test-title"
    assert tags["artist"] == "test-artist"
    assert tags["comment" if ext == "m4a" else "video_url"] == "https://example.test/video"
    assert any(stream.get("disposition", {}).get("attached_pic") for stream in data["streams"])
