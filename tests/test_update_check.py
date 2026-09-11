"""Tests for GitHub release parsing (no network)."""

import json
from pathlib import Path

from core.update_check import (
    is_update_available,
    load_update_feed,
    parse_github_release,
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


def test_load_update_feed(tmp_path: Path) -> None:
    """Feed JSON yields owner/repo; missing file returns None."""
    feed = tmp_path / "update_feed.json"
    feed.write_text(
        json.dumps({"owner": "acme", "repo": "SketchBook"}), encoding="utf-8"
    )
    loaded = load_update_feed(feed)
    assert loaded == {"owner": "acme", "repo": "SketchBook"}
    assert load_update_feed(tmp_path / "missing.json") is None
