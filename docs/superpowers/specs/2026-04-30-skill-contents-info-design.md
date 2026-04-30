# Skill Contents, Info Command & Scope Simplification — Design

## Goal

Surface what's inside a skill package (its `including` list) in both the web UI drawer and a new CLI `info` command; simplify the YAML scope model to `including`-only; make `init` smarter by pre-filling `including` from the existing config directory structure.

## Architecture

The `including` list from `skillhub.yaml` is sent as `contents` in push metadata, stored as a JSON text column on the `Version` DB record, and returned per-version in `GET /api/packages/{name}`. The web UI drawer gains a Contents section with HTMX-driven version switching. The CLI gains a `skillhub info` command that calls the same API.

## Tech Stack

FastAPI + SQLAlchemy (server), Click (CLI), HTMX + Jinja2 + Tailwind (web UI), SQLite.

---

## Section 1 — YAML & Packaging Simplification

### YAML template changes (`init`)
- Remove `excluding` field entirely.
- Simplify `ignore` to three entries only: `.env`, `*.env`, `config.json`.
- Remove the "Choose only one mode" comment block — `including` is the only scope mechanism.

### `packaging.py` changes
- Remove the `if including and excluding` mutual-exclusion guard.
- Remove the entire `excluding` branch from `build_zip`. The logic becomes:
  - If `including` is non-empty: package only those paths.
  - If `including` is empty: package everything under `config_dir` (minus `ignore`).

### Backward compatibility
Existing `skillhub.yaml` files with `excluding` will cause a `KeyError`-safe no-op (the key is simply absent from new code). If a user has an old yaml with `excluding`, `build` will silently ignore it — no crash, but no exclusion. This is acceptable for an internal tool.

---

## Section 2 — `init` Command: Auto-Populate `including`

### Config dir detection (unchanged)
- Check `.github/` → if exists, use it.
- Else check `.claude/` → if exists, use it.
- Else create `.github/`.

### Scanning for `including`

After resolving `config_dir`, scan it to build the `including` list:

```
For each top-level entry E in config_dir (sorted, excluding "skillhub.yaml"):
  If E is a file  → add "E.name" to including
  If E is a dir   → for each immediate child C of E (sorted):
                      add "E.name/C.name" to including
```

Example: `.github/` contains `skills/skilla/`, `skills/skillb/`, `agents/my-agent/`, `SETUP.md`:
```yaml
including:
  - agents/my-agent
  - skills/skilla
  - skills/skillb
  - SETUP.md
```

If `config_dir` is empty (freshly created), `including: []`.

### Generated template (new)

```yaml
name: my-skill-package
version: 1.0.0
description: Describe your skill package
author: your-name
tags:
  - skill
  - automation
server: http://localhost:8000

including:
  - skills/my-skill   # (pre-filled from scan, or [] if nothing found)

ignore:
  - .env
  - "*.env"
  - config.json
```

---

## Section 3 — Storing `contents` Per Version

### DB: new column on `Version`

Add `contents = Column(Text, nullable=True)` to the `Version` model. Stores a JSON array, e.g. `'["skills/skilla", "agents/my-agent"]'`. NULL for versions pushed before this change.

### Migration in `init_db()`

```python
from sqlalchemy import text

def init_db():
    os.makedirs("data", exist_ok=True)
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        cols = [r[1] for r in conn.execute(text("PRAGMA table_info(versions)"))]
        if "contents" not in cols:
            conn.execute(text("ALTER TABLE versions ADD COLUMN contents TEXT"))
            conn.commit()
```

### CLI push: send `contents` in metadata

In `push.py`, add to the metadata dict:
```python
"contents": config.get("including", []),
```

### Server: accept and store `contents`

In `packages.py` `push_package`, read from metadata:
```python
import json
contents_raw = meta.get("contents", [])
contents_json = json.dumps(contents_raw)
```
Store on `VersionRecord(... contents=contents_json)`.

### API response: `contents` per version

In `get_package`, include `contents` in each version dict:
```python
"contents": json.loads(v.contents) if v.contents else [],
```

---

## Section 4 — `info` CLI Command

### New file: `cli/skillhub/commands/info.py`

```
skillhub info <name>                   # shows latest version's contents
skillhub info <name> --version 1.2.0   # shows that version's contents
```

Calls `GET /api/packages/{name}` (existing `api.get_package`). Selects the target version from the response. Output format:

```
name:        my-skill
description: A great skill
author:      alice
tags:        copilot, review

version:     1.2.0
contents:
  skills/skilla
  skills/skillb
  agents/my-agent

version history:
  1.2.0  added formatter   2026-04-30
  1.1.0  initial release   2026-04-15
```

If `--version` is specified but not found: exit with error "Version X not found for package Y".
If package not found: exit with error "Package Y not found".
If `contents` is empty: print "  (no contents recorded)" under the contents header.

### Register in `cli.py`

```python
from skillhub.commands.info import info
cli.add_command(info)
```

---

## Section 5 — Web UI: Contents in Skill Detail Drawer

### New route: `GET /ui/skills/{name}/{version}/contents`

Returns an HTML fragment (new partial `partials/skill_version_contents.html`) containing the contents list for that specific version. Returns 404 if package or version not found.

### Updated `skill_detail.html`

Add a "Contents" section between the description and the CLI pull hint:

```html
<div class="mb-6">
  <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Contents</p>
  <div id="version-contents">
    {% include "partials/skill_version_contents.html" %}
  </div>
</div>
```

Each version row in the history table becomes clickable:
```html
<tr class="... cursor-pointer"
    hx-get="/ui/skills/{{ pkg.name }}/{{ v.version }}/contents"
    hx-target="#version-contents"
    hx-trigger="click">
```

### New partial: `partials/skill_version_contents.html`

```html
{% if contents %}
<ul class="space-y-1">
  {% for item in contents %}
  <li class="text-xs font-mono text-gray-700 bg-gray-50 rounded px-2 py-1">{{ item }}</li>
  {% endfor %}
</ul>
{% else %}
<p class="text-xs text-gray-400 italic">No contents recorded for this version.</p>
{% endif %}
```

### `ui.py` changes

- `skill_detail` endpoint: read `contents` from the latest version record (JSON decode), pass as a separate top-level context variable: `context={"pkg": pkg_data, "contents": contents_list}`. The partial inherits `contents` from this context via Jinja2 include.
- New `skill_version_contents` endpoint: query `Package` by name, find the `Version` record matching the version string, JSON-decode `contents`, render `partials/skill_version_contents.html` with `context={"contents": contents_list}`. Return 404 if package or version not found.

---

## Files Changed

| File | Change |
|------|--------|
| `server/app/database.py` | Add `contents` column to `Version`; migrate in `init_db()` |
| `server/app/routers/packages.py` | Accept + store `contents` in push; return per version in `get_package` |
| `server/app/routers/ui.py` | Pass `contents` to `skill_detail`; add `skill_version_contents` route |
| `server/app/templates/partials/skill_detail.html` | Add Contents section; make version rows clickable |
| `server/app/templates/partials/skill_version_contents.html` | New partial |
| `server/tests/test_packages.py` | Test `contents` stored and returned |
| `server/tests/test_ui.py` | Test Contents section rendered; version click returns fragment |
| `cli/skillhub/commands/init.py` | Auto-populate `including`; new template |
| `cli/skillhub/utils/packaging.py` | Remove `excluding` logic |
| `cli/skillhub/commands/push.py` | Add `contents` to push metadata |
| `cli/skillhub/commands/info.py` | New file |
| `cli/skillhub/cli.py` | Register `info` command |
| `cli/tests/test_init.py` | Update for new template + auto-populate |
| `cli/tests/test_build.py` | Remove `excluding` tests; keep packaging logic tests |
| `cli/tests/test_push.py` | Test `contents` sent in metadata |
| `cli/tests/test_info.py` | New file |
