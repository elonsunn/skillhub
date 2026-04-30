# Skill Contents, Info Command & Scope Simplification — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface each skill package's `including` list as `contents` in the web UI drawer and a new CLI `info` command; simplify packaging to `including`-only; make `init` auto-populate `including` from the existing config directory.

**Architecture:** `including` from `skillhub.yaml` is sent as `contents` in push metadata, stored as a JSON text column on the `Version` DB record, returned per-version by `GET /api/packages/{name}`, displayed in the web drawer with HTMX version-switching, and printed by a new `skillhub info` CLI command.

**Tech Stack:** FastAPI + SQLAlchemy + SQLite (server), Click + requests (CLI), HTMX + Jinja2 + Tailwind CDN (web UI), pytest.

---

### Task 1: Remove `excluding` from packaging

**Files:**
- Modify: `cli/skillhub/utils/packaging.py`
- Modify: `cli/tests/test_packaging.py`
- Modify: `cli/tests/test_build.py`

- [ ] **Step 1: Remove the two `excluding` tests from `test_packaging.py`**

Delete `test_excluding_removes_paths` (lines 58-63) and `test_both_including_and_excluding_raises` (lines 65-67) from `cli/tests/test_packaging.py`. The file after deletion:

```python
import zipfile
import pytest
import click
from skillhub.utils.packaging import build_zip


@pytest.fixture
def pkg_dir(tmp_path):
    d = tmp_path / ".github"
    d.mkdir()
    (d / "copilot-instructions.md").write_text("instructions")
    skills = d / "skills" / "my-tool"
    skills.mkdir(parents=True)
    (skills / "SKILL.md").write_text("skill content")
    (d / "agents").mkdir()
    (d / "agents" / "reviewer.md").write_text("agent content")
    (d / "skillhub.yaml").write_text("name: mypkg")
    (d / ".DS_Store").write_text("mac junk")
    (d / "__pycache__").mkdir()
    (d / "__pycache__" / "cache.pyc").write_text("bytecode")
    return d


def _names(zip_path):
    with zipfile.ZipFile(zip_path) as zf:
        return {n for n in zf.namelist() if not n.endswith("/")}


def test_all_files_included_by_default(pkg_dir):
    names = _names(build_zip(pkg_dir, {"name": "mypkg", "tags": ["t"]}))
    assert "copilot-instructions.md" in names
    assert "skills/my-tool/SKILL.md" in names
    assert "agents/reviewer.md" in names


def test_skillhub_yaml_always_excluded(pkg_dir):
    names = _names(build_zip(pkg_dir, {"name": "mypkg", "tags": ["t"]}))
    assert "skillhub.yaml" not in names


def test_ds_store_always_excluded(pkg_dir):
    names = _names(build_zip(pkg_dir, {"name": "mypkg", "tags": ["t"]}))
    assert ".DS_Store" not in names


def test_pycache_always_excluded(pkg_dir):
    names = _names(build_zip(pkg_dir, {"name": "mypkg", "tags": ["t"]}))
    assert not any("__pycache__" in n for n in names)


def test_including_limits_scope(pkg_dir):
    names = _names(build_zip(pkg_dir, {"name": "mypkg", "tags": ["t"], "including": ["skills/my-tool"]}))
    assert "skills/my-tool/SKILL.md" in names
    assert "agents/reviewer.md" not in names
    assert "copilot-instructions.md" not in names


def test_ignore_rules_applied(pkg_dir):
    (pkg_dir / ".env").write_text("SECRET=abc")
    names = _names(build_zip(pkg_dir, {"name": "mypkg", "tags": ["t"], "ignore": [".env"]}))
    assert ".env" not in names
    assert "copilot-instructions.md" in names


def test_zip_path_uses_package_name(pkg_dir):
    zip_path = build_zip(pkg_dir, {"name": "my-awesome-pkg", "tags": ["t"]})
    assert zip_path == pkg_dir.parent / "my-awesome-pkg.zip"
    assert zip_path.exists()
```

- [ ] **Step 2: Remove `test_build_both_including_excluding_error` from `test_build.py`**

Delete the last test function from `cli/tests/test_build.py`. File after deletion:

```python
import yaml
from click.testing import CliRunner
from skillhub.cli import cli


def test_build_success(config_dir, skillhub_yaml):
    (config_dir / "agents").mkdir()
    (config_dir / "agents" / "reviewer.md").write_text("agent")
    result = CliRunner().invoke(cli, ["build"])
    assert result.exit_code == 0, result.output
    assert "Built" in result.output
    assert "test-pkg.zip" in result.output


def test_build_empty_tags_error(config_dir):
    (config_dir / "skillhub.yaml").write_text(
        yaml.dump({"name": "p", "version": "1.0.0", "tags": [], "author": "a"})
    )
    result = CliRunner().invoke(cli, ["build"])
    assert result.exit_code != 0
    assert "tags must not be empty" in result.output
```

- [ ] **Step 3: Run packaging and build tests to confirm they pass as-is**

```bash
cd /home/elon/code/BitBucket/skillhub/cli
.venv/bin/pytest tests/test_packaging.py tests/test_build.py -v
```

Expected: All tests PASS (we only removed tests, not changed code yet).

- [ ] **Step 4: Simplify `packaging.py` — remove `excluding` branch**

Replace the full contents of `cli/skillhub/utils/packaging.py`:

```python
import zipfile
import click
import pathspec
from pathlib import Path

_ALWAYS_IGNORE = [
    "skillhub.yaml",
    ".DS_Store",
    "**/__pycache__/**",
    "*.pyc",
    ".git/",
]


def build_zip(config_dir: Path, config: dict) -> Path:
    including = config.get("including")

    ignore_spec = pathspec.PathSpec.from_lines(
        "gitignore", list(config.get("ignore", [])) + _ALWAYS_IGNORE
    )

    if including:
        candidates = []
        for inc in including:
            p = config_dir / inc
            if p.is_file():
                candidates.append(p)
            elif p.is_dir():
                candidates.extend(f for f in p.rglob("*") if f.is_file())
    else:
        candidates = [f for f in config_dir.rglob("*") if f.is_file()]

    files_to_zip = [
        f for f in candidates
        if not ignore_spec.match_file(str(f.relative_to(config_dir)))
    ]

    zip_path = config_dir.parent / f"{config['name']}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files_to_zip:
            zf.write(f, f.relative_to(config_dir))

    return zip_path
```

- [ ] **Step 5: Run all packaging tests**

```bash
cd /home/elon/code/BitBucket/skillhub/cli
.venv/bin/pytest tests/test_packaging.py tests/test_build.py -v
```

Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
cd /home/elon/code/BitBucket/skillhub
git add cli/skillhub/utils/packaging.py cli/tests/test_packaging.py cli/tests/test_build.py
git commit -m "feat: remove excluding scope mode — including-only packaging"
```

---

### Task 2: Update `init` — auto-populate `including` and simplify template

**Files:**
- Modify: `cli/skillhub/commands/init.py`
- Modify: `cli/tests/test_init.py`

- [ ] **Step 1: Write failing tests in `cli/tests/test_init.py`**

Replace the full contents of `cli/tests/test_init.py`:

```python
import yaml
from click.testing import CliRunner
from skillhub.cli import cli


def test_init_creates_yaml(config_dir):
    result = CliRunner().invoke(cli, ["init"])
    assert result.exit_code == 0, result.output
    assert "Created skillhub.yaml" in result.output
    data = yaml.safe_load((config_dir / "skillhub.yaml").read_text())
    assert data["name"] == "my-skill-package"
    assert data["version"] == "1.0.0"
    assert data["server"] == "http://localhost:8000"
    assert data["tags"] == ["skill", "automation"]
    assert "excluding" not in data
    assert data["ignore"] == [".env", "*.env", "config.json"]


def test_init_including_empty_when_dir_is_empty(config_dir):
    result = CliRunner().invoke(cli, ["init"])
    assert result.exit_code == 0, result.output
    data = yaml.safe_load((config_dir / "skillhub.yaml").read_text())
    assert data["including"] == []


def test_init_auto_populates_including(config_dir):
    (config_dir / "skills").mkdir()
    (config_dir / "skills" / "my-tool").mkdir()
    (config_dir / "skills" / "my-tool" / "SKILL.md").write_text("skill")
    (config_dir / "agents").mkdir()
    (config_dir / "agents" / "reviewer").mkdir()
    (config_dir / "agents" / "reviewer" / "config.yaml").write_text("agent")
    (config_dir / "SETUP.md").write_text("setup")

    result = CliRunner().invoke(cli, ["init"])
    assert result.exit_code == 0, result.output
    data = yaml.safe_load((config_dir / "skillhub.yaml").read_text())
    assert "agents/reviewer" in data["including"]
    assert "skills/my-tool" in data["including"]
    assert "SETUP.md" in data["including"]


def test_init_does_not_include_skillhub_yaml_in_scan(config_dir):
    # skillhub.yaml itself must never appear in including
    (config_dir / "skills" / "foo").mkdir(parents=True)
    result = CliRunner().invoke(cli, ["init"])
    assert result.exit_code == 0, result.output
    data = yaml.safe_load((config_dir / "skillhub.yaml").read_text())
    assert "skillhub.yaml" not in data["including"]


def test_init_fails_if_yaml_exists(config_dir):
    (config_dir / "skillhub.yaml").write_text("name: existing")
    result = CliRunner().invoke(cli, ["init"])
    assert result.exit_code != 0
    assert "skillhub.yaml already exists" in result.output


def test_init_creates_local_github_when_parent_has_one(tmp_path, monkeypatch):
    (tmp_path / ".github").mkdir()
    nested = tmp_path / "child" / "project"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)

    result = CliRunner().invoke(cli, ["init"])
    assert result.exit_code == 0, result.output
    assert (nested / ".github" / "skillhub.yaml").exists()
    assert not (tmp_path / ".github" / "skillhub.yaml").exists()
```

- [ ] **Step 2: Run to verify failures**

```bash
cd /home/elon/code/BitBucket/skillhub/cli
.venv/bin/pytest tests/test_init.py -v
```

Expected: `test_init_creates_yaml` FAIL (still has `excluding`, old ignore), `test_init_including_empty_when_dir_is_empty` FAIL or PASS depending on current code, `test_init_auto_populates_including` FAIL, `test_init_does_not_include_skillhub_yaml_in_scan` FAIL.

- [ ] **Step 3: Rewrite `cli/skillhub/commands/init.py`**

```python
import click
from pathlib import Path


def _scan_including(config_dir: Path) -> list[str]:
    items = []
    for entry in sorted(config_dir.iterdir()):
        if entry.name == "skillhub.yaml":
            continue
        if entry.is_file():
            items.append(entry.name)
        elif entry.is_dir():
            for child in sorted(entry.iterdir()):
                items.append(f"{entry.name}/{child.name}")
    return items


@click.command()
def init():
    cwd = Path.cwd()
    github_dir = cwd / ".github"
    claude_dir = cwd / ".claude"

    if github_dir.is_dir():
        config_dir = github_dir
    elif claude_dir.is_dir():
        config_dir = claude_dir
    else:
        config_dir = github_dir
        config_dir.mkdir()

    yaml_path = config_dir / "skillhub.yaml"
    if yaml_path.exists():
        raise click.ClickException("skillhub.yaml already exists.")

    including = _scan_including(config_dir)
    if including:
        including_block = "\n" + "\n".join(f"  - {item}" for item in including)
    else:
        including_block = " []"

    template = f"""name: my-skill-package
version: 1.0.0
description: Describe your skill package
author: your-name
tags:
  - skill
  - automation
server: http://localhost:8000

including:{including_block}

ignore:
  - .env
  - "*.env"
  - config.json
"""
    yaml_path.write_text(template)
    click.echo(f"Created skillhub.yaml in {config_dir}")
```

- [ ] **Step 4: Run tests**

```bash
cd /home/elon/code/BitBucket/skillhub/cli
.venv/bin/pytest tests/test_init.py -v
```

Expected: All 6 tests PASS.

- [ ] **Step 5: Run full CLI test suite to check for regressions**

```bash
cd /home/elon/code/BitBucket/skillhub/cli
.venv/bin/pytest tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
cd /home/elon/code/BitBucket/skillhub
git add cli/skillhub/commands/init.py cli/tests/test_init.py
git commit -m "feat: init auto-populates including from config dir structure"
```

---

### Task 3: Add `contents` column to `Version` model

**Files:**
- Modify: `server/app/database.py`
- Modify: `server/tests/test_packages.py`

- [ ] **Step 1: Write a failing test in `server/tests/test_packages.py`**

Add this test at the top of `server/tests/test_packages.py` (after existing imports):

```python
def test_version_stores_contents(db_session):
    import json
    pkg = Package(name="contents-test", description="", author="")
    db_session.add(pkg)
    db_session.flush()
    v = Version(
        package_id=pkg.id, version="1.0.0",
        message="init", file_path="contents-test/1.0.0.zip",
        contents=json.dumps(["skills/foo", "agents/bar"]),
    )
    db_session.add(v)
    db_session.commit()
    result = db_session.query(Version).filter_by(package_id=pkg.id).first()
    assert json.loads(result.contents) == ["skills/foo", "agents/bar"]


def test_version_contents_defaults_null(db_session):
    pkg = Package(name="null-contents", description="", author="")
    db_session.add(pkg)
    db_session.flush()
    v = Version(
        package_id=pkg.id, version="1.0.0",
        message="init", file_path="null-contents/1.0.0.zip",
    )
    db_session.add(v)
    db_session.commit()
    result = db_session.query(Version).filter_by(package_id=pkg.id).first()
    assert result.contents is None
```

- [ ] **Step 2: Run to verify failures**

```bash
cd /home/elon/code/BitBucket/skillhub/server
.venv/bin/pytest tests/test_packages.py::test_version_stores_contents tests/test_packages.py::test_version_contents_defaults_null -v
```

Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'contents'`

- [ ] **Step 3: Add `contents` column and migration to `server/app/database.py`**

```python
import json
import os
from datetime import datetime

from sqlalchemy import (
    Column, DateTime, ForeignKey, Integer, String, Text,
    UniqueConstraint, create_engine, text,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/skillhub.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Package(Base):
    __tablename__ = "packages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)
    author = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    versions = relationship("Version", back_populates="package", cascade="all, delete-orphan")
    tags = relationship("Tag", back_populates="package", cascade="all, delete-orphan")


class Version(Base):
    __tablename__ = "versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    package_id = Column(Integer, ForeignKey("packages.id"), nullable=False)
    version = Column(String, nullable=False)
    message = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    contents = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    package = relationship("Package", back_populates="versions")
    __table_args__ = (UniqueConstraint("package_id", "version"),)


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    package_id = Column(Integer, ForeignKey("packages.id"), nullable=False)
    tag_name = Column(String, nullable=False)

    package = relationship("Package", back_populates="tags")
    __table_args__ = (UniqueConstraint("package_id", "tag_name"),)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    os.makedirs("data", exist_ok=True)
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        cols = [r[1] for r in conn.execute(text("PRAGMA table_info(versions)"))]
        if "contents" not in cols:
            conn.execute(text("ALTER TABLE versions ADD COLUMN contents TEXT"))
            conn.commit()
```

- [ ] **Step 4: Run tests**

```bash
cd /home/elon/code/BitBucket/skillhub/server
.venv/bin/pytest tests/test_packages.py::test_version_stores_contents tests/test_packages.py::test_version_contents_defaults_null -v
```

Expected: Both PASS.

- [ ] **Step 5: Run full server test suite**

```bash
cd /home/elon/code/BitBucket/skillhub/server
.venv/bin/pytest tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
cd /home/elon/code/BitBucket/skillhub
git add server/app/database.py server/tests/test_packages.py
git commit -m "feat: add contents column to Version model with SQLite migration"
```

---

### Task 4: Server push stores `contents`, get returns it per version

**Files:**
- Modify: `server/app/routers/packages.py`
- Modify: `server/tests/test_packages.py`

- [ ] **Step 1: Write failing tests — add to `server/tests/test_packages.py`**

Add these tests at the end of `server/tests/test_packages.py`:

```python
def test_push_stores_contents(client):
    meta = _json.dumps({
        "version": "1.0.0", "message": "init",
        "description": "", "author": "", "tags": ["t"],
        "contents": ["skills/skilla", "agents/my-agent"],
    })
    client.post(
        "/api/packages/with-contents",
        data={"metadata": meta},
        files={"file": ("f.zip", _make_zip(), "application/zip")},
    )
    response = client.get("/api/packages/with-contents")
    assert response.status_code == 200
    data = response.json()
    assert data["versions"][0]["contents"] == ["skills/skilla", "agents/my-agent"]


def test_push_without_contents_defaults_empty_list(client):
    meta = _json.dumps({
        "version": "1.0.0", "message": "init",
        "description": "", "author": "", "tags": ["t"],
    })
    client.post(
        "/api/packages/no-contents",
        data={"metadata": meta},
        files={"file": ("f.zip", _make_zip(), "application/zip")},
    )
    response = client.get("/api/packages/no-contents")
    assert response.status_code == 200
    data = response.json()
    assert data["versions"][0]["contents"] == []


def test_get_package_returns_contents_per_version(client):
    zip_data = _make_zip()
    meta_v1 = _json.dumps({
        "version": "1.0.0", "message": "init",
        "description": "", "author": "", "tags": ["t"],
        "contents": ["skills/foo"],
    })
    meta_v2 = _json.dumps({
        "version": "1.0.1", "message": "update",
        "description": "", "author": "", "tags": ["t"],
        "contents": ["skills/foo", "skills/bar"],
    })
    client.post("/api/packages/multi-ver", data={"metadata": meta_v1}, files={"file": ("f.zip", zip_data, "application/zip")})
    client.post("/api/packages/multi-ver", data={"metadata": meta_v2}, files={"file": ("f.zip", zip_data, "application/zip")})

    response = client.get("/api/packages/multi-ver")
    data = response.json()
    assert data["versions"][0]["version"] == "1.0.1"
    assert data["versions"][0]["contents"] == ["skills/foo", "skills/bar"]
    assert data["versions"][1]["version"] == "1.0.0"
    assert data["versions"][1]["contents"] == ["skills/foo"]
```

- [ ] **Step 2: Run to verify failures**

```bash
cd /home/elon/code/BitBucket/skillhub/server
.venv/bin/pytest tests/test_packages.py::test_push_stores_contents tests/test_packages.py::test_push_without_contents_defaults_empty_list tests/test_packages.py::test_get_package_returns_contents_per_version -v
```

Expected: All 3 FAIL — `contents` key missing from API response.

- [ ] **Step 3: Update `server/app/routers/packages.py`**

Replace the full file:

```python
import json
import os
import shutil
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from packaging.version import InvalidVersion
from packaging.version import Version as SemVer
from sqlalchemy.orm import Session

from app.database import Package
from app.database import Tag
from app.database import Version as VersionRecord
from app.database import get_db

router = APIRouter()
STORAGE_ROOT = os.getenv("STORAGE_ROOT", "storage")


def _latest_version(pkg: Package) -> Optional[str]:
    if not pkg.versions:
        return None
    return max(pkg.versions, key=lambda v: SemVer(v.version)).version


@router.get("/packages")
def list_packages(
    search: Optional[str] = None,
    tag: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Package)
    if tag:
        query = query.join(Tag).filter(Tag.tag_name == tag).distinct()
    packages = query.all()
    if search:
        s = search.lower()
        packages = [
            p for p in packages
            if s in (p.name or "").lower() or s in (p.description or "").lower()
        ]
    return [
        {
            "name": p.name,
            "description": p.description,
            "author": p.author,
            "tags": [t.tag_name for t in p.tags],
            "latest_version": _latest_version(p),
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in packages
    ]


@router.get("/packages/{name}/{version}")
def download_package(name: str, version: str, db: Session = Depends(get_db)):
    pkg = db.query(Package).filter(Package.name == name).first()
    if not pkg:
        raise HTTPException(status_code=404, detail=f"Package '{name}' not found")

    if version == "latest":
        if not pkg.versions:
            raise HTTPException(status_code=404, detail=f"Package '{name}' has no versions")
        ver_record = max(pkg.versions, key=lambda v: SemVer(v.version))
    else:
        ver_record = next((v for v in pkg.versions if v.version == version), None)
        if not ver_record:
            raise HTTPException(
                status_code=404,
                detail=f"Version '{version}' not found for package '{name}'",
            )

    file_path = Path(STORAGE_ROOT) / ver_record.file_path
    if not file_path.exists():
        raise HTTPException(status_code=500, detail="Package file not found on disk")

    return FileResponse(
        path=str(file_path),
        media_type="application/zip",
        filename=f"{name}-{ver_record.version}.zip",
    )


@router.post("/packages/{name}")
def push_package(
    name: str,
    file: UploadFile,
    metadata: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        meta = json.loads(metadata)
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="Invalid metadata JSON")

    version = meta.get("version")
    message = meta.get("message")
    description = meta.get("description", "")
    author = meta.get("author", "")
    tags = meta.get("tags", [])
    contents = meta.get("contents", [])

    if not version or not message:
        raise HTTPException(status_code=422, detail="metadata must include 'version' and 'message'")

    if not tags:
        raise HTTPException(status_code=400, detail="tags must not be empty")

    try:
        new_ver = SemVer(version)
    except InvalidVersion:
        raise HTTPException(status_code=422, detail=f"Invalid semver: {version}")

    pkg = db.query(Package).filter(Package.name == name).first()

    if pkg:
        latest = _latest_version(pkg)
        if latest and SemVer(latest) >= new_ver:
            raise HTTPException(
                status_code=409,
                detail=f"Version {version} must be greater than current latest {latest}",
            )
        pkg.description = description or pkg.description
        pkg.author = author or pkg.author
    else:
        pkg = Package(name=name, description=description, author=author)
        db.add(pkg)
        db.flush()

    rel_path = f"{name}/{version}.zip"
    abs_path = Path(STORAGE_ROOT) / rel_path
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    with abs_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    db.add(VersionRecord(
        package_id=pkg.id,
        version=version,
        message=message,
        file_path=rel_path,
        contents=json.dumps(contents),
    ))

    db.query(Tag).filter(Tag.package_id == pkg.id).delete()
    for tag_name in tags:
        db.add(Tag(package_id=pkg.id, tag_name=tag_name))

    db.commit()

    return {"name": name, "version": version}


@router.get("/packages/{name}")
def get_package(name: str, db: Session = Depends(get_db)):
    pkg = db.query(Package).filter(Package.name == name).first()
    if not pkg:
        raise HTTPException(status_code=404, detail=f"Package '{name}' not found")
    return {
        "name": pkg.name,
        "description": pkg.description,
        "author": pkg.author,
        "tags": [t.tag_name for t in pkg.tags],
        "versions": [
            {
                "version": v.version,
                "message": v.message,
                "created_at": v.created_at.isoformat() if v.created_at else None,
                "contents": json.loads(v.contents) if v.contents else [],
            }
            for v in sorted(pkg.versions, key=lambda v: SemVer(v.version), reverse=True)
        ],
    }
```

- [ ] **Step 4: Run the three new tests**

```bash
cd /home/elon/code/BitBucket/skillhub/server
.venv/bin/pytest tests/test_packages.py::test_push_stores_contents tests/test_packages.py::test_push_without_contents_defaults_empty_list tests/test_packages.py::test_get_package_returns_contents_per_version -v
```

Expected: All 3 PASS.

- [ ] **Step 5: Run full server test suite**

```bash
cd /home/elon/code/BitBucket/skillhub/server
.venv/bin/pytest tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
cd /home/elon/code/BitBucket/skillhub
git add server/app/routers/packages.py server/tests/test_packages.py
git commit -m "feat: server stores and returns contents per version"
```

---

### Task 5: CLI `push` sends `including` as `contents`

**Files:**
- Modify: `cli/skillhub/commands/push.py`
- Modify: `cli/tests/test_push.py`

- [ ] **Step 1: Write a failing test — add to `cli/tests/test_push.py`**

Add this test at the end of `cli/tests/test_push.py`:

```python
def test_push_sends_contents_from_including(config_dir, skillhub_yaml):
    import yaml as _yaml
    data = _yaml.safe_load((config_dir / "skillhub.yaml").read_text())
    data["including"] = ["skills/my-tool", "agents/reviewer"]
    (config_dir / "skillhub.yaml").write_text(_yaml.dump(data))
    (config_dir / "skills").mkdir()
    (config_dir / "skills" / "my-tool").mkdir()
    (config_dir / "skills" / "my-tool" / "SKILL.md").write_text("skill")

    captured = {}

    def fake_push(server, name, zip_path, metadata):
        captured.update(metadata)
        return {"name": name, "version": metadata["version"]}

    with patch("skillhub.utils.api.get_package", return_value=None), \
         patch("skillhub.utils.api.push_package", side_effect=fake_push):
        result = CliRunner().invoke(cli, ["push", "-m", "test"])

    assert result.exit_code == 0, result.output
    assert captured.get("contents") == ["skills/my-tool", "agents/reviewer"]
```

- [ ] **Step 2: Run to verify failure**

```bash
cd /home/elon/code/BitBucket/skillhub/cli
.venv/bin/pytest tests/test_push.py::test_push_sends_contents_from_including -v
```

Expected: FAIL — `assert None == ["skills/my-tool", "agents/reviewer"]`

- [ ] **Step 3: Update `cli/skillhub/commands/push.py`**

Add `"contents": config.get("including", [])` to the metadata dict:

```python
import sys
import click
from packaging.version import Version
from skillhub.utils.platform import find_config_dir
from skillhub.utils.config import load_config, save_config, get_server_url
from skillhub.utils.packaging import build_zip
from skillhub.utils import api


@click.command()
@click.option("-m", "--message", required=True, help="Commit message for this version")
def push(message):
    config_dir = find_config_dir()
    config = load_config(config_dir)

    if not config.get("tags"):
        raise click.ClickException("tags must not be empty in skillhub.yaml")

    server = get_server_url(config)
    name = config["name"]

    existing = api.get_package(server, name)
    if existing is not None:
        latest_str = max(
            (v["version"] for v in existing["versions"]),
            key=lambda v: Version(v),
        )
        parsed = Version(latest_str)
        new_version = f"{parsed.major}.{parsed.minor}.{parsed.micro + 1}"
    else:
        new_version = config["version"]

    config["version"] = new_version
    save_config(config_dir, config)

    zip_path = build_zip(config_dir, config)

    metadata = {
        "version": new_version,
        "message": message,
        "description": config.get("description", ""),
        "author": config.get("author", ""),
        "tags": config.get("tags", []),
        "contents": config.get("including", []),
    }

    try:
        api.push_package(server, name, zip_path, metadata)
    except api.SkillHubAPIError as e:
        click.echo(f"Error: {e.detail}", err=True)
        click.echo(
            f"Warning: local skillhub.yaml version was updated to {new_version} "
            "but push failed. You may need to revert it manually.",
            err=True,
        )
        sys.exit(1)

    click.echo(f"Pushed {name}@{new_version}")
```

- [ ] **Step 4: Run the new test**

```bash
cd /home/elon/code/BitBucket/skillhub/cli
.venv/bin/pytest tests/test_push.py::test_push_sends_contents_from_including -v
```

Expected: PASS.

- [ ] **Step 5: Run full CLI test suite**

```bash
cd /home/elon/code/BitBucket/skillhub/cli
.venv/bin/pytest tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
cd /home/elon/code/BitBucket/skillhub
git add cli/skillhub/commands/push.py cli/tests/test_push.py
git commit -m "feat: push sends including list as contents in metadata"
```

---

### Task 6: CLI `info` command

**Files:**
- Create: `cli/skillhub/commands/info.py`
- Modify: `cli/skillhub/cli.py`
- Create: `cli/tests/test_info.py`

- [ ] **Step 1: Create `cli/tests/test_info.py`**

```python
import sys
from unittest.mock import patch
from click.testing import CliRunner
from skillhub.cli import cli


def _pkg(versions=None):
    return {
        "name": "my-skill",
        "description": "A great skill",
        "author": "alice",
        "tags": ["copilot", "review"],
        "versions": versions or [
            {
                "version": "1.2.0",
                "message": "added formatter",
                "created_at": "2026-04-30T10:00:00",
                "contents": ["skills/skilla", "agents/my-agent"],
            },
            {
                "version": "1.1.0",
                "message": "initial release",
                "created_at": "2026-04-15T10:00:00",
                "contents": ["skills/skilla"],
            },
        ],
    }


def test_info_shows_package_metadata(config_dir, skillhub_yaml):
    with patch("skillhub.utils.api.get_package", return_value=_pkg()):
        result = CliRunner().invoke(cli, ["info", "my-skill"])
    assert result.exit_code == 0, result.output
    assert "my-skill" in result.output
    assert "A great skill" in result.output
    assert "alice" in result.output
    assert "copilot" in result.output


def test_info_shows_latest_version_contents(config_dir, skillhub_yaml):
    with patch("skillhub.utils.api.get_package", return_value=_pkg()):
        result = CliRunner().invoke(cli, ["info", "my-skill"])
    assert "1.2.0" in result.output
    assert "skills/skilla" in result.output
    assert "agents/my-agent" in result.output


def test_info_version_flag_shows_that_versions_contents(config_dir, skillhub_yaml):
    with patch("skillhub.utils.api.get_package", return_value=_pkg()):
        result = CliRunner().invoke(cli, ["info", "my-skill", "--version", "1.1.0"])
    assert result.exit_code == 0, result.output
    assert "1.1.0" in result.output
    assert "skills/skilla" in result.output
    assert "agents/my-agent" not in result.output


def test_info_shows_version_history(config_dir, skillhub_yaml):
    with patch("skillhub.utils.api.get_package", return_value=_pkg()):
        result = CliRunner().invoke(cli, ["info", "my-skill"])
    assert "1.2.0" in result.output
    assert "1.1.0" in result.output
    assert "added formatter" in result.output
    assert "initial release" in result.output


def test_info_package_not_found(config_dir, skillhub_yaml):
    with patch("skillhub.utils.api.get_package", return_value=None):
        result = CliRunner().invoke(cli, ["info", "ghost"])
    assert result.exit_code != 0
    assert "not found" in result.output.lower()


def test_info_version_not_found(config_dir, skillhub_yaml):
    with patch("skillhub.utils.api.get_package", return_value=_pkg()):
        result = CliRunner().invoke(cli, ["info", "my-skill", "--version", "9.9.9"])
    assert result.exit_code != 0
    assert "9.9.9" in result.output
    assert "not found" in result.output.lower()


def test_info_empty_contents_shows_placeholder(config_dir, skillhub_yaml):
    pkg = _pkg(versions=[{
        "version": "1.0.0", "message": "init",
        "created_at": "2026-01-01T00:00:00", "contents": [],
    }])
    with patch("skillhub.utils.api.get_package", return_value=pkg):
        result = CliRunner().invoke(cli, ["info", "my-skill"])
    assert "no contents recorded" in result.output.lower()
```

- [ ] **Step 2: Run to verify failures**

```bash
cd /home/elon/code/BitBucket/skillhub/cli
.venv/bin/pytest tests/test_info.py -v
```

Expected: All FAIL — `No such command 'info'`

- [ ] **Step 3: Create `cli/skillhub/commands/info.py`**

```python
import sys
import click
from skillhub.utils.platform import find_config_dir
from skillhub.utils.config import load_config, get_server_url
from skillhub.utils import api


@click.command()
@click.argument("name")
@click.option("--version", default=None, help="Version to show contents for (default: latest)")
def info(name, version):
    try:
        config = load_config(find_config_dir())
    except click.ClickException:
        config = {}
    server = get_server_url(config)

    pkg = api.get_package(server, name)
    if pkg is None:
        raise click.ClickException(f"Package '{name}' not found")

    versions = pkg.get("versions", [])

    if version:
        ver_data = next((v for v in versions if v["version"] == version), None)
        if ver_data is None:
            raise click.ClickException(f"Version {version} not found for package '{name}'")
    else:
        ver_data = versions[0] if versions else None

    click.echo(f"{'name:':<13}{pkg['name']}")
    if pkg.get("description"):
        click.echo(f"{'description:':<13}{pkg['description']}")
    if pkg.get("author"):
        click.echo(f"{'author:':<13}{pkg['author']}")
    tags_str = ", ".join(pkg.get("tags", []))
    if tags_str:
        click.echo(f"{'tags:':<13}{tags_str}")

    if ver_data:
        click.echo()
        click.echo(f"{'version:':<13}{ver_data['version']}")
        contents = ver_data.get("contents", [])
        click.echo("contents:")
        if contents:
            for item in contents:
                click.echo(f"  {item}")
        else:
            click.echo("  (no contents recorded)")

    if versions:
        click.echo()
        click.echo("version history:")
        for v in versions:
            date = v.get("created_at", "")[:10] if v.get("created_at") else ""
            click.echo(f"  {v['version']:<12} {v['message']:<32} {date}")
```

- [ ] **Step 4: Register the command in `cli/skillhub/cli.py`**

```python
import click
from skillhub.commands.init import init
from skillhub.commands.list_cmd import list_cmd
from skillhub.commands.pull import pull
from skillhub.commands.setup_cmd import setup
from skillhub.commands.build import build
from skillhub.commands.push import push
from skillhub.commands.info import info


@click.group()
def cli():
    pass


cli.add_command(init)
cli.add_command(list_cmd, name="list")
cli.add_command(pull)
cli.add_command(setup)
cli.add_command(build)
cli.add_command(push)
cli.add_command(info)
```

- [ ] **Step 5: Run info tests**

```bash
cd /home/elon/code/BitBucket/skillhub/cli
.venv/bin/pytest tests/test_info.py -v
```

Expected: All 7 tests PASS.

- [ ] **Step 6: Run full CLI test suite**

```bash
cd /home/elon/code/BitBucket/skillhub/cli
.venv/bin/pytest tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
cd /home/elon/code/BitBucket/skillhub
git add cli/skillhub/commands/info.py cli/skillhub/cli.py cli/tests/test_info.py
git commit -m "feat: add info command to display skill package details"
```

---

### Task 7: Web UI — `skill_version_contents` partial and route

**Files:**
- Create: `server/app/templates/partials/skill_version_contents.html`
- Modify: `server/app/routers/ui.py`
- Modify: `server/tests/test_ui.py`

- [ ] **Step 1: Write failing tests — add to `server/tests/test_ui.py`**

Add these tests at the end of `server/tests/test_ui.py`. Also add `import json` at the top of the file after existing imports:

```python
import json


def test_skill_version_contents_returns_fragment(client, db_session):
    pkg = Package(name="frag-pkg", description="", author="")
    db_session.add(pkg)
    db_session.flush()
    db_session.add(Version(
        package_id=pkg.id, version="1.0.0",
        message="init", file_path="frag-pkg/1.0.0.zip",
        contents=json.dumps(["skills/foo", "agents/bar"]),
    ))
    db_session.commit()
    response = client.get("/ui/skills/frag-pkg/1.0.0/contents")
    assert response.status_code == 200
    assert "skills/foo" in response.text
    assert "agents/bar" in response.text


def test_skill_version_contents_empty_shows_placeholder(client, db_session):
    pkg = Package(name="empty-pkg", description="", author="")
    db_session.add(pkg)
    db_session.flush()
    db_session.add(Version(
        package_id=pkg.id, version="1.0.0",
        message="init", file_path="empty-pkg/1.0.0.zip",
    ))
    db_session.commit()
    response = client.get("/ui/skills/empty-pkg/1.0.0/contents")
    assert response.status_code == 200
    assert "No contents recorded" in response.text


def test_skill_version_contents_package_not_found(client):
    response = client.get("/ui/skills/ghost/1.0.0/contents")
    assert response.status_code == 404


def test_skill_version_contents_version_not_found(client, db_session):
    pkg = Package(name="found-pkg", description="", author="")
    db_session.add(pkg)
    db_session.commit()
    response = client.get("/ui/skills/found-pkg/9.9.9/contents")
    assert response.status_code == 404
```

Note: `_seed_pkg` in this file doesn't pass `contents`, so also update it to accept an optional `contents` parameter to support Task 8 tests. Update `_seed_pkg` at the top of `test_ui.py`:

```python
def _seed_pkg(db_session, name="my-skill", description="A skill", author="alice",
              tag="copilot", version="1.0.0", contents=None):
    pkg = Package(name=name, description=description, author=author)
    db_session.add(pkg)
    db_session.flush()
    db_session.add(Tag(package_id=pkg.id, tag_name=tag))
    db_session.add(Version(
        package_id=pkg.id, version=version,
        message="initial release", file_path=f"{name}/{version}.zip",
        contents=json.dumps(contents) if contents is not None else None,
    ))
    db_session.commit()
    return pkg
```

The updated import line at the top of `test_ui.py`:

```python
import json
from app.database import Package, Tag, Version
```

- [ ] **Step 2: Run to verify failures**

```bash
cd /home/elon/code/BitBucket/skillhub/server
.venv/bin/pytest tests/test_ui.py::test_skill_version_contents_returns_fragment tests/test_ui.py::test_skill_version_contents_empty_shows_placeholder tests/test_ui.py::test_skill_version_contents_package_not_found tests/test_ui.py::test_skill_version_contents_version_not_found -v
```

Expected: All 4 FAIL — `404 Not Found` (route doesn't exist yet).

- [ ] **Step 3: Create `server/app/templates/partials/skill_version_contents.html`**

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

- [ ] **Step 4: Add `skill_version_contents` route to `server/app/routers/ui.py`**

Add `import json` at the top of `ui.py` (after existing imports), and add the new route after `skill_detail`. The full updated `ui.py`:

```python
import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from packaging.version import Version as SemVer
from sqlalchemy.orm import Session, aliased

from app.database import Package, Tag, get_db

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


def _latest_version(pkg: Package) -> Optional[str]:
    if not pkg.versions:
        return None
    return max(pkg.versions, key=lambda v: SemVer(v.version)).version


def _all_tags(db: Session) -> list[str]:
    return sorted({row.tag_name for row in db.query(Tag.tag_name).distinct().all()})


@router.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    packages = db.query(Package).all()
    all_tags = _all_tags(db)
    pkgs_data = [
        {
            "name": p.name,
            "description": p.description or "",
            "author": p.author or "",
            "tags": [t.tag_name for t in p.tags],
            "latest_version": _latest_version(p),
        }
        for p in packages
    ]
    return templates.TemplateResponse(
        request=request,
        name="base.html",
        context={"packages": pkgs_data, "all_tags": all_tags, "active_tag": ""},
    )


@router.get("/ui/skills", response_class=HTMLResponse)
def skill_grid(
    request: Request,
    search: Optional[str] = None,
    tag: list[str] = Query(default=[]),
    db: Session = Depends(get_db),
):
    query = db.query(Package)
    for t in tag:
        alias = aliased(Tag)
        query = query.join(alias, Package.id == alias.package_id).filter(alias.tag_name == t)
    query = query.distinct()
    packages = query.all()
    if search:
        s = search.lower()
        packages = [
            p for p in packages
            if s in (p.name or "").lower() or s in (p.description or "").lower()
        ]
    pkgs_data = [
        {
            "name": p.name,
            "description": p.description or "",
            "author": p.author or "",
            "tags": [t.tag_name for t in p.tags],
            "latest_version": _latest_version(p),
        }
        for p in packages
    ]
    return templates.TemplateResponse(
        request=request,
        name="partials/skill_grid.html",
        context={"packages": pkgs_data},
    )


@router.get("/ui/skills/{name}", response_class=HTMLResponse)
def skill_detail(request: Request, name: str, db: Session = Depends(get_db)):
    pkg = db.query(Package).filter(Package.name == name).first()
    if not pkg:
        return Response(status_code=404)
    versions = sorted(pkg.versions, key=lambda v: SemVer(v.version), reverse=True)
    latest_ver = versions[0] if versions else None
    contents = json.loads(latest_ver.contents) if latest_ver and latest_ver.contents else []
    pkg_data = {
        "name": pkg.name,
        "description": pkg.description or "",
        "author": pkg.author or "",
        "tags": [t.tag_name for t in pkg.tags],
        "latest_version": _latest_version(pkg),
        "versions": [
            {
                "version": v.version,
                "message": v.message,
                "created_at": v.created_at.strftime("%Y-%m-%d") if v.created_at else "",
            }
            for v in versions
        ],
    }
    return templates.TemplateResponse(
        request=request,
        name="partials/skill_detail.html",
        context={"pkg": pkg_data, "contents": contents},
    )


@router.get("/ui/skills/{name}/{version}/contents", response_class=HTMLResponse)
def skill_version_contents(request: Request, name: str, version: str, db: Session = Depends(get_db)):
    pkg = db.query(Package).filter(Package.name == name).first()
    if not pkg:
        return Response(status_code=404)
    ver = next((v for v in pkg.versions if v.version == version), None)
    if not ver:
        return Response(status_code=404)
    contents = json.loads(ver.contents) if ver.contents else []
    return templates.TemplateResponse(
        request=request,
        name="partials/skill_version_contents.html",
        context={"contents": contents},
    )


@router.get("/ui/empty", response_class=HTMLResponse)
def empty():
    return HTMLResponse(content="")
```

- [ ] **Step 5: Run the four new tests**

```bash
cd /home/elon/code/BitBucket/skillhub/server
.venv/bin/pytest tests/test_ui.py::test_skill_version_contents_returns_fragment tests/test_ui.py::test_skill_version_contents_empty_shows_placeholder tests/test_ui.py::test_skill_version_contents_package_not_found tests/test_ui.py::test_skill_version_contents_version_not_found -v
```

Expected: All 4 PASS.

- [ ] **Step 6: Run full server test suite**

```bash
cd /home/elon/code/BitBucket/skillhub/server
.venv/bin/pytest tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
cd /home/elon/code/BitBucket/skillhub
git add server/app/templates/partials/skill_version_contents.html server/app/routers/ui.py server/tests/test_ui.py
git commit -m "feat: add skill_version_contents partial and HTMX route"
```

---

### Task 8: Web UI — skill detail drawer shows contents + clickable version rows

**Files:**
- Modify: `server/app/templates/partials/skill_detail.html`
- Modify: `server/tests/test_ui.py`

- [ ] **Step 1: Write failing tests — add to `server/tests/test_ui.py`**

Add these tests at the end of `server/tests/test_ui.py`:

```python
def test_skill_detail_shows_contents_section(client, db_session):
    _seed_pkg(db_session, name="content-skill", contents=["skills/foo", "agents/bar"])
    response = client.get("/ui/skills/content-skill")
    assert response.status_code == 200
    assert "skills/foo" in response.text
    assert "agents/bar" in response.text


def test_skill_detail_no_contents_shows_placeholder(client, db_session):
    _seed_pkg(db_session, name="empty-contents-skill")
    response = client.get("/ui/skills/empty-contents-skill")
    assert response.status_code == 200
    assert "No contents recorded" in response.text


def test_skill_detail_version_rows_have_htmx_contents_get(client, db_session):
    _seed_pkg(db_session, name="htmx-skill", version="2.0.0")
    response = client.get("/ui/skills/htmx-skill")
    assert 'hx-get="/ui/skills/htmx-skill/2.0.0/contents"' in response.text
    assert 'hx-target="#version-contents"' in response.text
```

- [ ] **Step 2: Run to verify failures**

```bash
cd /home/elon/code/BitBucket/skillhub/server
.venv/bin/pytest tests/test_ui.py::test_skill_detail_shows_contents_section tests/test_ui.py::test_skill_detail_no_contents_shows_placeholder tests/test_ui.py::test_skill_detail_version_rows_have_htmx_contents_get -v
```

Expected: All 3 FAIL — contents not in HTML, no HTMX attributes on rows.

- [ ] **Step 3: Update `server/app/templates/partials/skill_detail.html`**

Replace the full file:

```html
<div class="p-6">
  <div class="flex items-start justify-between mb-4">
    <div>
      <h2 class="text-xl font-bold text-gray-900">{{ pkg.name }}</h2>
      {% if pkg.author %}
      <p class="text-sm text-gray-400 mt-1">{{ pkg.author }}</p>
      {% endif %}
    </div>
    <div class="flex items-center gap-3">
      {% if pkg.latest_version %}
      <span class="px-2 py-1 text-xs font-medium bg-indigo-50 text-indigo-700 rounded-full">
        v{{ pkg.latest_version }}
      </span>
      {% endif %}
      <button class="text-gray-400 hover:text-gray-600 text-xl leading-none" hx-get="/ui/empty"
        hx-target="#drawer-content" type="button">&#x2715;</button>
    </div>
  </div>

  {% if pkg.tags %}
  <div class="flex flex-wrap gap-1 mb-4">
    {% for tag in pkg.tags %}
    <span class="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded-full">{{ tag }}</span>
    {% endfor %}
  </div>
  {% endif %}

  {% if pkg.description %}
  <p class="text-sm text-gray-700 mb-6">{{ pkg.description }}</p>
  {% endif %}

  <div class="mb-6">
    <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Contents</p>
    <div id="version-contents">
      {% include "partials/skill_version_contents.html" %}
    </div>
  </div>

  <div class="mb-6">
    <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Install via CLI</p>
    <div class="relative group">
      <pre
        class="bg-gray-900 text-green-400 text-sm rounded-lg px-4 py-3 font-mono overflow-x-auto">skillhub pull {{ pkg.name }}</pre>
      <button
        class="absolute top-2 right-2 px-2 py-1 text-xs bg-gray-700 text-gray-300 rounded opacity-0 group-hover:opacity-100 transition-opacity"
        type="button" onclick="navigator.clipboard.writeText('skillhub pull {{ pkg.name }}')">Copy</button>
    </div>
  </div>

  {% if pkg.versions %}
  <div>
    <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Version History</p>
    <table class="w-full text-sm">
      <thead>
        <tr class="text-xs text-gray-400 border-b border-gray-100">
          <th class="text-left py-2 font-medium w-24">Version</th>
          <th class="text-left py-2 font-medium">Message</th>
          <th class="text-left py-2 font-medium w-24">Date</th>
        </tr>
      </thead>
      <tbody>
        {% for v in pkg.versions %}
        <tr class="border-b border-gray-50 hover:bg-gray-50 cursor-pointer"
          hx-get="/ui/skills/{{ pkg.name }}/{{ v.version }}/contents"
          hx-target="#version-contents"
          hx-trigger="click">
          <td class="py-2 pr-4 font-mono text-indigo-600 text-xs">{{ v.version }}</td>
          <td class="py-2 pr-4 text-gray-600">{{ v.message }}</td>
          <td class="py-2 text-gray-400 text-xs whitespace-nowrap">{{ v.created_at }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  {% endif %}
</div>
```

- [ ] **Step 4: Run the three new tests**

```bash
cd /home/elon/code/BitBucket/skillhub/server
.venv/bin/pytest tests/test_ui.py::test_skill_detail_shows_contents_section tests/test_ui.py::test_skill_detail_no_contents_shows_placeholder tests/test_ui.py::test_skill_detail_version_rows_have_htmx_contents_get -v
```

Expected: All 3 PASS.

- [ ] **Step 5: Run full test suite (both server and CLI)**

```bash
cd /home/elon/code/BitBucket/skillhub/server
.venv/bin/pytest tests/ -v

cd /home/elon/code/BitBucket/skillhub/cli
.venv/bin/pytest tests/ -v
```

Expected: All tests PASS across both suites.

- [ ] **Step 6: Commit**

```bash
cd /home/elon/code/BitBucket/skillhub
git add server/app/templates/partials/skill_detail.html server/tests/test_ui.py
git commit -m "feat: skill detail drawer shows contents with clickable version rows"
```
