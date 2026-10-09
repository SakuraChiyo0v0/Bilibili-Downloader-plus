from copy import deepcopy

from ..common.enum import ParserType
from ..common.data import url_patterns
from ..parse.episode.bangumi import BangumiEpisodeParser
from ..parse.episode.favlist import FavlistEpisodeParser
from ..parse.episode.list import ListEpisodeParser
from ..parse.episode.tree import Attribute, EpisodeData
from ..parse.episode.video import VideoEpisodeParser
from ..parse.parser.bangumi import BangumiParser
from ..parse.parser.favlist import FavlistParser
from ..parse.parser.list import ListParser
from ..parse.parser.video import VideoParser


BANGUMI_CATEGORY_NAMES = {
    "ANIME",
    "DOCUMENTARY",
    "TV",
    "CHN_ANIME",
    "MOVIE",
    "VARIETY",
}


def get_parser_type(url: str):
    for parser_type, pattern in url_patterns:
        if pattern.search(url):
            return parser_type

    raise ValueError("Invalid link")


def detect_sync_source_type(url: str, category_name: str = "", episode_list: list[dict] = None):
    try:
        parser_type = get_parser_type(url)
    except Exception:
        parser_type = ""

    if parser_type == "favlist":
        return "favlist"

    if parser_type == "list":
        return "collection"

    if parser_type == "bangumi":
        return "bangumi"

    if category_name in BANGUMI_CATEGORY_NAMES:
        return "bangumi"

    episode_list = episode_list or []

    for episode in episode_list:
        attr = episode.get("attribute", 0)

        if attr & Attribute.FAVLIST_BIT:
            return "favlist"

        if attr & Attribute.COLLECTION_BIT or attr & Attribute.COLLECTION_LIST_BIT:
            return "collection"

    return ""


def calc_episode_key(episode_info: dict):
    attr = episode_info.get("attribute", 0)

    if attr & Attribute.AUDIO_BIT:
        return f"audio:{episode_info.get('sid')}"

    if attr & Attribute.BANGUMI_BIT:
        ep_id = episode_info.get("ep_id")

        if ep_id:
            return f"bangumi:{ep_id}"

    bvid = episode_info.get("bvid", "")
    cid = episode_info.get("cid", 0)
    aid = episode_info.get("aid", 0)

    if bvid and attr & (Attribute.FAVLIST_BIT | Attribute.COLLECTION_BIT | Attribute.COLLECTION_LIST_BIT | Attribute.NEED_PARSE_BIT):
        return f"video:{bvid}"

    if bvid and cid:
        return f"video:{bvid}:{cid}"

    if bvid:
        return f"video:{bvid}"

    if aid and cid:
        return f"video:{aid}:{cid}"

    url = episode_info.get("url", "")

    if url:
        return f"url:{url}"

    return f"title:{episode_info.get('title', '')}:{episode_info.get('number', '')}"


class SyncSourceParser:
    def parse(self, url: str):
        with EpisodeData.parsing(clear_cache = False):
            return self._parse(url)

    def _parse(self, url: str):
        parser_type = get_parser_type(url)

        match parser_type:
            case "favlist":
                result = self._parse_favlist(url)

            case "list":
                result = self._parse_list(url)

            case "bangumi":
                result = self._parse_bangumi(url)

            case "video":
                result = self._parse_video(url)

            case _:
                raise ValueError("Unsupported sync source")

        self._attach_episode_extra_data(result["episodes"])

        return result

    def _parse_favlist(self, url: str):
        parser = FavlistParser()
        first_info_data = parser.parse(url, 1, get_info_data = True)
        episodes, title = self._favlist_info_to_episodes(first_info_data, parser.get_category_name())
        extra_data = parser.get_extra_data()

        total_pages = extra_data.get("pagination_data", {}).get("total_pages", 1)

        for page in range(2, total_pages + 1):
            page_parser = FavlistParser()
            info_data = page_parser.parse(url, page, get_info_data = True)
            page_episodes, _ = self._favlist_info_to_episodes(info_data, page_parser.get_category_name())
            episodes.extend(page_episodes)

        return {
            "title": title,
            "source_type": "favlist",
            "episodes": episodes,
        }

    def _favlist_info_to_episodes(self, info_data: dict, category_name: str):
        episode_parser = FavlistEpisodeParser(info_data, category_name)
        node = episode_parser.parse(update_episode_list = False)

        return node.get_all_children(to_dict = True), node.title

    def _parse_list(self, url: str):
        parser = ListParser()
        first_info_data = parser.parse(url, 1, get_info_data = True)
        episodes, title = self._list_info_to_episodes(first_info_data, parser.get_category_name())
        extra_data = parser.get_extra_data()

        total_pages = extra_data.get("pagination_data", {}).get("total_pages", 1)

        for page in range(2, total_pages + 1):
            page_parser = ListParser()
            info_data = page_parser.parse(url, page, get_info_data = True)
            page_episodes, _ = self._list_info_to_episodes(info_data, page_parser.get_category_name())
            episodes.extend(page_episodes)

        return {
            "title": title,
            "source_type": "collection",
            "episodes": episodes,
        }

    def _list_info_to_episodes(self, info_data: dict, category_name: str):
        episode_parser = ListEpisodeParser(info_data, category_name)
        node = episode_parser.parse(update_episode_list = False)

        return node.get_all_children(to_dict = True), node.title

    def _parse_bangumi(self, url: str):
        parser = BangumiParser()
        parser.parse(url, 1, get_info_data = True)

        category_name = parser.get_category_name()
        episode_parser = BangumiEpisodeParser(parser.info_data.copy(), category_name)
        node = episode_parser.parse(update_episode_list = False)

        return {
            "title": node.title,
            "source_type": "bangumi",
            "episodes": node.get_all_children(to_dict = True),
        }

    def _parse_video(self, url: str):
        parser = VideoParser()
        info_data = parser.parse(url, 1, get_info_data = True)

        if not info_data.get("data", {}).get("ugc_season"):
            raise ValueError("Only collection videos can be synced")

        episode_parser = VideoEpisodeParser(info_data.copy(), ParserType.VIDEO.value)
        node = episode_parser.parse(update_episode_list = False)

        return {
            "title": node.title,
            "source_type": "collection",
            "episodes": node.get_all_children(to_dict = True),
        }

    def _attach_episode_extra_data(self, episodes: list[dict]):
        for episode in episodes:
            episode_id = episode.get("episode_id")

            if not episode_id:
                continue

            extra_data = EpisodeData.get_episode_data(episode_id)

            if extra_data:
                episode["_episode_extra_data"] = deepcopy(extra_data)
