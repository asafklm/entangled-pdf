# Development TODO

This file tracks known issues and pending tasks for the EntangledPdf project.

## Active Issues

### Issue 1: E2E Test Infrastructure - Venv Path ✅ RESOLVED

**Status:** Fixed in `fix/e2e-venv-path` branch  
**Date:** 2026-04-23

**Problem:**
E2E tests failed to start because `tests/e2e/global-setup.ts` used system Python (`python3`) instead of the project venv. System Python doesn't have dependencies (uvicorn, fastapi) installed.

**Solution:**
1. Updated `install.sh` to always create a venv at `./bin/` (committed)
2. Updated `tests/e2e/global-setup.ts` to use `./bin/python` (committed)

**Files Changed:**
- `install.sh` - Creates venv consistently
- `tests/e2e/global-setup.ts` - Uses venv Python
- `agent_docs/e2e-infrastructure-issue.md` - Documentation

**Verification:**
```bash
# Test after merge
npm run test:e2e -- tests/e2e/inverse-search.spec.ts
```

---

### Issue 2: E2E Test - PDF Loading Not Working ⚠️ DISCOVERED

**Status:** Discovered during venv fix testing  
**Date:** 2026-04-23

**Problem:**
E2E tests for inverse search fail because the PDF isn't being loaded via the `/api/load-pdf` API call. Tests show "No PDF Loaded" page instead of the rendered PDF.

**Evidence:**
```
- generic [ref=e2]:
  - heading "No PDF Loaded" [level=2] [ref=e3]
  - paragraph [ref=e4]:
    - text: Use
    - code [ref=e5]: entangle-pdf sync <filename>
    - text: to load a PDF file.
```

**Affected Tests:**
- `viewer includes inverse search UI elements`
- `long-press shows inverse search tooltip with confirmation`
- `long-press tooltip can be dismissed with Escape key`
- `tooltip can be dismissed and re-shown`
- (New tests) `ctrl+click shows inverse search tooltip with confirmation`
- (New tests) `cmd+click (macOS) shows inverse search tooltip`
- (New tests) `regular click does not show inverse search tooltip`

**Suspected Cause:**
The `/api/load-pdf` API call in the test setup may be failing silently, or the PDF path resolution isn't working correctly in the test environment.

**Next Steps:**
1. Add debug logging to verify API calls are succeeding
2. Check if `EXAMPLE_PDF` path is correct in E2E context
3. Verify the API response status and content
4. Check server logs for PDF loading errors

**Priority:** Medium (blocking new feature E2E tests)

---

### Issue 3: Ctrl+Click Implementation - Ready for Integration ✅ IMPLEMENTED

**Status:** Implemented in `feature/ctrl_click_inverse_search` branch  
**Date:** 2026-04-23

**Implementation:**
- Added `onCtrlClick` callback to `input-handler.ts`
- Added `handleCtrlClick` function to `viewer.ts`
- Detects Ctrl key (Linux/Windows) or Cmd key (macOS)
- Shows confirmation tooltip, sends WebSocket message on confirm
- Unit tests for handler infrastructure
- E2E tests for Ctrl+Click, Cmd+Click, and regular click

**Blocked By:**
- Issue #1 (venv path) - Needs E2E test infrastructure fix
- Issue #2 (PDF loading) - E2E tests fail due to PDF not loading

**Merge Order:**
1. Merge `fix/e2e-venv-path` to `main`
2. Merge `fix/e2e-venv-path` to `feature/ctrl_click_inverse_search`
3. Fix Issue #2 (PDF loading)
4. Verify all E2E tests pass
5. Merge `feature/ctrl_click_inverse_search` to `main`

---

## Completed Issues

### Documentation Migration

**Date:** 2026-04-23  
**Status:** ✅ Complete

**Action:** Renamed `docs/` folder to `agent_docs/` to align with OpenCode conventions.

---

## Future Improvements

### Testing

- [ ] Add CI check that verifies `./bin/python` exists after install
- [ ] Add E2E test for PDF switching between documents
- [ ] Add visual regression tests for marker rendering

### Documentation

- [ ] Update README.md with new `./bin/entangle-pdf` usage pattern
- [ ] Update AGENTS.md install commands to use `./bin/` prefix
- [ ] Add troubleshooting guide for "No PDF Loaded" errors

### Code Quality

- [ ] Consider adding retry logic to E2E PDF loading
- [ ] Add more debug logging to E2E test failures
- [ ] Standardize all shell scripts to use venv Python

---

## Legend

- ✅ Complete
- ⚠️ Blocked/Needs Attention
- 🔄 In Progress
- ⏸️ On Hold
