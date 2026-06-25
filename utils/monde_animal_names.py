"""
English folder names for monde-animal.fr downloads (continents and animals).
"""
from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path

try:
    from deep_translator import GoogleTranslator
except ImportError as e:
    GoogleTranslator = None  # type: ignore[misc, assignment]
    _IMPORT_ERROR = e
else:
    _IMPORT_ERROR = None

INVALID_WIN_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
CACHE_PATH = Path(__file__).resolve().parent / "data" / "monde_animal_en_names.json"

CONTINENT_FR_TO_EN: dict[str, str] = {
    "Afrique": "Africa",
    "Amérique centrale": "Central America",
    "Amérique du Nord": "North America",
    "Amérique du Sud": "South America",
    "Antarctique": "Antarctica",
    "Asie": "Asia",
    "Europe": "Europe",
    "Océanie": "Oceania",
}
CONTINENT_EN_NAMES = frozenset(CONTINENT_FR_TO_EN.values())

# Manual fixes for ambiguous or poor automatic translations.
MANUAL_ANIMAL_EN_OVERRIDES: dict[str, str] = {
    "Hypolaïs polyglotte": "Icterine warbler",
    "Rémiz penduline": "Eurasian penduline tit",
    "Salamandre tachetée": "Fire salamander",
    "Salamandre maculée": "Spotted salamander",
    "Zèbre de Grévy": "Grevy's zebra",
}


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
        cleaned = "unnamed"
    return cleaned[:max_len]


def load_animal_name_cache() -> dict[str, str]:
    """
    Load the French-to-English animal name cache from disk.

    Returns:
        Mapping of French common names to English folder names.
    """
    if not CACHE_PATH.exists():
        return {}
    return json.loads(CACHE_PATH.read_text(encoding="utf-8"))


def save_animal_name_cache(cache: dict[str, str]) -> None:
    """
    Persist the animal name translation cache.

    Args:
        cache: French-to-English mapping.
    """
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def english_animal_folder_names(cache: dict[str, str]) -> set[str]:
    """
    Return sanitized English folder names from the cache.

    Args:
        cache: French-to-English mapping.

    Returns:
        Set of English folder names.
    """
    return {sanitize_folder_name(english) for english in cache.values()}


def continent_name_en(continent_name: str) -> str:
    """
    Translate a continent folder name to English.

    Args:
        continent_name: French or English continent label.

    Returns:
        English continent folder name.
    """
    if continent_name in CONTINENT_EN_NAMES:
        return sanitize_folder_name(continent_name)
    english = CONTINENT_FR_TO_EN.get(continent_name)
    if not english:
        raise KeyError(f"Continent non mappé: {continent_name!r}")
    return sanitize_folder_name(english)


def animal_name_en(french_name: str, cache: dict[str, str] | None = None) -> str:
    """
    Translate a French animal common name to English for folder use.

    Args:
        french_name: French common name from the site.
        cache: Optional translation cache.

    Returns:
        English folder name.
    """
    mapping = cache if cache is not None else load_animal_name_cache()
    english = MANUAL_ANIMAL_EN_OVERRIDES.get(french_name) or mapping.get(french_name)
    if not english:
        raise KeyError(f"Animal non mappé: {french_name!r}")
    return sanitize_folder_name(english)


def fetch_site_french_animal_names() -> list[str]:
    """
    Fetch unique French animal names from monde-animal.fr continent pages.

    Returns:
        Sorted unique French common names.
    """
    from bs4 import BeautifulSoup

    from utils.download_monde_animal_refs import (
        CONTINENTS_URL,
        fetch_html,
        parse_animals,
        parse_continents,
    )

    html = fetch_html(CONTINENTS_URL)
    if not html:
        raise RuntimeError("Impossible de charger la page des continents.")

    names: set[str] = set()
    for continent in parse_continents(BeautifulSoup(html, "html.parser")):
        continent_html = fetch_html(continent.url)
        if not continent_html:
            continue
        for animal in parse_animals(BeautifulSoup(continent_html, "html.parser")):
            names.add(animal.name)
        time.sleep(0.5)

    return sorted(names)


def build_animal_name_cache(
    french_names: list[str],
    batch_size: int = 40,
    *,
    replace: bool = False,
) -> dict[str, str]:
    """
    Translate French animal names via Google Translate and return a cache.

    Args:
        french_names: Unique French common names.
        batch_size: Batch size for the translation API.
        replace: If True, rebuild the cache from scratch.

    Returns:
        French-to-English mapping.
    """
    if GoogleTranslator is None:
        raise ImportError(
            "deep-translator est requis. Installez-le avec: pip install deep-translator"
        ) from _IMPORT_ERROR

    translator = GoogleTranslator(source="fr", target="en")
    cache: dict[str, str] = {} if replace else load_animal_name_cache()
    pending = sorted(name for name in french_names if name not in cache)

    for index in range(0, len(pending), batch_size):
        batch = pending[index : index + batch_size]
        translated = translator.translate_batch(batch)
        for french, english in zip(batch, translated):
            cache[french] = english
        time.sleep(1)

    save_animal_name_cache(cache)
    cache.update(MANUAL_ANIMAL_EN_OVERRIDES)
    save_animal_name_cache(cache)
    return cache


def ensure_animal_name_cache() -> dict[str, str]:
    """
    Ensure French animal names from the site are translated in the cache.

    Returns:
        Complete French-to-English cache.
    """
    french_names = fetch_site_french_animal_names()
    cache = load_animal_name_cache()
    missing = [name for name in french_names if name not in cache]
    if missing:
        print(f"Traduction de {len(missing)} nom(s) d'animaux depuis le site...")
        cache = build_animal_name_cache(french_names)
    cache.update(MANUAL_ANIMAL_EN_OVERRIDES)
    save_animal_name_cache(cache)
    return cache


def merge_animal_folders(source: Path, target: Path) -> int:
    """
    Merge images from one animal folder into another, then remove the source.

    Args:
        source: Folder to merge from.
        target: Destination folder.

    Returns:
        Number of files copied.
    """
    copied = 0
    for image_path in source.iterdir():
        if not image_path.is_file():
            continue
        destination = target / image_path.name
        if destination.exists():
            continue
        shutil.copy2(image_path, destination)
        copied += 1
    if not any(source.iterdir()):
        source.rmdir()
    return copied


def rename_folders_to_english(output_dir: Path) -> tuple[int, int]:
    """
    Rename continent and animal folders to English.

    Args:
        output_dir: Root download directory.

    Returns:
        Tuple of (continents renamed, animals renamed).
    """
    cache = ensure_animal_name_cache()
    french_keys = set(cache.keys())
    continents_renamed = 0
    animals_renamed = 0

    for continent_dir in list(output_dir.iterdir()):
        if not continent_dir.is_dir():
            continue
        english_continent = continent_name_en(continent_dir.name)
        if english_continent != continent_dir.name:
            target = output_dir / english_continent
            if target.exists() and target != continent_dir:
                raise RuntimeError(
                    f"Collision continent: {continent_dir.name} -> {target}"
                )
            old_continent_name = continent_dir.name
            continent_dir.rename(target)
            continent_dir = target
            continents_renamed += 1
            print(f"  {old_continent_name} -> {english_continent}")

        for animal_dir in list(continent_dir.iterdir()):
            if not animal_dir.is_dir():
                continue
            if animal_dir.name not in french_keys:
                continue
            english_animal = animal_name_en(animal_dir.name, cache)
            if english_animal == animal_dir.name:
                continue
            target = continent_dir / english_animal
            if target.exists() and target != animal_dir:
                old_name = animal_dir.name
                copied = merge_animal_folders(animal_dir, target)
                animals_renamed += 1
                print(f"    {old_name} -> fusionné dans {english_animal} ({copied} fichier(s))")
                continue
            old_name = animal_dir.name
            animal_dir.rename(target)
            animals_renamed += 1
            print(f"    {old_name} -> {english_animal}")

    return continents_renamed, animals_renamed


def fix_known_english_folder_names(output_dir: Path) -> int:
    """
    Rename folders that already use English but have poor automatic translations.

    Args:
        output_dir: Root download directory.

    Returns:
        Number of folders renamed.
    """
    cache = load_animal_name_cache()
    cache.update(MANUAL_ANIMAL_EN_OVERRIDES)
    bad_to_good: dict[str, str] = {}
    for french_name in cache:
        desired = animal_name_en(french_name, cache)
        auto = sanitize_folder_name(cache.get(french_name, ""))
        if auto and auto != desired:
            bad_to_good[auto] = desired

    renamed = 0
    for continent_dir in output_dir.iterdir():
        if not continent_dir.is_dir():
            continue
        for animal_dir in list(continent_dir.iterdir()):
            if not animal_dir.is_dir():
                continue
            target_name = bad_to_good.get(animal_dir.name)
            if not target_name or target_name == animal_dir.name:
                continue
            old_name = animal_dir.name
            target = continent_dir / target_name
            if target.exists() and target != animal_dir:
                merge_animal_folders(animal_dir, target)
            else:
                animal_dir.rename(target)
            renamed += 1
            print(f"    {old_name} -> {target_name}")
    return renamed
