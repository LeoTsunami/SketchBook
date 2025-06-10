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

### Phase 4: Image Browser UI 🔄 (In Progress)
- [ ] Implement image grid view
  - [ ] Create scrollable grid layout
  - [ ] Add image thumbnails with labels
  - [ ] Implement dynamic loading for performance
  - [ ] Add image selection functionality
- [ ] Create tag management UI
  - [ ] Add tag search bar with autocompletion
  - [ ] Show currently active tags
  - [ ] Add/remove tag functionality
  - [ ] Visual feedback for tag operations
- [ ] Implement filtering system
  - [ ] Filter images by selected tags
  - [ ] Real-time update of displayed images
  - [ ] Clear filters option

---

## 🧠 DISCOVERIES / QUESTIONS

- [x] Research best practices for Qt application architecture
- [x] Investigate efficient image processing methods with Pillow
- [x] Plan database schema for extensibility
- [ ] Document setup process for new developers
- [ ] Consider adding image format conversion options
- [ ] Consider implementing batch processing options for large imports
- [ ] Consider adding image preview functionality

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
- [x] Image import & storage
- [x] Initial documentation

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

# Tasks

## ✅ Completed
- Image Grid Improvements
  - Added column slider (3-8 columns)
  - Optimized image display with dynamic row heights
  - Fixed image scaling and aspect ratio preservation
  - Implemented dark theme for grid and thumbnails
  - Removed image labels for cleaner interface
  - Fixed initial image loading and scroll behavior

## 🔄 In Progress

## 📋 Backlog

## 🔍 DISCOVERIES / QUESTIONS
