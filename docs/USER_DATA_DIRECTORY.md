# User Data Directory Management

## Vue d'ensemble

SketchBook stocke maintenant toutes les données utilisateur (images, paramètres, sessions) dans un dossier configurable par l'utilisateur, au lieu du dossier du projet.

## Dossier par défaut

Par défaut, SketchBook utilise :
- **Windows** : `C:\Users\<Username>\Documents\SketchBook`
- **Linux/Mac** : `~/Documents/SketchBook`

Si le dossier Documents n'existe pas, le dossier de base sera `~/SketchBook`.

## Structure du dossier utilisateur

```
SketchBook/
├── images/          # Images importées
├── sessions/        # Fichiers de sessions
└── config/          # Fichiers de configuration
    ├── settings.json
    ├── library.db           # Métadonnées images (SQLite)
    ├── images.json          # Legacy ; migré une fois puis archivé
    ├── session_presets.json
    ├── session_history.json
    └── user_tags_config.json
```

## Configuration du dossier

### Méthode 1 : Variable d'environnement (priorité la plus haute)

Définir la variable d'environnement `SKETCHBOOK_DATA_DIR` :

```bash
# Windows (PowerShell)
$env:SKETCHBOOK_DATA_DIR = "C:\MyData\SketchBook"

# Linux/Mac
export SKETCHBOOK_DATA_DIR="/home/user/MyData/SketchBook"
```

### Méthode 2 : Fichier de configuration

Un fichier de configuration est créé dans le dossier home de l'utilisateur :
- **Windows** : `C:\Users\<Username>\.sketchbook_config.json`
- **Linux/Mac** : `~/.sketchbook_config.json`

Contenu du fichier :
```json
{
    "data_dir": "C:\\Users\\Username\\Documents\\SketchBook"
}
```

### Méthode 3 : Via l'API Python (pour l'installer)

```python
from core.user_data import set_user_data_directory

# Définir le dossier utilisateur
success = set_user_data_directory("C:/MyData/SketchBook")
if success:
    print("Dossier configuré avec succès")
else:
    print("Erreur lors de la configuration")
```

## Utilisation dans l'installer Windows

Le wizard Inno Setup (`installer/sketchbook.iss`) demande **où installer l’application** (Program Files par défaut) et **où stocker la library d’images** (`Documents\SketchBook` par défaut).

À la première installation seulement, il écrit `%USERPROFILE%\.sketchbook_config.json` :

```json
{
  "data_dir": "C:\\Users\\Username\\Documents\\SketchBook"
}
```

Une mise à jour (Setup relancé, y compris depuis l’app) **ne réécrit pas** ce fichier s’il existe déjà. La désinstallation ne supprime pas le dossier library.

Le même chemin reste changeable plus tard dans Settings. API Python équivalente : `set_user_data_directory()` dans `core/user_data.py`.

## Migration des données existantes

Si vous avez des données dans l'ancien dossier `data/` du projet, vous devrez les migrer manuellement vers le nouveau dossier utilisateur.

## Notes techniques

- Le dossier est créé automatiquement s'il n'existe pas
- Tous les sous-dossiers nécessaires sont créés automatiquement
- Les chemins sont résolus de manière absolue pour éviter les problèmes de chemins relatifs
- La configuration est persistante entre les sessions
