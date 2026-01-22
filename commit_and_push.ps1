# Script pour commit et push vers GitHub
# À exécuter depuis PowerShell dans le dossier du projet

# Vérifier si git est disponible
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "Git n'est pas trouvé dans le PATH. Veuillez installer Git ou l'ajouter au PATH." -ForegroundColor Red
    exit 1
}

# Initialiser le dépôt si nécessaire
if (-not (Test-Path .git)) {
    Write-Host "Initialisation du dépôt Git..." -ForegroundColor Yellow
    git init
}

# Vérifier si le remote existe
$remoteExists = git remote get-url origin 2>$null
if (-not $remoteExists) {
    Write-Host "Configuration du remote GitHub..." -ForegroundColor Yellow
    git remote add origin https://github.com/LeoTsunami/SketchBook.git
} else {
    Write-Host "Remote déjà configuré: $remoteExists" -ForegroundColor Green
}

# Ajouter tous les fichiers
Write-Host "Ajout des fichiers..." -ForegroundColor Yellow
git add .

# Créer le commit
Write-Host "Création du commit..." -ForegroundColor Yellow
$commitMessage = @"
refactor: main window with tabs and cleanup

Description:
 - Added tabbed interface with Image Browser and Drawing Session tabs
 - Centered tab buttons in the tab bar
 - Window now opens maximized by default
 - Cleaned up unused code (removed pydantic import, unused functions)
 - Reorganized scripts into utils/ folder
 - Removed references/ folder and test_tags.py

Affected files:
 - gui/main_window.py
 - gui/styles/style_dark.qss
 - gui/styles/style_light.qss
 - core/image_db.py
 - core/image_manager.py
 - gui/session_dialog.py
 - utils/fix_image_paths.py
 - utils/import_existing_images.py
 - docs/CLEANUP_REPORT.md
"@

git commit -m $commitMessage

# Push vers GitHub
Write-Host "Push vers GitHub..." -ForegroundColor Yellow
git branch -M main
git push -u origin main

Write-Host "Terminé!" -ForegroundColor Green
