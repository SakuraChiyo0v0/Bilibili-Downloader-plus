from PySide6.QtWidgets import QVBoxLayout

from qfluentwidgets import SwitchSettingCard

from gui.component.setting import DownloadPathSettingCard, NumberSettingCard, DownloadFormatCard
from gui.component.widget.scroll import ScrollArea
from .card import NamingConventionCard, MultiTypeNamingConventionCard

from util.common.icon import ExtendedFluentIcon
from util.common.config import config
from util.common.enum import StorageType
from util.common.runtime import runtime

class DownloadSettingsPage(ScrollArea):
    def __init__(self, parent = None, type_ids = None):
        super().__init__(parent = parent)

        self.options_dialog = parent
        self.type_ids = type_ids or set()

        self.init_UI()

    def init_UI(self):
        self.download_path_card = DownloadPathSettingCard(self.options_dialog, save = False, parent = self)
        self.path_config = config.download_path
        if config.get(config.storage_type) == StorageType.WEBDAV:
            self.download_path_card.setTitle(self.tr("Local Cache"))
            if not getattr(self.options_dialog, "sync_mode", False):
                self.path_config = config.local_temp_path
                self.download_path_card.set_path(config.get(config.local_temp_path) or config.get(config.download_path), update_space = False)
        self.download_format_card = DownloadFormatCard(parent = self)
        self.naming_convention_card = self._create_naming_convention_card()
        if getattr(self.options_dialog, "sync_mode", False):
            # 编辑同步源时恢复其自己的规则选择；仍由上游规则列表提供有效规则。
            card = self.naming_convention_card
            choices = getattr(card, "rule_choices", None)
            if choices is None:
                choices = {card.type_id: card.rule_choice}
            for type_id, choice in choices.items():
                index = choice.findData(runtime.naming.target_rule_ids.get(type_id))
                if index >= 0:
                    choice.setCurrentIndex(index)
        self.show_dialog_card = SwitchSettingCard(ExtendedFluentIcon.OPTIONS, self.tr("Automatically show this dialog"), self.tr("Automatically show this dialog before downloading to customize settings"), config.show_download_options_dialog, self)
        self.show_dialog_card.setVisible(not getattr(self.options_dialog, "sync_mode", False))
        self.numbering_settings_card = NumberSettingCard(self.options_dialog, self)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.download_path_card)
        main_layout.addWidget(self.download_format_card)
        main_layout.addWidget(self.naming_convention_card)
        main_layout.addWidget(self.show_dialog_card)
        main_layout.addWidget(self.numbering_settings_card)

        main_layout.addStretch()

        self.setScrollLayout(main_layout)

    def _create_naming_convention_card(self):
        # 绝大多数解析结果只有一种内容类型，保持原先的单行外观；
        # 混有多种类型时才展开成逐类型选择
        if len(self.type_ids) > 1:
            return MultiTypeNamingConventionCard(self.type_ids, self)

        return NamingConventionCard(next(iter(self.type_ids), None), self)

    def on_save(self):
        config.set(self.path_config, self.download_path_card.path)

        runtime.naming.target_rule_ids = self.naming_convention_card.rule_ids
