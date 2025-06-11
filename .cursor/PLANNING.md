# SKETCHBOOK – Project Planning

## 🔥 Purpose (High-level vision)

Sketchbook is a Windows desktop application to help artists train with timed life drawing sessions based on a curated image library.  
It simulates traditional "model drawing classes" using tagged static images instead of live models.

It provides:
- Image import and compression/standardization
- Automatic and manual image tagging
- Custom course/session generation based on tags and timing presets
- A fullscreen slideshow player for training or always on top window
- Simple analytics for tracking artistic progression

---

## 🧱 Tech Stack

- **Language**: Python 3.12+
- **GUI Framework**: PySide6 or QtPy (depending on compatibility)
- **Image Processing**: Pillow, torchvision (optional for tagging), OpenCV
- **AI Tagging (optional)**: CLIP or other image recognition models
- **Filesystem**: Local directory-based image storage + JSON or SQLite for metadata
- **Platform**: Windows (desktop) and maybe mac version aswell
- **IDE**: Cursor

---

## ⚙️ Key Components (Modular Structure)
- `.cursor/`: Planing and task for cursor use
- `core/`: Main business logic (session engine, tag manager, analytics)
- `gui/`: UI components (Qt widgets, views, event handling)
- `data/`: Image library, metadata DB, settings
- `utils/`: Helpers (image conversion, compression, timing control)
- `docs/`: All documentation for dev and changelogs.
- `main.py`: Entry point
- `README.md`: User documentation

---

## ⛓️ Constraints

- Must be fast and lightweight (<= 300MB RAM)
- Must run offline, without external servers or cloud
- No user login or network dependencies
- Code must be organized in multiple files by responsibility
- Each module should be readable and maintainable
- Easy to package as a .exe via PyInstaller or similar
- Code should be documented inline (docstrings) and externally (README, HELP.md)

---

## 🧠 AI/Cursor Expectations

- Use this file as context for all features and refactors
- Propose modular, scalable solutions (avoid monoliths)
- Prefer readable, extensible code over clever tricks
- Ask for clarification before implementing if a design is unclear