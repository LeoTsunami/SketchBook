# SketchBook – Stratégie packaging, release et mise à jour

Document de référence pour le déploiement, la distribution et le développement local.

---

## 0. Packager one-command (recommandé)

Tout automatiser depuis la racine du repo :

```powershell
# Install tooling once
.\.venv\Scripts\python.exe -m pip install -r requirements-packaging.txt

# Bump patch + build zip + commit/tag/push + GitHub Release
.\scripts\package_release.ps1 --bump patch --notes "Library folder setting + packaging"

# Ou version explicite
.\scripts\package_release.ps1 0.2.0 --notes "First beta for testers"

# Build local only (pas de push / pas de Release)
.\scripts\package_release.ps1 --bump patch --notes "Local smoke" --no-push --skip-github
```

Équivalent Python :

```powershell
.\.venv\Scripts\python.exe scripts\package_release.py --bump patch --notes "..."
```

### Ce que la commande fait

1. Met à jour le fichier **`VERSION`** (source unique ; `core.version.get_version()` / About).
2. Préfixe **`docs/CHANGELOG.md`** et **`docs/CHANGELOG_FR.md`**.
3. Lance **PyInstaller** (`SketchBook.spec`, mode **onedir**).
4. Produit **`dist/SketchBook-Windows-vX.Y.Z.zip`**.
5. Commit + tag `vX.Y.Z` + push (sauf `--no-push`).
6. Crée une **GitHub Release** avec le zip (si `gh` est installé ; sinon message d’aide).

### Options utiles

| Flag | Effet |
|------|--------|
| `--bump patch\|minor\|major` | Incrémente `VERSION` |
| `--notes "..."` | Obligatoire — notes changelog + Release |
| `--skip-build` | Réutilise `dist/SketchBook` déjà buildé |
| `--skip-github` | Pas de `gh release create` |
| `--no-push` | Tag local seulement |
| `--dry-run` | Affiche les étapes git/gh (build réel sauf `--skip-build`) |
| `--skip-changelog` | Ne touche pas aux changelogs |

### Prérequis

- Windows + `.venv` avec deps runtime.
- `pip install -r requirements-packaging.txt` (PyInstaller).
- Pour publier : `git` + [GitHub CLI `gh`](https://cli.github.com/) authentifié (`gh auth login`).

---

## 1. Objectifs regroupés

| Besoin | Détail |
|--------|--------|
| **App autonome** | Fonctionne sur un PC sans Python installé. Toutes les dépendances dans le dossier de l’app. |
| **Installateur Windows** | Plus tard (Inno Setup). Pour la beta : **zip onedir** suffit. |
| **Distribution via GitHub** | Release GitHub + asset zip (puis setup.exe plus tard). |
| **Mise à jour à l’ouverture** | À brancher ensuite (API Releases + version app). |
| **Emplacement library** | Choix dans Settings (déjà en place) ; l’installer pourra préremplir le même `data_dir`. |

---

## 2. Build et packaging (pour distribution)

- **Outil** : PyInstaller en mode **onedir** (`SketchBook.spec`).
- **Point d’entrée** : `bootstrap.py` (frozen + dev) : fixe cwd / `sys.path` pour QSS et ressources.
- **Résultat** : `dist/SketchBook/` avec `SketchBook.exe` + `_internal` / libs.
- **Données utilisateur** : toujours hors install (`Documents/SketchBook` ou Settings / `SKETCHBOOK_DATA_DIR`).

---

## 3. Installateur Windows (prochaine étape)

- **Outil** : Inno Setup (ou NSIS / WiX).
- **Rôle** : copier le onedir, raccourcis, désinstall ; optionnellement demander le dossier **library** (`set_user_data_directory`).
- **Fichier produit** : `SketchBook-Setup-x.x.x.exe` à attacher à la Release (le packager pourra l’appeler ensuite).

---

## 4. Distribution via GitHub Releases

- Tag `vX.Y.Z` + asset `SketchBook-Windows-vX.Y.Z.zip`.
- L’utilisateur dézippe et lance `SketchBook.exe` (beta). Plus tard : setup.exe.

---

## 5. Mise à jour à l’ouverture (check GitHub)

À implémenter après les premières Releases : comparer `get_version()` à `releases/latest`.

---

## 6. Raccourci dev

Lancer en local : `.\.venv\Scripts\python.exe bootstrap.py` (ou `main.py`).

---

## 7. Synthèse des livrables

| Élément | Statut |
|--------|--------|
| `VERSION` + `core/version.py` | Fait |
| `bootstrap.py` | Fait |
| `SketchBook.spec` | Fait |
| `scripts/package_release.py` (+ `.ps1`) | Fait |
| Zip Windows en Release | Fait (via script + `gh`) |
| Installateur Inno Setup | À faire |
| Check update au démarrage | À faire |
