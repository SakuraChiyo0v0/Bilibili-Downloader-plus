from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from urllib.error import HTTPError
import io
import json

import pytest


ROOT = Path(__file__).resolve().parent.parent
SPEC = spec_from_file_location("release_guard", ROOT / "scripts/release_guard.py")
MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


@pytest.mark.parametrize("draft,published", [(False, True), (True, False)])
def test_public_assets_are_protected_and_drafts_can_be_repaired(monkeypatch, draft, published):
    requests = []
    def fetch(request, timeout):
        requests.append(request)
        assert timeout == 30
        return io.BytesIO(json.dumps({"draft": draft}).encode())
    monkeypatch.setattr(MODULE, "urlopen", fetch)
    assert MODULE.is_published("owner/repo", "v2.20.0+plus.1") is published
    assert requests[0].full_url.endswith("/v2.20.0%2Bplus.1")


@pytest.mark.parametrize("status", [404, 403, 500])
def test_only_missing_release_allows_build_on_http_error(monkeypatch, status):
    def fetch(*args, **kwargs):
        raise HTTPError("https://api.github.com", status, "test", {}, None)
    monkeypatch.setattr(MODULE, "urlopen", fetch)
    if status == 404:
        assert not MODULE.is_published("owner/repo", "v2.20.0+plus.1")
    else:
        with pytest.raises(HTTPError):
            MODULE.is_published("owner/repo", "v2.20.0+plus.1")
