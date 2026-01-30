feat: session countdown second-by-second and red gradient toward zero

Description:
- Timer ticks every second (interval 1s) instead of 100ms; countdown decreases second by second
- Countdown overlay moved from top-right to top-left in session window
- Countdown label color interpolates toward red as remaining time approaches 0 (dark: white→red, light: black→red); color reset on image change or session start

Affected files:
- gui/session_timer.py
- gui/slideshow_window.py
- docs/CHANGELOG.md
- docs/CHANGELOG_FR.md
- docs/DOC_USER.md
- .cursor/TASKS.md
