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

## Utilisation dans l'installer

L'installer peut utiliser la fonction `set_user_data_directory()` pour configurer le dossier lors de l'installation :

```python
from core.user_data import set_user_data_directory, get_user_data_directory

# Obtenir le dossier par défaut
default_dir = get_user_data_directory()
print(f"Dossier par défaut: {default_dir}")

# Demander à l'utilisateur de choisir un dossier
user_choice = input(f"Choisir un dossier (défaut: {default_dir}): ").strip()
if user_choice:
    if set_user_data_directory(user_choice):
        print(f"Dossier configuré: {user_choice}")
    else:
        print("Erreur: impossible de configurer le dossier")
```

## Migration des données existantes

Si vous avez des données dans l'ancien dossier `data/` du projet, vous devrez les migrer manuellement vers le nouveau dossier utilisateur.

## Notes techniques

- Le dossier est créé automatiquement s'il n'existe pas
- Tous les sous-dossiers nécessaires sont créés automatiquement
- Les chemins sont résolus de manière absolue pour éviter les problèmes de chemins relatifs
- La configuration est persistante entre les sessions
