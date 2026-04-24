# Development TODO

This file tracks known issues and pending tasks for the EntangledPdf project.

## Active Issues

### Issue 1: E2E Test Infrastructure - Venv Path ✅ RESOLVED

**Status:** Fixed and merged to `main`  
**Date:** 2026-04-23

**Problem:**
E2E tests failed to start because `tests/e2e/global-setup.ts` used system Python (`python3`) instead of the project venv. System Python doesn't have dependencies (uvicorn, fastapi) installed.

**Solution:**
1. Changed venv location from `bin/` to `.venv/` (avoids conflicts with `scripts/` directory)
2. Updated `install.sh` to create venv at `.venv/`
3. Updated `tests/e2e/global-setup.ts` to use `.venv/bin/python`
4. Updated CI workflow to use `.venv/bin/python` and `.venv/bin/pip`
5. Moved `bin/entangle-pdf-test-cleanup` → `scripts/entangle-pdf-test-cleanup`

**Files Changed:**
- `install.sh` - Creates venv at `.venv/`
- `.gitignore` - Ignores `.venv/` directory
- `tests/e2e/global-setup.ts` - Uses venv Python
- `.github/workflows/ci.yml` - Uses venv Python for all test steps
- `scripts/entangle-pdf-test-cleanup` - Moved from `bin/`
- `agent_docs/e2e-infrastructure-issue.md` - Documentation

**Verification:** ✅ CI passing on all jobs

---

### Issue 2: E2E Test - PDF Loading ✅ RESOLVED

**Status:** Fixed and merged to `main`  
**Date:** 2026-04-23

**Problem:**
E2E tests for inverse search initially failed because the PDF wasn't being loaded. Tests showed "No PDF Loaded" page instead of the rendered PDF.

**Root Cause:**
The issue was actually due to the venv infrastructure problem (Issue #1), not the PDF loading itself. Once the venv fix was applied, all E2E tests began working correctly.

**Resolution:**
All E2E tests now passing:
- ✅ `viewer includes inverse search UI elements`
- ✅ `long-press shows inverse search tooltip with confirmation`
- ✅ `long-press tooltip can be dismissed with Escape key`
- ✅ `tooltip can be dismissed and re-shown`
- ✅ `ctrl+click shows inverse search tooltip with confirmation`
- ✅ `cmd+click (macOS) shows inverse search tooltip`
- ✅ `regular click does not show inverse search tooltip`
- ✅ `inverse search is enabled on server`
- ✅ `inverse search is disabled`
- ✅ `inverse search is disabled in HTTP mode`

---

### Issue 3: Ctrl+Click Implementation - ✅ COMPLETE

**Status:** Merged to `main`  
**Date:** 2026-04-24

**Implementation:**
- Added `onCtrlClick` callback to `input-handler.ts`
- Added `handleCtrlClick` function to `viewer.ts`
- **Fixed iPad/Magic Keyboard reliability** by detecting Ctrl on `mousedown` instead of `click`
  - Tracks modifier key state across mouse events to avoid Safari/iPadOS click event issues
  - Integrates with long-press detector (shares mousedown/mouseup events)
  - Works reliably on iPad with Magic Keyboard trackpad
- Shows confirmation tooltip, sends WebSocket message on confirm
- Unit tests for handler infrastructure
- E2E tests for Ctrl+Click, Cmd+Click, and regular click (all passing)

**Files Changed:**
- `static/input-handler.ts` - Core Ctrl+Click detection (mousedown-based)
- `static/viewer.ts` - Tooltip handling
- `tests/js/input-handler.test.ts` - Unit tests
- `tests/e2e/inverse-search.spec.ts` - E2E tests for Ctrl+Click, Cmd+Click

**Merge Date:** 2026-04-24

---

## Completed Issues

### Documentation Migration

**Date:** 2026-04-23  
**Status:** ✅ Complete

**Action:** Renamed `docs/` folder to `agent_docs/` to align with OpenCode conventions.

---

## Future Improvements

### Testing

- [x] ~~Add CI check that verifies `./.venv/bin/python` exists after install~~ (Resolved)
- [ ] Add E2E test for PDF switching between documents
- [ ] Add visual regression tests for marker rendering

### Documentation

- [x] ~~Update README.md with new venv usage pattern~~ (Resolved: uses `.venv/`)
- [x] ~~Update AGENTS.md install commands~~ (Resolved)
- [ ] Add troubleshooting guide for modifier key issues on mobile devices

### Code Quality

- [x] ~~Consider adding retry logic to E2E PDF loading~~ (Resolved: Was venv issue)
- [ ] Add diagnostic mode for inverse search (log all mouse events)
- [x] ~~Standardize all shell scripts to use venv Python~~ (Resolved)

---

## Recently Completed (2026-04-24)

### Ctrl+Click Inverse Search Feature
**Status:** ✅ **MERGED TO MAIN**

Full implementation of Ctrl+Click (Linux/Windows) and Cmd+Click (macOS) for inverse search:

1. **Infrastructure Fixes**
   - Fixed venv path (`.venv/` instead of `bin/`)
   - Moved test cleanup script to `scripts/`
   - Updated CI workflow to use venv Python consistently

2. **Core Implementation**
   - Detects Ctrl/Cmd modifier on `mousedown` (more reliable than `click`)
   - Tracks state across mouse events
   - Integrates seamlessly with existing long-press detector
   - Shows confirmation tooltip with "Go to Source?" prompt
   - Sends WebSocket message to trigger inverse search

3. **Cross-Platform Support**
   - Desktop (Ctrl+Click): Works on all browsers
   - macOS (Cmd+Click): Works on Safari, Chrome, Firefox
   - iPad + Magic Keyboard: **Fixed intermittent behavior** by using mousedown detection
   - Mobile: Long-press continues to work as primary method

4. **Tests**
   - Unit tests: 210 passed
   - E2E tests: 10 passed (all inverse search scenarios)
   - CI: All jobs passing

**Files Modified:**
- `static/input-handler.ts` - Core detection logic
- `static/viewer.ts` - Tooltip integration
- `tests/e2e/inverse-search.spec.ts` - E2E tests
- `tests/js/input-handler.test.ts` - Unit tests
- `install.sh` - Venv creation
- `.github/workflows/ci.yml` - CI updates
- `agent_docs/TODO.md` - This file

---

## Legend

- ✅ Complete
- ⚠️ Blocked/Needs Attention
- 🔄 In Progress
- ⏸️ On Hold
