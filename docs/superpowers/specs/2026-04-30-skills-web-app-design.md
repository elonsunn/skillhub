# Skills Web App Design

**Date:** 2026-04-30
**Status:** Approved

## Overview

A server-rendered web UI for browsing the SkillHub package registry. Built with HTMX + Jinja2 + Tailwind CDN, served directly by the existing FastAPI server. The existing `/api/packages` JSON endpoints are untouched.

## Architecture

New files are additive — no existing files are modified except `main.py` (two lines: mount static files, include ui router).

```
server/
  app/
    routers/
      ui.py                  ← all UI routes
    templates/
      base.html              ← full page shell (Tailwind CDN, HTMX CDN, two-column layout)
      partials/
        skill_grid.html      ← skill cards grid (swappable fragment)
        skill_card.html      ← single card component (included by skill_grid)
        skill_detail.html    ← side panel content (swappable fragment)
    static/
      style.css              ← minimal custom CSS if needed
```

## Routes

| Route | Returns | Triggered by |
|---|---|---|
| `GET /` | Full page (`base.html` + initial skill grid) | Browser navigation |
| `GET /ui/skills` | `skill_grid.html` fragment | Search input or tag filter click |
| `GET /ui/skills/{name}` | `skill_detail.html` fragment | Skill card click |

All UI routes call the existing database query logic directly (same queries as the JSON API) rather than calling themselves over HTTP.

## HTMX Wiring

- **Search box**: `hx-get="/ui/skills" hx-trigger="input delay:300ms" hx-include="[name='search'],[name='tag']"` — swaps `#skill-grid`
- **Tag pills**: each pill is `hx-get="/ui/skills" hx-vals='{"tag": "<tagname>"}' hx-include="[name='search']" hx-target="#skill-grid"`; active tag state stored in a hidden `<input name="tag">` that is updated on click; clicking the active tag clears it (sends empty tag value)
- **Skill card**: `hx-get="/ui/skills/{name}" hx-target="#detail-panel"` — swaps the right panel in
- **Close button**: swaps an empty fragment into `#detail-panel` to hide it

## Layout

Two-column flex layout:
- **Left column** (~60%): sticky toolbar (search + tag pills) above a scrollable responsive skill grid (2–3 columns wide, 1 on mobile)
- **Right column** (~40%): detail panel, hidden until a card is clicked

## Components

### Skill Card
- Name, author, latest version badge
- Tag pills
- One-line description (truncated with ellipsis)

### Tag Filter
- All unique tags collected from all packages at page load, rendered as clickable pills above the grid
- One active at a time; re-fetches grid on selection/deselection

### Detail Panel
- Name, author, latest version badge
- Full description
- CLI hint: `skillhub pull <name>` in a styled `<pre>` block with a copy-to-clipboard button
- Version history table: version, commit message, date — newest first

## Dependencies Added

- `jinja2` — template rendering (add to `requirements.txt`)
- `python-multipart` — already present (used by push endpoint)
- HTMX and Tailwind loaded via CDN (no build step)
