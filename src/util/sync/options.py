from copy import deepcopy
from contextlib import contextmanager

from ..common.config import config
from ..common.enum import ConventionType, NumberingType, StorageType
from ..common.runtime import runtime
from ..download.task.options import _OPTION_SPEC, snapshot


_MEDIA_OPTIONS = (
    "download_video_stream", "download_audio_stream", "merge_video_audio",
    "keep_original_files", "download_danmaku", "download_subtitle",
    "download_cover", "download_metadata", "embed_chapter", "download_path",
)
_QUALITY_OPTIONS = ("video_quality_id", "audio_quality_id", "video_codec_id")
_NUMBER_OPTIONS = ("current_starting_number", "global_starting_number")


def normalize_options(options: dict | None) -> dict:
    """兼容旧源快照，规则 ID 失效时交给上游按内容类型回落默认规则。"""
    result = deepcopy(options or {})
    if result.get("delete_cover_after_attach") is None and "cleanup_cover_after_attach" in result:
        result["delete_cover_after_attach"] = result["cleanup_cover_after_attach"]
    result.pop("cleanup_cover_after_attach", None)
    result.pop("target_naming_rule_id", None)
    rule_ids = {}
    for key, value in (result.get("naming_rule_ids") or {}).items():
        try:
            rule_ids[str(int(ConventionType(int(key))))] = value
        except (ValueError, TypeError):
            continue
    result["naming_rule_ids"] = rule_ids
    return result


def capture_download_options() -> dict:
    result = snapshot()
    result.update({key: deepcopy(config.get(getattr(config, key))) for key in _MEDIA_OPTIONS})
    result.update({key: getattr(runtime.download, key) for key in _QUALITY_OPTIONS})
    result.update({key: getattr(runtime.naming, key) for key in _NUMBER_OPTIONS})
    result["numbering_type"] = config.get(config.numbering_type).value
    result["naming_rule_ids"] = {str(int(key)): value for key, value in runtime.naming.target_rule_ids.items()}
    result["version"] = 2
    if result["storage_type"] == StorageType.WEBDAV.value:
        result["download_path"] = config.get(config.local_temp_path) or result["download_path"]
    return result


def apply_download_options(options: dict | None):
    options = normalize_options(options)
    for key in (*_MEDIA_OPTIONS, *_OPTION_SPEC, "numbering_type"):
        if options.get(key) is None:
            continue
        value = deepcopy(options[key])
        enum_type = NumberingType if key == "numbering_type" else _OPTION_SPEC.get(key)
        if enum_type is not None:
            value = enum_type(value)
        config.set(getattr(config, key), value)
    for key in _QUALITY_OPTIONS:
        if options.get(key) is not None:
            setattr(runtime.download, key, options[key])
    for key in _NUMBER_OPTIONS:
        if key in options:
            setattr(runtime.naming, key, options[key])
    runtime.naming.target_rule_ids = {ConventionType(int(key)): value for key, value in options["naming_rule_ids"].items()}


@contextmanager
def scoped_download_options(options: dict | None):
    """仅供 GUI 编辑同步源选项；后台建任务直接传 options，不改全局状态。"""
    original = capture_download_options()
    original["download_path"] = config.get(config.download_path)
    extras = {
        name: deepcopy(config.get(getattr(config, name)))
        for name in ("show_download_options_dialog", "local_temp_path")
    }
    try:
        apply_download_options(options)
        # 源选项已保存最终本地路径，源对话框只编辑这一处。
        config.set(config.local_temp_path, "")
        yield
    finally:
        apply_download_options(original)
        for name, value in extras.items():
            config.set(getattr(config, name), value)
