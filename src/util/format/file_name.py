from ..parse.episode.tree import Attribute
from ..download.task.info import TaskInfo

from ..common.enum import ConventionType
from ..common.config import config

from .time import Time

from pathlib import Path
from string import Formatter
from typing import List
import logging

logger = logging.getLogger(__name__)

class FileNameFormatter:
    def __init__(self):
        self.type_id = None
        self.rule = None
        self.variable_data: dict = {}

        self.attribute = None

    def set_type_id(self, type_id: int):
        self.type_id = type_id

    def set_rule(self, rule: str):
        self.rule = rule

    def set_variable_data(self, data: TaskInfo | List[dict]):
        if isinstance(data, TaskInfo):
            self.variable_data = self.get_variable_data_from_task_info(data)

            self.type_id = self.get_type_id_from_task_info(data)

        elif isinstance(data, list):
            for entry in data:
                name = entry.get("name")
                example = entry.get("example")

                if name in ["pub_time", "create_time", "last_watched_time", "fav_time"]:
                    example = Time.from_timestamp(1772841600)

                self.variable_data[name] = example

    def format(self):
        try:
            if not self.rule:
                self.rule = self.get_rule_from_config(self.type_id)

            if self.attribute:
                self.rule = self.get_special_rule()

            return self.__normalize_path(self.__format_rule(self.rule))

        except Exception as e:
            logger.exception(f"格式化文件名时发生错误")

            return None

    def __format_rule(self, rule: str):
        formatter = Formatter()
        parsed_rule = list(formatter.parse(rule))
        result = []

        for index, (literal_text, field_name, format_spec, conversion) in enumerate(parsed_rule):
            result.append(literal_text)

            if field_name is None:
                continue

            if self.__is_conditional_hyphen(field_name, format_spec, conversion):
                result.append("-" if self.__has_next_variable_value(parsed_rule, index + 1, formatter) else "")

                continue

            result.append(self.__format_field(formatter, field_name, format_spec, conversion))

        return "".join(result)

    def __is_conditional_hyphen(self, field_name: str, format_spec: str, conversion: str):
        return field_name == "-" and not format_spec and conversion is None

    def __has_next_variable_value(self, parsed_rule: list, start_index: int, formatter: Formatter):
        for _, field_name, format_spec, conversion in parsed_rule[start_index:]:
            if field_name is None:
                continue

            if self.__is_conditional_hyphen(field_name, format_spec, conversion):
                continue

            value = self.__format_field(formatter, field_name, format_spec, conversion)

            return value != ""

        return False

    def __format_field(self, formatter: Formatter, field_name: str, format_spec: str, conversion: str):
        value, _ = formatter.get_field(field_name, (), self.variable_data)
        value = formatter.convert_field(value, conversion)
        format_spec = formatter.vformat(format_spec, (), self.variable_data)

        if value is None:
            return ""

        return formatter.format_field(value, format_spec)

    def __normalize_path(self, path_str: str):
        if not path_str:
            return path_str
        
        path_str = path_str.removeprefix("/").removeprefix("\\")

        path = Path(path_str)
        normalized_parts = []

        for part in path.parts:
            cleaned_part = part.strip(" .")

            if cleaned_part:
                normalized_parts.append(cleaned_part)

        if not normalized_parts:
            return "_"

        return str(Path(*normalized_parts))

    def get_special_rule(self):
        if self.rule is None:
            self.rule = ""

        rule_map = {
            Attribute.DOWNLOAD_AS_SINGLE_VIDEO_BIT: "{leaf_title}",
        }

        for attr, rule in rule_map.items():
            if self.attribute & attr:
                return str(Path(rule))
        
        return self.rule
        
    def get_rule_from_config(self, type_id: int = None):
        # 从命名规则配置中查询到对应的命名规则模板
        for entry in config.get(config.naming_rule_list):
            if entry["type"] == type_id and entry["default"]:
                return entry["rule"]

    def get_rule_by_id(self, rule_id: int):
        for entry in config.get(config.naming_rule_list):
            if entry["id"] == rule_id:
                return entry["rule"]

    def get_variable_data_from_task_info(self, task_info: TaskInfo):
        return {
            "pub_time": Time.from_timestamp(task_info.Episode.pubtime),
            "pub_ts": task_info.Episode.pubtime,
            "create_time": Time.from_timestamp(task_info.Basic.created_time),
            "create_ts": task_info.Basic.created_time,
            "fav_time": Time.from_timestamp(task_info.Episode.favtime),
            "fav_ts": task_info.Episode.favtime,
            "last_watched_time": Time.from_timestamp(task_info.Episode.viewtime),
            "last_watched_ts": task_info.Episode.viewtime,
            "number": int(task_info.Episode.number),
            "uploader": task_info.Episode.uploader,
            "uploader_uid": task_info.Episode.uploader_uid,
            "video_quality": task_info.Episode.video_quality,
            "audio_quality": task_info.Episode.audio_quality,
            "video_codec": task_info.Episode.video_codec,

            "aid": task_info.Episode.aid,
            "bvid": task_info.Episode.bvid,
            "cid": task_info.Episode.cid,
            "ep_id": task_info.Episode.ep_id,
            "season_id": task_info.Episode.season_id,

            "leaf_title": task_info.Episode.leaf_title,
            "part_title": task_info.Episode.part_title,
            "parent_title": task_info.Episode.parent_title,
            "section_title": task_info.Episode.section_title,
            "collection_title": task_info.Episode.collection_title,
            "series_title": task_info.Episode.series_title,
            "season_title": task_info.Episode.season_title,
            "episode_title": task_info.Episode.episode_title,

            "season_number": task_info.Episode.season_number,
            "episode_number": task_info.Episode.episode_number,
            "p": task_info.Episode.part_number,

            "favorites_name": task_info.Episode.favorites_name,
            "favorites_id": task_info.Episode.favorites_id,
            "favorites_owner":task_info.Episode.favorites_owner,
            "favorites_owner_id": task_info.Episode.favorites_owner_id,
            "space_owner": task_info.Episode.space_owner,
            "space_owner_id": task_info.Episode.space_owner_id
        }
    
    def get_type_id_from_task_info(self, task_info: TaskInfo):
        self.attribute = task_info.Episode.attribute

        return self.get_type_id_from_attribute(task_info.Episode.attribute)

    def get_type_id_from_attribute(self, attribute: int):
        type_map = {
            Attribute.FAVLIST_BIT: ConventionType.FAVORITE,
            Attribute.SPACE_BIT: ConventionType.SPACE,
            Attribute.HISTORY_BIT: ConventionType.HISTORY,
            Attribute.WATCH_LATER_BIT: ConventionType.WATCH_LATER,
            Attribute.WEEKLY_BIT: ConventionType.WEEKLY,
            Attribute.AUDIO_BIT: ConventionType.AUDIO,

            Attribute.NORMAL_BIT: ConventionType.NORMAL,
            Attribute.PART_BIT: ConventionType.PART,
            Attribute.COLLECTION_BIT: ConventionType.COLLECTION,
            Attribute.INTERACTIVE_BIT: ConventionType.INTERACTIVE_VIDEO,
            Attribute.BANGUMI_BIT: ConventionType.BANGUMI,
            Attribute.CHEESE_BIT: ConventionType.CHEESE,
        }

        for attr, type_id in type_map.items():
            if attribute & attr != 0:
                return type_id

    def get_rule_list_from_attribute(self, attribute: int):
        type_id = self.get_type_id_from_attribute(attribute)

        rule_list = []

        for entry in config.get(config.naming_rule_list):
            if entry["type"] == type_id:
                rule_list.append(entry)

        return rule_list
