# Changelog

## 2026-02-03 (image grid: load visible pixmaps only, debounced)
### ✅ Tasks:
- Load thumbnail pixmaps only for visible items with QTimer to avoid main-thread lag

- Scroll no longer triggers immediate visibility check: `_on_scroll` only starts a 120 ms debounce timer; when it fires, `_check_visible_thumbnails` runs and enqueues visible image IDs into `pending_load_queue` (capped at 60).
- A separate `load_ticker_timer` (80 ms) processes the queue: at most 2 loads per tick via `_process_pending_loads`, so pixmap loads and `set_image()` are spread over time and the main thread is not flooded.
- `clear()` now stops both timers and empties the pending queue.
 → Result: Scrolling large grids is much smoother; pixmaps load progressively for visible thumbnails only.
---

## 2026-01-30 (max width in import settings)
### ✅ Tasks:
- Add Maximum Width to image import settings

- Settings dialog: new "Maximum Width" spin box (360–4320 px, default 1920) in Image Import Compression section, alongside Maximum Height.
- Import resize logic: images are now fitted within both max_width and max_height (smaller of the two ratios is used so neither dimension is exceeded). Aspect ratio is preserved.
- Tests: `test_import_image_with_metadata` updated to assert dimensions within default limits and aspect ratio preserved (no longer uses removed MAX_WIDTH constant).
 → Result: Users can cap both width and height for imported images.
---

## 2026-01-30 (Camera-Angle as global AND constraint)
### ✅ Tasks:
- Camera-Angle and label categories constrain all category filters (AND)

- Label categories (e.g. "Camera-Angle:", "Miscellaneous:") are now applied as a **global AND** on top of the category filter. Example: Human + Wide-Angle shows only images that are both Human and Wide-Angle.
- Logic in `_filter_images_by_category`: first compute images matching any active regular category (with subtags); then keep only those that also have all selected label-category tags (constraining_tags). If no category is selected, only constraining tags are applied (e.g. Wide-Angle alone = all images with Wide-Angle).
 → Result: Selecting a category then a camera angle (or other label tag) correctly narrows results to that combination.
---

## 2026-01-30 (tag removal in background)
### ✅ Tasks:
- Tag removal on one or many images moved to background thread

- Remove-tag action (from tag chip × on selected images) now uses the same worker as tag assignment: `TagApplyWorker` with `operation="remove"` runs in the thread pool.
- `ImageGrid._remove_tag_from_selection` creates a `TagApplyWorker`, connects progress/finished/error, and starts it in `thread_pool`; handlers `_on_remove_tag_finished` and `_on_remove_tag_error` run on the main thread and refresh thumbnails or emit errors.
- New signals on `ImageGrid`: `tag_remove_progress`, `tag_remove_finished`, `tag_remove_error` so the main window can show status/progress (same UX as "Applying tag...").
- Main window connects to these signals and shows "Removing tag 'X'..." with progress bar, then cleans up on finished/error.
- Unit tests in `tests/test_tag_apply_worker.py` for remove operation, empty list, and error path.
 → Result: Removing a tag from many images no longer blocks the UI; same threading model as assigning a tag.
---

## 2026-01-30
### ✅ Tasks:
- Session countdown: second-by-second and red gradient toward 0

- Timer now ticks every second (interval 1s) instead of 100ms; countdown decreases second by second.
- Countdown overlay moved from top-right to top-left in the session window.
- Countdown label color interpolates toward red as remaining time approaches 0 (dark theme: white → red; light theme: black → red). Color is reset when changing image or starting session.
 → Result: Clearer, less distracting countdown in top-left; urgency feedback as time runs out.
---

## 2026-01-27
### ✅ Tasks:
- Drawing sessions (Course + Constant interval)
- Display tags on selected images in grid
- Settings dialog and menu improvements

- **Sessions**: Session Settings now starts a dedicated session window.
  - **Course** sessions: duration 10–60 min (step 10). Phases: WarmUp (30 s/image), Gesture (1 min/image), Anatomy (5 min/image), Shading (10 min/image). Presets defined in `gui/ressources/session_configs.json`.
  - **Constant interval**: fixed duration per image (30 s, 1/3/5/10/20 min).
  - Image list is built from currently filtered images (by tags), shuffled randomly.
  - Session window: fullscreen or “Window always on top” (from Session Settings).
  - Countdown per image in top-right; bottom bar: Play/Pause, Previous, Next; Space toggles controls, Escape closes and returns to main window.
  - Main window hides when session starts and re-shows when session window is closed.
- Session logic in `core/session_manager.py`: `load_course_config`, `build_course_run`, `SessionManager.start_session` (image_ids, type, course_duration_minutes / interval_seconds, window_mode), navigation (advance_image, previous_image, get_current_duration, get_session_progress).
- Unit tests in `tests/test_session_manager.py` for config loading, run building, and manager navigation.
 → Result: Users can run timed drawing sessions from filtered images with Course or constant timing; session runs in a separate fullscreen or always-on-top window with countdown and controls.
---
### ✅ Tasks (UI/tags):
- Display tags on selected images in grid
- Settings dialog and menu improvements

- Added tag display in ImageThumbnail when image is selected
- Tags are shown at the bottom of selected images with their icons
- Each tag chip has a remove button (×) to delete the tag from all selected images
- Tags are automatically refreshed when updated
- Added TagChip widget for displaying tags in thumbnails
- Added styles for tag chips in both dark and light themes
- Tags container uses a grid layout that wraps automatically
- Optimized tag chip layout: text elides (crops) when space is limited, preserving icon and remove button visibility
- Icon and remove button maintain minimum sizes while text adapts to available space
- Removed obsolete EditTagDialog - all tag editing now happens directly in the main UI
- Removed keyboard shortcuts text from File menu actions (cleaner UI)
- Added Settings dialog accessible from File menu
- Settings dialog includes theme selection (Light/Dark)
- Settings dialog includes image compression settings:
  - Maximum height for imported images (default: 1080p, range: 360p-4K)
  - JPEG compression quality slider (default: 75, range: 30-100) with quality descriptions
- Updated image import to use max_height instead of max_width for better control
- Compression quality default changed from 85 to 75 for better file size/quality balance
 → Result: Users can now see and manage tags directly on selected images in the grid, with improved layout on small thumbnails. Settings are now centralized in a dedicated dialog for easier configuration.
---

## 2026-01-23
### ✅ Tasks:
- Default tag dictionary update

- Replaced base tag categories and tag lists
- Included category names in search autocomplete
- Synced default tags with the tag tree
- Marked the "User Tags" category label as non-addable
- Enforced existing-tag validation with shake feedback on invalid input
- Supported nested tag dictionaries in default tags JSON
- Collapsed tag categories until their tag is selected
- Replaced tag tree with category/subtag button grid
- Made the tag grid scrollable and switched sub-tags to single-column layout
- Switched tag filtering to OR by category and AND within sub-tags
- Reorganized tag grid: categories in first column, sub-tags horizontally to the right
 → Result: Default tags and categories are now consistent and searchable from the start
---

## 2024-03-06
### ✅ Tasks:
- Project Setup and Basic Structure
    - Created project directory structure (core, gui, data, utils)
    - Set up Python virtual environment and dependencies
    - Implemented basic GUI window structure
    - Created initial module files and documentation
    → Result: Basic application structure is in place with a working GUI shell

### ✅ Tasks:
- GitHub Repository Setup
    - Initialized Git repository
    - Configured .gitignore for Python project
    - Set up documentation structure in docs/
    - Created main README.md for project visibility
    → Result: Project is now properly version controlled and documented on GitHub

### ✅ Tasks:
- UI Design Reference
    - Added reference UI image for image browser
    - Created detailed UI specifications document
    - Documented design system and components
    → Result: Clear UI guidelines established for development

### ✅ Tasks:
- Settings Management Implementation
    - Created settings.json template with default configuration
    - Implemented Settings class with validation and type checking
    - Added comprehensive unit tests for settings management
    - Set up data persistence with JSON storage
    → Result: Robust settings system ready for application configuration

### ✅ Tasks:
    - File System Utilities Implementation
        - Created file_utils.py with path handling and directory management
        - Implemented safe file operations and directory validation
        - Added comprehensive unit tests with pytest
        → Result: Robust file system utilities ready for use across the application

### ✅ Tasks:
    - GUI Window Implementation
        - Created main window with menu structure (File, View, Help)
        - Implemented theme switching (Dark/Light mode)
        - Added status bar and about dialog
        - Created comprehensive unit tests
        → Result: Basic GUI shell ready with theme support

## 2024-03-07
### ✅ Tasks:
    - Settings Manager Implementation
        - Created settings.json template with default configuration
        - Implemented settings manager in core/settings.py with full functionality
        - Added comprehensive unit tests in tests/test_settings.py
        → Result: Complete settings management system with JSON persistence, type validation, and test coverage

## 2024-03-26
### ✅ Tasks:
    - Image Import System
        - Implemented file dialog for image selection
        - Added drag & drop support for images
        - Created image processing utilities
        → Result: Users can now import images via file dialog or drag & drop, with automatic resizing and optimization
    
    - Image Database
        - Designed and implemented JSON-based metadata storage
        - Added support for image tags and notes
        - Created CRUD operations for metadata management
        → Result: Complete metadata management system for imported images

## 2024-03-19
### ✅ Image Grid Improvements

- Added column slider functionality
  - Implemented slider control (3-8 columns)
  - Added dynamic grid resizing
  - Optimized layout updates with debouncing

- Optimized image display
  - Implemented dynamic row heights based on image content
  - Fixed aspect ratio preservation
  - Improved image scaling quality
  - Added proper image centering

- UI Improvements
  - Implemented dark theme for grid and thumbnails
  - Removed image labels for cleaner interface
  - Added hover effects on thumbnails
  - Styled scrollbars to match dark theme

- Performance Optimizations
  - Improved image loading and caching
  - Optimized scroll performance
  - Fixed initial image loading
  - Reduced unnecessary layout updates

→ Result: A more polished and responsive image grid with better visual consistency and improved performance

## 2024-03-27
### ✅ Tasks:
    - Image Grid Optimization
        - Fixed column slider responsiveness
        - Improved image layout and aspect ratio handling
        - Removed complex locking mechanism causing UI freezes
        - Optimized layout update timing
        → Result: Smooth and responsive image grid with proper aspect ratios and no UI blocking

## 2024-12-19
### ✅ Tasks:
    - Selection System Improvements
        - Fixed drag selection rectangle visibility when starting drag on thumbnails
        - Centralized all mouse event handling in ImageGrid (removed from ImageThumbnail)
        - Improved rubber band positioning and styling for better visibility
        - Enhanced Ctrl+drag behavior: always removes thumbnails from selection
        - Fixed image centering in thumbnails for better visual alignment
        → Result: Intuitive and responsive selection system with proper visual feedback

--- 