# ✅ SKETCHBOOK – TASKS.md

**Purpose**: Track development progress, current tasks, backlog, and milestones.  
Update this file via prompt:  
→ `"Update task"`

---

## 📌 CURRENT TASKS (Sprint 1: Project Setup)

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

### Phase 2: Core Features Foundation 🔄 (In Progress)
- [x] Define internal settings format (JSON)
  - [x] Create settings.json template
  - [x] Implement settings manager in `core/settings.py`
- [x] Implement basic file system utilities in `utils/`
  - [x] File path handling
  - [x] Directory creation/validation
- [x] Create first GUI window
  - [x] Empty Qt window with basic menu structure
  - [x] Dark/Light mode support preparation

### Phase 3: Image Management Basics
- [x] Implement image import system
  - [x] File dialog for selection
  - [x] Drag & drop support
  - [x] Basic error handling
- [x] Create image processing utilities
  - [x] Auto-resize/compress images (1080p max width)
  - [x] Format standardization
- [x] Set up local image database structure
  - [x] Design JSON/SQLite schema for image metadata
  - [x] Implement basic CRUD operations

---

## 🧠 DISCOVERIES / QUESTIONS

- [x] Research best practices for Qt application architecture
- [ ] Investigate efficient image processing methods with Pillow
- [ ] Plan database schema for extensibility
- [ ] Document setup process for new developers

---

## 🧱 BACKLOG (Future Sprints)

### Sprint 2: Image Management & Tagging
- [ ] Implement basic manual tagging UI
- [ ] Create tag management system
- [ ] Build image browser interface
- [ ] Write helper function: `load_images_by_tags()`

### Sprint 3: Session Management
- [ ] Design session presets system
- [ ] Implement slideshow player
- [ ] Add basic timer functionality
- [ ] Create session configuration UI

### Sprint 4: Advanced Features
- [ ] Implement auto-tagging using AI
- [ ] Add analytics tracking system
- [ ] Create export functionality
- [ ] Polish UI/UX

---

## 🎯 MILESTONES

### v0.1 – Foundation (Current Goal)
- [x] Basic project structure
- [x] Working GUI shell
- [ ] Image import & storage
- [ ] Initial documentation

### v0.2 – Core Features
- [ ] Manual image tagging
- [ ] Basic slideshow functionality
- [ ] Simple timing system

### v0.3 – Enhanced Features
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
