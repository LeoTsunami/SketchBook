# SketchBook – Stratégie packaging, release et mise à jour

Document de référence pour le déploiement, la distribution et le développement local.

---

## 1. Objectifs regroupés

| Besoin | Détail |
|--------|--------|
| **App autonome** | Fonctionne sur un PC sans Python installé. Toutes les dépendances dans le dossier de l’app. |
| **Installateur Windows** | Un .exe d’installation qui demande où installer et installe l’app (exe + libs). |
| **Distribution via GitHub** | Les utilisateurs téléchargent l’installateur depuis une Release GitHub (un clic sur “Download”). |
| **Mise à jour à l’ouverture** | Au lancement, l’app vérifie sur GitHub s’il existe une nouvelle release et propose (ou applique) la mise à jour. |
| **Raccourci dev** | Sur le PC de dev, un raccourci pour lancer l’app en mode “dev” sans ouvrir l’IDE (Cursor/VS). |

---

## 2. Build et packaging (pour distribution)

- **Outil** : PyInstaller en mode **onedir**.
- **Point d’entrée** : `bootstrap.py` (déjà en place) : en mode “frozen” il utilise le dossier du bundle ; en dev il utilise la racine du projet.
- **Résultat** : un dossier contenant :
  - `SketchBook.exe` (runtime Python + bootstrap),
  - les modules de l’app (core, gui, utils, main),
  - toutes les libs (PySide6, Pillow, etc.).
- **Données utilisateur** : inchangées. Toujours via `user_data` (Documents/SketchBook ou `SKETCHBOOK_DATA_DIR`), hors du dossier d’installation.

À faire côté projet (quand on implémente) :
- Fichier `.spec` PyInstaller pour onedir, avec les datas (core, gui, utils, main.py, ressources).
- Build sur une machine ou en CI (GitHub Actions) à chaque release.

---

## 3. Installateur Windows

- **Outil** : Inno Setup (ou NSIS / WiX).
- **Rôle** :
  - Copier le dossier produit par PyInstaller vers le chemin choisi (ex. `C:\Program Files\SketchBook` ou `%LocalAppData%\SketchBook`).
  - Créer raccourcis (Bureau, Menu Démarrer).
  - Proposer une option désinstallation.
- **Fichier produit** : `SketchBook-Setup-x.x.x.exe` (ou `.msi`), à publier en asset de la Release GitHub.

---

## 4. Distribution via GitHub Releases

- **Repo** : code source sur GitHub comme aujourd’hui.
- **Releases** : pour chaque version (tag, ex. `v1.0.0`) :
  - Créer une Release GitHub.
  - Attacher l’installateur (`SketchBook-Setup-x.x.x.exe`) en asset.
- **Utilisateur** : va sur la page Releases → clique sur “Download” pour le fichier d’installateur → lance l’exe → choisit le dossier d’installation → l’app est installée. Aucun Python à installer.

---

## 5. Mise à jour à l’ouverture (check GitHub)

- **Moment** : au démarrage de l’app (après affichage de la fenêtre ou en arrière-plan).
- **Mécanisme** :
  - Appeler l’API GitHub (ex. `GET https://api.github.com/repos/<owner>/<repo>/releases/latest`).
  - Comparer la version du release (tag ou `tag_name`) avec la version courante de l’app (stockée dans le code ou un fichier de version).
  - Si une version plus récente existe :
    - **Option simple** : afficher une boîte de dialogue (“Une mise à jour est disponible : v1.2.0. Télécharger ?”) avec un lien vers la page Release ou l’asset d’installateur.
    - **Option avancée** : télécharger le nouvel installateur en arrière-plan et proposer “Redémarrer pour installer” (plus complexe, à envisager plus tard).
- **Version courante** : à définir au même endroit (ex. `__version__` dans `main.py` ou fichier `version.txt` / `pyproject.toml`) et à incrémenter à chaque release.
- **Rate limiting** : l’API GitHub a des limites ; faire le check une fois par session ou avec un délai minimum entre deux checks pour éviter les abus.

À faire : ajouter un module ou une fonction “check for updates” appelée au démarrage, + stockage de la version dans le projet.

---

## 6. Raccourci dev (lancer l’app sans IDE)

- **But** : sur le PC de dev, un double-clic (ou raccourci) lance l’app en mode “code local”, sans ouvrir Cursor/Visual Studio.
- **Méthode** :
  - **Option A – Raccourci vers un script .bat / .ps1**  
    Le script :
    1. Active l’environnement virtuel du projet (ex. `venv\Scripts\activate` ou chemin complet vers `venv\Scripts\python.exe`).
    2. Lance `python bootstrap.py` (ou `python main.py`) depuis la racine du repo.
    - Le raccourci Windows pointe vers ce .bat/.ps1 (ou vers `python.exe` avec “Démarrer dans” = racine du projet et argument `bootstrap.py`).
  - **Option B – Raccourci vers l’exe du venv avec arguments**  
    Cible du raccourci :  
    `C:\...\SketchBook\venv\Scripts\pythonw.exe`  
    Argument : `bootstrap.py`  
    “Démarrer dans” : `C:\...\SketchBook`  
    (Utiliser `pythonw.exe` pour ne pas garder une console ouverte.)
- **Emplacement** : raccourci sur le Bureau ou dans le Menu Démarrer, nommé ex. “SketchBook (dev)”.

À faire : créer un fichier `run_dev.bat` (ou `run_dev.ps1`) à la racine du projet et documenter dans le README ou ce fichier comment créer le raccourci.

---

## 7. Synthèse des livrables à prévoir

| Élément | Statut / action |
|--------|------------------|
| Bootstrap (`bootstrap.py`) | Déjà en place. |
| PyInstaller spec (onedir) | À créer quand on implémente le build. |
| Script build (optionnel) | Script ou CI qui lance PyInstaller puis Inno Setup. |
| Installateur Inno Setup | À créer ; prend le dossier PyInstaller en entrée. |
| Version dans le projet | À ajouter (`__version__` ou fichier dédié). |
| Check update au démarrage | À implémenter (appel API GitHub + dialogue ou lien). |
| Raccourci dev | Fichier `run_dev.bat` (ou .ps1) + doc pour créer le raccourci. |

---

## 8. Ordre d’implémentation suggéré

1. **Version** : définir et lire la version (ex. `main.py` ou `version.txt`).
2. **Raccourci dev** : ajouter `run_dev.bat` (ou équivalent) et documenter.
3. **Check update** : module “check for updates” au démarrage (dialogue + lien GitHub).
4. **Build** : finaliser le .spec PyInstaller et produire un dossier onedir.
5. **Installateur** : script Inno Setup et génération de `SketchBook-Setup-x.x.x.exe`.
6. **CI (optionnel)** : GitHub Action sur tag/release qui build + génère l’installateur et l’attache à la Release.

Ce document peut être mis à jour au fur et à mesure (statut des tâches, choix d’outils, URLs du repo GitHub).
