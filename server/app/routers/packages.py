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
        query = query.join(Tag).filter(Tag.tag_name == tag)
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
