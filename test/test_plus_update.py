import httpx
import pytest

from util.common.version import FORK_REPOSITORY_URL
from util.misc import update


def release(tag, **kwargs):
    return {"tag_name": tag, "body": "Release notes", "draft": False, "prerelease": False, **kwargs}


def test_plus_update_selects_latest_revision_without_following_external_url():
    result = update.parse_github_releases([
        release("v2.20.0+plus.2"),
        release("v2.20.0+plus.10", html_url = "https://example.invalid/other-project"),
        release("v2.20.0+plus.9"),
    ], "2.20.0+plus.1")
    assert result["should_update"]
    assert not result["required"]
    assert result["version"] == "2.20.0+plus.10"
    assert result["update_url"] == f"{FORK_REPOSITORY_URL}/releases/tag/v2.20.0%2Bplus.10"


def test_drafts_legacy_tags_and_preview_releases_are_ignored():
    result = update.parse_github_releases([
        release("v9.0.0"),
        release("v9.0.0+plus.1", draft = True),
        release("v8.0.0+plus.1", prerelease = True),
        release("v7.0.0-rc1+plus.1"),
        release(None),
    ], "2.20.0+plus.1")
    assert not result["should_update"]
    assert result["version"] == "2.20.0+plus.1"


def test_preview_opt_in_is_respected():
    result = update.parse_github_releases([
        release("v2.20.0+plus.2"),
        release("v2.21.0-rc1+plus.1", prerelease = True),
    ], "2.20.0+plus.1", include_preview = True)
    assert result["version"] == "2.21.0-rc1+plus.1"
    assert result["should_update"]


@pytest.mark.parametrize("tag", ["v2.20.0+plus.1", "v2.19.0+plus.99"])
def test_equal_and_older_versions_are_not_updates(tag):
    assert not update.parse_github_releases([release(tag)], "2.20.0+plus.1")["should_update"]


def test_malformed_api_response_is_an_error():
    with pytest.raises(ValueError, match = "Invalid GitHub"):
        update.parse_github_releases({"message": "rate limited"}, "2.20.0+plus.1")


def test_plus_checks_only_our_repository_and_closes_client(monkeypatch):
    monkeypatch.setattr(update.config, "app_version", "2.20.0+plus.1")
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(200, json = [release("v2.20.0+plus.2")])
    client = httpx.Client(transport = httpx.MockTransport(handler))
    monkeypatch.setattr(update, "_create_http_client", lambda: client)
    monkeypatch.setattr(update, "_create_client", lambda: pytest.fail("Plus must not use the upstream channel"))

    info, error = update.check_for_update()

    assert error is None and info["should_update"]
    assert client.is_closed
    assert len(requests) == 1
    assert str(requests[0].url).startswith("https://api.github.com/repos/SakuraChiyo0v0/Bilibili-Downloader-plus/releases?")
    assert "cookie" not in requests[0].headers


def test_network_failure_does_not_claim_latest_or_fall_back_upstream(monkeypatch):
    monkeypatch.setattr(update.config, "app_version", "2.20.0+plus.1")
    client = httpx.Client(transport = httpx.MockTransport(lambda request: httpx.Response(403, json = {"message": "rate limited"})))
    monkeypatch.setattr(update, "_create_http_client", lambda: client)
    monkeypatch.setattr(update, "_create_client", lambda: pytest.fail("Do not silently switch channels"))

    info, error = update.check_for_update()

    assert info is None and error
    assert client.is_closed


def test_skipped_plus_revision_is_hidden_only_for_automatic_checks(monkeypatch):
    from types import SimpleNamespace

    shown = []
    monkeypatch.setattr(update, "config", SimpleNamespace(
        skip_version = "skip", app_version = "2.20.0+plus.1", get = lambda item: "2.20.0+plus.2",
    ))
    monkeypatch.setattr(update, "signal_bus", SimpleNamespace(
        update = SimpleNamespace(show_dialog = SimpleNamespace(emit = shown.append)),
    ))
    info = update.parse_github_releases([release("v2.20.0+plus.2")], "2.20.0+plus.1")
    updater = update.Updater()
    updater.check(info, manual = False)
    assert shown == []
    updater.check(info, manual = True)
    assert shown == [info]
