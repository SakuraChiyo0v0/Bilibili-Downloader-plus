"""旧增强版配置只迁入上游已有概念，不恢复旧命名引擎。"""
from copy import deepcopy

import pytest

from util.common.config import config, patch_fork_download_options
from util.common.enum import OriginalFileType
from util.common.runtime import runtime


@pytest.fixture(autouse = True)
def restore_options(monkeypatch):
    names = ("download_video_stream", "download_audio_stream", "merge_video_audio", "keep_original_files", "keep_original_files_type", "delete_cover_after_attach")
    saved = {name: deepcopy(config.get(getattr(config, name))) for name in names}
    quality = vars(runtime.download).copy()
    monkeypatch.setattr(config, "save", lambda: None)
    yield
    for name, value in saved.items():
        config.set(getattr(config, name), value, save = False)
    vars(runtime.download).update(quality)


def test_old_media_preferences_move_to_upstream_config():
    patch_fork_download_options({
        "Download Options": {
            "download_video_stream": False, "download_audio_stream": True,
            "merge_video_audio": False, "keep_original_files": True,
            "keep_original_files_type": 2, "audio_quality_id": 30251,
        },
        "Additional": {"cleanup_cover_after_attach": True},
    })
    assert config.get(config.download_video_stream) is False
    assert config.get(config.download_audio_stream) is True
    assert config.get(config.merge_video_audio) is False
    assert config.get(config.keep_original_files) is True
    assert config.get(config.keep_original_files_type) == OriginalFileType.AUDIO
    assert runtime.download.audio_quality_id == 30251
    assert config.get(config.delete_cover_after_attach) is True


def test_explicit_upstream_preferences_take_precedence():
    config.set(config.download_video_stream, True, save = False)
    config.set(config.delete_cover_after_attach, False, save = False)
    patch_fork_download_options({
        "Download": {"download_video_stream": True},
        "Download Options": {"download_video_stream": False},
        "Additional": {"cleanup_cover_after_attach": True, "delete_cover_after_attach": False},
    })
    assert config.get(config.download_video_stream) is True
    assert config.get(config.delete_cover_after_attach) is False


def test_invalid_old_preferences_do_not_break_upgrade():
    config.set(config.download_video_stream, True, save = False)
    config.set(config.keep_original_files_type, OriginalFileType.BOTH, save = False)
    patch_fork_download_options({"Download Options": {"download_video_stream": "false", "keep_original_files_type": 99}})
    assert config.get(config.download_video_stream) is True
    assert config.get(config.keep_original_files_type) == OriginalFileType.BOTH
