# ✅ SKETCHBOOK – TASKS.md

**Purpose**: Track development progress, current tasks, backlog, and milestones.  
Update this file via prompt:  
→ `"Update task"`

---

## 📌 CURRENT TASKS (Sprint 4: Advanced Features)

- [x] Add hierarchy depth colors and expand/collapse arrows for categories and tags with children (2026-04-08)
- [x] Unify tag interactions: simple click for filter/expand-collapse and modifier+drag for tag-library multi-selection (2026-04-08)
- [x] Improve hierarchy readability: keep sub-category position stable and render children directly below parent with subtle child framing (2026-04-08)
- [x] Fix recursive tag hierarchy filtering so selecting a parent sub-category includes all nested child tags in the image grid (2026-04-08)
- [x] Update default tag dictionary and search autocomplete (2026-01-23)
- [x] Validate tag input with feedback animation (2026-01-23)
- [x] Collapse tag categories until selected (2026-01-23)
- [x] Replace tag tree with button grid (2026-01-23)
- [x] Make tag grid scrollable and single-column subtags (2026-01-23)
- [x] Switch to OR category and AND subtag filters (2026-01-23)
- [x] Reorganize tag grid layout: categories in first column (2026-01-23)
- [x] Display tags on selected images in grid with icons and remove buttons (2026-01-27)
- [x] Session countdown: second-by-second tick, top-left position, red gradient toward 0 (2026-01-30)
- [x] Slideshow fullscreen avec fitInView (scene.itemsBoundingRect, KeepAspectRatio) ; crossfade avec workaround (repaint + processEvents + délai 80 ms) pour éviter le resize pendant le fondu (2026-01-30)
- [x] Tag removal on selection moved to background thread (same TagApplyWorker as assign) (2026-01-30)
- [x] Camera-Angle (and label categories) as global AND constraint for all category filters (2026-01-30)
- [x] Tag library: edit user tags – rename (right-click), drag-drop onto category/tag, Add tag with icon (2026-02-03)
- [x] Tag library: "Parent to tag..." in right-click menu – multi-select (Ctrl+click), gray tags, select parent then OK/Cancel (2026-03-14)
- [x] Persist grid column count in user settings so same value on reopen (2026-02-05)
- [x] Code cleanup: remove unused code, factorize duplicates, improve maintainability (2026-02-06)
- [x] Add "Session Course Random" sort option to preview session order before starting (2026-02-06)
- [x] Image grid: right-click single image -> "Start session from this image" and ignore previous images in session order (2026-03-24)

### Phase 1: Basic Structure ✅ (Completed: 2024-03-06)
- [x] Set up base Python project with multi-file structure
  - [x] Create directories: `core/`, `gui/`, `data/`, `utils/`
  - [x] Set up Python virtual environment
  - [x] Create requirements.txt with initial dependencies:
    - PySide6/QtPy
    - Pillow
    - black (for formatting)
    - pytest (for testing)
- [x] Initialize Git and GitHub repository
  - [x] Configure .gitignore
  - [x] Set up documentation structure
  - [x] Create initial README.md

### Phase 2: Core Features Foundation ✅ (Completed: 2024-03-27)
- [x] Define internal settings format (JSON)
  - [x] Create settings.json template
  - [x] Implement settings manager in `core/settings.py`
- [x] Implement basic file system utilities in `utils/`
  - [x] File path handling
  - [x] Directory creation/validation
- [x] Create first GUI window
  - [x] Empty Qt window with basic menu structure
  - [x] Dark/Light mode support with persistence
  - [x] Theme system implementation

### Phase 3: Image Management Basics ✅ (Completed: 2024-03-27)
- [x] Implement image import system
  - [x] File dialog for selection
  - [x] Drag & drop support
  - [x] Comprehensive error handling
  - [x] Progress tracking and user feedback
- [x] Create image processing utilities
  - [x] Auto-resize/compress images (1920p max width)
  - [x] Format standardization
  - [x] Image optimization
- [x] Set up local image database structure
  - [x] Implement Pydantic models for metadata
  - [x] Create JSON-based storage system
  - [x] Implement CRUD operations
  - [x] Add tag-based search functionality

### Phase 4: Image Browser UI ✅ (Completed: 2024-12-19)
- [x] Implement image grid view
  - [x] Create scrollable grid layout
  - [x] Add image thumbnails with labels
  - [x] Implement dynamic loading for performance
  - [x] Add image selection functionality
    - [x] Individual selection
    - [x] Multiple selection with drag rectangle
    - [x] Shift/Ctrl modifiers support
    - [x] Visual selection feedback
    - [x] Context menu for selected images
      - [x] Add tags with autocomplete
      - [x] Delete from library with confirmation
      - [x] Use selection for drawing session
- [x] Create tag management UI
  - [x] Add tag search bar with autocompletion
  - [x] Show currently active tags
  - [x] Add/remove tag functionality
  - [x] Visual feedback for tag operations
- [x] Implement filtering system
  - [x] Filter images by selected tags
  - [x] Real-time update of displayed images
  - [x] Clear filters option

### Phase 5: Session Management ✅ (Completed: 2024-12-19)
- [x] Design session presets system
  - [x] Create session preset data model
  - [x] Implement preset storage (JSON)
  - [x] Add preset management UI
- [x] Implement slideshow player
  - [x] Create fullscreen slideshow window
  - [x] Add basic image navigation (next/previous)
  - [x] Implement image transition effects
  - [x] Add keyboard shortcuts for navigation
- [x] Add basic timer functionality
  - [x] Create timer widget with countdown
  - [x] Add timer controls (start, pause, reset)
  - [x] Implement timer presets (30s, 1min, 2min, 5min, etc.)
  - [x] Add timer completion notification
- [x] Create session configuration UI
  - [x] Design session setup dialog
  - [x] Add image selection for session
  - [x] Configure timer settings
  - [x] Add session start/stop controls

### Phase 6: Advanced Features (Current Sprint)
- [x] **Drawing sessions (Course + Constant)** (2026-01-27)
  - [x] JSON course config (10–60 min): WarmUp / Gesture / Anatomy / Shading (`gui/ressources/session_configs.json`)
  - [x] SessionManager: build run from tags filter + config, navigation API
  - [x] Session window: countdown top-right, play/pause/prev/next, fullscreen or always-on-top
  - [x] Main window: hide on session start, re-show on session close
- [ ] Implement auto-tagging using AI
  - [ ] Research AI tagging libraries (CLIP, etc.)
  - [ ] Create AI tagging service
  - [ ] Add auto-tagging to image import
  - [ ] Implement manual AI tagging trigger
- [ ] Add analytics tracking system
  - [ ] Design analytics data model
  - [ ] Track session completion rates
  - [ ] Track drawing time and progress
  - [ ] Create analytics dashboard
- [ ] Create export functionality
  - [ ] Export session data to CSV/JSON
  - [ ] Export image collections
  - [ ] Backup/restore functionality
- [ ] Polish UI/UX
  - [ ] Improve visual design
  - [ ] Add animations and transitions
  - [ ] Optimize performance
  - [ ] Add accessibility features

---

## 🧠 DISCOVERIES / QUESTIONS

- [x] Research best practices for Qt application architecture
- [x] Investigate efficient image processing methods with Pillow
- [x] Plan database schema for extensibility
- [ ] Document setup process for new developers
- [ ] Consider adding image format conversion options
- [ ] Consider implementing batch processing options for large imports
- [ ] Consider adding image preview functionality
- [x] Research Qt fullscreen and always-on-top window management
- [x] Plan session data persistence format
- [ ] Research AI image recognition libraries for auto-tagging
- [ ] Plan analytics data structure and storage

---

## 🧱 BACKLOG (Future Sprints)

### Sprint 5: Polish & Optimization
- [x] **Image grid: load pixmaps only for visible thumbnails with QTimer** (2026-02-03)
  - Debounce scroll (120 ms) before running visibility check; pending load queue + load ticker (80 ms, max 2 loads per tick) to avoid main-thread lag when scrolling.
- [ ] Performance optimization (other)
- [ ] Memory usage optimization
- [ ] Error handling improvements
- [ ] User experience refinements

### Future bugfix
- [ ] **Slideshow – correction du resize pendant le fondu** : améliorer ou rendre plus robuste le correctif actuel (repaint + processEvents + délai 80 ms avant démarrage du fondu) ; ou explorer une approche sans délai (ex. layout items uniquement sans fitInView pendant le crossfade) si le problème réapparaît sur certains environnements.

---

## 🎯 MILESTONES

### v0.1 – Foundation ✅ (Completed: 2024-12-19)
- [x] Basic project structure
- [x] Working GUI shell
- [x] Image import & storage
- [x] Initial documentation

### v0.2 – Core Features ✅ (Completed: 2024-12-19)
- [x] Manual image tagging
- [x] Basic slideshow functionality
- [x] Simple timing system

### v0.3 – Enhanced Features (Current Goal)
- [ ] Session templates
- [ ] Full slideshow controls
- [ ] Basic analytics

### v1.0 – Complete Artist Tool
- [ ] Auto-tagging
- [ ] Advanced analytics
- [ ] Export capabilities
- [ ] Polished UI/UX

---

## 📝 Development Guidelines

- Follow PEP 8 style guide
- Write unit tests for new features
- Document all functions with Google-style docstrings
- Keep files under 500 lines
- Update documentation with changes

---

## 🛠️ GLOBAL RULES (for Cursor)

# Tasks

## ✅ Completed
- Image Grid Improvements
  - Added column slider (3-8 columns)
  - Optimized image display with dynamic row heights
  - Fixed image scaling and aspect ratio preservation
  - Implemented dark theme for grid and thumbnails
  - Removed image labels for cleaner interface
  - Fixed initial image loading and scroll behavior
- Bug Fixes
  - Fixed NameError: name 'ImageThumbnail' is not defined in main_window.py
  - Added missing imports for ImageThumbnail and TagChip classes
- UI Improvements
  - Removed popup dialog when clicking on images (preparing for selection functionality)
  - Enhanced drag selection: rectangle now appears when starting drag from image thumbnails
  - Added visual styling to selection rectangle for better visibility
- Code Refactoring
  - Split image_grid.py (946 lines) into two files for better maintainability
  - Created gui/image_thumbnail.py (235 lines) for ImageThumbnail class
  - Reduced image_grid.py to 754 lines (under 800-line limit)
- Selection System Improvements (2024-12-19)
  - Fixed drag selection rectangle visibility when starting drag on thumbnails
  - Centralized all mouse event handling in ImageGrid (removed from ImageThumbnail)
  - Improved rubber band positioning and styling for better visibility
  - Enhanced Ctrl+drag behavior: always removes thumbnails from selection
  - Fixed image centering in thumbnails for better visual alignment
- Sprint 2: Image Management & Tagging ✅ (Completed: 2024-12-19)
  - [x] Implement basic manual tagging UI
  - [x] Create tag management system
  - [x] Build image browser interface
  - [x] Write helper function: `load_images_by_tags()` (implemented as `search_images()`)
- Sprint 3: Session Management ✅ (Completed: 2024-12-19)
  - [x] Design session presets system
    - [x] Create session preset data model (`SessionPreset`)
    - [x] Implement preset storage (JSON)
    - [x] Add preset management UI (`SessionDialog`)
  - [x] Implement slideshow player
    - [x] Create fullscreen slideshow window (`SlideshowWindow`)
    - [x] Add basic image navigation (next/previous)
    - [x] Implement image transition effects
    - [x] Add keyboard shortcuts for navigation (Space, Left/Right, S, P, Escape)
  - [x] Add basic timer functionality
    - [x] Create timer widget with countdown (`SessionTimer`)
    - [x] Add timer controls (start, pause, reset)
    - [x] Implement timer presets (30s, 1min, 2min, 5min, etc.)
    - [x] Add timer completion notification
  - [x] Create session configuration UI
    - [x] Design session setup dialog (`SessionDialog`)
    - [x] Add image selection for session
    - [x] Configure timer settings
    - [x] Add session start/stop controls
  - [x] Session Management System
    - [x] Create session manager (`SessionManager`)
    - [x] Implement session lifecycle (create, start, end)
    - [x] Add session history tracking
    - [x] Create comprehensive test suite

## 🔄 In Progress
- Sprint 4: Advanced Features
  - AI auto-tagging research
  - Analytics system design
  - Export functionality planning

## ✅ Completed (2026-02-10)
- Default random course order and improved grid image quality
  - Default grid sort set to "Session Course Random" on first launch (then persisted per user choice).
  - Persisted last chosen sort index in user settings (`ui.grid.sort_index`) so reopening the app restores the same behavior.
  - Increased thumbnail source resolution in `ImageLoaderWorker` (higher upscale factor, still using `Qt.SmoothTransformation`) for crisper images in the image grid.
  - Image viewer window: fit-in-view applied correctly on first open, added Previous/Next navigation following the grid order, rotate buttons (CW/CCW) that update the underlying file and metadata, and a crop tool with save to disk.
  - Image viewer crop UX (2026-02-11): click Crop → rule-of-thirds grid + 4 draggable corner points; Valider to apply, Annuler to cancel.

## 📋 Backlog

## 🔍 DISCOVERIES / QUESTIONS
