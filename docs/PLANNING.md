# Project Planning & Rules

## 🎯 Project Overview
[Project description to be added]

## 📁 Directory Structure
```
SketchBook/
├── core/         # Core business logic
├── data/         # Data storage and configuration
├── docs/         # All documentation files
├── gui/          # User interface components
├── tests/        # Test files mirroring main structure
└── utils/        # Utility functions and helpers
```

## 🔄 Automated Verification Steps
### Pre-Task Checklist
1. **Documentation Review**
   - [ ] Read `docs/PLANNING.md`
   - [ ] Check `docs/TASK.md`
   - [ ] Review relevant sections in `docs/DOC_DEV.md`

2. **File Location Verification**
   - Documentation files MUST be in `docs/`:
     - PLANNING.md
     - TASK.md
     - CHANGELOG.md
     - CHANGELOG_FR.md
     - DOC_DEV.md
     - DOC_USER.md
     - CIR_VERROUS.md
   - Tests MUST be in `tests/` mirroring main structure
   - Source code MUST be in appropriate module directories

3. **Code Standards Check**
   - [ ] PEP8 compliance
   - [ ] Type hints present
   - [ ] Docstrings (Google style)
   - [ ] Black formatting

4. **Test Requirements**
   - [ ] Unit tests for new features
   - [ ] Tests mirror source structure
   - [ ] Minimum test coverage:
     - 1 expected use case
     - 1 edge case
     - 1 failure case

### Post-Task Checklist
1. **Documentation Updates**
   - [ ] Update `docs/TASK.md`
   - [ ] Add entry in `docs/CHANGELOG.md` and `docs/CHANGELOG_FR.md`
   - [ ] Update `docs/DOC_DEV.md` if internal logic changed
   - [ ] Update `docs/DOC_USER.md` if user behavior changed
   - [ ] Update `docs/CIR_VERROUS.md` if R&D blockers found

2. **Code Quality**
   - [ ] No file exceeds 500 lines
   - [ ] Clear module separation
   - [ ] Consistent import structure
   - [ ] Non-obvious code is commented

3. **Commit Standards**
   - Format: `type: function/feature name`
   - Description must include:
     ```
     Description:
      - [Brief explanation of changes]
      - [Benefits/reasons if relevant]
     Affected files:
      - path/to/file1
      - path/to/file2
     ```

## 🛠 Development Standards
### Language & Tools
- Python as primary language
- FastAPI for APIs
- SQLAlchemy/SQLModel for ORM
- Pydantic for data validation
- Black for formatting
- Pytest for testing

### Code Style
- Follow PEP8
- Use type hints
- Google style docstrings
- Clear module separation
- Max 500 lines per file

### Documentation Style
- Clear and concise
- Always bilingual (EN/FR) for changelogs
- Technical details in DOC_DEV.md
- User instructions in DOC_USER.md
- R&D blockers in CIR_VERROUS.md

## 🔍 Quality Control
### Testing Requirements
- Unit tests for all features
- Test files mirror source structure
- Minimum test coverage requirements
- Regular test suite execution

### Code Review Guidelines
- Check documentation updates
- Verify file structure
- Ensure test coverage
- Validate code style
- Review performance impact 