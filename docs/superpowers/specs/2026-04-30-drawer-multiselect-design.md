# Drawer & Multi-select Tag Filter Enhancement Design

**Date:** 2026-04-30
**Status:** Approved

## Overview

Two UI enhancements to the existing HTMX skills web app:
1. The detail side panel becomes a slide-in drawer overlay that closes when the user clicks outside it.
2. The tag filter supports selecting multiple tags simultaneously (AND logic) with a clear-all button.

## Enhancement 1: Drawer Overlay

### Layout Change

The current two-column flex layout (grid + fixed right panel) is replaced with a single full-width column for the skill grid. The drawer is a fixed overlay — it does not push the grid content.

### HTML Structure (base.html)

Two new elements added outside the main layout div:

**Backdrop:**
```html
<div id="drawer-backdrop"
  class="fixed inset-0 bg-black/40 z-20 hidden"
  hx-get="/ui/empty"
  hx-trigger="click"
  hx-target="#drawer-content">
</div>
```
- `hidden` by default; shown (via JS `classList.remove('hidden')`) when drawer opens
- Full-screen click target: clicking it triggers HTMX to swap empty content into the drawer, then `htmx:afterSwap` closes the drawer

**Drawer:**
```html
<div id="drawer"
  class="fixed top-0 right-0 h-full w-96 bg-white shadow-2xl z-30
         transform translate-x-full transition-transform duration-300 overflow-y-auto">
  <div id="drawer-content"></div>
</div>
```
- Off-screen by default (`translate-x-full`); slides in via `translate-x-0`
- `#drawer-content` is the HTMX swap target (replaces the old `#detail-panel`)

### Open/Close Logic (JS in base.html)

```javascript
function openDrawer() {
  document.getElementById('drawer').classList.replace('translate-x-full', 'translate-x-0');
  document.getElementById('drawer-backdrop').classList.remove('hidden');
}

function closeDrawer() {
  document.getElementById('drawer').classList.replace('translate-x-0', 'translate-x-full');
  document.getElementById('drawer-backdrop').classList.add('hidden');
}

document.addEventListener('htmx:afterSwap', (e) => {
  if (e.detail.target.id === 'drawer-content') {
    if (e.detail.target.innerHTML.trim() === '') {
      closeDrawer();
    } else {
      openDrawer();
    }
  }
});
```

### Skill Card Change

`hx-target` changes from `#detail-panel` to `#drawer-content`. No other changes to `skill_card.html`.

### Close Button in skill_detail.html

The close button already points to `hx-get="/ui/empty" hx-target="#detail-panel"` — update target to `#drawer-content`. The `htmx:afterSwap` listener handles the rest.

### Removed

- The `<div id="detail-panel">` right column is removed from the flex layout.

---

## Enhancement 2: Multi-select Tag Filter (AND logic)

### Backend (ui.py)

`skill_grid` route signature changes:
```python
# Before
tag: Optional[str] = None

# After
tags: list[str] = Query(default=[])
```

Filter logic changes to require ALL selected tags (AND):
```python
for t in tags:
    alias = aliased(Tag)
    query = query.join(alias, Package.id == alias.package_id).filter(alias.tag_name == t)
query = query.distinct()
```

### Frontend (base.html)

Selected tags tracked in a JS `Set`:
```javascript
const selectedTags = new Set();
```

**Tag pill click** (`selectTag(tag)`):
- Toggles tag in/out of `selectedTags`
- Updates pill styling: active pills get indigo background, inactive get white
- Shows/hides the "Clear filters" button based on `selectedTags.size > 0`
- Regenerates hidden `<input name="tag">` elements in `#tag-inputs` (one per selected tag)
- Fires `htmx.ajax('GET', '/ui/skills', { values: { search, tag: [...selectedTags] } })`

**Hidden inputs container** (replaces the single `<input type="hidden" name="tag">`):
```html
<div id="tag-inputs"></div>
```
Populated by JS before each request.

**Clear button** (shown only when tags are selected):
```html
<button id="clear-tags" class="hidden ..." onclick="clearTags()">Clear filters</button>
```

`clearTags()` empties `selectedTags`, resets all pill styles, clears `#tag-inputs`, hides the clear button, and fires a grid refresh with no tag filters.

### URL Query Params

Multiple same-key params: `GET /ui/skills?tag=copilot&tag=review`  
FastAPI's `Query(default=[])` handles this natively — no other route changes needed.

---

## Files Changed

| File | Change |
|------|--------|
| `server/app/routers/ui.py` | `tag: Optional[str]` → `tags: list[str] = Query(default=[])`, AND filter logic with aliased joins |
| `server/app/templates/base.html` | Remove right column, add drawer + backdrop, replace single-tag JS with multi-tag Set logic, add clear button |
| `server/app/templates/partials/skill_card.html` | `hx-target="#detail-panel"` → `hx-target="#drawer-content"` |
| `server/app/templates/partials/skill_detail.html` | Close button target: `#detail-panel` → `#drawer-content` |
| `server/tests/test_ui.py` | Update single-tag filter test to use `?tag=X`, add `?tag=X&tag=Y` AND test (only packages with both tags returned), add `?tag=` (empty) test confirming all packages returned |
