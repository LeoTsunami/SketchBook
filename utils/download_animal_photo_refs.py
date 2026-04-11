#!/usr/bin/env python3
"""
Script pour télécharger récursivement toutes les images du site
animal-photo-references.com à partir de la section Mammals.

Usage:
    python -m utils.download_animal_photo_refs

Dépendances (hors requirements runtime) : voir `requirements-tools.txt`
    pip install -r requirements-tools.txt

Les images sont enregistrées dans le dossier configuré (OUTPUT_DIR).
Respecte une pause entre requêtes pour limiter la charge sur le serveur.
"""
from __future__ import annotations

import re
import time
import hashlib
from pathlib import Path
from urllib.parse import urljoin, urlparse
from typing import Set

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError as e:
    raise ImportError(
        "Ce script nécessite requests et beautifulsoup4. "
        "Installez-les avec: pip install -r requirements-tools.txt"
    ) from e

# Configuration
BASE_URL = "https://www.animal-photo-references.com"
START_PATH = "/mammals"
OUTPUT_DIR = Path(r"C:\Users\recoc\Pictures\LifeDrawing\Animal\FromAnimalPhotoRef.com")
REQUEST_DELAY_SEC = 1.0
IMAGE_DELAY_SEC = 0.25
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

# Pages à ne pas crawler (segment de chemin, sans /)
IGNORED_PAGE_SEGMENTS = frozenset({
    "art-gallery-submissions",
    "art-gallery-sumissions",  # typo possible sur le site
    "contact",
    "about",
    "how-to-use",
    "terms-of-use",
    "support",
})

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "SketchBook-RefDownload/1.0 (Art reference; educational use)",
    "Accept": "text/html,image/*,*/*",
    "Accept-Language": "en-US,en;q=0.9",
})


def is_same_site(url: str) -> bool:
    """Return True if URL belongs to animal-photo-references.com."""
    parsed = urlparse(url)
    if not parsed.netloc:
        return True
    return "animal-photo-references.com" in parsed.netloc


def normalize_page_url(url: str) -> str:
    """Normalize page URL (remove fragment, ensure scheme)."""
    url = urljoin(BASE_URL, url)
    parsed = urlparse(url)
    path = parsed.path.rstrip("/") or "/"
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def should_skip_page(url: str) -> bool:
    """Return True if this page should not be crawled (contact, about, etc.)."""
    parsed = urlparse(url)
    path = (parsed.path or "/").strip("/")
    if not path:
        return False
    segments = path.lower().split("/")
    return any(seg in IGNORED_PAGE_SEGMENTS for seg in segments)


def url_to_subfolder_path(url: str) -> Path:
    """
    Return the relative folder path for a page URL (e.g. mammals/cats/big-cats).
    Used to store images in subfolders named after the page.
    """
    parsed = urlparse(url)
    path = (parsed.path or "/").strip("/")
    if not path:
        return Path("mammals")  # fallback for root
    # Sanitize: only keep safe path parts
    parts = [re.sub(r"[^\w\-]", "_", p) for p in path.split("/") if p]
    return Path(*parts) if parts else Path("mammals")


def fetch_html(url: str) -> str | None:
    """Fetch HTML content; returns None on failure."""
    try:
        r = SESSION.get(url, timeout=15)
        r.raise_for_status()
        return r.text
    except requests.RequestException as e:
        print(f"  [skip] {url}: {e}")
        return None


def extract_links_and_images(soup: BeautifulSoup, page_url: str) -> tuple[list[str], list[str]]:
    """
    Extract same-site page links and image URLs from parsed HTML.

    Args:
        soup: Parsed BeautifulSoup document.
        page_url: URL of the current page (for resolving relative URLs).

    Returns:
        (list of page URLs to crawl, list of image URLs).
    """
    page_links: list[str] = []
    image_urls: list[str] = []

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#") or href.startswith("mailto:"):
            continue
        full = urljoin(page_url, href)
        if not is_same_site(full):
            continue
        parsed = urlparse(full)
        path = (parsed.path or "/").rstrip("/") or "/"
        full = f"{parsed.scheme}://{parsed.netloc}{path}"
        if should_skip_page(full):
            continue
        page_links.append(full)

    for img in soup.find_all("img", src=True):
        src = img.get("src") or img.get("data-src")
        if not src:
            continue
        full = urljoin(page_url, src)
        if not full.startswith("http"):
            continue
        image_urls.append(full)

    # Squarespace / common galleries: links to images (same extension or known CDN)
    for a in soup.find_all("a", href=True):
        href = a["href"]
        full = urljoin(page_url, href)
        parsed = urlparse(full)
        path_lower = (parsed.path or "").lower()
        if path_lower.endswith(tuple(IMAGE_EXTENSIONS)):
            image_urls.append(full)
        if "squarespace-cdn.com" in (parsed.netloc or ""):
            image_urls.append(full)

    return page_links, image_urls


def safe_filename(url: str, index: int) -> str:
    """Generate a safe filename from URL and index to avoid collisions."""
    parsed = urlparse(url)
    name = Path(parsed.path).stem or "image"
    name = re.sub(r"[^\w\-.]", "_", name)[:80]
    suffix = Path(parsed.path).suffix.lower()
    if suffix not in IMAGE_EXTENSIONS:
        suffix = ".jpg"
    if index > 0:
        return f"{name}_{index}{suffix}"
    return f"{name}{suffix}"


def download_image(url: str, folder: Path, seen: Set[str]) -> Path | None:
    """
    Download one image to folder if not already seen. Returns path if saved, else None.
    """
    if url in seen:
        return None
    try:
        r = SESSION.get(url, timeout=20, stream=True)
        r.raise_for_status()
        content_type = (r.headers.get("Content-Type") or "").lower()
        if "image/" not in content_type and not url.lower().endswith(tuple(IMAGE_EXTENSIONS)):
            return None
        data = r.content
        if len(data) < 100:
            return None
    except requests.RequestException as e:
        print(f"  [skip image] {url[:70]}...: {e}")
        return None

    seen.add(url)
    time.sleep(IMAGE_DELAY_SEC)
    # Dedupe by content hash to avoid same image under different URL
    h = hashlib.sha256(data).hexdigest()[:12]
    base = safe_filename(url, 0)
    stem, ext = (Path(base).stem, Path(base).suffix)
    if not ext or ext.lower() not in IMAGE_EXTENSIONS:
        ext = ".jpg"
    path = folder / f"{stem}_{h}{ext}"
    if path.exists():
        return path
    path.write_bytes(data)
    return path


def crawl_and_download(
    start_url: str,
    output_dir: Path,
    delay: float = REQUEST_DELAY_SEC,
) -> None:
    """
    Crawl pages from start_url (same site only) and download all images into output_dir.

    Args:
        start_url: Full URL of the first page (e.g. mammals index).
        output_dir: Directory where to save images.
        delay: Seconds to wait between page requests.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    to_visit: list[str] = [start_url]
    visited: Set[str] = set()
    seen_images: Set[str] = set()
    downloaded = 0

    while to_visit:
        url = to_visit.pop(0)
        if url in visited:
            continue
        visited.add(url)
        if should_skip_page(url):
            continue
        # Dossier par page (ex. mammals/cats/big-cats)
        subfolder = url_to_subfolder_path(url)
        page_dir = output_dir / subfolder
        page_dir.mkdir(parents=True, exist_ok=True)
        print(f"[page] {url} -> {subfolder}")
        time.sleep(delay)

        html = fetch_html(url)
        if not html:
            continue

        soup = BeautifulSoup(html, "html.parser")
        page_links, image_urls = extract_links_and_images(soup, url)

        for link in page_links:
            norm = normalize_page_url(link)
            if should_skip_page(norm):
                continue
            if norm not in visited and norm not in to_visit:
                to_visit.append(norm)

        for img_url in image_urls:
            path = download_image(img_url, page_dir, seen_images)
            if path:
                downloaded += 1
                print(f"  -> {subfolder / path.name}")

    print(f"\nTerminé. Pages visitées: {len(visited)}, images téléchargées: {downloaded}")
    print(f"Dossier: {output_dir}")


def main() -> None:
    """Entry point: crawl from mammals and save images to OUTPUT_DIR."""
    start_url = urljoin(BASE_URL, START_PATH)
    print(f"Récupération des images depuis {start_url}")
    print(f"Sortie: {OUTPUT_DIR}\n")
    crawl_and_download(start_url, OUTPUT_DIR, delay=REQUEST_DELAY_SEC)


if __name__ == "__main__":
    main()
