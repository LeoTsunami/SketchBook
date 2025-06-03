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