#!/usr/bin/env python3
"""
One-command SketchBook packager (Windows).

Bumps version, updates changelogs, builds a PyInstaller onedir zip, commits/tags,
and optionally creates a GitHub Release.

Examples:
    python scripts/package_release.py --bump patch --notes "Library folder setting"
    python scripts/package_release.py 0.2.0 --notes "Beta build for testers"
    python scripts/package_release.py --bump patch --notes "fix" --skip-github
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import date
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from core.semver import bump_version, parse_semver
from windows_installer import (
    compile_installer,
    detect_github_repo,
    write_update_feed,
)

VERSION_FILE = ROOT / "VERSION"
CHANGELOG_EN = ROOT / "docs" / "CHANGELOG.md"
CHANGELOG_FR = ROOT / "docs" / "CHANGELOG_FR.md"
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"
SPEC_FILE = ROOT / "SketchBook.spec"
APP_FOLDER_NAME = "SketchBook"
FEED_FILE = ROOT / "update_feed.json"


def run(
    cmd: list[str],
    *,
    check: bool = True,
    capture: bool = False,
) -> subprocess.CompletedProcess:
    """
    Run a subprocess from the repo root.

    Args:
        cmd: Command and arguments.
        check: Raise on non-zero exit.
        capture: Capture stdout/stderr.

    Returns:
        CompletedProcess: Process result.
    """
    print(f"> {' '.join(cmd)}")
    return subprocess.run(
        cmd,
        cwd=ROOT,
        check=check,
        text=True,
        capture_output=capture,
    )


def read_version() -> str:
    """
    Read the current version from VERSION.

    Returns:
        str: Current semantic version.
    """
    return VERSION_FILE.read_text(encoding="utf-8").strip().splitlines()[0].strip()


def write_version(version: str) -> None:
    """
    Persist version to the VERSION file (single source of truth).

    Args:
        version: New semantic version.
    """
    parse_semver(version)
    VERSION_FILE.write_text(f"{version}\n", encoding="utf-8")


def prepend_changelog(path: Path, version: str, notes: str, lang: str) -> None:
    """
    Prepend a release section to a changelog file.

    Args:
        path: Changelog markdown path.
        version: Release version.
        notes: Release notes body.
        lang: ``en`` or ``fr`` for heading wording.
    """
    today = date.today().isoformat()
    if lang == "fr":
        header = f"## {today} (v{version})\n### ✅ Tâches:\n"
        result = "→ Résultat: build Windows packagé pour distribution.\n---\n\n"
    else:
        header = f"## {today} (v{version})\n### ✅ Tasks:\n"
        result = "→ Result: Windows build packaged for distribution.\n---\n\n"
    bullet_lines = []
    for line in notes.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        if not line.startswith("-"):
            line = f"- {line}"
        bullet_lines.append(line)
    body = "\n".join(bullet_lines) if bullet_lines else f"- Release v{version}"
    section = f"{header}{body}\n{result}"
    existing = path.read_text(encoding="utf-8") if path.exists() else "# Changelog\n\n"
    # Keep top title if present
    if existing.lstrip().startswith("#"):
        first_nl = existing.find("\n")
        title = existing[: first_nl + 1] if first_nl >= 0 else existing
        rest = existing[len(title) :]
        path.write_text(title + "\n" + section + rest.lstrip("\n"), encoding="utf-8")
    else:
        path.write_text(section + existing, encoding="utf-8")


def ensure_pyinstaller() -> Path:
    """
    Return the project venv python, ensuring PyInstaller is importable.

    Returns:
        Path: Python executable to use for the build.
    """
    venv_python = ROOT / ".venv" / "Scripts" / "python.exe"
    python = venv_python if venv_python.exists() else Path(sys.executable)
    probe = subprocess.run(
        [str(python), "-c", "import PyInstaller; print(PyInstaller.__version__)"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if probe.returncode != 0:
        print("PyInstaller missing — installing into the active environment…")
        run([str(python), "-m", "pip", "install", "pyinstaller>=6.0.0"])
    return python


def build_onedir(python: Path) -> Path:
    """
    Run PyInstaller and return the onedir output folder.

    Args:
        python: Interpreter that has PyInstaller.

    Returns:
        Path: ``dist/SketchBook`` folder.
    """
    if not SPEC_FILE.exists():
        raise FileNotFoundError(f"Missing spec: {SPEC_FILE}")
    run(
        [
            str(python),
            "-m",
            "PyInstaller",
            str(SPEC_FILE),
            "--noconfirm",
            "--clean",
        ]
    )
    out = DIST_DIR / APP_FOLDER_NAME
    if not out.is_dir():
        raise RuntimeError(f"Build output not found: {out}")
    return out


def zip_folder(folder: Path, zip_path: Path) -> Path:
    """
    Zip an onedir build for distribution.

    Args:
        folder: Folder to archive (contents at zip root under SketchBook/).
        zip_path: Destination zip path.

    Returns:
        Path: Created zip file.
    """
    if zip_path.exists():
        zip_path.unlink()
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in folder.rglob("*"):
            if file_path.is_file():
                arcname = Path(APP_FOLDER_NAME) / file_path.relative_to(folder)
                zf.write(file_path, arcname.as_posix())
    return zip_path


def which(cmd: str) -> Optional[str]:
    """
    Locate an executable on PATH (with common Windows fallbacks for ``gh``).

    Args:
        cmd: Command name.

    Returns:
        Optional[str]: Full path or None.
    """
    found = shutil.which(cmd)
    if found:
        return found
    if cmd.lower() in {"gh", "gh.exe"}:
        candidates = [
            Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
            / "GitHub CLI"
            / "gh.exe",
            Path(os.environ.get("LocalAppData", ""))
            / "Programs"
            / "GitHub CLI"
            / "gh.exe",
        ]
        for path in candidates:
            if path.is_file():
                return str(path)
    return None


def git_release_steps(
    version: str,
    assets: list[Path],
    notes: str,
    *,
    dry_run: bool,
    no_push: bool,
    skip_github: bool,
) -> None:
    """
    Commit version files, tag, push, and create a GitHub Release when possible.

    Args:
        version: Release version.
        assets: Files to attach (Setup.exe, zip).
        notes: Release notes.
        dry_run: Print actions only.
        no_push: Do not push remotes.
        skip_github: Skip ``gh release create``.
    """
    tag = f"v{version}"
    files = [
        VERSION_FILE,
        CHANGELOG_EN,
        CHANGELOG_FR,
        FEED_FILE,
        ROOT / "bootstrap.py",
        ROOT / "SketchBook.spec",
        ROOT / "core" / "version.py",
        ROOT / "core" / "semver.py",
        ROOT / "core" / "settings.py",
        ROOT / "core" / "update_check.py",
        ROOT / "gui" / "main_window.py",
        ROOT / "gui" / "settings_dialog.py",
        ROOT / "gui" / "update_coordinator.py",
        ROOT / "gui" / "update_dialog.py",
        ROOT / "gui" / "update_worker.py",
        ROOT / "installer" / "sketchbook.iss",
        ROOT / "scripts" / "package_release.py",
        ROOT / "scripts" / "package_release.ps1",
        ROOT / "scripts" / "package_release.bat",
        ROOT / "scripts" / "windows_installer.py",
        ROOT / "requirements-packaging.txt",
        ROOT / ".cursor" / "PACKAGING_AND_RELEASE_STRATEGY.md",
        ROOT / ".cursor" / "TASKS.md",
        ROOT / "docs" / "USER_DATA_DIRECTORY.md",
        ROOT / "tests" / "test_semver.py",
        ROOT / "tests" / "test_settings.py",
        ROOT / "tests" / "test_update_check.py",
        ROOT / "tests" / "test_windows_installer.py",
    ]
    existing = [str(p.relative_to(ROOT)) for p in files if p.exists()]
    asset_names = " ".join(path.name for path in assets)

    if dry_run:
        print(f"[dry-run] git add {' '.join(existing)}")
        print(f'[dry-run] git commit -m "Release {tag}"')
        print(f"[dry-run] git tag {tag}")
        if not no_push:
            print("[dry-run] git push && git push origin tag")
        if not skip_github:
            print(f"[dry-run] gh release create {tag} {asset_names}")
        return

    if existing:
        run(["git", "add", *existing])
        status = run(["git", "status", "--porcelain"], capture=True)
        if status.stdout.strip():
            run(["git", "commit", "-m", f"Release {tag}"])
        else:
            print("Nothing to commit (version files already up to date).")

    run(["git", "tag", "-f", tag])
    if not no_push:
        run(["git", "push"])
        run(["git", "push", "-f", "origin", tag])

    if skip_github:
        print("Skipped GitHub Release (--skip-github).")
        for asset in assets:
            print(f"Local asset: {asset}")
        return

    gh = which("gh")
    if not gh:
        quoted = " ".join(f'"{a}"' for a in assets)
        print(
            "\nWARNING: `gh` CLI not found. Tag was pushed (if allowed) but "
            "no GitHub Release was created.\n"
            "Install GitHub CLI, then run:\n"
            f'  gh release create {tag} {quoted} --title "SketchBook {tag}" '
            f'--notes "{notes}"\n'
        )
        return

    check = subprocess.run(
        [gh, "release", "view", tag],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if check.returncode == 0:
        run([gh, "release", "delete", tag, "--yes"], check=False)
    cmd = [
        gh,
        "release",
        "create",
        tag,
        *[str(asset) for asset in assets],
        "--title",
        f"SketchBook {tag}",
        "--notes",
        notes,
    ]
    run(cmd)


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    """
    Parse CLI arguments.

    Args:
        argv: Optional argv override.

    Returns:
        argparse.Namespace: Parsed options.
    """
    parser = argparse.ArgumentParser(
        description="Package SketchBook for Windows and publish to GitHub Releases."
    )
    parser.add_argument(
        "version",
        nargs="?",
        help="Explicit version X.Y.Z (optional if --bump is used).",
    )
    parser.add_argument(
        "--bump",
        choices=("major", "minor", "patch"),
        help="Bump current VERSION instead of passing an explicit version.",
    )
    parser.add_argument(
        "--notes",
        required=True,
        help="Release notes (used in changelogs and GitHub Release).",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip PyInstaller (zip an existing dist/SketchBook if present).",
    )
    parser.add_argument(
        "--skip-installer",
        action="store_true",
        help="Skip Inno Setup (zip only; no Setup.exe).",
    )
    parser.add_argument(
        "--skip-github",
        action="store_true",
        help="Do not create/upload a GitHub Release.",
    )
    parser.add_argument(
        "--no-push",
        action="store_true",
        help="Commit/tag locally but do not push.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the plan only (no VERSION/changelog/build/git/github changes).",
    )
    parser.add_argument(
        "--skip-changelog",
        action="store_true",
        help="Do not modify CHANGELOG files.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    """
    Entry point for the packager.

    Args:
        argv: Optional CLI argv.

    Returns:
        int: Process exit code.
    """
    args = parse_args(argv)
    current = read_version()
    if args.version and args.bump:
        print("Use either an explicit version or --bump, not both.")
        return 2
    if args.version:
        new_version = args.version.lstrip("v")
        parse_semver(new_version)
    elif args.bump:
        new_version = bump_version(current, args.bump)
    else:
        print("Provide a version (e.g. 0.2.0) or --bump patch|minor|major.")
        return 2

    print(f"Packaging SketchBook {current} -> {new_version}")
    if args.dry_run:
        print("[dry-run] Would write VERSION, changelogs, build, tag, and release.")
        print(f"[dry-run] notes={args.notes!r}")
        print(
            f"[dry-run] zip=dist/SketchBook-Windows-v{new_version}.zip "
            f"setup=dist/SketchBook-Setup-v{new_version}.exe "
            f"skip_build={args.skip_build} skip_installer={args.skip_installer} "
            f"skip_github={args.skip_github} no_push={args.no_push}"
        )
        return 0

    write_version(new_version)

    repo = detect_github_repo(run)
    if repo:
        write_update_feed(repo[0], repo[1], FEED_FILE)
        print(f"Update feed: {repo[0]}/{repo[1]}")
    else:
        print("No GitHub origin remote; update_feed.json not written.")

    if not args.skip_changelog:
        prepend_changelog(CHANGELOG_EN, new_version, args.notes, "en")
        prepend_changelog(CHANGELOG_FR, new_version, args.notes, "fr")
        print("Changelogs updated.")

    if args.skip_build:
        app_dir = DIST_DIR / APP_FOLDER_NAME
        if not app_dir.is_dir():
            print(f"--skip-build but missing {app_dir}")
            return 1
        print(f"Reusing existing build at {app_dir}")
    else:
        python = ensure_pyinstaller()
        app_dir = build_onedir(python)

    zip_path = DIST_DIR / f"SketchBook-Windows-v{new_version}.zip"
    zip_folder(app_dir, zip_path)
    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"Created {zip_path} ({size_mb:.1f} MiB)")

    assets = [zip_path]
    if args.skip_installer:
        print("Skipped Inno Setup (--skip-installer).")
    else:
        try:
            setup_path = compile_installer(new_version, DIST_DIR)
        except (FileNotFoundError, RuntimeError) as exc:
            print(str(exc))
            return 1
        setup_mb = setup_path.stat().st_size / (1024 * 1024)
        print(f"Created {setup_path} ({setup_mb:.1f} MiB)")
        assets.insert(0, setup_path)

    git_release_steps(
        new_version,
        assets,
        args.notes,
        dry_run=False,
        no_push=args.no_push,
        skip_github=args.skip_github,
    )
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
