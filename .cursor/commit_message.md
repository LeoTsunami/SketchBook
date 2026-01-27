feat: display tags on selected images with grid layout and multi-selection removal

Description:
- Added tag display in ImageThumbnail when image is selected
- Tags are shown at the bottom of selected images with their icons in a grid layout (wraps automatically)
- Each tag chip has a remove button (×) that removes the tag from ALL selected images
- Tags are larger with white text for better visibility
- Tags are automatically refreshed when updated via EditTagDialog
- Fixed mouse event handling to allow tag chips to be clickable
- Added TagChip widget for displaying tags in thumbnails
- Added styles for tag chips in both dark and light themes

Affected files:
- gui/image_thumbnail.py
- gui/image_grid.py
- gui/styles/style_dark.qss
- gui/styles/style_light.qss
- docs/CHANGELOG.md
- docs/CHANGELOG_FR.md
- docs/DOC_USER.md
- .cursor/TASKS.md
