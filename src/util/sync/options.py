from copy import deepcopy
from contextlib import contextmanager

from ..common.config import config
from ..common.enum import (
    CoverType,
    DanmakuType,
    MetadataType,
    NumberingType,
    StorageType,
    SubtitleType,
    VideoContainer,
)


def _enum_value(value):
    return getattr(value, "value", value)


def capture_download_options() -> dict:
    return {
        "version": 1,
        "video_quality_id": config.video_quality_id,
        "audio_quality_id": config.audio_quality_id,
        "video_codec_id": config.video_codec_id,
        "download_video_stream": config.download_video_stream,
        "download_audio_stream": config.download_audio_stream,
        "merge_video_audio": config.merge_video_audio,
        "keep_original_files": config.keep_original_files,
        "keep_original_files_type": config.keep_original_files_type,
        "download_path": config.get(config.download_path),
        "storage_type": _enum_value(config.get(config.storage_type)),
        "target_naming_rule_id": config.target_naming_rule_id,
        "naming_rule_ids": deepcopy(config.get(config.download_option_naming_rule_ids) or {}),
        "numbering_type": _enum_value(config.get(config.numbering_type)),
        "current_starting_number": config.current_starting_number or 1,
        "global_starting_number": config.global_starting_number,
        "download_danmaku": config.get(config.download_danmaku),
        "danmaku_type": _enum_value(config.get(config.danmaku_type)),
        "danmaku_style": deepcopy(config.get(config.danmaku_style)),
        "download_subtitle": config.get(config.download_subtitle),
        "subtitle_type": _enum_value(config.get(config.subtitle_type)),
        "subtitle_language": deepcopy(config.get(config.subtitle_language)),
        "subtitle_style": deepcopy(config.get(config.subtitle_style)),
        "download_cover": config.get(config.download_cover),
        "cover_type": _enum_value(config.get(config.cover_type)),
        "attach_cover": config.get(config.attach_cover),
        "attach_cover_audio": config.get(config.attach_cover_audio),
        "cleanup_cover_after_attach": config.get(config.cleanup_cover_after_attach),
        "download_metadata": config.get(config.download_metadata),
        "metadata_type": _enum_value(config.get(config.metadata_type)),
        "auto_tag": config.get(config.auto_tag),
        "write_video_url_tag": config.get(config.write_video_url_tag),
        "video_container": _enum_value(config.get(config.video_container)),
        "m4a_to_mp3": config.get(config.m4a_to_mp3),
    }


_ENUM_OPTION_MAP = {
    "storage_type": StorageType,
    "numbering_type": NumberingType,
    "danmaku_type": DanmakuType,
    "subtitle_type": SubtitleType,
    "cover_type": CoverType,
    "metadata_type": MetadataType,
    "video_container": VideoContainer,
}


_CONFIG_OPTION_MAP = {
    "video_quality_id": "download_option_video_quality_id",
    "audio_quality_id": "download_option_audio_quality_id",
    "video_codec_id": "download_option_video_codec_id",
    "download_video_stream": "download_option_video_stream",
    "download_audio_stream": "download_option_audio_stream",
    "merge_video_audio": "download_option_merge_video_audio",
    "keep_original_files": "download_option_keep_original_files",
    "keep_original_files_type": "download_option_keep_original_files_type",
    "download_path": "download_path",
    "storage_type": "storage_type",
    "naming_rule_ids": "download_option_naming_rule_ids",
    "numbering_type": "numbering_type",
    "download_danmaku": "download_danmaku",
    "danmaku_type": "danmaku_type",
    "danmaku_style": "danmaku_style",
    "download_subtitle": "download_subtitle",
    "subtitle_type": "subtitle_type",
    "subtitle_language": "subtitle_language",
    "subtitle_style": "subtitle_style",
    "download_cover": "download_cover",
    "cover_type": "cover_type",
    "attach_cover": "attach_cover",
    "attach_cover_audio": "attach_cover_audio",
    "cleanup_cover_after_attach": "cleanup_cover_after_attach",
    "download_metadata": "download_metadata",
    "metadata_type": "metadata_type",
    "auto_tag": "auto_tag",
    "write_video_url_tag": "write_video_url_tag",
    "video_container": "video_container",
    "m4a_to_mp3": "m4a_to_mp3",
}


_RUNTIME_OPTION_NAMES = [
    "video_quality_id",
    "audio_quality_id",
    "video_codec_id",
    "download_video_stream",
    "download_audio_stream",
    "merge_video_audio",
    "keep_original_files",
    "keep_original_files_type",
    "target_naming_rule_id",
    "current_starting_number",
    "global_starting_number",
]


_EXTRA_CONFIG_ITEM_NAMES = [
    "show_download_options_dialog",
    "local_temp_path",
]


def _enum_option(key: str, value):
    enum_type = _ENUM_OPTION_MAP.get(key)

    if enum_type and not isinstance(value, enum_type):
        return enum_type(value)

    return value


def _set_config_option(key: str, value):
    config_item_name = _CONFIG_OPTION_MAP.get(key)

    if not config_item_name:
        return

    config.set(getattr(config, config_item_name), _enum_option(key, deepcopy(value)))


def apply_download_options(options: dict | None):
    if not options:
        return

    for name in _RUNTIME_OPTION_NAMES:
        if name in options:
            setattr(config, name, deepcopy(options[name]))

    for key, value in options.items():
        _set_config_option(key, value)


def _capture_dialog_config_state():
    state = capture_download_options()

    for name in _EXTRA_CONFIG_ITEM_NAMES:
        state[name] = deepcopy(config.get(getattr(config, name)))

    return state


def _restore_dialog_config_state(state: dict):
    apply_download_options(state)

    for name in _EXTRA_CONFIG_ITEM_NAMES:
        if name in state:
            config.set(getattr(config, name), deepcopy(state[name]))


@contextmanager
def scoped_download_options(options: dict | None):
    original = _capture_dialog_config_state()

    try:
        apply_download_options(options)
        yield
    finally:
        _restore_dialog_config_state(original)


def get_option(options: dict | None, key: str, default=None):
    if options and key in options:
        return options[key]

    return default


def get_task_option(task_info, key: str, default=None):
    value = getattr(task_info.Download, key, None)

    if value in (None, "", -1):
        return default

    return value


@contextmanager
def temporary_runtime_download_options(options: dict | None):
    if not options:
        yield
        return

    attrs = [
        "video_quality_id",
        "audio_quality_id",
        "video_codec_id",
        "download_video_stream",
        "download_audio_stream",
        "merge_video_audio",
        "keep_original_files",
        "keep_original_files_type",
        "target_naming_rule_id",
        "current_starting_number",
        "global_starting_number",
    ]
    original = {name: getattr(config, name) for name in attrs}

    try:
        for name in attrs:
            if name in options:
                setattr(config, name, options[name])

        yield
    finally:
        for name, value in original.items():
            setattr(config, name, value)
