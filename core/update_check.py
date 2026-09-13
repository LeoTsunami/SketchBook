"""
GitHub Releases update check (no extra dependencies).

Reads owner/repo from bundled ``update_feed.json`` and compares the latest
release tag to the running app version.
"""

from __future__ import annotations

import json
import re
import ssl
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

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


def describe_update_feed_search() -> str:
    """
    Describe which ``update_feed.json`` paths were probed.

    Returns:
        str: Human-readable candidate list with found/missing.
    """
    parts: list[str] = []
    for candidate in _feed_candidates():
        state = "ok" if candidate.is_file() else "missing"
        parts.append(f"{candidate} [{state}]")
    return "; ".join(parts) if parts else "(no candidates)"


def resolve_cafile() -> Optional[str]:
    """
    Locate a CA bundle for HTTPS (certifi, then frozen fallbacks).

    Frozen PyInstaller builds often have empty default SSL paths, which
    makes GitHub ``releases/latest`` fail with a certificate error.

    Returns:
        Optional[str]: Path to ``cacert.pem``, or None.
    """
    try:
        import certifi

        where = certifi.where()
        if where and Path(where).is_file():
            return where
    except ImportError:
        pass
    roots: list[Path] = []
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            roots.append(Path(meipass))
        roots.append(Path(sys.executable).resolve().parent)
    for root in roots:
        for relative in (Path("certifi") / "cacert.pem", Path("cacert.pem")):
            candidate = root / relative
            if candidate.is_file():
                return str(candidate)
    return None


def ssl_context() -> ssl.SSLContext:
    """
    Build an SSL context that works in frozen Windows builds.

    Returns:
        ssl.SSLContext: Default context, pinned to certifi when available.
    """
    cafile = resolve_cafile()
    if cafile:
        return ssl.create_default_context(cafile=cafile)
    return ssl.create_default_context()


def describe_ssl_context() -> str:
    """
    Describe the certificate bundle used for GitHub HTTPS.

    Returns:
        str: ``cafile`` / ``capath`` and the resolved certifi path.
    """
    paths = ssl.get_default_verify_paths()
    return (
        f"cafile={paths.cafile!s} capath={paths.capath!s} "
        f"openssl_cafile={paths.openssl_cafile!s} "
        f"resolved_cafile={resolve_cafile()!s}"
    )


def _urlopen(
    request: urllib.request.Request,
    timeout: int,
    opener: Optional[Callable[..., object]] = None,
):
    """
    Open ``request`` with an SSL context unless a test opener is supplied.

    Args:
        request: Prepared urllib request.
        timeout: Socket timeout in seconds.
        opener: Optional ``urlopen`` replacement (tests).

    Returns:
        The ``urlopen`` response object.
    """
    if opener is not None:
        return opener(request, timeout=timeout)
    return urllib.request.urlopen(request, timeout=timeout, context=ssl_context())


def explain_unparsed_release(payload: Dict[str, Any]) -> str:
    """
    Explain why ``parse_github_release`` rejected a payload.

    Args:
        payload: Decoded GitHub release JSON.

    Returns:
        str: Short diagnostic for the developer log.
    """
    if payload.get("message"):
        return f"GitHub API message: {payload.get('message')}"
    if payload.get("draft"):
        return "Latest release is a draft."
    if payload.get("prerelease"):
        return "Latest release is marked pre-release."
    tag = str(payload.get("tag_name") or "")
    if tag:
        try:
            version = normalize_version(tag)
        except (TypeError, ValueError):
            version = ""
        if not version or not re.fullmatch(r"\d+\.\d+\.\d+", version):
            return f"Unsupported tag_name={tag!r}."
    names = [str(asset.get("name") or "") for asset in payload.get("assets") or []]
    if not names:
        return f"Release {tag or '(no tag)'} has no assets."
    return f"No Setup.exe on {tag or '(no tag)'}; assets={names}"


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


def fetch_latest_release_with_reason(
    owner: str,
    repo: str,
    *,
    opener: Optional[Callable[..., object]] = None,
    timeout: int = 15,
) -> Tuple[Optional[ReleaseInfo], Optional[str]]:
    """
    GET GitHub ``releases/latest`` and return a parse or a failure reason.

    Args:
        owner: GitHub user or org.
        repo: Repository name.
        opener: Optional ``urlopen`` replacement (tests).
        timeout: Request timeout in seconds.

    Returns:
        (ReleaseInfo, None) on success, or (None, reason) on failure.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": f"{USER_AGENT}/{get_version()}",
            "Accept": "application/vnd.github+json",
        },
    )
    try:
        with _urlopen(request, timeout, opener=opener) as response:
            status = getattr(response, "status", None)
            raw = response.read()
    except urllib.error.HTTPError as exc:
        snippet = ""
        try:
            snippet = exc.read()[:240].decode("utf-8", errors="replace").strip()
        except (OSError, UnicodeError):
            snippet = ""
        extra = f" body={snippet}" if snippet else ""
        return None, f"HTTP {exc.code} {exc.reason} for {url}{extra}"
    except urllib.error.URLError as exc:
        return None, f"URL error for {url}: {exc.reason!s}"
    except TimeoutError:
        return None, f"Timeout after {timeout}s: {url}"
    except OSError as exc:
        return None, f"OS error for {url}: {exc}"
    if status not in (None, 200):
        return None, f"Unexpected HTTP {status} from {url} ({len(raw)} bytes)"
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        return None, f"Invalid JSON from {url} ({len(raw)} bytes): {exc}"
    if not isinstance(payload, dict):
        return None, f"GitHub JSON is not an object ({type(payload).__name__})."
    parsed = parse_github_release(payload)
    if parsed is None:
        return None, explain_unparsed_release(payload)
    return parsed, None


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
    release, _reason = fetch_latest_release_with_reason(
        owner, repo, opener=opener, timeout=timeout
    )
    return release


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
    dest.parent.mkdir(parents=True, exist_ok=True)
    with _urlopen(request, timeout, opener=opener) as response:
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
