from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from packaging.version import Version as SemVer
from sqlalchemy.orm import Session

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
