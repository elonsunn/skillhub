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
            }
            for v in sorted(pkg.versions, key=lambda v: SemVer(v.version), reverse=True)
        ],
    }
