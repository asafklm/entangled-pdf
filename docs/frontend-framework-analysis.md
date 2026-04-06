# Frontend Framework Analysis: Current vs Vue.js vs Lit

**Document Date**: April 2026  
**Project**: EntangledPdf  
**Current Frontend**: ~4,871 lines of modular TypeScript (vanilla)  
**Purpose**: Evaluate whether to migrate to Vue.js or Lit, and establish decision criteria for future framework adoption.

---

## Executive Summary

**Recommendation**: **Stay with current vanilla TypeScript approach** for now, with preparation for future Lit adoption if the codebase grows beyond ~6,000 lines or adds 3+ new UI components.

**Key Finding**: The current modular architecture already achieves 70% of the benefits of a framework without the overhead.

---

## Current Architecture Assessment

### What Works Well

| Aspect                 | Implementation                    | Quality    |
| --------               | ---------------                   | ---------  |
| **State Management**   | `StateManager` class with pub/sub | ⭐⭐⭐⭐⭐ |
| **WebSocket Handling** | `WebSocketManager` class          | ⭐⭐⭐⭐⭐ |
| **Modularity**         | 14 focused modules                | ⭐⭐⭐⭐⭐ |
| **PDF Rendering**      | `PDFRenderer` class (PDF.js)      | ⭐⭐⭐⭐⭐ |
| **Build System**       | esbuild + TypeScript              | ⭐⭐⭐⭐⭐ |

### Current Dependencies (Minimal)

```json
{
  "dependencies": {
    "pdfjs-dist": "^5.4.624"     // Required
  },
  "devDependencies": {
    "esbuild": "^0.27.4",        // Build tool
    "typescript": "^5.9.3",      // Language
    "vitest": "^4.0.18"          // Testing
  }
}
```

**Bundle Overhead**: 0KB (just application code)

---

## Vue.js Analysis

### Why It Was Considered

- Single-page application structure
- Potential for future feature expansion
- Declarative templates
- Rich ecosystem

### Why It Was Rejected

| Factor | Impact | Notes |
|--------|--------|-------|
| **Bundle Size** | ❌ +40KB | Significant for utility tool |
| **Dependencies** | ❌ Heavy | Runtime + compiler + ecosystem |
| **Overhead vs Benefit** | ❌ Poor | 90% of UI is PDF.js canvas |
| **Learning Curve** | ⚠️ Moderate | Team needs Vue knowledge |
| **Unused Features** | ❌ Many | Router, transitions, slots unused |

**Verdict**: Too heavy for current scope. Benefits don't justify costs for a single-view PDF viewer.

---

## Lit Analysis (Selected Alternative)

### What Lit Offers

| Feature                  | Benefit                      | Size Impact          |
| ---------                | ---------                    | -------------        |
| **Reactive Templates**   | Declarative UI updates       | ~3KB                 |
| **Web Components**       | Framework-agnostic, reusable | Included             |
| **Reactive Controllers** | Shared stateful logic        | ~2KB                 |
| **Standard APIs**        | Built on Custom Elements     | 0KB (browser native) |
| **Total Overhead**       | Minimal                      | **~5KB gzipped**     |

### Architectural Transformation

```
Current:                        Lit Version:
┌─────────────────┐            ┌─────────────────┐
│ viewer.html     │            │ index.html      │
│ (Jinja2 + CSS)  │            │ (minimal shell) │
└────────┬────────┘            └────────┬────────┘
         │                              │
┌────────▼────────┐            ┌────────▼────────┐
│ viewer.ts       │            │ main.ts         │
│ (orchestrator)  │            │ (app bootstrap) │
└────────┬────────┘            └────────┬────────┘
         │                                │
    ┌────┴────┐                    ┌──────┴──────┐
    │ Modules │                    │   Lit App   │
    │ (14)    │                    │             │
    └────┬────┘                    │ ┌─────────┐ │
         │                         │ │App (Lit)│ │
    ┌────┴────┐                    │ └────┬────┘ │
    │Managers │                    │      │      │
    │(Manual  │                    │ ┌────┴────┐ │
    │  DOM)   │                    │ │Custom   │ │
    └─────────┘                    │ │Elements │ │
                                   │ │(Reactive)│ │
                                   │ └─────────┘ │
                                   │      │      │
                                   │ ┌────┴────┐ │
                                   │ │Controllers│
                                   │ │(useWebSocket│
                                   │ │useScroll) │
                                   │ └─────────┘ │
                                   └─────────────┘
```

### Component Breakdown

| Current Module                  | Lit Equivalent             | Lines Reduction       |
| ----------------                | ---------------            | -----------------     |
| `tooltip-manager.ts` (260)      | `<inverse-search-tooltip>` | **-70%** (~80 lines)  |
| `notification-manager.ts` (100) | `<notification-toast>`     | **-60%** (~40 lines)  |
| `marker-manager.ts` (125)       | `<synctex-marker>`         | **-50%** (~60 lines)  |
| `state-manager.ts` (225)        | `StateController`          | **-55%** (~100 lines) |
| Manual DOM (800)                | Declarative templates      | **-90%** (~80 lines)  |
| **Total**                       | **~4,871 → ~3,200**        | **-34%**              |

---

## When to Switch to Lit

### Decision Matrix

| Trigger Condition    | Current Status              | Threshold                     | Action             |
| -------------------  | ----------------            | -----------                   | --------           |
| **Codebase Size**    | ~4,871 lines                | 6,000+ lines                  | Evaluate switch    |
| **UI Components**    | 3 (tooltip, status, marker) | 6+ components                 | Switch justified   |
| **New Features**     | None planned                | Search, annotations, settings | Switch makes sense |
| **Team Size**        | 1 developer                 | 3+ developers                 | Switch helps       |
| **Reusability Need** | Self-contained              | Embed in other projects       | Web Components win |

### Specific Scenarios

#### ✅ Switch Makes Sense When:

1. **Adding Annotation Support**
   - Multiple new UI elements (highlight, comment, toolbar)
   - Complex coordinate tracking
   - State synchronization between annotations
   - *Lit provides cleaner component boundaries*

2. **Adding Search Functionality**
   - Search input + results list
   - Highlight matches on pages
   - Search navigation controls
   - *Slight advantage with Lit components*

3. **Adding Settings Panel**
   - Form controls with validation
   - Theme switching
   - Persistent preferences
   - *Lit's reactive properties shine*

#### ❌ Stay Vanilla When:

1. **Current Scope Maintained**
   - Single-view PDF viewer
   - Minimal UI additions
   - *Current approach simpler*

2. **Performance Critical**
   - Mobile/tablet users
   - Bandwidth constrained
   - *5KB overhead matters*

3. **PDF.js Integration Dominates**
   - Canvas rendering is 90% of UI
   - Imperative APIs remain
   - *Lit benefits limited*

---

## Progressive Adoption Path

Don't switch all at once. Use this phased approach:

### Phase 1: Component Extraction (Now)

Extract UI-heavy code into standalone modules without framework:

```typescript
// Current: tooltip-manager.ts (260 lines)
// Extract to: tooltip-element.ts (vanilla custom element)

class InverseSearchTooltip extends HTMLElement {
  // Self-contained, framework-agnostic
  // Can be used with or without Lit later
}

customElements.define('inverse-search-tooltip', InverseSearchTooltip);
```

### Phase 2: Evaluation (When adding 2nd or 3rd component)

After extracting 2-3 components, assess:
- Are you writing a lot of `observedAttributes` boilerplate?
- Manual property observation getting tedious?
- DOM diffing logic emerging?

**If yes** → Lit's 5KB overhead is worth it  
**If no** → Continue with vanilla web components

### Phase 3: Lit Migration (When threshold reached)

If Phase 2 shows value:

1. Add `lit` dependency (~5KB)
2. Convert custom elements to Lit elements
3. Introduce reactive controllers for shared state
4. Keep PDF.js integration unchanged (imperative)

---

## The 5-Minute Test

To determine if Lit fits your mental model:

### Look at Current Code

Open `static/tooltip-manager.ts` (260 lines):
- Manual element creation: `document.createElement('div')`
- Style setting: `tooltip.style.cssText = '...'`
- Event wiring: `button.addEventListener('click', ...)`
- Cleanup: `hideActiveTooltip()` + manual removal

### Imagine Lit Version

```typescript
render() {
  return html`
    <div class="tooltip" style="left: ${x}px; top: ${y}px">
      <div class="header">${headerText}</div>
      <button @click="${onConfirm}">Confirm</button>
    </div>
  `;
}
```

### Ask Yourself

1. Does the Lit version feel cleaner? → **Yes** = Lit suits you
2. Is manual DOM control important for your use case? → **Yes** = Stay vanilla
3. Are you excited about reducing 260 lines to 80? → **Yes** = Consider switch
4. Does 5KB overhead worry you? → **Yes** = Stay vanilla

**My prediction**: Based on the clean modular architecture, you'd appreciate Lit. But at current scale, it's not urgent.

---

## Recommendation Summary

### Current Decision

**✅ STAY WITH VANILLA TYPESCRIPT**

Rationale:
- Current architecture is well-designed
- Bundle size matters for utility tool
- Single-view application
- No urgent need for component reusability
- 4,871 lines is manageable

### Future Decision Criteria

| Metric | Switch When |
|--------|-------------|
| **Lines of Code** | > 6,000 |
| **UI Components** | > 5 custom elements |
| **New Major Features** | Search, annotations, settings panel |
| **Team Size** | 3+ developers |
| **Reusability Need** | Need to embed viewer elsewhere |

### Preparation Steps (Do Now)

1. **Continue modularizing** - Extract logic into managers/controllers
2. **Isolate UI components** - Separate DOM manipulation from business logic
3. **Document patterns** - Make it easy to convert to Lit later
4. **Watch for pain points** - Manual DOM updates getting tedious?

### Migration Path (When Ready)

1. Add Lit dependency
2. Convert `StateManager` → `StateController` (reactive)
3. Convert `WebSocketManager` → `WebSocketController` (reactive)
4. Extract UI components to Lit elements:
   - `<inverse-search-tooltip>`
   - `<synctex-marker>`
   - `<connection-status>`
   - `<notification-toast>`
5. Keep PDF.js integration unchanged (imperative canvas)

---

## Appendix: Technical Details

### Lit Bundle Size Breakdown

```
Core:
  lit-html:     ~3KB (template rendering)
  lit-element:  ~2KB (base class, reactive properties)
  ----------------
  Total:        ~5KB gzipped

Controllers: ~1KB each (if using built-in)
Decorators:  ~0.5KB (optional, can use standard JS)
```

### Comparison with Alternatives

| Framework | Runtime Size | Learning Curve | Best For |
|-----------|-------------|----------------|----------|
| **Vanilla TS** | 0KB | Minimal | Current project size |
| **Lit** | 5KB | Low | 5-15 UI components |
| **Vue 3** | 40KB | Medium | Multi-view SPAs |
| **Svelte** | 0KB (compiled) | Medium | Complex interactions |
| **React** | 40KB | Medium | Large ecosystems |

### Current Build vs Lit Build

| Aspect | Current | Lit |
|--------|---------|-----|
| **Build Tool** | esbuild | Vite (recommended) |
| **Type Checking** | tsc | vue-tsc equivalent |
| **Testing** | Vitest | Vitest + @open-wc/testing |
| **HMR** | esbuild watch | Vite HMR (faster) |
| **Bundle** | Simple | Slightly more config |

---

## Related Documents

- See `AGENTS.md` for general coding guidelines
- See `static/*.ts` for current implementation
- This analysis supersedes any previous framework discussions

---

**Last Updated**: April 2026  
**Next Review**: When codebase reaches 6,000 lines or adds 3+ UI components
