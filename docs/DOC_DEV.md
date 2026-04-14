# Documentation Développeur

## Structure du Projet

```
SketchBook/
├── core/           # Logique métier principale
├── data/           # Stockage des données
│   ├── images/     # Images importées
│   ├── sessions/   # Configurations des sessions
│   └── config/     # Fichiers de configuration
├── gui/            # Interface utilisateur
├── utils/          # Utilitaires
└── tests/          # Tests unitaires
```

## Configuration de l'Environnement

1. Prérequis :
   - Python 3.12+
   - pip (gestionnaire de paquets Python)

2. Installation :
   ```bash
   # Créer un environnement virtuel
   python -m venv venv
   
   # Activer l'environnement virtuel
   # Sur Windows :
   .\venv\Scripts\activate
   # Sur Unix :
   source venv/bin/activate
   
   # Dépendances runtime (application)
   pip install -r requirements.txt

   # Outils de dev et tests (optionnel)
   pip install -r requirements-dev.txt

   # Script optionnel utils/download_animal_photo_refs.py (scraping)
   pip install -r requirements-tools.txt
   ```

   Le dépôt utilise en pratique le dossier **`.venv`** (à la racine). Si vous voyez une erreur du type « No Python at …\OtherUser\…\Python312\python.exe » après un clone ou un changement de machine, le venv a été créé sur un autre PC : supprimez le dossier `.venv`, puis recréez-le avec `py -3.12 -m venv .venv` (Windows) et `pip install -r requirements.txt` (puis `-r requirements-dev.txt` si vous développez).

### Démarrage (performance)

- Les polices embarquées **Kalam** ne sont chargées que pour les thèmes dont le QSS les référence (`light`, `neon_night`, `sunset_glass`, `midnight_ocean`). Le thème **dark** utilise **Segoe UI** (système) sans TTF au lancement.
- Le **backfill** des dates d’import (`import_date`) pour les entrées anciennes est déclenché après le premier affichage via `QTimer`, pour ne pas bloquer l’ouverture sur une grosse base.
- Les modules lourds **SessionSettingsDialog**, **SlideshowWindow** et **ImageViewerWindow** sont importés à la demande depuis `main_window.py` pour réduire le coût d’import initial.

## Architecture

### GUI (gui/)
- `image_grid.py` : Au-delà de `VIRTUALIZATION_THRESHOLD` images, une grille virtualisée réutilise un **pool** de widgets `ImageThumbnail`. Le pool est **redimensionné** (agrandi si besoin) quand le nombre de colonnes ou la hauteur de ligne change. **Redimensionnement de la fenêtre** : un throttle ~16 ms (`_schedule_window_resize_relayout`) applique un relayout avec `_resize_interactive=True` (vignettes en `FastTransformation` via `_fast_resize_active` posé directement sur les widgets — pas de parcours parent), puis `resize_finalize_timer` (~140 ms) appelle `apply_full_quality_fit()`. En mode non virtualisé, `_do_relayout` met à jour les cellules **in place**. **Lazy load / scroll** : dict `_image_id_to_index` pour lookups O(1) au lieu de scans O(n). `ImageLoaderWorker` émet un pixmap rapide (`fast_ready`) affiché immédiatement, puis le pixmap HQ qui remplace (deux phases). Thread pool 8 workers, 16 loads/tick, file 300, scale 2.0x. Vue virtualisée : les vignettes déjà correctes ne sont pas réassignées ; les appels géométrie omis si dimensions inchangées. **Animation sidebar** : pendant l'animation de largeur du panneau gauche, `_sidebar_anim_active=True` sur chaque `ImageThumbnail` déclenche un resize ultra-léger dans `resizeEvent` : `resetTransform + scale + centerOn` (simple opération matricielle, pas de `fitInView`). Seules les vignettes visibles sont relayées par frame (`_do_relayout_visible_only`). En fin d'animation, flag désactivé, layout complet + `fitInView` qualité. **Scroll anchor** : `_get_scroll_anchor` / `_restore_scroll_anchor` utilisent `_last_layout_row_h` (hauteur de ligne du dernier layout) pour un ancrage déterministe sans dérive. **Nettoyage grille** : `_drain_thumbnail_grid_layout()` retire tous les widgets du `QGridLayout` (`takeAt` + `deleteLater`) ; appelée depuis `clear()` dans tous les cas et au début de `_update_virtualized_view()` pour éviter des cellules orphelines (mode non virtualisé) qui se superposent au pool en géométrie absolue après des changements de filtres / passage virtualisé ↔ non virtualisé.
- `image_thumbnail.py` : vignette en carte transparente (plus de fond gris), ombre portée légère (`QGraphicsDropShadowEffect` sur `image_container`), hover lumineux via `QGraphicsColorizeEffect` faible sur la vue, et bordure de sélection bleue gérée par propriété dynamique `selected` + QSS thème.
- `main_window.py` : **Layout 2 lignes** : ligne 1 (`TopChromeBar`, 38 px) — menus File/View/Tools/Help + boutons fenêtre ; ligne 2 (`TabBarRow`, 32 px) — onglets Life Drawing / WhiteBoard / Market (`QButtonGroup`) + contrôles grille dans `_life_drawing_controls` (masqué hors onglet 0). `QStackedWidget` (`_content_stack`) : page 0 = image browser, pages 1-2 = placeholders. `_on_tab_changed(index)` bascule page + visibilité contrôles. Drag/double-clic fonctionnent sur les deux barres. Fenêtre principale. Crée et cache la fenêtre au lancement d’une session ; réaffiche à la fermeture de la session. Bibliothèque de tags : sélection multi-tags (Ctrl+clic), menu « Parent to tag... » avec mode parent (barre OK/Cancel), `_on_parent_select_ok` applique placements (category/parent_tag). Session : `_on_session_settings_clicked(start_from_image_id=...)` permet de démarrer depuis une image de la grille, en réutilisant le même dialogue. Sidebar tags non flottante : rail compact intégré au panneau gauche (largeur bouton) par défaut, ouverture animée au survol (button -> bibliothèque complète), repli au `Leave` du panneau ; bouton rail masqué quand la bibliothèque est ouverte.
- `window_chrome.py` : Module UI partagé pour fenêtres secondaires : `WindowChromeBar` (barre custom draggable avec boutons min/max/close), `enable_frameless_window(window)` et `apply_glass_button_style(button, primary=...)`. Objectif : éviter la duplication de chrome natif/custom et harmoniser le style des actions entre fenêtres.
- `slideshow_window.py` : Fenêtre de session (plein écran ou toujours au premier plan). Décompte en haut à gauche, barre de contrôles (Play/Pause, Précédent, Suivant). Chargement d’image : `ImageLoaderWorker` ; le signal `finished` transporte **un seul** pixmap HQ (le slot `_on_image_loaded` ne doit pas attendre un tuple). Affichage : `QGraphicsView` sans barres de défilement, `fitInView` sur le rect des items ; fond de scène / vue transparents pour afficher le même fond `QMainWindow` que l’app (règle extraite du QSS du thème via `gui/theme_qss_utils.py`). En pause, **Éditer** ouvre `_SessionImageViewerWindow` (sous-classe de `ImageViewerWindow`), identique au double-clic sur la grille (crop, rotation, zoom dans la visionneuse).
- `session_settings_dialog.py` : Type de session (Course / Constant), durée course (10–60 min) ou intervalle, mode fenêtre.
- `image_viewer_window.py` : Fenêtre de visualisation d’une image (zoom molette, Précédent/Suivant, rotation, crop). La scène et la `QGraphicsView` sont configurées en **fond transparent** (style + `viewport().setAutoFillBackground(False)`) pour que le dégradé global `QMainWindow` remplace le gris par défaut autour de l’image en `fitInView`. Mode crop : clic sur Crop affiche une grille règle des tiers et 4 poignées (`CropHandleItem`) déplaçables ; Valider applique le crop (Pillow) et met à jour les métadonnées, Annuler quitte le mode. Overlay (rect, lignes, poignées) créés dans la scène et retirés à la sortie du mode pour éviter des références invalides après `scene.clear()`.

### Core (core/)
- Module principal contenant la logique métier
- `session_manager.py` : Gestion des sessions (Course et intervalle constant). `load_course_config`, `build_course_run`, `SessionManager.start_session` (image_ids, type, durée/intervalle, window_mode), navigation (advance_image, previous_image, get_current_duration, get_session_progress). Presets Course dans `gui/ressources/session_configs.json` (10–60 min, phases Warm-up / Gesture / Short pose 2m30 / Anatomy / Shading).
- `user_tags_config.py` : Config des tags utilisateur (placements, icônes, `registered_only`). Fichier `user_tags_config.json` dans le répertoire config des données utilisateur. `load_config()`, `save_config(placements, icons, registered_only)`, `get_placement()`, `get_icon_filename()`, `set_placement()`, `rename_in_config()`.
- `image_db.py` : `ImageDatabase.rename_tag(old_name, new_name)` renomme un tag sur toutes les images et retourne le nombre d’images mises à jour.
- Version actuelle : 0.1.0

### Utils (utils/)
- Utilitaires pour la manipulation de fichiers et le traitement d'images
- `keep_awake.py` : `prevent_sleep()` / `allow_sleep()` — sous Windows, utilise `SetThreadExecutionState` pour empêcher la veille écran/système pendant la session ; appelé par la fenêtre de session au démarrage et à la fermeture.
- En cours de développement

## Conventions de Code

1. Style :
   - Suivre PEP 8
   - Utiliser des docstrings au format Google
   - Limiter les fichiers à 500 lignes maximum

2. Tests :
   - Écrire des tests unitaires pour chaque nouvelle fonctionnalité
   - Utiliser pytest
   - Placer les tests dans le dossier `tests/` en miroir de la structure du projet

3. Documentation :
   - Documenter toutes les fonctions avec des docstrings
   - Ajouter des commentaires pour le code complexe
   - Mettre à jour ce document pour les changements d'architecture 

## Types de Commits

Format: `[type]: [module] Action description`

### Types principaux :
- `[feat]` : Nouvelle fonctionnalité
- `[fix]` : Correction de bug
- `[docs]` : Modification de la documentation
- `[style]` : Formatage, point-virgules manquants, etc. (pas de changement de code)
- `[refactor]` : Refactorisation du code
- `[test]` : Ajout ou modification de tests
- `[chore]` : Maintenance, mise à jour de dépendances, etc.
- `[perf]` : Amélioration des performances
- `[ci]` : Modification des fichiers de CI/CD
- `[build]` : Modification du système de build ou des dépendances externes
- `[revert]` : Annulation d'un commit précédent

### Exemples :
```
[feat]: [gui] Add dark mode support
[fix]: [core] Fix image loading crash
[docs]: [project] Update installation guide
[refactor]: [utils] Simplify file handling logic
```

### Structure du message :
```
[type]: [module] Action description

🎯 Description:
- [Détail des modifications en français]
- [Raisons ou bénéfices si pertinent]

🔍 Affected files:
- path/to/file1
- path/to/file2
```

## Settings Manager (`core/settings.py`)

The Settings Manager provides a centralized way to handle application configuration. It uses JSON for persistence and includes type validation.

### Usage

```python
from core.settings import settings

# Get a setting (with optional default)
theme = settings.get("ui.theme", default="dark")

# Set a setting
settings.set("ui.theme", "light")

# Save changes
settings.save()

# Reset to defaults
settings.reset()

# Get all settings
all_settings = settings.all
```

### Configuration Structure

The settings are organized in the following structure:
```json
{
    "version": "0.1.0",
    "ui": {
        "theme": "dark",
        "language": "fr",
        "window": {...},
        "grid": {...}
    },
    "images": {...},
    "session": {...},
    "database": {...}
}
```

### File Locations
- Default configuration: `Documents/SketchBook/config/settings.json` (or custom location via user_data)
- Unit tests: `tests/test_settings.py`

## File System Utilities (`utils/file_utils.py`)

The File System Utilities module provides safe and convenient functions for file and directory operations.

### Usage

```python
from utils.file_utils import ensure_dir, safe_path, list_files

# Create/ensure directory exists
from core.user_data import user_data
data_dir = user_data.get_images_dir()

# Safely join paths (prevents directory traversal)
safe_file_path = safe_path(data_dir, "user_uploads", "image.jpg")

# List files with pattern matching
image_files = list_files(data_dir, "*.jpg", recursive=True)
```

### Available Functions

- `ensure_dir(path)`: Create/ensure directory exists
- `validate_dir(path)`: Check if directory exists and is accessible
- `safe_path(base_path, *parts)`: Safely join paths (prevents directory traversal)
- `list_files(directory, pattern="*", recursive=False)`: List files matching pattern
- `safe_remove(path)`: Remove file or directory; returns `True` on success, `False` if the path does not exist or removal fails
- `get_file_size(path)`: Get file size in bytes

### File Locations
- Implementation: `utils/file_utils.py`
- Unit tests: `tests/test_file_utils.py`

## Main Window (`gui/main_window.py`)

The main window provides the application's primary interface and menu structure.

### Features

- File menu:
  - Import Images (Ctrl+I)
  - Exit (Alt+F4)
- View menu:
  - Theme switching (Light/Dark)
- Help menu:
  - About dialog

### Theme Support

The application supports light and dark themes, controlled via:
```python
from gui.main_window import MainWindow

window = MainWindow()
window._set_theme("dark")  # or "light"
```

Theme settings are persisted in the application settings.

### Default Tags and Autocomplete

Base tags are defined in `gui/ressources/default_tags.json`. Category names are treated as tags and nested dictionaries inside lists are supported (e.g., `{ "Vehicle": ["Car"] }`).
Category buttons are displayed in the first column of a grid inside a scroll area. Sub-tag buttons appear horizontally to the right of their category when active.
Filtering logic: categories act as a global OR, and sub-tags act as AND within their category.

### File Locations
- Implementation: `gui/main_window.py`
- Unit tests: `tests/test_main_window.py`

## Image Management System

### Image Import
The image import system is implemented in `core/image_manager.py` and provides the following features:

- Supported formats: JPG, JPEG, PNG
- Automatic image processing:
  - Resizing to fit within max width and max height (settings: `images.max_width`, `images.max_height`; aspect ratio preserved)
  - Conversion to RGB color space
  - JPEG compression with configurable quality
  - Unique filename generation to prevent conflicts

#### Usage Example
```python
from core.image_manager import ImageManager

# Initialize manager
manager = ImageManager()

# Import single image
result_path = manager.import_image(source_path)
if result_path:
    print(f"Image imported to: {result_path}")

# Import multiple images
successful, total = manager.import_images([path1, path2, path3])
print(f"Imported {successful} out of {total} images")

# Get list of imported images
images = manager.get_image_list()
```

### GUI Integration
The main window (`gui/main_window.py`) implements image import via:

1. File Dialog:
   - Accessible through File > Import Images... menu
   - Filters for supported image formats
   - Multiple file selection support

2. Drag & Drop:
   - Accepts files with supported extensions
   - Validates file types before accepting drop
   - Provides visual feedback during drag

### Configuration
Image processing settings can be customized via the settings system:

- `images.storage_path`: Directory for imported images (default: user data directory + "/images")
- `images.max_width`: Maximum width for imported images in pixels (default: 1920)
- `images.max_height`: Maximum height for imported images in pixels (default: 1080)
- `images.compression.quality`: JPEG compression quality (default: 75)

### Image Database
The image database system is implemented in `core/image_db.py` and provides a JSON-based storage solution for image metadata.

#### Data Model
```python
class ImageMetadata(BaseModel):
    id: str                  # Unique identifier (filename without extension)
    path: Path              # Path to image file relative to storage directory
    original_filename: str   # Original filename before import
    import_date: datetime   # Import timestamp
    width: int              # Image width in pixels
    height: int             # Image height in pixels
    file_size: int         # File size in bytes
    format: str            # Image format (e.g., 'JPEG', 'PNG')
    tags: List[str]        # User-defined tags
    notes: str             # User notes about the image
```

#### Database Operations
The `ImageDatabase` class provides the following operations:

1. **Add Image**
   ```python
   db.add_image(metadata: ImageMetadata) -> bool
   ```
   - Adds new image metadata to the database
   - Returns `False` if image ID already exists

2. **Get Image**
   ```python
   db.get_image(image_id: str) -> Optional[ImageMetadata]
   ```
   - Retrieves metadata for a specific image
   - Returns `None` if image not found

3. **Update Image**
   ```python
   db.update_image(image_id: str, **updates) -> bool
   ```
   - Updates metadata fields for an image
   - Returns `False` if image not found

4. **Delete Image**
   ```python
   db.delete_image(image_id: str) -> bool
   ```
   - Removes image metadata from database
   - Returns `False` if image not found

5. **List Images**
   ```python
   db.list_images() -> List[ImageMetadata]
   ```
   - Returns list of all image metadata

6. **Search Images**
   ```python
   db.search_images(tags: Optional[List[str]] = None) -> List[ImageMetadata]
   ```
   - Searches images by tags
   - Returns all images if no tags specified

#### Storage Format
The database is stored in JSON format with the following structure:
```json
{
  "image_id_1": {
    "id": "image_id_1",
    "path": "relative/path/to/image.jpg",
    "original_filename": "original.jpg",
    "import_date": "2024-03-26T12:34:56",
    "width": 1920,
    "height": 1080,
    "file_size": 1024000,
    "format": "JPEG",
    "tags": ["landscape", "nature"],
    "notes": "Mountain vista"
  },
  // ... more images ...
}
```

#### Configuration
Database settings can be customized via the settings system:
- `images.db_path`: Path to the JSON database file (default: user data directory + "/config/images.json")

## Image Grid Component

The `ImageGrid` class manages the display of image thumbnails in a responsive grid layout. Key features include:

### Layout Management
- Uses Qt's `QGridLayout` for efficient image arrangement
- Maintains consistent aspect ratio (1.2:1, height:width) for all thumbnails
- Minimum thumbnail height of 150px to ensure visibility
- Dynamic column adjustment via slider with smooth transitions
- **`relayout_after_sidebar_step()`**: Stops the debounced `layout_timer` and calls `_update_layout()` immediately while preserving scroll ratio. **No longer called per-frame** during sidebar animation — the animation defers all relayout to `set_sidebar_width_animation_active(False)`.
- **`set_sidebar_width_animation_active(bool)`**: While `True`, `resizeEvent` does **not** start the debounced `layout_timer` and **no grid relayout happens**. Qt handles viewport clip/expand natively via `setWidgetResizable(True)` + `setFixedSize` children at near-zero cost. When set to `False` (animation ends): captures viewport as crossfade overlay (`_start_crossfade_overlay`), then runs a single `_update_layout()` + `_apply_full_quality_fit_all_thumbnails()`, restores scroll via anchor-based `_get_scroll_anchor` / `_restore_scroll_anchor` (deterministic first-row + pixel-offset — no ratio drift), and fades out the overlay over 200ms (`QPropertyAnimation` on `QGraphicsOpacityEffect`).
- **`setFixedSize(w, h)`** is used instead of separate `setFixedWidth` + `setFixedHeight` calls in `_do_relayout`, `_update_virtualized_view`, `_load_next_batch`, and `prepend_image` — halves the number of `resizeEvent` firings per thumbnail during any relayout pass.

### Application startup sequence

- **`main.py`**: Builds `QApplication`, theme/QSS, then `MainWindow()` + `show()` + `exec()`. No longer schedules `run_import_date_backfill` here.
- **`MainWindow`**: `ImageManager()` still loads `images.json` synchronously in its constructor (unavoidable without a larger DB refactor). UI shell (menus, chrome, empty `ImageGrid`, overlays) builds in `__init__`. **Tag grid content** and **image list** are **not** loaded in `_setup_ui`; first **`showEvent`** sets `_startup_scheduled` and **`QTimer.singleShot(0, _deferred_startup_load)`**.
- **`_deferred_startup_load()`**: Status *Loading library…*, `_load_tags_into_grid()`, then either **`StartupSortRunnable`** on `QThreadPool.globalInstance()` (non-`course_random`) — snapshot via **`ImageDatabase.snapshot_metadata_values()`** + **`_sort_images`** off the GUI thread — or synchronous `_apply_category_filters()` for **`course_random`**. **`_finalize_startup_load()`** sets *Ready*, runs **`run_import_date_backfill`**, sets **`_startup_load_done`**. **`run_startup_load_for_tests()`** performs the same steps synchronously (pytest fixture).
- **`gui/startup_sort_worker.py`**: `StartupSortSignals` lives on the main thread; `StartupSortRunnable.run()` emits `finished` with a sorted `list` or an `Exception` (fallback to unsorted path).

### Main window layout (central widget)

- **`_setup_menu()`**: Builds `self._file_menu`, `_view_menu`, `_tools_menu`, `_help_menu` as `QMenu` instances (no `QMenuBar` — `menuBar().hide()`). Shortcuts on actions still work.
- **`_setup_floating_logo()`** / **`_position_floating_logo()`**: Logo `QLabel` is a child of the central widget (not in the top layout), mouse-transparent, raised above the chrome strip. **`resizeEvent`** re-anchors it.
- **`_setup_top_chrome_bar()`**: Thin row (`TopChromeBar`): reserved width for logo overlap, `QToolButton` menus, `addStretch()`, **Shuffle**, **Sort**, **Columns**.
- **Tag panel hover**: `eventFilter` on `tag_filters_floating_btn` — `Enter` / `MouseMove` call `_tag_panel_overlay.show_animated()` when the overlay is not yet `isVisible()`; `QTimer.singleShot(0, _position_floating_grid_overlays)` hides the trigger and re-stacks widgets. **`panel_did_hide`** (from `TagPanelOverlay`) runs `_position_floating_grid_overlays` so the trigger reappears after the slide-out animation.
- **`_setup_image_browser()`**: Full-width image grid (no splitter). **`TagPanelOverlay`** + **`tag_filters_floating_btn`** + **Start session** are children of `image_grid.viewport()`; `set_tag_popover_stack_under(session_settings_btn)` keeps `TagHoverPopover` below the session button in z-order.
- **`_position_floating_grid_overlays()`**: Uses `_grid_viewport_top_inset` (logo height + 24px) for the tag trigger height and Y position; hides the trigger while `_tag_panel_overlay.isVisible()`. Raises **Start session** last so it stays on top of the tag overlay and tag popover.

### Performance Optimizations
- Asynchronous image loading using `QThreadPool`
- Debounced layout updates using `QTimer`
- **Scroll debounce**: On scroll, only a debounce timer is started; when it fires, `_check_visible_thumbnails` runs and enqueues visible image IDs into `pending_load_queue` (capped for performance). A separate `load_ticker_timer` processes the queue with a limited number of pixmap loads per tick (`_process_pending_loads`), so the main thread is not flooded when scrolling quickly.
- Efficient thumbnail resizing with proper scaling
- Viewport-based loading for visible thumbnails only (queue + ticker instead of loading all visible at once)

### Thumbnail image quality and fitting (`gui/thumbnail_fitting.py`)

- **Single source of truth**: `gui/thumbnail_fitting.py` centralises all image→cell fitting logic.
  - `FitMode` enum: `FIT_ALL` (no crop), `FIT_HEIGHT` (fill height), `FIT_WIDTH` (fill width), `CROP_ALL` (fill cell, crop excess).
  - `fit_pixmap_in_view(view, scene, pixmap_item, mode)` — applies the chosen strategy via `fitInView` / transform.
  - `compute_fitted_size(image_w, image_h, cell_w, cell_h, mode)` — pure-geometry helper that returns the final (display_w, display_h) for a given image in a given cell.
- `ImageThumbnail.set_image()` and `resizeEvent()` both delegate to `fit_pixmap_in_view()`, so images are *always* re-fitted when the cell size changes (column slider, window resize, sidebar animation).
- `ImageThumbnail.set_fit_mode(mode)` updates the display mode and immediately re-fits the current image.
- `ImageGrid.set_fit_mode(mode)` propagates the mode to all existing thumbnails and the pool.
- The user selects the mode via a "Display:" combo box in the top chrome bar; the choice is persisted in `ui.grid.fit_mode`.
- `QGraphicsView` render hints `SmoothPixmapTransform` and `Antialiasing` are enabled for crisp downscaling.
- Thumbnails are loaded by `ImageLoaderWorker` with two passes:
  - A lightweight `fast_pixmap` (currently not displayed in the grid but kept for potential future uses such as placeholders).
  - A **high‑quality pixmap** that is upscaled using a factor of at least 3.0× on standard DPI screens (or the device pixel ratio on HiDPI screens), then downscaled by Qt in the view.
- The worker uses `Qt.SmoothTransformation` for the high‑quality pixmap, applies `setDevicePixelRatio()`, and uses `KeepAspectRatioByExpanding` for crop/fill-like modes so clipped areas still keep enough detail.
- The grid caches these high‑quality pixmaps per image ID in `pixmap_cache` and reuses them both for the main grid and for the scroll preview overlay (extract strip), balancing quality and performance.

### Tag operations (apply / remove)
- Applying a tag to many images (from main window) uses `TagApplyWorker` in the thread pool; progress and completion are handled on the main thread.
- Removing a tag from selected images (× on a tag chip in the grid) uses the same `TagApplyWorker` with `operation="remove"`; `ImageGrid._remove_tag_from_selection` starts the worker and connects `tag_remove_progress`, `tag_remove_finished`, `tag_remove_error` so the main window can show status/progress.

### Tag filtering (category vs label)
- **Regular categories** (Human, Animal, etc.): OR between categories; AND between sub-tags within a category. Example: Human + Portrait = images with Human and Portrait.
- **Label categories** ("Camera-Angle:", "Miscellaneous:"): their sub-tags are applied as a **global AND** on top of the category result. Example: Human + Wide-Angle = images that are Human *and* Wide-Angle. Logic in `MainWindow._filter_images_by_category`: first filter by regular categories, then keep only images that also have all selected label-category tags.
- **Recursive hierarchy support**: selected sub-tags are expanded with all recursive descendants (`parent_tag` chain) before filtering. This enables unlimited nested sub-categories (e.g. selecting `Felin` also matches `Chat`/`Tiger`/`Lion`).
- **Hierarchy UI rendering**: tag/category buttons now include expand/collapse indicators for entries with children (`▶` / `▼`). A depth-based color style is applied from computed hierarchy depth (`_get_tag_depth_in_category`) to improve visual parsing of nested structures.
- **Selection interaction model**: tag-library selection mode is now entered only with modifier+drag (`Ctrl` or `Shift` + drag). Simple click is not intercepted by the library selection event filter anymore and falls through to normal tag click behavior (filter + expand/collapse).
- **Stable hierarchy layout**: `_sync_tag_grid_state` now preserves tag order and renders children directly on a new row under each selected parent, instead of moving the selected parent block to the top. Child rows receive a subtle framed style through `is_child=True` in `_set_hierarchy_button_style`.

### Key Methods
```python
def set_columns(self, columns: int):
    """Updates the grid layout with the specified number of columns.
    Triggers layout recalculation and image reloading as needed."""

def _calculate_optimal_dimensions(self):
    """Calculates optimal thumbnail dimensions based on viewport size,
    column count, and desired aspect ratio (1.2:1)."""

def _do_relayout(self):
    """Performs the actual grid layout update, maintaining proper
    thumbnail sizes and aspect ratios."""
```

### Session start from grid context menu
- `ImageGrid` exposes a context menu action **"Start session from this image"** only when exactly one image is selected.
- The grid emits `start_session_from_image_requested(image_id)`.
- `MainWindow` listens to this signal and calls `_on_session_settings_clicked(start_from_image_id=image_id)`.
- Image slicing is centralized in `_slice_images_from_start(images, start_image_id)` so session order is preserved while removing preceding images.

--- 