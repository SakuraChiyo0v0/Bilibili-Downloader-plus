from PySide6.QtCore import QObject, Signal, Slot

from ..common.data.auto_parse import AutoParsePayload
from ..common.translator import Translator
from ..common.data import url_patterns
from ..common.enum import ParserType
from ..common.config import config
from .episode.tree import EpisodeData

from threading import Event
import logging
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger(__name__)

class WorkerBase:
    def get_parser(self, parser_type: str):
        match parser_type:
            case "video":
                from .parser.video import VideoParser
                return VideoParser()
            
            case "bangumi":
                from .parser.bangumi import BangumiParser
                return BangumiParser()
            
            case "cheese":
                from .parser.cheese import CheeseParser
                return CheeseParser()
            
            case "space":
                from .parser.space import SpaceParser
                return SpaceParser()
            
            case "favlist":
                from .parser.favlist import FavlistParser
                return FavlistParser()
            
            case "list":
                from .parser.list import ListParser
                return ListParser()
            
            case "popular":
                from .parser.popular import PopularParser
                return PopularParser()
            
            case "watch_later":
                from .parser.watch_later import WatchLaterParser
                return WatchLaterParser()
            
            case "history":
                from .parser.history import HistoryParser
                return HistoryParser()
            
            case "audio":
                from .parser.audio import AudioParser
                return AudioParser()
            
            case _:
                raise ValueError("未知的解析类型")

    def get_parser_type(self, url: str):
        for parser_type, pattern in url_patterns:
            if pattern.search(url):
                return parser_type

        raise ValueError(Translator.ERROR_MESSAGES("INVALID_LINK"))

    def optimize_parser(self, url: str, parser_type: str):
        if parser_type == "list" and config.get(config.optimize_ugc_season_list_parse):
            return self.try_optimize_ugc_season_list(url)

        return url, parser_type

    def try_optimize_ugc_season_list(self, url: str):
        canonical_url = self.get_canonical_ugc_season_list_url(url)

        if not canonical_url:
            return url, "list"

        try:
            from .parser.list import ListParser

            parser = ListParser()
            info_data = parser.parse(canonical_url, 1, get_info_data = True)
            archives = info_data.get("data", {}).get("archives", [])
            bvid = next((entry.get("bvid") for entry in archives if entry.get("bvid")), "")

            if not bvid:
                return url, "list"

            optimized_url = f"https://www.bilibili.com/video/{bvid}"
            logger.info("合集列表链接已优化为投稿视频链接：%s -> %s", url, optimized_url)

            return optimized_url, "video"

        except Exception:
            logger.warning("合集列表链接优化失败，将回退到原解析链路：%s", url, exc_info = True)

            return url, "list"

    def get_canonical_ugc_season_list_url(self, url: str):
        parsed_url = urlparse(url if "://" in url else f"https://{url}")

        if parsed_url.netloc != "space.bilibili.com":
            return ""

        path_parts = [part for part in parsed_url.path.split("/") if part]

        if len(path_parts) != 3 or path_parts[1] != "lists":
            return ""

        mid, season_id = path_parts[0], path_parts[2]

        if not mid.isdigit() or not season_id.isdigit():
            return ""

        if parse_qs(parsed_url.query).get("type", [""])[0] != "season":
            return ""

        return f"https://space.bilibili.com/{mid}/lists/{season_id}?type=season"

class ParseWorker(WorkerBase, QObject):
    success = Signal(str, dict)
    error = Signal(str)
    finished = Signal()

    def __init__(self, url: str, pn: int = 1):
        super().__init__()

        self.url = url
        self.pn = pn
        self.parser_type = ""

    @Slot()
    def run(self):
        EpisodeData.clear_cache()

        try:
            self.parser_type = self.get_parser_type(self.url)

            self.get_redirect_url()

            self.url, self.parser_type = self.optimize_parser(self.url, self.parser_type)

            parser = self.get_parser(self.parser_type)

            parser.parse(self.url, self.pn)

            self.success.emit(parser.get_category_name(), parser.get_extra_data())

        except Exception as e:
            self.on_error()

            self.error.emit(str(e))

        finally:
            self.finished.emit()

            self.deleteLater()

    def get_redirect_url(self):
        from .parser.festival import FestivalParser
        from .parser.b23 import B23Parser

        _parsers = {
            "b23": B23Parser(),
            "festival": FestivalParser()
        }

        for parser_type, parser in _parsers.items():
            if parser_type in self.url:
                self.url = parser.parse(self.url)

                self.parser_type = self.get_parser_type(self.url)

    def on_error(self):
        logger.exception("解析失败")

class ProgressParseWorker(WorkerBase, QObject):
    # 后台解析线程，负责自动解析流程中的进度回传
    success = Signal(str, dict)
    error = Signal(str)
    finished = Signal()

    update_progress = Signal(str)

    def __init__(self, info_data: AutoParsePayload):
        super().__init__()

        self.data: AutoParsePayload = info_data
        self.stop_event = Event()

    @Slot()
    def run(self):
        try:
            parser = self._get_parser()
            parser.parse()

            self.success.emit(parser.get_category_name(), {})

            logger.info("自动解析完成")

        except Exception as e:
            logger.exception("解析失败")

            self.error.emit(str(e))

        finally:
            self.finished.emit()

    def _get_parser(self):
        match self.data.parser_type:
            case ParserType.INTERACTIVE_VIDEO:
                return self._get_interactive_video_parser()

            case ParserType.DYNAMIC:
                return self._get_dynamic_parser()
            
            case ParserType.BATCH:
                return self._get_dynamic_parser()

        raise ValueError(f"Unsupported parser type: {self.data.parser_type}")

    def _get_interactive_video_parser(self):
        from .parser.video import InteractiveVideoParser

        return InteractiveVideoParser(self.data.data, self._update_progress_callback, self.stop_event)

    def _get_dynamic_parser(self):
        from .parser.dynamic import DynamicParser

        parser_type = self.get_parser_type(self.data.url)

        base_parser = self.get_parser(parser_type)

        return DynamicParser(self.data, base_parser, self._update_progress_callback, self.stop_event)

    def _update_progress_callback(self, text: str):
        self.update_progress.emit(text)

    def trigger_stop(self):
        self.stop_event.set()
