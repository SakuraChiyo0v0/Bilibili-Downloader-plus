from .card import (
    DownloadPathSettingCard, PrioritySettingCard, DanmakuSettingCard, SubtitleSettingCard, CoverSettingCard,
    MetadataSettingCard, NumberSettingCard, CDNSettingCard, ProxySettingCard, FFmpegSettingCard,
    DownloadFormatCard, ParsingSettingCard, WindowBehaviorSettingCard, DownloadHandlingSettingCard,
    DownloadConcurrencySettingCard, DownloadConcurrencySettingCard, PersonalizationCard,
    CheckUpdateSettingCard, OtherAdvancedSettingCard
)
from .storage_card import StorageSettingCard
from .group import FontGroup, BorderGroup, ColorGroup, MarginGroup, AlignmentGroup, AdvancedGroup, ResolutionGroup
from .widget import (
    SettingSwitchButton, SettingComboBox, EditActionWidget, ParseActionWidget, InsertActionWidget, SettingSlider
)