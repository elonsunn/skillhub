import os
import secrets
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from packaging.version import Version as SemVer
from sqlalchemy.orm import Session

from app.database import Package, get_db

router = APIRouter()
security = HTTPBasic()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

STORAGE_ROOT = os.getenv("STORAGE_ROOT", "storage")


def _require_admin(credentials: HTTPBasicCredentials = Depends(security)):
    expected_user = os.getenv("ADMIN_USERNAME", "admin").encode()
    expected_pass = os.getenv("ADMIN_PASSWORD", "admin").encode()
    user_ok = secrets.compare_digest(credentials.username.encode(), expected_user)
    pass_ok = secrets.compare_digest(credentials.password.encode(), expected_pass)
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )


@router.get("/admin", response_class=HTMLResponse)
def admin_page(
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(_require_admin),
):
    packages = db.query(Package).order_by(Package.name).all()
    pkgs_data = [
        {
            "name": p.name,
            "description": p.description or "",
            "author": p.author or "",
            "version_count": len(p.versions),
            "latest_version": (
                max(p.versions, key=lambda v: SemVer(v.version)).version
                if p.versions
                else None
            ),
            "created_at": p.created_at.strftime("%Y-%m-%d") if p.created_at else "",
            "tags": [t.tag_name for t in p.tags],
        }
        for p in packages
    ]
    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={"packages": pkgs_data},
    )


@router.delete("/admin/skills/{name}", response_class=HTMLResponse)
def delete_skill(
    name: str,
    db: Session = Depends(get_db),
    _: None = Depends(_require_admin),
):
    pkg = db.query(Package).filter(Package.name == name).first()
    if not pkg:
        raise HTTPException(status_code=404, detail=f"Package '{name}' not found")

    # Delete version files from storage
    for ver in pkg.versions:
        file_path = Path(STORAGE_ROOT) / ver.file_path
        file_path.unlink(missing_ok=True)

    # Remove the package's storage directory if it exists
    pkg_dir = Path(STORAGE_ROOT) / name
    if pkg_dir.is_dir():
        shutil.rmtree(pkg_dir, ignore_errors=True)

    db.delete(pkg)
    db.commit()

    # Return empty so htmx swaps the row out
    return HTMLResponse(content="", status_code=200)
