#!/usr/bin/env python3
"""
Télécharge les photos de référence depuis monde-animal.fr (par continent).

Structure de sortie :
    <OUTPUT_DIR>/<Continent>/<Animal>/images...

Usage:
    py -3 -m utils.download_monde_animal_refs --folders-only
    py -3 -m utils.download_monde_animal_refs --test
    py -3 -m utils.download_monde_animal_refs --download

Dépendances : voir `requirements-tools.txt`
"""
from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError as e:
    raise ImportError(
        "Ce script nécessite requests et beautifulsoup4. "
        "Installez-les avec: pip install -r requirements-tools.txt"
    ) from e

from utils.monde_animal_names import (
    animal_name_en,
    continent_name_en,
    fix_known_english_folder_names,
    rename_folders_to_english,
)

BASE_URL = "https://www.monde-animal.fr"
CONTINENTS_URL = f"{BASE_URL}/zone-geographique/continent/"
OUTPUT_DIR = Path(r"C:\Users\recoc\Pictures\LifeDrawing\Animal\FromMondeAnimal.fr")
REQUEST_DELAY_SEC = 0.8
IMAGE_DELAY_SEC = 0.25
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": "SketchBook-RefDownload/1.0 (Art reference; educational use)",
        "Accept": "text/html,image/*,*/*",
        "Accept-Language": "fr-FR,fr;q=0.9",
    }
)

INVALID_WIN_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


@dataclass
class ImageCache:
    """Cache des images déjà téléchargées (évite les requêtes réseau en double)."""

    url_to_source: dict[str, Path] = field(default_factory=dict)


@dataclass(frozen=True)
class Continent:
    """Continent list entry."""

    name: str
    url: str
    slug: str


@dataclass(frozen=True)
class Animal:
    """Animal list entry on a continent page."""

    name: str
    url: str
    slug: str


def sanitize_folder_name(name: str, max_len: int = 120) -> str:
    """
    Return a Windows-safe folder name.

    Args:
        name: Raw display name.
        max_len: Maximum length of the result.

    Returns:
        Sanitized folder name.
    """
    cleaned = INVALID_WIN_CHARS.sub("", name).strip().rstrip(".")
    cleaned = re.sub(r"\s+", " ", cleaned)
    if not cleaned:
        cleaned = "sans-nom"
    return cleaned[:max_len]


def slug_from_url(url: str) -> str:
    """
    Extract the last path segment from a URL.

    Args:
        url: Page URL.

    Returns:
        Slug string.
    """
    path = urlparse(url).path.strip("/")
    return path.split("/")[-1] if path else "unknown"


def fetch_html(url: str) -> str | None:
    """
    Fetch HTML content.

    Args:
        url: Page URL.

    Returns:
        HTML text or None on failure.
    """
    try:
        response = SESSION.get(url, timeout=20)
        response.raise_for_status()
        return response.text
    except requests.RequestException as exc:
        print(f"  [skip] {url}: {exc}")
        return None


def parse_continents(soup: BeautifulSoup) -> list[Continent]:
    """
    Parse continent links from the continents index page.

    Args:
        soup: Parsed HTML.

    Returns:
        List of continents.
    """
    continents: list[Continent] = []
    for heading in soup.find_all("h2"):
        link = heading.find("a", href=True)
        if not link:
            continue
        href = urljoin(CONTINENTS_URL, link["href"])
        if "/zone-geographique/" not in href or href.rstrip("/").endswith("/continent"):
            continue
        slug = slug_from_url(href)
        continents.append(
            Continent(
                name=heading.get_text(strip=True),
                url=href,
                slug=slug,
            )
        )
    return continents


def parse_animals(soup: BeautifulSoup) -> list[Animal]:
    """
    Parse animal fiche links from a continent page.

    Args:
        soup: Parsed HTML.

    Returns:
        List of animals.
    """
    animals: list[Animal] = []
    seen_urls: set[str] = set()
    for heading in soup.find_all("h2"):
        link = heading.find("a", href=True)
        if not link:
            continue
        href = urljoin(BASE_URL, link["href"])
        if "/fiches-animaux/" not in href:
            continue
        if href in seen_urls:
            continue
        seen_urls.add(href)
        animals.append(
            Animal(
                name=heading.get_text(strip=True),
                url=href,
                slug=slug_from_url(href),
            )
        )
    return animals


def animal_folder_name(animal: Animal) -> str:
    """
    Build the folder name for an animal (English common name).

    Args:
        animal: Animal metadata.

    Returns:
        Folder name.
    """
    return animal_name_en(animal.name)


def common_name_from_folder(folder: Path) -> str:
    """
    Extract the common animal name from a folder path.

    Args:
        folder: Animal directory.

    Returns:
        Common name (part before ``__`` when present).
    """
    name = folder.name
    if "__" in name:
        return name.split("__", 1)[0]
    return name


def extract_gallery_image_urls(soup: BeautifulSoup, page_url: str) -> list[str]:
    """
    Extract photo URLs from the animal gallery section only.

    Args:
        soup: Parsed animal page HTML.
        page_url: Animal page URL for resolving relatives.

    Returns:
        Ordered list of unique image URLs.
    """
    urls: list[str] = []
    seen: set[str] = set()
    gallery = soup.select_one(".ma-gallery")
    if not gallery:
        return urls

    for image in gallery.select(".image-block img"):
        for attr in ("data-src", "data-lazy-src", "src"):
            raw = (image.get(attr) or "").strip()
            if not raw or raw.startswith("data:"):
                continue
            full = urljoin(page_url, raw)
            if full in seen:
                break
            if not full.startswith("http"):
                break
            seen.add(full)
            urls.append(full)
            break

    return urls


def safe_image_filename(url: str, index: int) -> str:
    """
    Build a filesystem-safe image filename from a URL.

    Args:
        url: Image URL.
        index: Index used to avoid collisions.

    Returns:
        Filename with extension.
    """
    parsed = urlparse(url)
    stem = sanitize_folder_name(Path(parsed.path).stem, max_len=80)
    suffix = Path(parsed.path).suffix.lower()
    if suffix not in IMAGE_EXTENSIONS:
        suffix = ".webp"
    if index:
        return f"{index:02d}_{stem}{suffix}"
    return f"{stem}{suffix}"


def copy_cached_image(source: Path, folder: Path) -> Path | None:
    """
    Copy a previously downloaded image into another animal folder.

    Args:
        source: Existing image file.
        folder: Destination folder.

    Returns:
        Destination path or None if already present.
    """
    destination = folder / source.name
    if destination.exists():
        return None
    shutil.copy2(source, destination)
    return destination


def download_image(url: str, folder: Path, cache: ImageCache) -> Path | None:
    """
    Download one gallery image, or copy it from cache if already fetched.

    Args:
        url: Image URL.
        folder: Destination folder.
        cache: Network download cache keyed by image URL.

    Returns:
        Saved path or None.
    """
    if url in cache.url_to_source:
        return copy_cached_image(cache.url_to_source[url], folder)

    try:
        response = SESSION.get(url, timeout=25, stream=True)
        response.raise_for_status()
        content_type = (response.headers.get("Content-Type") or "").lower()
        if "image/" not in content_type and not url.lower().endswith(
            tuple(IMAGE_EXTENSIONS)
        ):
            return None
        data = response.content
        if len(data) < 200:
            return None
    except requests.RequestException as exc:
        print(f"    [skip image] {url[:80]}...: {exc}")
        return None

    time.sleep(IMAGE_DELAY_SEC)

    digest = hashlib.sha256(data).hexdigest()[:10]
    base = safe_image_filename(url, 0)
    stem, ext = Path(base).stem, Path(base).suffix
    path = folder / f"{stem}_{digest}{ext}"
    if not path.exists():
        path.write_bytes(data)
    cache.url_to_source[url] = path
    return path


def list_image_files(folder: Path) -> list[Path]:
    """
    List image files in a folder.

    Args:
        folder: Directory to scan.

    Returns:
        Sorted image paths.
    """
    return sorted(
        path
        for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def rename_folders_to_common_names(output_dir: Path) -> int:
    """
    Rename animal folders to keep only the common name.

    Args:
        output_dir: Root download directory.

    Returns:
        Number of folders renamed.
    """
    renamed = 0
    for continent_dir in output_dir.iterdir():
        if not continent_dir.is_dir():
            continue
        for animal_dir in continent_dir.iterdir():
            if not animal_dir.is_dir():
                continue
            new_name = common_name_from_folder(animal_dir)
            if new_name == animal_dir.name:
                continue
            target = animal_dir.parent / new_name
            if target.exists():
                raise RuntimeError(
                    f"Collision lors du renommage: {animal_dir} -> {target}"
                )
            animal_dir.rename(target)
            renamed += 1
            print(f"  {animal_dir.name} -> {new_name}")
    return renamed


def fill_missing_copies(output_dir: Path) -> tuple[int, int]:
    """
    Copy images into empty folders that share the same common animal name.

    Args:
        output_dir: Root download directory.

    Returns:
        Tuple of (folders filled, files copied).
    """
    name_sources: dict[str, Path] = {}
    empty_folders: list[Path] = []

    for continent_dir in output_dir.iterdir():
        if not continent_dir.is_dir():
            continue
        for animal_dir in continent_dir.iterdir():
            if not animal_dir.is_dir():
                continue
            common_name = common_name_from_folder(animal_dir)
            images = list_image_files(animal_dir)
            if images and common_name not in name_sources:
                name_sources[common_name] = animal_dir
            elif not images:
                empty_folders.append(animal_dir)

    folders_filled = 0
    files_copied = 0
    for animal_dir in empty_folders:
        common_name = common_name_from_folder(animal_dir)
        source_dir = name_sources.get(common_name)
        if not source_dir:
            continue
        copied_here = 0
        for source_file in list_image_files(source_dir):
            if copy_cached_image(source_file, animal_dir):
                copied_here += 1
        if copied_here:
            folders_filled += 1
            files_copied += copied_here
            print(f"  [copie] {animal_dir.relative_to(output_dir)} ({copied_here} fichier(s))")

    return folders_filled, files_copied


def ensure_animal_folder(root: Path, continent: Continent, animal: Animal) -> Path:
    """
    Create continent/animal folder hierarchy.

    Args:
        root: Output root directory.
        continent: Continent metadata.
        animal: Animal metadata.

    Returns:
        Path to the animal folder.
    """
    continent_dir = root / continent_name_en(continent.name)
    animal_dir = continent_dir / animal_folder_name(animal)
    animal_dir.mkdir(parents=True, exist_ok=True)
    return animal_dir


def iter_continents(
    continents: Iterable[Continent],
    only_slugs: set[str] | None,
) -> Iterable[Continent]:
    """
    Filter continents by slug if requested.

    Args:
        continents: Source list.
        only_slugs: Optional slug whitelist.

    Yields:
        Matching continents.
    """
    for continent in continents:
        if only_slugs and continent.slug not in only_slugs:
            continue
        yield continent


def run(
    output_dir: Path,
    folders_only: bool,
    download_images: bool,
    continent_slugs: set[str] | None,
    animal_limit: int | None,
) -> None:
    """
    Crawl monde-animal.fr and create folders / download gallery images.

    Args:
        output_dir: Destination root.
        folders_only: If True, only create folders.
        download_images: If True, download gallery images.
        continent_slugs: Optional continent slug filter.
        animal_limit: Optional max animals per continent.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    html = fetch_html(CONTINENTS_URL)
    if not html:
        raise SystemExit("Impossible de charger la page des continents.")

    continents = parse_continents(BeautifulSoup(html, "html.parser"))
    if not continents:
        raise SystemExit("Aucun continent trouvé.")

    total_folders = 0
    total_images = 0
    image_cache = ImageCache()
    slug_page_cache: dict[str, list[str]] = {}

    for continent in iter_continents(continents, continent_slugs):
        print(f"\n[continent] {continent.name} ({continent.url})")
        time.sleep(REQUEST_DELAY_SEC)

        continent_html = fetch_html(continent.url)
        if not continent_html:
            continue

        animals = parse_animals(BeautifulSoup(continent_html, "html.parser"))
        if animal_limit is not None:
            animals = animals[:animal_limit]

        print(f"  {len(animals)} animal(s)")
        for animal in animals:
            animal_dir = ensure_animal_folder(output_dir, continent, animal)
            total_folders += 1
            print(f"  [dossier] {animal_dir.relative_to(output_dir)}")

            if folders_only or not download_images:
                continue

            if animal.slug in slug_page_cache:
                image_urls = slug_page_cache[animal.slug]
            else:
                time.sleep(REQUEST_DELAY_SEC)
                animal_html = fetch_html(animal.url)
                if not animal_html:
                    continue
                soup = BeautifulSoup(animal_html, "html.parser")
                image_urls = extract_gallery_image_urls(soup, animal.url)
                slug_page_cache[animal.slug] = image_urls

            if not image_urls:
                continue

            for image_url in image_urls:
                saved = download_image(image_url, animal_dir, image_cache)
                if saved:
                    total_images += 1
                    print(f"    -> {saved.name}")

    print(
        f"\nTerminé. Dossiers créés: {total_folders}, "
        f"images téléchargées: {total_images}"
    )
    print(f"Racine: {output_dir}")


def build_parser() -> argparse.ArgumentParser:
    """
    Build CLI argument parser.

    Returns:
        Configured ArgumentParser.
    """
    parser = argparse.ArgumentParser(
        description="Crée l'arborescence et télécharge les photos depuis monde-animal.fr."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help=f"Dossier de sortie (défaut: {OUTPUT_DIR})",
    )
    parser.add_argument(
        "--folders-only",
        action="store_true",
        help="Crée uniquement les dossiers continent/animal.",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Télécharge les images de la galerie « Photos » de chaque fiche.",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test rapide: Antarctique seulement, 3 animaux, avec téléchargement.",
    )
    parser.add_argument(
        "--continent",
        action="append",
        dest="continents",
        metavar="SLUG",
        help="Limiter à un continent (slug URL, ex: afrique, antarctique).",
    )
    parser.add_argument(
        "--animal-limit",
        type=int,
        default=None,
        metavar="N",
        help="Limiter le nombre d'animaux par continent.",
    )
    parser.add_argument(
        "--fill-missing",
        action="store_true",
        help="Copie les images manquantes vers les dossiers vides (même espèce, autre continent).",
    )
    parser.add_argument(
        "--rename-common",
        action="store_true",
        help="Renomme les dossiers animaux pour ne garder que le nom commun.",
    )
    parser.add_argument(
        "--translate-en",
        action="store_true",
        help="Renomme continents et animaux en anglais.",
    )
    return parser


def main() -> None:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    folders_only = args.folders_only
    download_images = args.download
    continent_slugs = set(args.continents) if args.continents else None
    animal_limit = args.animal_limit

    if args.translate_en:
        print(f"Traduction des dossiers en anglais dans {args.output_dir}\n")
        continents_renamed, animals_renamed = rename_folders_to_english(
            args.output_dir
        )
        fixed = fix_known_english_folder_names(args.output_dir)
        print(
            f"\nTerminé. Continents renommés: {continents_renamed}, "
            f"animaux renommés: {animals_renamed}, corrections: {fixed}"
        )
        return

    if args.rename_common:
        print(f"Renommage des dossiers dans {args.output_dir}\n")
        renamed = rename_folders_to_common_names(args.output_dir)
        print(f"\nTerminé. Dossiers renommés: {renamed}")
        return

    if args.fill_missing:
        print(f"Remplissage des dossiers vides dans {args.output_dir}\n")
        folders_filled, files_copied = fill_missing_copies(args.output_dir)
        print(
            f"\nTerminé. Dossiers remplis: {folders_filled}, "
            f"fichiers copiés: {files_copied}"
        )
        return

    if args.test:
        continent_slugs = {"antarctique"}
        animal_limit = 3
        download_images = True
        folders_only = False

    if not folders_only and not download_images:
        folders_only = True

    run(
        output_dir=args.output_dir,
        folders_only=folders_only,
        download_images=download_images,
        continent_slugs=continent_slugs,
        animal_limit=animal_limit,
    )


if __name__ == "__main__":
    main()
