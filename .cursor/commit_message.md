feat: tag removal on selection in background thread (same worker as assign)

Description:
- Remove-tag action (× on tag chip for selected images) now runs in background via TagApplyWorker with operation="remove"
- ImageGrid._remove_tag_from_selection creates worker, connects progress/finished/error, starts in thread_pool; handlers refresh thumbnails on main thread
- New signals on ImageGrid: tag_remove_progress, tag_remove_finished, tag_remove_error for main window status/progress
- Main window connects to these signals and shows "Removing tag 'X'..." with progress bar, cleanup on finished/error
- Unit tests in tests/test_tag_apply_worker.py for remove operation, empty list, error path

Affected files:
- gui/image_grid.py
- gui/main_window.py
- tests/test_tag_apply_worker.py
- docs/CHANGELOG.md
- docs/CHANGELOG_FR.md
- docs/DOC_DEV.md
- docs/DOC_USER.md
- .cursor/TASKS.md
