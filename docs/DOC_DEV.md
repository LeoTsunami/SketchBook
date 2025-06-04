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

--- 