# Project Cleanup Implementation Plan

**Date**: 2026-03-03
**Related Design**: [2026-03-03-project-cleanup-design.md](./2026-03-03-project-cleanup-design.md)
**Execution Strategy**: Subagent-Driven Development (Single Session)

---

## Overview

This implementation plan provides step-by-step instructions for cleaning up the AutoLabeler project. The plan is organized into 5 phases with 14 bite-sized tasks, each designed to be completed in under 10 minutes.

**Execution Approach**: Subagent-Driven Development
- All work completed in current session
- No new git worktrees needed
- Frequent commits after each phase
- Review checkpoints between major phases

---

## Phase 1: Documentation Organization

**Duration**: 5 minutes
**Risk**: None (just moving files)
**Objective**: Organize scattered documentation into structured `docs/` folder

### Task 1.1: Create Documentation Folder Structure

**Files to Create**:
- `docs/user/` (new directory)
- `docs/dev/` (new directory)
- `docs/guides/` (new directory)

**Command**:
```bash
mkdir -p docs/user docs/dev docs/guides
```

**Verification**:
```bash
ls -la docs/
# Expected output:
# drwxr-xr-x ... docs/user
# drwxr-xr-x ... docs/dev
# drwxr-xr-x ... docs/guides
```

**Commit**: None yet (wait for all doc moves)

---

### Task 1.2: Move User Documentation

**Files to Move**:
- `USER_GUIDE.md` → `docs/user/USER_GUIDE.md`
- `用户使用手册.md` → `docs/user/用户使用手册.md`

**Command**:
```bash
git mv USER_GUIDE.md docs/user/
git mv 用户使用手册.md docs/user/
```

**Verification**:
```bash
ls -la docs/user/
# Expected: 2 files (USER_GUIDE.md, 用户使用手册.md)
test -f docs/user/USER_GUIDE.md  # Should exist
test -f docs/user/用户使用手册.md  # Should exist
```

---

### Task 1.3: Move Developer Documentation

**Files to Move**:
- `requirement.md` → `docs/dev/requirement.md`
- `jishukaifawendang.md` → `docs/dev/jishukaifawendang.md`
- `CURRENT_STATE.md` → `docs/dev/CURRENT_STATE.md`
- `HANDOFF.md` → `docs/dev/HANDOFF.md`

**Command**:
```bash
git mv requirement.md docs/dev/
git mv jishukaifawendang.md docs/dev/
git mv CURRENT_STATE.md docs/dev/
git mv HANDOFF.md docs/dev/
```

**Verification**:
```bash
ls -la docs/dev/
# Expected: 4 files
```

---

### Task 1.4: Move Technical Guides

**Files to Move**:
- `CODE_CONVERSION_RULES.md` → `docs/guides/CODE_CONVERSION_RULES.md`
- `SMALL_OBJECT_DETECTION.md` → `docs/guides/SMALL_OBJECT_DETECTION.md`
- `jishukaifawendang_backup.md` → `docs/guides/jishukaifawendang_backup.md`

**Command**:
```bash
git mv CODE_CONVERSION_RULES.md docs/guides/
git mv SMALL_OBJECT_DETECTION.md docs/guides/
git mv jishukaifawendang_backup.md docs/guides/
```

**Verification**:
```bash
ls -la docs/guides/
# Expected: 3 files
```

---

### Task 1.5: Verify Documentation Accessible

**Command**:
```bash
# Check all docs are accessible
find docs/ -name "*.md" | wc -l
# Expected: 9 .md files in docs/ folder

# Verify no broken links (check references to moved files)
grep -r "requirement.md\|jishukaifawendang.md\|USER_GUIDE.md" . --include-dir=docs 2>/dev/null || echo "No references in docs"
```

**Commit**: Phase 1 Complete
```bash
git add docs/
git commit -m "Phase 1: Organize documentation into structured folders

- Move user docs to docs/user/
- Move dev docs to docs/dev/
- Move guides to docs/guides/
- All 9 documentation files organized"
```

**Checkpoint**: Can you access `docs/user/USER_GUIDE.md`?

---

## Phase 2: Build Artifact Removal

**Duration**: 2 minutes
**Risk**: None (can regenerate)
**Objective**: Remove build artifacts to free disk space (~2.6GB)

### Task 2.1: Remove Build Directories

**Directories to Remove**:
- `dist/` (1.4GB)
- `build/` (162MB)
- `runs/` (2.6MB)

**Command**:
```bash
rm -rf dist/
rm -rf build/
rm -rf runs/
```

**Verification**:
```bash
# Verify directories are gone
test ! -d dist && echo "dist/ removed successfully"
test ! -d build && echo "build/ removed successfully"
test ! -d runs && echo "runs/ removed successfully"

# Check disk space freed
du -sh . 2>/dev/null | tail -1
```

---

### Task 2.2: Remove Archive Files

**Files to Remove**:
- `auto_yolo_label.zip` (2.4GB)
- `tests/105954-32435.zip`
- `tests/use_test/105954-32435.zip`

**Command**:
```bash
rm -f auto_yolo_label.zip
rm -f tests/105954-32435.zip
rm -f tests/use_test/105954-32435.zip
```

**Verification**:
```bash
# Verify files are gone
test ! -f auto_yolo_label.zip && echo "Archive removed"
test ! -f tests/105954-32435.zip && echo "Test archive removed"
```

---

### Task 2.3: Verify Application Still Runs

**Command**:
```bash
python main.py &
sleep 3
pkill -f python
# Expected: GUI launches successfully
```

**Alternative Verification** (if GUI not available):
```bash
# Test core imports work
python -c "from core.scanner import Scanner; from core.sampler import Sampler; print('Imports OK')"
# Expected: Imports OK
```

**Commit**: Phase 2 Complete
```bash
git add -A  # Tell git to stop tracking removed files
git commit -m "Phase 2: Remove build artifacts and free 2.6GB

- Remove dist/ (1.4GB)
- Remove build/ (162MB)
- Remove runs/ (2.6MB)
- Remove archive files (*.zip)
- Application still runs normally"
```

**Checkpoint**: Disk space freed ~2.6GB?

---

## Phase 3: Tools Directory Removal

**Duration**: 1 minute
**Risk**: Low (tools not imported)
**Objective**: Remove unused debugging scripts

### Task 3.1: Check for Tool Imports

**Command**:
```bash
# Verify tools are not imported by core code
grep -r "from tools\." core/ gui/ utils/ config/ main.py build.py 2>/dev/null || echo "No imports found"
# Expected: No imports found (tools/ is isolated)
```

**If imports Found**: STOP and report to user before proceeding.

---

### Task 3.2: Remove Tools Directory

**Command**:
```bash
rm -rf tools/
```

**Verification**:
```bash
test ! -d tools && echo "tools/ removed successfully"
```

---

### Task 3.3: Verify No Broken Imports

**Command**:
```bash
# Test all core imports still work
python -c "from core.scanner import Scanner; print('Scanner OK')"
python -c "from utils.mapping_manager import MappingManager; print('MappingManager OK')"
python -c "from gui.app import main; print('GUI OK')"
# Expected: All imports work
```

**Commit**: Phase 3 Complete
```bash
git add -A
git commit -m "Phase 3: Remove unused tools directory

- Remove tools/ (one-time debugging scripts)
- No imports from tools/ in core code
- All imports still work"
```

**Checkpoint**: Can you run `python -c "from core.scanner import Scanner"` without errors?

---

## Phase 4: Test Cleanup

**Duration**: 3 minutes
**Risk**: Medium (removing tests)
**Objective**: Remove integration and edge-case tests, keep core tests

### Task 4.1: Remove Integration Tests

**Files to Remove**:
- `tests/test_training_integration.py`
- `tests/test_inference_separated_storage.py`

**Command**:
```bash
rm -f tests/test_training_integration.py
rm -f tests/test_inference_separated_storage.py
```

**Verification**:
```bash
test ! -f tests/test_training_integration.py && echo "Integration test removed"
```

---

### Task 4.2: Remove Edge-Case Tests

**Files to Remove**:
- `tests/test_small_object_config.py`
- `tests/test_conversion_rule.py`
- `tests/test_converter_xml_to_txt.py`
- `tests/test_image_utils.py`
- `tests/test_home_navigation.py`

**Command**:
```bash
rm -f tests/test_small_object_config.py
rm -f tests/test_conversion_rule.py
rm -f tests/test_converter_xml_to_txt.py
rm -f tests/test_image_utils.py
rm -f tests/test_home_navigation.py
```

**Verification**:
```bash
ls tests/test_*.py | wc -l
# Expected: 9 files (scanner, sampler, trainer, inferencer, restorer, converter, mapping_manager, path_encoder, device)
```

---

### Task 4.3: Run Core Tests

**Command**:
```bash
pytest tests/ -v
# Expected: 9 tests pass
```

**If Tests Fail**: ROLLBACK
```bash
git checkout HEAD~1 -- tests/  # Restore removed tests
# Investigate why tests failed before proceeding
```

**Commit**: Phase 4 Complete
```bash
git add -A
git commit -m "Phase 4: Remove integration and edge-case tests

- Remove 8 test files (integration, edge-case)
- Keep 9 core tests (scanner, sampler, trainer, inferencer, restorer, converter, mapping_manager, path_encoder, device)
- All core tests pass"
```

**Checkpoint**: Do all 9 core tests pass with `pytest tests/ -v`?

---

## Phase 5: Post-Cleanup Updates

**Duration**: 5 minutes
**Risk**: Low
**Objective**: Update documentation and reflect new structure

### Task 5.1: Update .gitignore

**File**: `.gitignore`

**Add Lines**:
```gitignore
# Build artifacts
dist/
build/
runs/

# Archives
*.zip
*.tar.gz

# PyInstaller
*.spec.bak
```

**Command**:
```bash
cat >> .gitignore << 'EOF'
# Build artifacts
dist/
build/
runs/

# Archives
*.zip
*.tar.gz

# PyInstaller
*.spec.bak
EOF
```

**Verification**:
```bash
cat .gitignore | grep -E "^dist/|^build/|^runs/"
# Expected: dist/, build/, runs/ entries present
```

---

### Task 5.2: Update CLAUDE.md Project Structure Section

**File**: `CLAUDE.md`

**Section to Update**: Lines 92-112 (Project Structure)

**Old Content**:
```markdown
## Project Structure

```
auto_yolo_label/
├── core/                    # Core business logic
│   ├── scanner.py          # Scan site folders
│   ├── sampler.py          # Sample images
│   ├── trainer.py          # YOLO training
│   ├── inferencer.py       # Batch inference
│   ├── restorer.py         # Restore labels
│   └── converter.py        # YOLO txt → VOC xml
├── utils/                   # Utilities
│   ├── path_encoder.py     # Encode/decode paths with __ separator
│   ├── mapping_manager.py  # Thread-safe mapping.json management
│   ├── device.py           # GPU/CPU auto-detection
│   └── exceptions.py       # Custom exceptions
├── gui/                     # PySide6 GUI layer
│   ├── pages/              # Page widgets
│   └── workers/            # QThread workers
└── tests/                   # Unit tests
```

**New Content**:
```markdown
## Project Structure

```
auto_yolo_label/
├── core/                    # Core business logic
│   ├── scanner.py          # Scan site folders
│   ├── sampler.py          # Sample images
│   ├── trainer.py          # YOLO training
│   ├── inferencer.py       # Batch inference
│   ├── restorer.py         # Restore labels
│   └── converter.py        # YOLO txt → VOC xml
├── utils/                   # Utilities
│   ├── path_encoder.py     # Encode/decode paths with __ separator
│   ├── mapping_manager.py  # Thread-safe mapping.json management
│   ├── device.py           # GPU/CPU auto-detection
│   └── exceptions.py       # Custom exceptions
├── gui/                     # PySide6 GUI layer
│   ├── pages/              # Page widgets
│   └── workers/            # QThread workers
├── docs/                    # Documentation (organized)
│   ├── user/               # User guides
│   ├── dev/                # Developer docs
│   └── guides/             # Technical guides
├── tests/                   # Unit tests (9 core tests)
└── config/                  # Configuration
```

**Command**:
```bash
# Replace lines 92-112 in CLAUDE.md with new structure
# (Manual edit or use Edit tool)
```

---

### Task 5.3: Update CLAUDE.md Testing Section

**File**: `CLAUDE.md`

**Section to Update**: Lines 258-272 (Testing Summary)
**Change**: Update test count from 115 to ~85 (9 core tests)
**Update Table**:
```markdown
| Module | Tests | Key Areas |
|--------|-------|-----------|
| PathEncoder | 9 | Encode/decode, special chars |
| MappingManager | 13 | Thread safety, file lock |
| Scanner | 10 | Hidden dir skip, statistics |
| Sampler | 13 | Priority sampling, train/val split |
| Restorer | 10 | Label restoration, formats |
| Trainer | 12 | Config, device/batch auto |
| Inferencer | 12 | Batch inference, progress |
| Converter | 19 | Coordinate precision, XML validity |

**Total**: ~85 tests passing (9 core modules)
```

**Command**: Edit CLAUDE.md to update test count

---

### Task 5.4: Update CLAUDE.md Quick References

**File**: `CLAUDE.md`

**Section to Update**: Lines 351-356 (Quick References)
**Changes**:
```markdown
## Quick References

- Product requirements: `docs/dev/requirement.md`
- Technical spec: `docs/dev/jishukaifawendang.md`
- **Current progress**: `docs/dev/CURRENT_STATE.md`
- User guide: `docs/user/USER_GUIDE.md`
```

**Command**: Edit CLAUDE.md to update documentation paths

---

### Task 5.5: Final Verification

**Command**:
```bash
# 1. Application runs
python main.py &
sleep 3
pkill -f python

# 2. All core tests pass
pytest tests/ -v

# 3. Documentation accessible
test -f docs/user/USER_GUIDE.md
test -f docs/dev/requirement.md
test -f docs/guides/CODE_CONVERSION_RULES.md

# 4. No broken imports
python -c "from core.scanner import Scanner; from utils.mapping_manager import MappingManager; print('All imports OK')"

# Expected: All checks pass
```

**Commit**: Phase 5 Complete - PROJECT COMPLETE
```bash
git add .gitignore CLAUDE.md
git commit -m "Phase 5: Post-cleanup updates - PROJECT COMPLETE

- Update .gitignore with build artifact patterns
- Update CLAUDE.md to reflect new structure
- Update documentation paths to docs/ folder
- Update test count (115 → ~85)
- All verification checks pass
- Application runs normally
- All core tests pass

✅ PROJECT CLEANUP COMPLETE

Disk space saved: ~2.6GB
Test files reduced: 17 → 9
Documentation: Organized in docs/ folder
Build artifacts: Removed
Tools directory: Removed
"
```

**Final Checkpoint**: All verification commands pass?

---

## Summary

**Total Tasks**: 14 tasks across 5 phases
**Estimated Duration**: 16 minutes total
**Risk Level**: Low-Medium (with rollback strategy)

**Success Metrics**:
- ✅ Application runs normally
- ✅ All core tests pass (9 tests)
- ✅ Documentation organized in `docs/` folder
- ✅ No broken imports
- ✅ Disk space saved: ~2.6GB
- ✅ Project structure cleaner

**Rollback Strategy**:
- Each phase has its own commit
- Use `git reset --hard HEAD~1` to rollback one phase
- All removed files listed in design doc for manual restoration

**Execution Approach**: Subagent-Driven Development (single session, frequent commits)

---

## Appendix: Quick Reference Commands

### Verify Application Works
```bash
python main.py &
sleep 3
pkill -f python
```

### Run Core Tests
```bash
pytest tests/ -v
# Expected: 9 tests pass
```

### Check Disk Space
```bash
du -sh . 2>/dev/null | tail -1
```

### List Remaining Tests
```bash
ls tests/test_*.py
# Expected: 9 files
```

### Check Documentation Structure
```bash
find docs/ -name "*.md"
# Expected: 9 files
```

### Verify No Broken Imports
```bash
python -c "from core.scanner import Scanner; from utils.mapping_manager import MappingManager; from gui.app import main; print('OK')"
```

---

**End of Implementation Plan**
