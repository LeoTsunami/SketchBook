# Changelog

## 2026-07-31 (v0.1.1)
### ✅ Tasks:
- First Windows package: automated packager (PyInstaller zip), version from VERSION file, About dialog reads app version.
→ Result: Windows build packaged for distribution.
---

## 2026-04-19 (Session view: cross dissolve, urgency tint, countdown ticks)
### ✅ Tasks:
- **Cross dissolve**: each slide is scaled/centered in a fixed viewport-sized scene rect so both images keep correct size during the fade (no post-dissolve recrop when aspect ratios differ).
- **Urgency background**: letterbox background shifts toward red as the per-image timer runs out.
- **Countdown sound**: soft tick on the last 10 seconds of each image timer (silent when paused).

  - Added: `gui/slideshow_image_layout.py`, `gui/session_countdown_sound.py`.
  - Updated: `gui/slideshow_window.py`.
  - Added tests: `tests/test_slideshow_session_polish.py`.
→ Result: smoother transitions and clearer end-of-pose feedback (visual + audio).
---

## 2026-04-13
### ✅ Tasks:
- Make workspace Python run configuration machine-agnostic

  - Updated `.vscode/settings.json` to stop pinning a hard `.venv` interpreter path.
  - Switched `python.defaultInterpreterPath` to `python` and enabled terminal environment activation.
  - Avoids Play/Run failures on PCs where `.venv` is absent or recreated with different local Python installs.
→ Result: Running from Cursor Play now uses an available local interpreter instead of a machine-specific venv path.
---

## 2026-04-13 (UI polish: grid spacing, tags rail, fade, session CTA)
### ✅ Tasks:
- Apply requested UI tuning on the Life Drawing viewport overlays

  - Image grid: increased left content margin by +15 px (`35 -> 50`) to add visual breathing room from the left edge/rail.
  - Tags filters trigger: increased width by +10 px (`36 -> 46`) and effective height by +25 px; restyled to a lighter blue while preserving the current high-opacity look.
  - Tag library overlay: increased panel width by +10 px (`360 -> 370`) and height budget by +25 px for a roomier open panel.
  - Bottom grid fade: switched to viewport palette-derived color when available (fallback to theme map) and reduced darkness with a softer gradient stop profile.
  - Start session CTA: replaced green style with a blue glass-like button, stronger blue drop shadow, and looping animated border glow to attract attention.
→ Result: The viewport UI now matches the requested spacing and visual direction, with a lighter tags rail, less muddy bottom fade, and a more prominent Start session call-to-action.
---

## 2026-04-13 (Tab system layout)
### ✅ Tasks:
- Introduce a two-line header with tab navigation

  - Line 1 (top chrome): logo reserve, File/View/Tools/Help menus, window buttons (unchanged)
  - Line 2 (tab bar): tab buttons (Life Drawing / WhiteBoard / Market) on the left, grid controls (Shuffle, Sort, Columns, Display) on the right -- controls hidden when not on the Life Drawing tab
  - Content: QStackedWidget with 3 pages; page 0 = existing image browser (grid + tag panel + session button), pages 1-2 = placeholder coming-soon panels
  - Drag and double-click for window move/maximize now work on both chrome bar and tab bar backgrounds
  - QSS: TabBarRow + TabButton rules added to all 5 theme files (dark, light, midnight_ocean, sunset_glass, neon_night) with per-theme accent colors for the active-tab underline
  - Tests: `tests/test_tab_layout.py`
→ Result: The app is structured for multiple tools; the first tab is the existing Life Drawing workflow, two more are ready for future features.
---

## 2026-04-13 (Image grid: ghost thumbnails after tag filtering)
### ✅ Tasks:
- Fix stale non-interactive image fragments in the grid gutters

  - Root cause: non-virtualized thumbnails use `QGridLayout`; virtualized mode uses a fixed pool with absolute geometry on `content`. When `thumbnail_pool` was non-empty, `clear()` returned early without removing grid layout items, so after switching between large (virtual) and small (grid) result sets, orphan cells kept painting old pixmaps.
  - Added `_drain_thumbnail_grid_layout()` and call it from `clear()` always, and from `_update_virtualized_view()` before pool assignment.
  - Tests: `tests/test_image_grid_ghost_widgets.py`
→ Result: Tag and filter changes no longer leave ghost thumbnails behind the live grid.
---

## 2026-04-13 (Image viewer: theme letterboxing)
### ✅ Tasks:
- Remove default gray background behind the image in the grid double-click viewer

  - `ImageViewerWindow`: `QGraphicsScene.setBackgroundBrush(Qt.transparent)`, `QGraphicsView` stylesheet with `background: transparent`, `viewport().setAutoFillBackground(False)` so the global `QMainWindow` gradient shows around `fitInView` letterboxing
  - Tests: `tests/test_image_viewer_window.py` (transparent setup, clear edge case, unknown id failure path)
→ Result: The large image viewer matches the active theme instead of a flat gray panel around the picture.
---

## 2026-04-12 (Planning: market study, pricing, startup costs)
### ✅ Tasks:
- Add market, subscription pricing, and non-dev cost planning document

  - New file `docs/Plans/sketchbook-260412_marche-prix-couts.md`: market segments and competitive landscape, subscription pricing reflection (tiers, freemium, marketplace commission), estimated year-1 non-development costs (legal, accounting, cloud, payments, distribution, marketing ranges) with EUR bands and scenarios
→ Result: A working commercial baseline for pricing decisions and bootstrap budgeting outside engineering effort.
---

## 2026-04-12 (Planning: commercial & technical roadmap)
### ✅ Tasks:
- Add commercial/technical planning document aligned with product vision

  - New file `docs/Plans/sketchbook-260412_commercial-technique.md`: target architecture (desktop client + backend services), online DB/catalog, auth & payments, packaging & distribution, legal/marketing checklist, phased rollout and risks
  - Grounded in current codebase state (local JSON metadata, no network layer)
→ Result: Shared reference for what a commercial, cloud-augmented SketchBook implies without changing application code.
---

## 2026-04-12 (Startup: empty window first, background sort)
### ✅ Tasks:
- Deferred heavy work until after the first paint

  - `MainWindow.showEvent` schedules `_deferred_startup_load` via `QTimer.singleShot(0)` so the frameless shell + chrome appear before tag grid fill and image list
  - Tag library (`_load_tags_into_grid`) + status **Loading library…** run first on the GUI thread; metadata **sort** for non-`course_random` modes runs in `QThreadPool` via `StartupSortRunnable` (`gui/startup_sort_worker.py`)
  - `ImageDatabase.snapshot_metadata_values()` returns a thread-safe copy under `_save_lock`; main thread applies filters with `_apply_category_filters(_pre_sorted_images=…)`
  - `course_random` startup path stays on the GUI thread (shuffle + filters)
  - `run_import_date_backfill` moved to `_finalize_startup_load` (after grid is ready); removed duplicate `QTimer` from `main.py`
  - Tests: `run_startup_load_for_tests()` sync path for `main_window` fixture
→ Result: Faster time-to-window; large libraries sort off the main thread before the first grid bind.
---

## 2026-04-12 (Floating tag panel UX)
### ✅ Tasks:
- Tag library overlay polish

  - Hide **Tags filters** trigger while the tag panel is visible (`isVisible()`), including during slide animations; show again only after `panel_did_hide`
  - Tag panel and trigger use a top inset (`logo height + 24px`) so they no longer extend under the floating logo; `TagPanelOverlay` animates at `y = top_inset` with reduced height
  - **Start session** is raised last in `_position_floating_grid_overlays` so it stays above the tag rail, overlay, and image tag popover
  - `TagHoverPopover` stores anchor thumbnail + viewport and `refresh_position()` on scroll/resize; `stackUnder(session button)` keeps the popover below **Start session**
→ Result: Tag UI stays clear of the logo; session button remains topmost among viewport overlays; selected-image tag popover follows the thumbnail while scrolling.
---

## 2026-04-12 (Image grid: unified sidebar animation system)
### ✅ Tasks:
- Replace crossfade overlay with ultra-fast per-frame resize during sidebar animation; fix scroll stability and eliminate sporadic image resets

  - Remove QLabel crossfade overlay system entirely (QGraphicsOpacityEffect, QPropertyAnimation, QEasingCurve)
  - `_get_scroll_anchor` uses cached `_last_layout_row_h` (from previous layout pass) to match current content layout
  - `_store_layout_row_height()` at end of every layout pass
  - `_sidebar_anim_active` flag on `ImageThumbnail`: `resizeEvent` uses `resetTransform + scale + centerOn` instead of `fitInView`
  - `_fast_scale_in_view()` on `ImageThumbnail`: direct transform for all FitMode variants with `FastTransformation`
  - Per-frame visible-only relayout (`_do_relayout_visible_only`), content height set explicitly, anchor restored
  - `_apply_full_quality_fit_visible_thumbnails()`: quality fit on visible ~30 thumbnails only at animation end
  - **Scroll signal blocking**: `QSignalBlocker` on scrollbar for entire duration of `relayout_after_sidebar_step` and `set_sidebar_width_animation_active(False)` — prevents `_on_scroll` from firing when `content.setFixedHeight` clamps the scroll value
  - **`_on_scroll` guard**: early return when `_sidebar_width_animation_active` is True — prevents visibility timer, load batches, and scroll preview during animation
  - **`set_image` respects `_sidebar_anim_active`**: images arriving from thread pool during animation use `_fast_scale_in_view` instead of expensive `fitInView + SmoothTransformation`
  - **Animation-end content height**: explicitly set `content.setMinimumHeight` at animation end before scroll anchor restore (QGridLayout LayoutRequest hasn't processed yet)
→ Result: Sidebar expand/collapse works identically at any scroll position (top, middle, bottom); no sporadic image resets; scroll perfectly preserved; expand and collapse behave symmetrically.
---

## 2026-04-12 (Image grid: defer all relayout during sidebar animation)
### ✅ Tasks:
- Sidebar animation resize optimization — zero relayout during animation

  - Remove per-frame grid relayout during sidebar animation: `_flush_sidebar_live_relayout` now only repositions floating overlays (no `relayout_after_sidebar_step` per tick)
  - Qt's `setWidgetResizable(True)` + `setFixedSize` children handles viewport clip/expand natively in C++ at near-zero cost
  - Replace `setFixedWidth()` + `setFixedHeight()` with single `setFixedSize()` in `_do_relayout`, `_update_virtualized_view`, `_load_next_batch`, `prepend_image` — halves the number of `resizeEvent` firings per thumbnail
  - `_apply_full_quality_fit_all_thumbnails()` runs once at animation end for sharp rendering
→ Result: Sidebar expand/collapse is completely lag-free; thumbnails snap to new size at animation end.
---

## 2026-04-12 (Image grid: comprehensive resize + scroll performance overhaul)
### ✅ Tasks:
- Resize performance

  - Direct `_fast_resize_active` flag on thumbnails — eliminates O(depth) parent-chain walk on every resizeEvent for every visible cell
  - Skip `_calculate_row_heights` during interactive resize (wasted O(n) iteration)
  - Virtualized view: skip same-image reassign (`assign_metadata` + `clear_pixmap` + `set_image`) for thumbnails that already show the correct image — major win for small scrolls
  - Virtualized view: skip geometry calls (`setFixedWidth/Height`, `setFixedSize`) when dimensions haven't changed
  - Content height update only when value actually changed

- Lazy load / scroll performance

  - O(1) `_image_id_to_index` dict replaces O(n) linear scans in `_load_thumbnail_image` and `_on_image_loaded` (called every 15ms tick with up to 20k images)
  - Two-phase image loading: worker emits `fast_ready` with cell-sized FastTransformation pixmap *before* computing HQ — thumbnails show content instantly while sharp version loads
  - Thread pool increased 4 → 8; loads per tick 8 → 16; pending queue 220 → 300
  - Scale factor reduced 3.0x → 2.0x (loads 600x720 instead of 900x1080 per cell — ~55% fewer pixels)
  - Extract (scroll preview) workers skip fast_ready emission (240x240 previews don't need two-phase)
→ Result: Window resize and scroll are significantly more fluid; images appear near-instantly with fast preview then upgrade to sharp.
---

## 2026-04-11 (Image grid: smooth sidebar fold)
### ✅ Tasks:
- Tag sidebar collapse: avoid debounced `layout_timer` during width animation so only `relayout_after_sidebar_step` updates the grid (preserves scroll ratio).

- `ImageGrid.set_sidebar_width_animation_active()`; `MainWindow` sets it for the duration of `_toggle_left_sidebar` animation.
→ Result: Gallery resize stays as fluid when folding the sidebar as when expanding it.
---

## 2026-04-11 (`safe_remove`: missing path returns False)
### ✅ Tasks:
- Fix `safe_remove` so a non-existent path returns `False` (previously fell through and returned `True`).

→ Result: Aligns with docstring and `tests/test_file_utils.py`.
---

## 2026-04-11 (Session: fullscreen fit + Éditer opens ImageViewerWindow)
### ✅ Tasks:
- Slideshow: restore `QGraphicsView` fullscreen `fitInView`; pause edit uses the grid viewer

- Replaced embedded session crop/rotate with `_SessionImageViewerWindow` (subclass of `ImageViewerWindow`): **Éditer** opens the same viewer as grid double-click; closing it reloads the slide and restores Précédent/Suivant/Pause (session stays paused).
- While the viewer is open, session navigation buttons are hidden.
- Removed `session_graphics_view.py` and `session_image_edit.py`; closing the session window disables viewer callback to avoid reload during shutdown.
→ Result: Full-area image display again; editing matches the main image viewer UX.
---

## 2026-04-11 (Virtualized image grid: fix empty rows when changing columns)
### ✅ Tasks:
- Fix progressive empty rows at the bottom of the grid (virtualized mode)

- The thumbnail pool was allocated only once; more columns → narrower cells → shorter rows → more rows visible in the same viewport, so the pool became too small and lower slots had no widget.
- `_ensure_virtualized_pool` now grows the pool to `_required_virtualized_pool_size()` whenever layout/viewport/columns change; capped pool size by catalog length.
- Row index math for the visible range now subtracts the grid’s top content margin so scroll position matches `y = margin_top + row * stride`.
- Tests in `tests/test_image_grid_virtualized_pool.py`.
→ Result: Scrolling and column changes keep all visible cells filled in large libraries.
---

## 2026-04-11 (Faster startup: deps split, lazy imports, deferred backfill, theme fonts)
### ✅ Tasks:
- Startup performance and dependency cleanup

- Trimmed `requirements.txt` to runtime only (PySide6, QtPy, Pillow); removed unused `pydantic`.
- Added `requirements-dev.txt` (black, pytest, pytest-qt, mypy, types-Pillow) and `requirements-tools.txt` (requests, beautifulsoup4 for `utils/download_animal_photo_refs.py`).
- Deferred `import_date` backfill to `QTimer.singleShot(0, ...)` after the main window is shown (`ImageManager.run_import_date_backfill()`).
- Lazy-import `SessionSettingsDialog`, `SlideshowWindow`, and `ImageViewerWindow` inside `gui/main_window.py` handlers.
- Load embedded **Kalam** only when the active theme’s QSS uses it; removed unused **Caveat** registration at startup.
- Tests: `run_import_date_backfill` delegation/error propagation; `load_theme_fonts` behavior for dark vs Kalam themes.
→ Result: Leaner installs, less work before first frame, and fewer font files touched on the default dark theme.
---

## 2026-04-10 (Ignore `.venv` in Git)
### ✅ Tasks:
- Stop tracking the virtual environment in version control

- Added `.venv/` to `.gitignore` (only `venv/` was listed before).
- Ran `git rm -r --cached .venv` so existing tracked venv files are removed from the index; local `.venv` remains on disk.
→ Result: Clones no longer inherit a machine-specific venv; each developer recreates it locally.
---

## 2026-04-10 (Recreate `.venv` for local Python 3.12)
### ✅ Tasks:
- Fix broken virtualenv pointing at another machine’s Python path (`C:\Users\Leo\...`)

- Removed the stale `.venv` whose `pyvenv.cfg` referenced `Leo\AppData\Local\Programs\Python\Python312` (path missing on this PC).
- Recreated `.venv` with the local install at `C:\Users\recoc\AppData\Local\Programs\Python\Python312` (`py -3.12 -m venv .venv`) and reinstalled dependencies from `requirements.txt`.
→ Result: `SketchBook/.venv/Scripts/python.exe` runs again; `main.py` starts with PySide6 available.
---

## 2026-04-10 (Default Crop All + reduced thumbnail pixelation)
### ✅ Tasks:
- Make crop mode the default display strategy and improve perceived thumbnail sharpness

- Changed default startup fit mode to `Crop All` when no previous user preference exists (`ui.grid.fit_mode` now defaults to `CROP_ALL`).
- Increased high-quality worker upscale factor from `2.0x` to `3.0x` minimum to reduce visible pixelation during crop/fill rendering.
- Aligned worker scaling mode with display mode: uses `KeepAspectRatioByExpanding` for crop/fill-like modes so the source pixmap has enough detail for clipped areas.
- Enabled smooth transform mode directly on `QGraphicsPixmapItem` in thumbnails.
→ Result: The default view is now crop/cover, and thumbnails stay cleaner when zoomed by crop/fill display modes.
---

## 2026-04-10 (User-selectable image display mode: Fit All / Fit Height / Fit Width / Crop All)
### ✅ Tasks:
- Add a "Display" combo box to the top chrome bar so the user chooses how images are fitted in grid cells

- Extended `gui/thumbnail_fitting.py` with a `FitMode` enum (`FIT_ALL`, `FIT_HEIGHT`, `FIT_WIDTH`, `CROP_ALL`) and corresponding logic in `fit_pixmap_in_view()` and `compute_fitted_size()`.
- Added `set_fit_mode()` to `ImageThumbnail` and `ImageGrid`; all existing and newly-created thumbnails inherit the current mode.
- Added a "Display:" combo box in the top chrome bar (next to Columns), wired to `ImageGrid.set_fit_mode()` with persistence via `ui.grid.fit_mode` setting.
- Updated `tests/test_thumbnail_fitting.py` from 10 to 21 cases covering all four modes plus the enum itself.
→ Result: Users can now choose their preferred display strategy; the setting is saved and restored on relaunch.
---

## 2026-04-10 (Unified thumbnail fitting module + top-bar centering fix)
### ✅ Tasks:
- Create a dedicated `gui/thumbnail_fitting.py` module as single source of truth for image→cell fitting
- Fix top chrome bar vertical centering

- Created `gui/thumbnail_fitting.py` with `fit_pixmap_in_view()` (uses `QGraphicsView.fitInView` with `KeepAspectRatio`) and `compute_fitted_size()` (pure geometry computation).
- Rewrote `ImageThumbnail.set_image()` and `resizeEvent()` to delegate all scaling to `fit_pixmap_in_view()`, replacing the broken `centerOn()`+`resetTransform()` pattern that caused oversized pixmaps to be cropped and undersized ones to stay too small.
- Enabled `SmoothPixmapTransform` and `Antialiasing` render hints on the `QGraphicsView` for crisp downscaling.
- Removed layout-level `setAlignment(Qt.AlignVCenter)` from the top chrome bar (conflicted with per-widget `AlignVCenter` flags), removed vertical content margins, and increased bar height to 38 px so all controls are genuinely centered.
- Added `tests/test_thumbnail_fitting.py` with 10 pytest cases covering landscape/portrait/square images, edge cases, and the invariant that output never exceeds cell size.
→ Result: All images now display fully without crop, maximized within their cells; top-bar controls are vertically centered.

## 2026-04-10 (Top-bar vertical centering + no-crop thumbnail fitting – superseded)
### ✅ Tasks:
- Vertically center top chrome controls and ensure image thumbnails always fit fully in grid cells

- Updated top chrome layout margins to use equal top/bottom spacing so controls are visually centered in the bar.
- Updated thumbnail worker scaling to fit each source image within the full target cell box (`target_width` x `target_height`) using `Qt.KeepAspectRatio`.
- Preserved maximum visible size while guaranteeing full-image display (no crop/clipping caused by width-only scaling).
→ Result: Initial attempt — did not work because the root causes were architectural (see entry above).
---

## 2026-04-10 (Text color consistency pass: white informational labels)
### ✅ Tasks:
- Unify key informational text colors to white for visual consistency

- Updated tag library header labels (`Tags Library`, parent-selection helper text) to explicit white.
- Updated top chrome helper labels (`Sort`, `Columns`, and column count) to white.
- Updated right status metrics (`Images: N` and selection summary) to white.
→ Result: Informational UI text now has consistent white contrast across the main screen.
---

## 2026-04-10 (Chrome balance tweak: bigger logo, stronger shadow, thinner top strip)
### ✅ Tasks:
- Adjust logo emphasis and reduce top chrome thickness

- Increased floating logo size for stronger branding presence.
- Added a pronounced drop shadow on the floating logo to improve depth and separation from background gradients.
- Reduced top chrome bar height slightly to keep a lighter upper silhouette.
→ Result: The header keeps strong branding with better logo contrast while the top strip feels slimmer and cleaner.
---

## 2026-04-10 (Custom chrome final UX pass)
### ✅ Tasks:
- Final polish for frameless window UX and top chrome proportions

- Improved resize cursor feedback by updating edge-hit cursor state through the global event filter (including when hovering child widgets near borders).
- Corrected custom window glyphs for minimize/maximize/restore (`-`, `□`, `❐`) to look closer to standard window controls.
- Adjusted proportions: slightly reduced floating logo size, increased top chrome bar height, and widened compact left sidebar rail.
→ Result: Frameless behavior feels more native (clear resize affordance) and the top layout balance is closer to the intended final design.
---

## 2026-04-10 (Top bar polish: resizable frameless + transparent menu buttons)
### ✅ Tasks:
- Keep the custom frameless window resizable and refine top menu button visuals

- Added edge/corner hit-testing and native `startSystemResize(...)` delegation so the frameless main window remains resizable from borders.
- Updated `File / View / Tools / Help` top buttons to transparent background, with very low-alpha white hover feedback.
- Increased custom top chrome height for better readability and spacing.
→ Result: The custom title bar keeps the desired visual style while preserving practical window resize behavior.
---

## 2026-04-10 (Custom themed window bar with app menus and window controls)
### ✅ Tasks:
- Replace the native title bar with a custom themed top bar that includes app menus and minimize/maximize/close controls

- Enabled frameless main window mode and added custom window control buttons (`_`, `[]`/restore, `X`) in the existing top chrome row.
- Kept `File / View / Tools / Help` in the same row as grid controls and added window-state sync for maximize/restore button behavior.
- Added drag and double-click handling on the custom top bar background to support move and maximize/restore interactions.
→ Result: The app now uses a non-white, theme-consistent custom title bar where menus and window controls live on the same horizontal row.
---

## 2026-04-10 (Tag sidebar visual cleanup: transparent library + hidden splitter handle)
### ✅ Tasks:
- Remove tag library scroll area background and make the main content splitter separator invisible

- Updated `MainWindow` to make `tags_scroll_area` transparent via object-scoped stylesheet (`TagLibraryScrollArea`).
- Updated the main horizontal splitter to use a zero-width, transparent handle (`MainImageSplitter`) so the divider is no longer visible.
- Kept behavior intact while simplifying the visual separation between tag library and gallery.
→ Result: The tag library now blends with its panel background, and the splitter separator is visually hidden for a cleaner interface.
---

## 2026-04-10 (Environment fix: stable Python for PySide6)
### ✅ Tasks:
- Replace unstable project virtual environment interpreter and restore Qt bindings loading

- Installed stable Python 3.12.10 locally and recreated `.venv` with `py -3.12 -m venv .venv`.
- Reinstalled all dependencies from `requirements.txt` in the new environment.
- Verified that `PySide6` and `shiboken6` import successfully and that `main.py` imports without runtime binding errors.
→ Result: The project now uses a stable virtual environment (`.venv`) where Qt bindings load correctly, enabling normal app startup from Cursor.
---

## 2026-04-10 (Developer experience: run main.py from Cursor Play button)
### ✅ Tasks:
- Add workspace VS Code/Cursor Python run configuration for direct launch of `main.py`

- Added `.vscode/launch.json` with a dedicated `Python: Run main.py` launch profile.
- Added `.vscode/settings.json` to pin the workspace interpreter to `.venv\\Scripts\\python.exe`.
- Configured launch to run in integrated terminal with workspace root as current working directory.
→ Result: `main.py` can now be launched directly from Cursor with the Play/Run action using the project virtual environment.
---

## 2026-04-10 (Environment setup: local Python virtual environment)
### ✅ Tasks:
- Create a local Python virtual environment and install project dependencies from `requirements.txt`

- Created `.venv` at the project root with `py -3 -m venv .venv`.
- Upgraded `pip` inside the virtual environment to latest available version.
- Installed all dependencies listed in `requirements.txt` (GUI, image processing, validation, tooling, and typing packages).
→ Result: The project now has a ready-to-use isolated Python environment with all required dependencies installed.
---

## 2026-04-10 (Tag sidebar: floating controls, wider panel, grid relayout on animation end)
### ✅ Tasks:
- Independent floating tag toggle + branding logo on the image grid; fully collapse the tag rail; open panel width for 3 tag columns; full-height tag scroll; center **Start session** at bottom; relayout grid only when sidebar animation ends

- **Top chrome bar**: Thin row; **floating logo** (child of central widget, not in layout); **File / View / Tools / Help** + **Shuffle** / **Sort** / **Columns**. **Tags filters**: lower on grid, **hover opens** tag library when closed.
- **Refinement pass**: Vertically centered top menu buttons, increased top inset inside the tag library so content does not pass under the floating logo, auto-collapse tag sidebar on mouse leave, and lowered the floating **Tags filters** button again.
- **Interaction tweak**: Floating **Tags filters** is now vertical on the far-left under the logo footprint; opening is driven by hover only (enter/mouse-move on the control while closed), and top-row buttons get a little extra top breathing space.
- **Stability + layout tweak**: Fixed intermittent Qt warning `QFont::setPointSize <= 0` by cloning and clamping tag-chip font size when app font point size is invalid; converted **Tags filters** into a full-height left rail (glued to x=0) below logo area.
- **Interaction model update**: Removed floating behavior for the tag toggle. Left sidebar now has two hover-driven animated states: compact rail (button-only, collapsed width) by default, and expanded tag library (button hidden) while hovered.
- **Smoothness pass**: Improved collapse smoothness by using ultra-frequent coalesced relayout ticks, lightweight live layout path during sidebar animation, delayed compact spacer height application until collapse finishes, and scroll ratio preservation without triggering scrollbar side effects each frame.
- **Tag rail**: Collapses to width **0** when closed; open width **~360** px; top inset so the library does not sit under the logo band; larger logo.
- **Tag library layout**: Scroll area uses stretch so it fills the vertical space inside the folding panel; removed the old bottom stretch that stole height from the scroll view.
- **Start session**: Anchored to the **bottom center** of the image grid viewport (was bottom-right).
- **Gallery animation**: `ImageGrid.relayout_after_sidebar_step()` runs **only when the sidebar width animation finishes** (not during the animation).
- **Status bar**: Image count and selection weight moved to the **right side of the status bar** (with messages / dev-style feedback). Tag panel slightly narrower; top inset under logo band; larger logo.
- **Tests**: `tests/test_image_grid.py` covers `relayout_after_sidebar_step` (expected use, empty grid, failure path).
 → Result: Tag filters are always reachable from the same floating control; the logo sits top-left; the tag library uses the panel height better; the session button is centered at the bottom.
---

## 2026-04-08 (Tag hierarchy: recursive descendant filtering)
### ✅ Tasks:
- Fix tag filtering so selecting a parent sub-category includes all nested descendants in the image grid

- **Recursive filtering**: In `MainWindow`, category and label filters now expand selected tags with all recursive descendants before matching image tags. This makes parent sub-categories behave as expected (e.g. selecting `Felin` also matches images tagged with `Chat`, `Tiger`, `Lion`).
- **OR descendant matching for selected sub-category**: each selected sub-category now creates an OR group made of itself + recursive descendants (instead of a global AND on all descendants). This fixes the "0 images" case when selecting a parent sub-category like `Felin`.
- **Hierarchy visual cues**: categories and tags now display expand/collapse arrows when they have children (`▶` collapsed, `▼` expanded). Added depth-based hierarchy coloring for tags and categories so nested levels are easier to identify in the grid.
- **Consistent tag interactions**: simple click now stays dedicated to filter/expand-collapse behavior. Tag-library multi-selection is now only done via modifier+drag (`Ctrl` or `Shift` + drag), avoiding accidental click selection.
- **Hierarchy layout UX**: child tags are now rendered directly on a new line under their selected parent, with stable parent position in the category order (no parent jump). Child rows also get a subtle visual frame.
- **New modern themes**: added three gradient-based themes (`Neon Night`, `Sunset Glass`, `Midnight Ocean`) and made them selectable both in Settings and in the View > Theme menu.
- **Modernized default dark style**: updated the base dark theme with a soft purple/indigo gradient background and cleaner translucent controls. Switched default app typography to `Segoe UI` for a simpler white modern look.
- **Tag sidebar behavior**: removed the unused top section from the left vertical splitter and switched to a fixed-width collapsible sidebar with open/close animation for the tag panel.
- **Cycle safety**: Added cycle protection in descendant traversal to avoid infinite recursion if an invalid parent loop exists in user placements.
- **Tests**: Added unit tests in `tests/test_main_window.py` for expected recursive expansion, leaf-tag edge case, and cycle failure case.
 → Result: Tag hierarchy supports unlimited nested sub-categories/sub-tags for filtering, and clicking a parent sub-category now includes images tagged with deeper child tags.
---

## 2026-03-24 (Session start from selected image in grid)
### ✅ Tasks:
- Add a context-menu action to start a session from one selected image in the image grid

- **Context menu behavior**: In `ImageGrid`, right-click now shows **"Start session from this image"** only when exactly one image is selected.
- **Session start behavior**: Triggering this action opens the existing Session Settings dialog and starts the session from that selected image onward; images before it in the current ordered list are ignored for that session.
- **Implementation**: Added `start_session_from_image_requested` signal in `ImageGrid`, connected in `MainWindow` to a new handler that reuses `_on_session_settings_clicked(start_from_image_id=...)`. Added `_slice_images_from_start()` helper to keep list order while cutting preceding images.
- **Tests**: Added unit tests for session-start slicing logic (expected use, edge case, failure case) in `tests/test_main_window.py`.
 → Result: You can right-click a single thumbnail and launch a session that begins exactly at that image, continuing with the same current order.
---

## 2026-03-14 (Tag library: auto-scroll during tag drag)
### ✅ Tasks:
- Auto-scroll tag library when dragging tags near top or bottom edge

- **Behavior**: While dragging one or more user tags, if the cursor is within 40 px of the top or bottom of the tag library scroll area, the area scrolls up or down automatically (every 120 ms) so you can reach tags above or below without releasing the drag.
- **Implementation**: `_tag_drag_in_progress` flag and `_tag_drag_scroll_timer` (QTimer) started before `drag.exec_()` and stopped in a `finally` block; `_on_tag_drag_scroll_tick()` uses global cursor position and viewport rect to adjust `tags_scroll_area.verticalScrollBar()`.
 → Result: Dragging tags to reparent or apply to images is easier when the list is long; the list scrolls as you move the cursor toward the edges.
---

## 2026-03-14 (Tag library: "Parent to tag..." from right-click menu)
### ✅ Tasks:
- Add "Parent to tag..." to tag library context menu (user tags only)

- **Multi-select**: Ctrl+click on user tags to select several; right-click one of them → "Parent to tag..." to move all selected tags under a chosen parent.
- **Parent-select mode**: After choosing "Parent to tag...", the tags to move are grayed out. A bar appears at the top of the Tags Library: "Select parent tag: (none)" with **OK** and **Cancel**. Click any other tag or category to set it as the parent (label updates to "Select parent tag: &lt;name&gt;"). **OK** applies the same placement as drag-and-drop (tags become children of that tag or under that category); **Cancel** exits without changes.
- **Implementation**: `_tag_library_selection` for Ctrl+click, `_parent_select_mode` with bar widgets and `_on_parent_select_ok` / `_on_parent_select_cancel`; `eventFilter` on user tag buttons for Ctrl+click; `_sync_tag_grid_state` grays buttons in `_tags_to_parent` when in parent mode.
 → Result: Users can reparent one or several user tags without drag-and-drop, by choosing a parent then confirming.
---

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