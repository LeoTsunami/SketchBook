# SketchBook – Stratégie packaging, release et mise à jour

Document de référence pour le déploiement, la distribution et le développement local.

---

## 0. Packager one-command (recommandé)

Tout automatiser depuis la racine du repo :

```powershell
# Tooling once
.\.venv\Scripts\python.exe -m pip install -r requirements-packaging.txt
winget install JRSoftware.InnoSetup
gh auth login

# Bump patch + PyInstaller + Setup.exe + commit/tag/push + GitHub Release
.\scripts\package_release.ps1 --bump patch --notes "Beta for testers"

# Ou version explicite / wrapper .bat
.\scripts\package_release.ps1 0.2.0 --notes "First beta for testers"
scripts\package_release.bat --bump patch --notes "..."

# Build local only (pas de push / pas de Release)
.\scripts\package_release.ps1 --bump patch --notes "Local smoke" --no-push --skip-github
```

Équivalent Python : `.\.venv\Scripts\python.exe scripts\package_release.py --bump patch --notes "..."`

### Ce que la commande fait

1. Met à jour **`VERSION`** (SemVer `X.Y.Z` ; `core.version.get_version()` / About).
2. Écrit **`update_feed.json`** (`owner`/`repo` depuis `git remote origin`) pour le check update.
3. Préfixe **`docs/CHANGELOG.md`** et **`docs/CHANGELOG_FR.md`**.
4. Lance **PyInstaller** (`SketchBook.spec`, onedir).
5. Compile **Inno Setup** → `dist/SketchBook-Setup-vX.Y.Z.exe`.
6. Produit aussi **`dist/SketchBook-Windows-vX.Y.Z.zip`** (fallback portable).
7. Commit + tag `vX.Y.Z` + push (sauf `--no-push`).
8. Crée une **GitHub Release** avec Setup.exe + zip (si `gh` est installé).

Aucune bibliothèque d’images n’est embarquée.

### Options utiles

| Flag | Effet |
|------|--------|
| `--bump patch\|minor\|major` | Incrémente `VERSION` |
| `--notes "..."` | Obligatoire — notes changelog + Release |
| `--skip-build` | Réutilise `dist/SketchBook` déjà buildé |
| `--skip-installer` | Pas de Setup.exe (zip seulement) |
| `--skip-github` | Pas de `gh release create` |
| `--no-push` | Tag local seulement |
| `--dry-run` | Affiche le plan (aucune écriture) |
| `--skip-changelog` | Ne touche pas aux changelogs |

### Prérequis

- Windows + `.venv` runtime.
- `pip install -r requirements-packaging.txt` (PyInstaller).
- [Inno Setup 6](https://jrsoftware.org/isinfo.php) (`ISCC.exe`) : `winget install JRSoftware.InnoSetup`.
- Pour publier : `git` + [GitHub CLI `gh`](https://cli.github.com/) (`gh auth login`). GitHub Releases est **gratuit** sur un repo public.

---

## 1. Objectifs

| Besoin | Détail |
|--------|--------|
| **App autonome** | Pas de Python chez le testeur. PyInstaller onedir. |
| **Installateur wizard** | Inno Setup : dossier app + dossier library d’images. |
| **Distribution** | GitHub Release : `SketchBook-Setup-vX.Y.Z.exe` (+ zip). |
| **Mise à jour** | Au démarrage, `releases/latest` ; télécharge le Setup et le lance en silencieux. |
| **Library** | Hors install (`Documents\SketchBook` ou chemin choisi). Rien n’est bundlé. |

---

## 2. Build PyInstaller

- Spec : `SketchBook.spec` (entrée `bootstrap.py`).
- Sortie : `dist/SketchBook/SketchBook.exe`.
- `VERSION` et `update_feed.json` sont bundlés.

---

## 3. Installateur Windows (Inno Setup)

Script : [`installer/sketchbook.iss`](installer/sketchbook.iss).

- Dossier app : `{autopf}\SketchBook` (Program Files).
- Dossier library : page wizard, défaut `{userdocs}\SketchBook` ; écrit `%USERPROFILE%\.sketchbook_config.json` **seulement s’il n’existe pas**.
- Mise à jour in-app : `Setup.exe /VERYSILENT /NORESTART` — ne réécrit pas le chemin library.
- Désinstall : ne touche pas aux images / `library.db`.
- Pas de signature Authenticode pour l’instant : SmartScreen peut avertir les testeurs.

---

## 4. GitHub Releases

- Tag `vX.Y.Z`.
- Assets : Setup.exe (principal) + zip portable.
- L’API `releases/latest` est publique (pas de token dans l’app).

---

## 5. Mise à jour à l’ouverture

- `core/update_check.py` + `gui/update_coordinator.py`.
- Setting `updates.check_on_startup` (Settings) ; Help → Check for updates.
- Ignorer une version : `updates.skipped_version`.
- Échec réseau au boot : silencieux.

---

## 6. Raccourci dev

`.\.venv\Scripts\python.exe bootstrap.py` (ou `main.py`).

---

## 7. Synthèse des livrables

| Élément | Statut |
|--------|--------|
| `VERSION` + `core/semver.py` | Fait |
| `bootstrap.py` / `SketchBook.spec` | Fait |
| `scripts/package_release.py` (+ `.ps1` / `.bat`) | Fait |
| Installateur Inno Setup | Fait |
| GitHub Release Setup.exe + zip | Fait |
| Check update au démarrage | Fait |
