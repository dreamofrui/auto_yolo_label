# Project Cleanup Design Document

**Date**: 2026-03-03
**Author**: Claude Code Assistant
**Status**: Approved

---

## Executive Summary

This document outlines a comprehensive cleanup strategy for the AutoLabeler project to remove unused artifacts, reduce complexity, and improve organization while preserving all essential functionality.

**Impact**:
- Disk space saved: ~2.6GB
- Test files reduced: 17 → 9 (43% reduction)
- Documentation: Organized into structured `docs/` folder
- Build artifacts: Completely removed
- Tools directory: Removed (one-time debugging scripts)

---

## Goals

### Primary Objectives
1. **Free disk space** - Remove build artifacts (2.6GB)
2. **Simplify codebase** - Remove unused tools, tests, and reduce complexity
3. **Improve organization** - Organize scattered documentation into structured folders
4. **Ensure stability** - Preserve all core functionality and essential test coverage

### Success Criteria
- ✅ Application runs normally (`python main.py` launches GUI)
- ✅ Core tests pass (`pytest tests/ -v` - 9 essential tests)
- ✅ All documentation accessible in `docs/` folder
- ✅ No broken imports or missing dependencies
- ✅ Project structure is clean and maintainable

---

## Design Decisions

### Decision 1: Cleanup Scope (Balanced Approach)

**Chosen Approach**: Balanced Cleanup (Approach B)

**Rationale**: Matches user preferences exactly - removes unused artifacts while preserving essential test coverage and all documentation.

**Alternatives Considered**:
- **Conservative**: Keep tools and integration tests (rejected - too much clutter remains)
- **Aggressive**: Remove more tests and consolidate docs (rejected - loses important safety net)

---

### Decision 2: Tools Directory

**Action**: Remove entire `tools/` directory

**Files Removed** (7 files, 56KB):
- `debug_training_data.py` - One-time debugging
- `fix_small_boxes.py` - One-time fix script
- `batch_txt_to_xml.py` - Batch utility (rarely used)
- `diagnose_conversion.py` - One-time diagnosis
- `test_inference.py` - One-time testing
- `disk_usage_analyzer.py` - One-time analysis
- `find_yolo_cache.py` - One-time cache finder

**Rationale**: User confirmed these are one-time debugging scripts no longer needed.

---

### Decision 3: Test Cleanup

**Action**: Keep core tests only (9 files), remove integration and edge-case tests (8 files)

**Tests Removed** (8 files):
- `test_training_integration.py` - Integration test
- `test_inference_separated_storage.py` - Integration test
- `test_small_object_config.py` - Edge case configuration
- `test_conversion_rule.py` - Conversion rule tests
- `test_converter_xml_to_txt.py` - Redundant with test_converter.py
- `test_image_utils.py` - Not core business logic
- `test_home_navigation.py` - GUI test, not business logic

**Tests Kept** (9 files):
- `test_scanner.py` - Scanner core logic
- `test_sampler.py` - Sampler core logic
- `test_trainer.py` - Trainer core logic
- `test_inferencer.py` - Inferencer core logic
- `test_restorer.py` - Restorer core logic
- `test_converter.py` - Converter core logic
- `test_mapping_manager.py` - MappingManager utilities
- `test_path_encoder.py` - PathEncoder utilities
- `test_device.py` - Device detection utilities

**Rationale**: Core tests provide essential coverage for all business logic. Integration and edge-case tests are no longer needed for stable project.

**Test Coverage Impact**:
- Before: 115 tests across 17 files
- After: ~85 tests across 9 files (estimated)
- Coverage: All core modules remain tested

---

### Decision 4: Build Artifacts Removal

**Action**: Remove all build artifacts

**Files/Directories Removed** (~2.6GB):
- `dist/` - 1.4GB built executable
- `build/` - 162MB build intermediates
- `runs/` - 2.6MB training runs history
- `auto_yolo_label.zip` - 2.4GB full project archive
- `tests/105954-32435.zip` - Test data archive
- `tests/use_test/105954-32435.zip` - Duplicate test data archive

**Rationale**: Build artifacts can be regenerated. Archives are redundant with git history.

---

### Decision 5: Documentation Organization

**Action**: Organize all documentation into structured `docs/` folder

**New Structure**:
```
docs/
├── user/                           # User-facing documentation
│   ├── USER_GUIDE.md              # English user guide
│   └── 用户使用手册.md             # Chinese user manual
├── dev/                            # Development documentation
│   ├── requirement.md             # Product requirements
│   ├── jishukaifawendang.md       # Technical design spec
│   ├── CURRENT_STATE.md           # Current progress tracking
│   └── HANDOFF.md                 # Project handoff notes
└── guides/                         # Technical guides
    ├── CODE_CONVERSION_RULES.md   # Conversion rules reference
    ├── SMALL_OBJECT_DETECTION.md  # Small object detection guide
    └── jishukaifawendang_backup.md # Backup of technical spec
```

**Files Moved** (9 files):
- Root .md files → `docs/` subfolders organized by purpose

**Rationale**: Clear separation by audience (users vs developers) and purpose (requirements, guides, status).

---

## New Project Structure

```
auto_yolo_label/
├── core/                    # Core business logic (unchanged)
│   ├── scanner.py
│   ├── sampler.py
│   ├── trainer.py
│   ├── inferencer.py
│   ├── restorer.py
│   └── converter.py
├── gui/                     # GUI components (unchanged)
│   ├── pages/
│   ├── workers/
│   └── widgets/
├── utils/                   # Utilities (unchanged)
│   ├── mapping_manager.py
│   ├── path_encoder.py
│   ├── device.py
│   └── exceptions.py
├── tests/                   # Tests (reduced to 9 core tests)
│   ├── test_scanner.py
│   ├── test_sampler.py
│   ├── test_trainer.py
│   ├── test_inferencer.py
│   ├── test_restorer.py
│   ├── test_converter.py
│   ├── test_mapping_manager.py
│   ├── test_path_encoder.py
│   └── test_device.py
├── docs/                    # Documentation (new organized structure)
│   ├── user/
│   ├── dev/
│   └── guides/
├── config/                  # Configuration (unchanged)
├── main.py                  # Entry point (unchanged)
├── build.py                 # Build script (unchanged)
├── build_exe.spec          # PyInstaller config (unchanged)
├── requirements.txt         # Dependencies (unchanged)
└── CLAUDE.md               # AI assistant guide (needs update)
```

---

## Implementation Strategy

### Phase 1: Preparation (No Risk)
**Duration**: 2 minutes
**Risk**: None

1. Create `docs/` folder structure
2. Move documentation files to new locations
3. Test: All imports still work

**Verification**:
```bash
python main.py  # Should launch GUI
```

---

### Phase 2: Build Artifact Removal (No Risk)
**Duration**: 1 minute
**Risk**: None (can regenerate)

1. Remove `dist/`, `build/`, `runs/` directories
2. Remove `.zip` archive files
3. Test: Application still runs

**Verification**:
```bash
python main.py  # Should launch GUI
```

---

### Phase 3: Tools Removal (Low Risk)
**Duration**: 1 minute
**Risk**: Low (tools not imported)

1. Remove `tools/` directory
2. Test: No imports from tools/

**Verification**:
```bash
# Check no imports from tools
python -c "from utils import mapping_manager, path_encoder, device"
python -c "from gui.app import main"
```

---

### Phase 4: Test Cleanup (Higher Risk)
**Duration**: 2 minutes
**Risk**: Medium (removing tests)

1. Remove integration/edge-case tests (8 files)
2. Run remaining tests: `pytest tests/ -v`
3. Verify: All 9 core tests pass

**Verification**:
```bash
# Run all remaining tests
pytest tests/ -v

# Expected: 9 tests pass (scanner, sampler, trainer, inferencer, restorer, converter, mapping_manager, path_encoder, device)
```

---

### Phase 5: Post-Cleanup Updates (Low Risk)
**Duration**: 5 minutes
**Risk**: Low

1. Update `CLAUDE.md` to reflect new structure
2. Update project structure section
3. Update testing commands section
4. Update documentation references
5. Add `.gitignore` entries for build artifacts

**Verification**:
```bash
python main.py  # Final verification
pytest tests/ -v  # All tests pass
```

---

## Verification Checklist

### After Each Phase
- [ ] Application launches: `python main.py`
- [ ] No import errors in console
- [ ] GUI loads correctly

### After Phase 4 (Test Cleanup)
- [ ] Run: `pytest tests/test_scanner.py -v`
- [ ] Run: `pytest tests/test_sampler.py -v`
- [ ] Run: `pytest tests/test_trainer.py -v`
- [ ] Run: `pytest tests/test_inferencer.py -v`
- [ ] Run: `pytest tests/test_restorer.py -v`
- [ ] Run: `pytest tests/test_converter.py -v`
- [ ] Run: `pytest tests/test_mapping_manager.py -v`
- [ ] Run: `pytest tests/test_path_encoder.py -v`
- [ ] Run: `pytest tests/test_device.py -v`
- [ ] All 9 tests pass: `pytest tests/ -v`

### Final Verification
- [ ] Application runs: `python main.py`
- [ ] All core tests pass: `pytest tests/ -v`
- [ ] Documentation accessible in `docs/` folder
- [ ] No broken imports
- [ ] Project structure is clean

---

## Rollback Plan

### Git Strategy
- Commit after each phase with descriptive message
- If tests fail: `git reset --hard HEAD~1` (rollback one commit)
- Keep list of removed files for 30 days in case manual restoration needed

### Rollback Commands
```bash
# If Phase 1 fails
git reset --hard HEAD

# If Phase 4 fails (tests removed)
git checkout HEAD~1 -- tests/  # Restore test files
pytest tests/ -v  # Verify tests pass
```

---

## Post-Cleanup Updates

### CLAUDE.md Updates Required

**Sections to Update**:
1. **Project Structure** - Update ASCII diagram to reflect new structure
2. **Testing Commands** - Update to reflect 9 core tests
3. **Quick References** - Update documentation paths to `docs/` folder

**New .gitignore Entries**:
```
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

---

## Risk Assessment

| Risk Area | Impact | Mitigation |
|-----------|--------|------------|
| Tools removal | Low | Not imported by core code |
| Test removal | Medium | Keep core tests, Git rollback available |
| Build artifact removal | None | Can regenerate anytime |
| Doc reorganization | Low | Just moving files, not deleting |

---

## Success Metrics

- ✅ Disk space saved: ~2.6GB
- ✅ Test files reduced: 17 → 9 (43% reduction)
- ✅ Documentation organized: 9 files in structured folders
- ✅ Build artifacts removed: 100%
- ✅ Tools directory removed: 100%
- ✅ All core functionality preserved
- ✅ All core tests passing
- ✅ Project structure cleaner and more maintainable

---

## Next Steps

After design approval:
1. Invoke **writing-plans** skill to create detailed implementation plan
2. Execute implementation in phases
3. Update CLAUDE.md to reflect new structure
4. Verify all functionality works

---

## Approval

**Design Status**: ✅ Approved by user (2026-03-03)

**Ready for Implementation**: Yes

---

## Appendix: Files to Remove

### Build Artifacts (2.6GB)
- `dist/` directory
- `build/` directory
- `runs/` directory
- `auto_yolo_label.zip`
- `tests/105954-32435.zip`
- `tests/use_test/105954-32435.zip`

### Tools Directory (56KB)
- `tools/debug_training_data.py`
- `tools/fix_small_boxes.py`
- `tools/batch_txt_to_xml.py`
- `tools/diagnose_conversion.py`
- `tools/test_inference.py`
- `tools/disk_usage_analyzer.py`
- `tools/find_yolo_cache.py`
- `tools/README.md`

### Tests (8 files)
- `tests/test_training_integration.py`
- `tests/test_inference_separated_storage.py`
- `tests/test_small_object_config.py`
- `tests/test_conversion_rule.py`
- `tests/test_converter_xml_to_txt.py`
- `tests/test_image_utils.py`
- `tests/test_home_navigation.py`
- `tests/105954-32435.zip`
- `tests/use_test/105954-32435.zip`

---

## Appendix: Documentation File Moves

### Move to docs/user/
- `USER_GUIDE.md` → `docs/user/USER_GUIDE.md`
- `用户使用手册.md` → `docs/user/用户使用手册.md`

### Move to docs/dev/
- `requirement.md` → `docs/dev/requirement.md`
- `jishukaifawendang.md` → `docs/dev/jishukaifawendang.md`
- `CURRENT_STATE.md` → `docs/dev/CURRENT_STATE.md`
- `HANDOFF.md` → `docs/dev/HANDOFF.md`

### Move to docs/guides/
- `CODE_CONVERSION_RULES.md` → `docs/guides/CODE_CONVERSION_RULES.md`
- `SMALL_OBJECT_DETECTION.md` → `docs/guides/SMALL_OBJECT_DETECTION.md`
- `jishukaifawendang_backup.md` → `docs/guides/jishukaifawendang_backup.md`

---

**End of Design Document**
