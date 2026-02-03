perf: load thumbnail pixmaps only for visible items with debounced scroll and load ticker

Description:
- Scroll no longer triggers immediate visibility check; _on_scroll only starts a 120 ms debounce timer; when it fires, _check_visible_thumbnails enqueues visible image IDs into pending_load_queue (capped at 60)
- A separate load_ticker_timer (80 ms) processes the queue with at most 2 pixmap loads per tick (_process_pending_loads), spreading set_image() and cache updates over time to avoid main-thread lag
- clear() stops both timers and empties the pending queue
- Unit tests in tests/test_image_grid.py for scroll debounce, queue/ticker, and clear behavior

Affected files:
- gui/image_grid.py
- tests/test_image_grid.py
- docs/CHANGELOG.md
- docs/CHANGELOG_FR.md
- docs/DOC_DEV.md
- .cursor/TASKS.md
