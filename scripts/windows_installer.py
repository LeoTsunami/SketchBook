"""
Windows installer helpers for the SketchBook packager.

Finds Inno Setup's ISCC, writes update_feed.json, compiles the Setup.exe.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
ISS_FILE = ROOT / "installer" / "sketchbook.iss"
FEED_FILE = ROOT / "update_feed.json"

_GITHUB_HTTPS = re.compile(
    r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/.]+?)(?:\.git)?/?$",
    re.IGNORECASE,
)


def parse_github_remote(url: str) -> Optional[Tuple[str, str]]:
    """
    Parse owner/repo from a GitHub remote URL.

    Args:
        url: ``git@github.com:org/repo.git`` or HTTPS equivalent.

    Returns:
        (owner, repo) or None.
    """
    text = url.strip()
    match = _GITHUB_HTTPS.search(text.replace("ssh://", ""))
    if not match:
        return None
    return match.group("owner"), match.group("repo")


def detect_github_repo(run) -> Optional[Tuple[str, str]]:
    """
    Read ``origin`` and parse GitHub owner/repo.

    Args:
        run: ``package_release.run`` callable.

    Returns:
        (owner, repo) or None.
    """
    result = run(
        ["git", "remote", "get-url", "origin"],
        check=False,
        capture=True,
    )
    if result.returncode != 0 or not result.stdout:
        return None
    return parse_github_remote(result.stdout.strip())


def write_update_feed(owner: str, repo: str, dest: Path = FEED_FILE) -> Path:
    """
    Write the bundled GitHub feed file.

    Args:
        owner: GitHub owner.
        repo: Repository name.
        dest: Output JSON path.

    Returns:
        Path: Written file.
    """
    dest.write_text(
        json.dumps({"owner": owner, "repo": repo}, indent=2) + "\n",
        encoding="utf-8",
    )
    return dest


def find_iscc() -> Optional[Path]:
    """
    Locate Inno Setup 6 compiler.

    Returns:
        Path to ``ISCC.exe`` or None.
    """
    found = shutil.which("ISCC") or shutil.which("ISCC.exe")
    if found:
        return Path(found)
    roots = [
        os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
        os.environ.get("ProgramFiles", r"C:\Program Files"),
    ]
    local_app = os.environ.get("LOCALAPPDATA", "")
    if local_app:
        roots.append(str(Path(local_app) / "Programs"))
    for root in roots:
        candidate = Path(root) / "Inno Setup 6" / "ISCC.exe"
        if candidate.is_file():
            return candidate
    return None


def compile_installer(version: str, dist_dir: Path) -> Path:
    """
    Compile ``installer/sketchbook.iss`` to ``dist/SketchBook-Setup-vX.Y.Z.exe``.

    Args:
        version: SemVer without ``v``.
        dist_dir: PyInstaller / ISCC output directory.

    Returns:
        Path: Built Setup.exe.

    Raises:
        FileNotFoundError: Inno Setup is not installed.
        RuntimeError: ISCC failed or output is missing.
    """
    iscc = find_iscc()
    if iscc is None:
        raise FileNotFoundError(
            "Inno Setup 6 (ISCC.exe) not found.\n"
            "Install it with:\n"
            "  winget install JRSoftware.InnoSetup\n"
            "then re-run the packager."
        )
    if not ISS_FILE.is_file():
        raise FileNotFoundError(f"Missing installer script: {ISS_FILE}")
    dist_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(iscc),
        f"/DMyAppVersion={version}",
        f"/O{dist_dir}",
        str(ISS_FILE),
    ]
    print(f"> {' '.join(cmd)}")
    completed = subprocess.run(cmd, cwd=ROOT, check=False, text=True)
    if completed.returncode != 0:
        raise RuntimeError("Inno Setup compilation failed.")
    setup_path = dist_dir / f"SketchBook-Setup-v{version}.exe"
    if not setup_path.is_file():
        raise RuntimeError(f"Setup.exe not found: {setup_path}")
    return setup_path
