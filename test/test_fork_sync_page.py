"""同步页面的真实构造回归，防止仅测试入口方法而遗漏模块导入。"""

from PySide6.QtWidgets import QApplication, QWidget
import pytest


@pytest.fixture(scope = "module")
def app():
    instance = QApplication.instance() or QApplication([])
    import res.resources_rc  # noqa: F401
    return instance


def test_sync_page_and_source_dialog_construct(app, monkeypatch):
    from gui.interface.sync import AddSyncSourceDialog, SyncInterface, SyncSourceItem
    from util.sync.info import SyncSourceInfo
    from util.sync.manager import sync_manager

    monkeypatch.setattr(sync_manager, "sources", lambda: [])
    parent = QWidget()
    page = SyncInterface(parent)
    source = SyncSourceInfo(sync_id = "qa", title = "Release smoke", source_type = "collection")
    item = SyncSourceItem(source, parent)
    dialog = AddSyncSourceDialog(parent)

    assert page.objectName() == "SyncInterface"
    assert item.source.sync_id == "qa"
    assert dialog.options
    for widget in (dialog, item, page):
        widget.close()
