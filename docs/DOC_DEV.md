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
   
   # Installer les dépendances
   pip install -r requirements.txt
   ```

## Architecture

### GUI (gui/)
- `main_window.py` : Fenêtre principale de l'application
  - Classe `MainWindow` : Gère la fenêtre principale et ses composants

### Core (core/)
- Module principal contenant la logique métier
- Version actuelle : 0.1.0

### Utils (utils/)
- Utilitaires pour la manipulation de fichiers et le traitement d'images
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
- Default configuration: `data/config/settings.json`
- Unit tests: `tests/test_settings.py`

## File System Utilities (`utils/file_utils.py`)

The File System Utilities module provides safe and convenient functions for file and directory operations.

### Usage

```python
from utils.file_utils import ensure_dir, safe_path, list_files

# Create/ensure directory exists
data_dir = ensure_dir("data/images")

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
- `safe_remove(path)`: Safely remove file or directory
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

### File Locations
- Implementation: `gui/main_window.py`
- Unit tests: `tests/test_main_window.py`

## Image Management System

### Image Import
The image import system is implemented in `core/image_manager.py` and provides the following features:

- Supported formats: JPG, JPEG, PNG
- Automatic image processing:
  - Resizing to max width of 1920px (preserving aspect ratio)
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

- `images.storage_path`: Directory for imported images (default: "data/images")
- `images.compression.quality`: JPEG compression quality (default: 85)

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
- `images.db_path`: Path to the JSON database file (default: "data/config/images.json")

--- 