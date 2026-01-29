feat: drawing sessions (Course + Constant interval)

Description:
- Session Settings now starts a dedicated session window instead of only showing a message
- Course sessions: duration 10–60 min (step 10), phases WarmUp (30s/image), Gesture (1min), Anatomy (5min), Shading (10min); presets in gui/ressources/session_configs.json
- Constant interval sessions: fixed duration per image (30s, 1/3/5/10/20 min)
- Image list built from currently filtered images (by tags), shuffled randomly
- Session window: fullscreen or "Window always on top" (from Session Settings)
- Countdown per image in top-right; bottom bar: Play/Pause, Previous, Next; Space toggles controls, Escape closes and returns to main window
- Main window hides when session starts and re-shows when session window is closed
- SessionManager extended with load_course_config, build_course_run, start_session(image_ids, type, ...), navigation (advance_image, previous_image, get_current_duration, get_session_progress)
- Unit tests added in tests/test_session_manager.py

Affected files:
- core/session_manager.py
- gui/slideshow_window.py
- gui/main_window.py
- gui/session_settings_dialog.py
- gui/ressources/session_configs.json (new)
- tests/test_session_manager.py (new)
- docs/CHANGELOG.md
- docs/CHANGELOG_FR.md
- docs/DOC_USER.md
- docs/DOC_DEV.md
- .cursor/TASKS.md
