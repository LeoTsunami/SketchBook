"""
GitHub Releases update check (no extra dependencies).

Reads owner/repo from bundled ``update_feed.json`` and compares the latest
release tag to the running app version.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from core.semver import is_newer, normalize_version
from core.version import get_version

SETUP_NAME_RE = re.compile(r"^SketchBook-Setup-v?\d+\.\d+\.\d+\.exe$", re.IGNORECASE)
USER_AGENT = "SketchBook-Updater"
FEED_FILENAME = "update_feed.json"


@dataclass(frozen=True)
class ReleaseInfo:
    """Parsed GitHub release that includes a Windows Setup.exe asset."""

    version: str
    tag: str
    setup_url: str
    setup_name: str
    notes: str


def _feed_candidates() -> list[Path]:
    """
    Return likely locations of ``update_feed.json`` (dev + frozen).

    Returns:
        list[Path]: Paths to try in order.
    """
    here = Path(__file__).resolve().parent
    candidates = [
        here.parent / FEED_FILENAME,
        Path.cwd() / FEED_FILENAME,
    ]
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.insert(0, Path(meipass) / FEED_FILENAME)
        candidates.insert(0, Path(sys.executable).resolve().parent / FEED_FILENAME)
    return candidates


def load_update_feed(path: Optional[Path] = None) -> Optional[Dict[str, str]]:
    """
    Load GitHub owner/repo from the update feed file.

    Args:
        path: Optional explicit feed path (tests).

    Returns:
        Dict with ``owner`` and ``repo``, or None if missing/invalid.
    """
    paths = [path] if path is not None else _feed_candidates()
    for candidate in paths:
        if candidate is None or not candidate.is_file():
            continue
        try:
            data = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        owner = str(data.get("owner") or "").strip()
        repo = str(data.get("repo") or "").strip()
        if owner and repo:
            return {"owner": owner, "repo": repo}
    return None


def parse_github_release(payload: Dict[str, Any]) -> Optional[ReleaseInfo]:
    """
    Extract version and Setup.exe URL from a GitHub release JSON object.

    Args:
        payload: Decoded ``releases/latest`` (or a specific release) body.

    Returns:
        ReleaseInfo or None when the payload has no usable Setup asset.
    """
    if payload.get("draft") or payload.get("prerelease"):
        return None
    tag = str(payload.get("tag_name") or "")
    try:
        version = normalize_version(tag)
        # Validate X.Y.Z without importing parse errors into None.
        if not re.fullmatch(r"\d+\.\d+\.\d+", version):
            return None
    except (TypeError, ValueError):
        return None
    setup_url = ""
    setup_name = ""
    for asset in payload.get("assets") or []:
        name = str(asset.get("name") or "")
        url = str(asset.get("browser_download_url") or "")
        if SETUP_NAME_RE.match(name) and url:
            setup_url = url
            setup_name = name
            break
    if not setup_url:
        return None
    notes = str(payload.get("body") or "").strip()
    return ReleaseInfo(
        version=version,
        tag=tag,
        setup_url=setup_url,
        setup_name=setup_name,
        notes=notes,
    )


def is_update_available(
    latest: str,
    current: str,
    skipped_version: str = "",
) -> bool:
    """
    Return True when ``latest`` should be offered to the user.

    Args:
        latest: Version on GitHub.
        current: Installed app version.
        skipped_version: Version the user chose to ignore.

    Returns:
        bool: True when latest is newer and not skipped.
    """
    if skipped_version and normalize_version(skipped_version) == normalize_version(
        latest
    ):
        return False
    return is_newer(latest, current)


def fetch_latest_release(
    owner: str,
    repo: str,
    *,
    opener: Optional[Callable[..., object]] = None,
    timeout: int = 15,
) -> Optional[ReleaseInfo]:
    """
    GET GitHub ``releases/latest`` and parse it.

    Args:
        owner: GitHub user or org.
        repo: Repository name.
        opener: Optional ``urlopen`` replacement (tests).
        timeout: Request timeout in seconds.

    Returns:
        ReleaseInfo or None on network/parse failure.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": f"{USER_AGENT}/{get_version()}",
            "Accept": "application/vnd.github+json",
        },
    )
    open_url = opener or urllib.request.urlopen
    try:
        with open_url(request, timeout=timeout) as response:
            raw = response.read()
    except (urllib.error.URLError, TimeoutError, OSError):
        return None
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    return parse_github_release(payload)


def download_file(
    url: str,
    dest: Path,
    progress: Optional[Callable[[int, int], None]] = None,
    *,
    opener: Optional[Callable[..., object]] = None,
    timeout: int = 60,
) -> None:
    """
    Download ``url`` to ``dest``, reporting byte progress.

    Args:
        url: Direct asset URL.
        dest: Destination file path.
        progress: Optional ``(downloaded, total)`` callback. ``total`` may be 0.
        opener: Optional ``urlopen`` replacement (tests).
        timeout: Request timeout in seconds.

    Raises:
        OSError: On HTTP or filesystem failure.
    """
    request = urllib.request.Request(
        url,
        headers={"User-Agent": f"{USER_AGENT}/{get_version()}"},
    )
    open_url = opener or urllib.request.urlopen
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open_url(request, timeout=timeout) as response:
        total = 0
        try:
            total = int(response.headers.get("Content-Length") or 0)
        except (TypeError, ValueError):
            total = 0
        downloaded = 0
        with open(dest, "wb") as handle:
            while True:
                chunk = response.read(64 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
                downloaded += len(chunk)
                if progress:
                    progress(downloaded, total)
