"""Tests for GitHub release parsing (no network)."""

import io
import json
import urllib.error
from pathlib import Path

from core.update_check import (
    explain_unparsed_release,
    fetch_latest_release_with_reason,
    is_update_available,
    load_update_feed,
    parse_github_release,
    resolve_cafile,
    ssl_context,
)


def _payload(tag: str, asset_name: str = "SketchBook-Setup-v0.2.0.exe") -> dict:
    """Build a minimal GitHub release JSON body."""
    return {
        "tag_name": tag,
        "draft": False,
        "prerelease": False,
        "body": "notes",
        "assets": [
            {
                "name": asset_name,
                "browser_download_url": "https://example.com/" + asset_name,
            }
        ],
    }


def test_parse_github_release_setup_asset() -> None:
    """Setup.exe asset is selected from the release payload."""
    info = parse_github_release(_payload("v0.2.0"))
    assert info is not None
    assert info.version == "0.2.0"
    assert info.setup_name == "SketchBook-Setup-v0.2.0.exe"
    assert info.setup_url.endswith(".exe")


def test_parse_github_release_missing_setup() -> None:
    """Zip-only releases are ignored."""
    payload = _payload("v0.2.0", "SketchBook-Windows-v0.2.0.zip")
    assert parse_github_release(payload) is None


def test_parse_github_release_skips_draft() -> None:
    """Drafts are not offered as updates."""
    payload = _payload("v0.3.0")
    payload["draft"] = True
    assert parse_github_release(payload) is None


def test_is_update_available_and_skipped() -> None:
    """Skip list hides a version the user dismissed."""
    assert is_update_available("0.2.0", "0.1.1") is True
    assert is_update_available("0.1.1", "0.1.1") is False
    assert is_update_available("0.2.0", "0.1.1", skipped_version="0.2.0") is False


def test_explain_unparsed_release_lists_assets() -> None:
    """Zip-only payloads mention the missing Setup.exe and asset names."""
    payload = _payload("v0.2.0", "SketchBook-Windows-v0.2.0.zip")
    reason = explain_unparsed_release(payload)
    assert "Setup.exe" in reason
    assert "SketchBook-Windows-v0.2.0.zip" in reason


def test_fetch_reason_url_error() -> None:
    """Network/SSL failures return the URLError reason."""

    def _opener(_request, timeout=15):
        raise urllib.error.URLError("certificate verify failed")

    release, reason = fetch_latest_release_with_reason(
        "acme", "SketchBook", opener=_opener
    )
    assert release is None
    assert reason is not None
    assert "certificate verify failed" in reason


def test_fetch_reason_http_error() -> None:
    """HTTP errors include status code and response snippet."""

    def _opener(_request, timeout=15):
        raise urllib.error.HTTPError(
            url="https://api.github.com/repos/acme/SketchBook/releases/latest",
            code=403,
            msg="Forbidden",
            hdrs=None,
            fp=io.BytesIO(b'{"message":"API rate limit exceeded"}'),
        )

    release, reason = fetch_latest_release_with_reason(
        "acme", "SketchBook", opener=_opener
    )
    assert release is None
    assert reason is not None
    assert "HTTP 403" in reason
    assert "rate limit" in reason


def test_ssl_context_uses_ca_bundle() -> None:
    """HTTPS checks pin a CA file when certifi (or a bundle) is present."""
    ctx = ssl_context()
    assert ctx is not None
    cafile = resolve_cafile()
    if cafile:
        assert Path(cafile).is_file()


def test_load_update_feed(tmp_path: Path) -> None:
    """Feed JSON yields owner/repo; missing file returns None."""
    feed = tmp_path / "update_feed.json"
    feed.write_text(
        json.dumps({"owner": "acme", "repo": "SketchBook"}), encoding="utf-8"
    )
    loaded = load_update_feed(feed)
    assert loaded == {"owner": "acme", "repo": "SketchBook"}
    assert load_update_feed(tmp_path / "missing.json") is None
