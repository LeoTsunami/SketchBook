feat: add settings dialog and improve menu UI

Description:
- Removed keyboard shortcut text from File menu actions (cleaner UI)
- Added Settings action in File menu
- Created SettingsDialog with theme selection and image compression settings
- Settings dialog includes:
  - Theme selector (Light/Dark)
  - Maximum height for imported images (default: 1080p, range: 360p-4K)
  - JPEG compression quality slider (default: 75, range: 30-100) with quality descriptions
- Updated image import to use max_height instead of max_width for better control
- Changed default compression quality from 85 to 75 for better file size/quality balance
- Updated settings.py to include max_height parameter
- Updated image_manager.py to use settings for compression and resizing

Affected files:
- gui/main_window.py
- gui/settings_dialog.py (new)
- core/settings.py
- core/image_manager.py
- docs/CHANGELOG.md
- docs/CHANGELOG_FR.md
