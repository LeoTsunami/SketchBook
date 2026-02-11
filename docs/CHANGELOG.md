# Changelog

## 2026-02-11 (Image viewer: crop with rule-of-thirds grid and 4 draggable points)
### ✅ Tasks:
- Replace right-drag crop with a dedicated crop mode: grid in thirds + Valider/Annuler

- **Crop flow**: Click **Crop** → a rule-of-thirds grid is shown over the image and the crop rectangle starts as the full image. Four draggable corner handles (white circles) let you resize the crop area. **Valider** applies the crop and saves to disk; **Annuler** cancels and exits crop mode.
- **Bug fix**: Removed use of `QRubberBand` in the viewer (it was used but not imported, causing a NameError on right-click). Crop is no longer based on rubber-band drag.
- **Internal**: `ZoomGraphicsView` no longer handles crop; crop mode state, overlay items (rect, grid lines, `CropHandleItem`), and Valider/Annuler are handled in `ImageViewerWindow`. Overlay items are removed from the scene when exiting crop mode to avoid stale references after `scene.clear()`.
 → Result: Cropping is clearer and uses a rule-of-thirds grid with explicit validate/cancel actions.
---

## 2026-02-09 (Session: keep screen and system awake during session)
### ✅ Tasks:
- Prevent display and system sleep while the session window is open

- **Windows**: Uses `SetThreadExecutionState` (ES_DISPLAY_REQUIRED | ES_SYSTEM_REQUIRED) via `utils/keep_awake.py` so the screen and PC stay awake during fullscreen or windowed session. Restored to normal when the session window is closed.
- **Other platforms**: No-op (no extra dependency); could be extended later (e.g. macOS/Linux).
- **Tests**: `tests/test_keep_awake.py` for prevent_sleep/allow_sleep idempotence.
 → Result: The computer no longer goes to sleep during a drawing session.
---

## 2026-02-10 (Grid: default Session Course Random + crisper thumbnails)
### ✅ Tasks:
- Make "Session Course Random" the default sort mode and improve thumbnail quality in the image grid

- **Default sort behavior**: On first launch, the image grid now defaults to the "Session Course Random" sort mode so the gallery immediately reflects the same pseudo-random order as course sessions. The last chosen sort index is persisted in user settings (`ui.grid.sort_index`) and restored on subsequent launches.
- **Shuffle UI consistency**: The Shuffle button visibility is now synchronized with the initial sort combo state so it is shown whenever "Session Course Random" is active, including at startup.
- **Higher-quality thumbnails**: The `ImageLoaderWorker` now generates higher-resolution pixmaps for thumbnails by using a larger upscale factor (minimum 2.0x on standard DPI) with `Qt.SmoothTransformation`. Thumbnails look noticeably sharper in the grid, especially after window resizes and on larger column configurations.
 → Result: Users see a course-style random order by default when opening the app, and thumbnails in the image grid are rendered with better visual quality.
---

## 2026-02-10 (Image viewer: fit, navigation, rotate, crop)
### ✅ Tasks:
- Improve the single-image viewer window with better initial sizing and navigation tools

- **Fit on first open**: The image viewer now defers `fitInView` with a short `QTimer.singleShot(0, ...)` so that the very first time you open it, the image uses the full available window size instead of appearing tiny and only fixing itself on re-open.
- **Previous/Next navigation**: The viewer automatically reads the current ordered list of images from the `ImageGrid` (`all_images`) and exposes **Previous** / **Next** buttons to move through the same sequence as in the grid, starting from the double-clicked image.
- **In-place rotation**: Two buttons, **Rotate ⟲** and **Rotate ⟳**, call `ImageManager.rotate_image()` to rotate the current image 90° counterclockwise or clockwise on disk and refresh the display, updating metadata width/height.
- **Interactive crop & save**: Right-drag in the viewer draws a crop rectangle; clicking **Crop** applies the crop to the underlying file via Pillow, updates metadata (width, height, file size), and reloads the result so you can non-destructively reframe references inside SketchBook.
 → Result: The image viewer opens at a useful zoom level on first use, supports quick browsing of neighbour images, and lets users rotate or crop references directly from within the app.
---

## 2026-02-09 (Session: Next/Previous treat Get ready and phase titles as steps)
### ✅ Tasks:
- Next and Previous (and Left/Right) treat Get ready, phase titles and images as equal steps

- **Unified step navigation**: Get ready, each phase title and each image are steps. Next goes: Get ready → first phase/image, phase title → image, image → next phase title or image. Previous goes back one step (e.g. back to phase title, or back to Get ready from the first phase/title).
- **Get ready is a step**: From the first phase or first image, Previous can return to the Get ready screen (with 3-2-1 countdown). From Get ready, Next continues to the first content.
 → Result: Same behavior for every step; you can pass or come back to any screen (Get ready, phase titles, images) with Next/Previous.
---

## 2026-02-09 (Course: add Short pose phase 2m30, rebalance warmup/gesture)
### ✅ Tasks:
- Add intermediate phase between 1 min and 5 min in Course presets

- **New phase "Short pose"**: Inserted at 2 min 30 (150 s) between Gesture (1 min) and Anatomy (5 min). Naming follows common life-drawing usage for short poses.
- **Preset rebalance**: All course presets (10–60 min) updated: more weight on Warm-up and Gesture where possible; 10 min preset now has 5 warm-up + 2 gesture + 1 short pose + 1 anatomy (~12 min total to include the new phase).
- **Phase subtitle**: Slideshow shows "2 min 30" for 150 s phases (non-integer minutes) in the phase title overlay.
- **Docs and tests**: DOC_USER, DOC_DEV, session_manager docstring updated; test_session_manager asserts updated for new 10 min slot count and duration 150.
 → Result: Course sessions now progress 30s → 1 min → 2m30 → 5 min → 10 min with clearer warmup/gesture emphasis.
---

## 2026-02-06 (add Session Course Random sort option)
### ✅ Tasks:
- Add "Session Course Random" sort option to preview session order

- **New sort option**: Added "Session Course Random" to the grid sort combo box. This option uses the same deterministic random algorithm as Course sessions, allowing users to preview the exact order of images that will be used in a session before starting it.
- **Deterministic shuffle**: Implemented `_shuffle_images_for_session()` in `core/image_db.py` and `_shuffle_image_ids_for_session()` in `core/session_manager.py` that use a deterministic seed based on sorted image IDs. This ensures the same set of images always produces the same random order, matching between grid preview and actual session.
- **Session consistency**: Updated `build_course_run()` and "Constant interval" session initialization to use the same deterministic shuffle, ensuring the grid preview order matches the session order exactly.
 → Result: Users can now preview the session order in the grid before starting a session, making it easier to prepare for drawing sessions.
---

## 2026-02-06 (code cleanup: remove unused code and factorize duplicates)
### ✅ Tasks:
- Code cleanup: remove unused code, factorize duplicates, improve maintainability

- **Removed obsolete code**: Deleted `gui/session_dialog.py` (replaced by `SessionSettingsDialog`). Removed unused `get_current_session()` method and `current_session` attribute from `SessionManager`. Removed duplicate `load_stylesheet()` function from `gui/image_grid.py`.
- **Factorized icon utilities**: Created `gui/icon_utils.py` with centralized `find_tag_icon()` and `invert_icon()` functions. Replaced 5 duplicate `_invert_icon()` implementations and 4 duplicate `_find_tag_icon()` implementations across the codebase. All icon handling now goes through a single, well-documented module.
- **Cleaned up SessionManager**: Removed unused `get_current_session()` method that created dynamic classes. Added TODO comments for future persistence implementation of presets and session history. Kept paths and data structures for future installer integration.
- **Migrated deprecated search**: Updated `ImageManager.search_images()` to internally use `search_images_advanced()` for consistency. Updated `gui/image_grid.py` to use `search_images_advanced()` directly.
- **Improved debug functions**: Enhanced documentation for `_dbg()` and `_dbg_space()` functions in `slideshow_window.py` with clear flag-based control.
- **Documented installer API**: Enhanced documentation for `set_user_data_directory()` and `get_user_data_directory()` in `core/user_data.py` as public API for installers to configure user data paths.
 → Result: Codebase is cleaner, more maintainable, with reduced duplication. All functionality preserved. Ready for installer deployment with configurable user data paths.
---

## 2026-02-05 (persist grid column count)
### ✅ Tasks:
- Persist grid column count in user settings

- When the user changes the column slider (3–10 columns), the value is now saved via `settings.save()` after `settings.set("ui.grid.columns", value)`. On reopen, the slider and grid use `settings.get("ui.grid.columns", 4)` (already in place).
 → Result: The chosen number of columns is restored at next launch.
---

## 2026-02-03 (tag library: edit user tags)
### ✅ Tasks:
- Tag library: modify user tags (default tags remain read-only)

- **Rename**: Right-click a user tag → "Rename...". Renames the tag on all images and in config (placements/icons). Default tags have no context menu.
- **Drag and drop**: Drag a user tag from the library and drop it onto a category or another tag. Dropping on a category places the tag under that category; dropping on a tag makes that tag the "parent" (sub-category) so the user tag appears under it in the grid. Placements are stored in `user_tags_config.json` (user data config dir).
- **Add tag**: "Add tag" button opens a dialog with a name field and an optional icon picker (icons from `gui/ressources/icones/tags`). New tags are registered and appear under Miscellaneous until moved by drag-drop. They can be applied to images like any user tag.
- **Persistence**: `core/user_tags_config.py` loads/saves placements, icons, and `registered_only` (tags added via UI not yet on any image). `ImageDatabase.rename_tag(old, new)` renames a tag on all images.
 → Result: Users can organize, rename, and add custom tags from the tag library; default tags are fixed but can receive new tags as children.
---

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