from app.database import Package, Version, Tag


def test_package_model_relationships(db_session):
    pkg = Package(name="test-pkg", description="A test package", author="alice")
    db_session.add(pkg)
    db_session.flush()

    db_session.add(Tag(package_id=pkg.id, tag_name="copilot"))
    db_session.add(Version(
        package_id=pkg.id, version="1.0.0",
        message="initial release", file_path="test-pkg/1.0.0.zip"
    ))
    db_session.commit()

    result = db_session.query(Package).filter_by(name="test-pkg").first()
    assert result is not None
    assert result.description == "A test package"
    assert len(result.tags) == 1
    assert result.tags[0].tag_name == "copilot"
    assert len(result.versions) == 1
    assert result.versions[0].version == "1.0.0"


def test_list_packages_empty(client):
    response = client.get("/api/packages")
    assert response.status_code == 200
    assert response.json() == []


def test_list_packages_returns_summary(client, db_session):
    from app.database import Package, Version, Tag
    pkg = Package(name="my-config", description="Team config", author="alice")
    db_session.add(pkg)
    db_session.flush()
    db_session.add(Tag(package_id=pkg.id, tag_name="copilot"))
    db_session.add(Version(
        package_id=pkg.id, version="1.0.0",
        message="init", file_path="my-config/1.0.0.zip"
    ))
    db_session.commit()

    response = client.get("/api/packages")
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "my-config"
    assert data[0]["author"] == "alice"
    assert data[0]["latest_version"] == "1.0.0"
    assert "copilot" in data[0]["tags"]


def test_list_packages_search_by_name(client, db_session):
    from app.database import Package
    db_session.add(Package(name="copilot-tools", description="", author="alice"))
    db_session.add(Package(name="review-agents", description="", author="bob"))
    db_session.commit()

    response = client.get("/api/packages?search=copilot")
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "copilot-tools"


def test_list_packages_search_by_description(client, db_session):
    from app.database import Package
    db_session.add(Package(name="pkg-a", description="code review tools", author="alice"))
    db_session.add(Package(name="pkg-b", description="ppt generation", author="bob"))
    db_session.commit()

    response = client.get("/api/packages?search=review")
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "pkg-a"


def test_list_packages_filter_by_tag(client, db_session):
    from app.database import Package, Tag
    pkg1 = Package(name="pkg-a", description="", author="alice")
    pkg2 = Package(name="pkg-b", description="", author="bob")
    db_session.add_all([pkg1, pkg2])
    db_session.flush()
    db_session.add(Tag(package_id=pkg1.id, tag_name="copilot"))
    db_session.add(Tag(package_id=pkg2.id, tag_name="review"))
    db_session.commit()

    response = client.get("/api/packages?tag=copilot")
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "pkg-a"


def test_get_package_not_found(client):
    response = client.get("/api/packages/nonexistent")
    assert response.status_code == 404


def test_get_package_detail(client, db_session):
    from app.database import Package, Version, Tag
    pkg = Package(name="my-pkg", description="My package", author="tom")
    db_session.add(pkg)
    db_session.flush()
    db_session.add(Tag(package_id=pkg.id, tag_name="copilot"))
    db_session.add(Version(
        package_id=pkg.id, version="1.0.0",
        message="initial release", file_path="my-pkg/1.0.0.zip"
    ))
    db_session.add(Version(
        package_id=pkg.id, version="1.1.0",
        message="add feature", file_path="my-pkg/1.1.0.zip"
    ))
    db_session.commit()

    response = client.get("/api/packages/my-pkg")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "my-pkg"
    assert data["author"] == "tom"
    assert "copilot" in data["tags"]
    assert len(data["versions"]) == 2
    assert data["versions"][0]["version"] == "1.1.0"  # newest first
    assert data["versions"][1]["version"] == "1.0.0"


def test_get_package_with_no_versions(client, db_session):
    from app.database import Package
    pkg = Package(name="empty-pkg", description="No versions yet", author="alice")
    db_session.add(pkg)
    db_session.commit()

    response = client.get("/api/packages/empty-pkg")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "empty-pkg"
    assert data["versions"] == []


def test_download_specific_version(client, db_session, tmp_path):
    from app.database import Package, Version
    zip_content = b"PK\x03\x04fake zip content"
    pkg = Package(name="dl-pkg", description="", author="")
    db_session.add(pkg)
    db_session.flush()

    zip_path = tmp_path / "dl-pkg" / "1.0.0.zip"
    zip_path.parent.mkdir(parents=True)
    zip_path.write_bytes(zip_content)

    db_session.add(Version(
        package_id=pkg.id, version="1.0.0",
        message="init", file_path="dl-pkg/1.0.0.zip"
    ))
    db_session.commit()

    response = client.get("/api/packages/dl-pkg/1.0.0")
    assert response.status_code == 200
    assert "zip" in response.headers["content-type"]
    assert response.content == zip_content


def test_download_latest_resolves_highest_semver(client, db_session, tmp_path):
    from app.database import Package, Version
    pkg = Package(name="ver-pkg", description="", author="")
    db_session.add(pkg)
    db_session.flush()

    for ver in ["1.0.0", "2.0.0", "1.9.0"]:
        p = tmp_path / "ver-pkg" / f"{ver}.zip"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(f"content-{ver}".encode())
        db_session.add(Version(
            package_id=pkg.id, version=ver,
            message="msg", file_path=f"ver-pkg/{ver}.zip"
        ))
    db_session.commit()

    response = client.get("/api/packages/ver-pkg/latest")
    assert response.status_code == 200
    assert response.content == b"content-2.0.0"


def test_download_package_not_found(client):
    response = client.get("/api/packages/ghost/1.0.0")
    assert response.status_code == 404


def test_download_version_not_found(client, db_session):
    from app.database import Package
    pkg = Package(name="exists-pkg", description="", author="")
    db_session.add(pkg)
    db_session.commit()

    response = client.get("/api/packages/exists-pkg/9.9.9")
    assert response.status_code == 404


import io
import json as _json
import zipfile


def _make_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("skills/hello/SKILL.md", "# Hello")
    return buf.getvalue()


def test_push_creates_new_package(client):
    meta = _json.dumps({
        "version": "1.0.0", "message": "initial release",
        "description": "My package", "author": "alice", "tags": ["copilot"],
    })
    response = client.post(
        "/api/packages/new-pkg",
        data={"metadata": meta},
        files={"file": ("new-pkg.zip", _make_zip(), "application/zip")},
    )
    assert response.status_code == 200
    assert response.json() == {"name": "new-pkg", "version": "1.0.0"}


def test_push_new_version_on_existing_package(client):
    zip_data = _make_zip()
    meta_v1 = _json.dumps({"version": "1.0.0", "message": "init", "description": "", "author": "", "tags": ["t"]})
    meta_v2 = _json.dumps({"version": "1.0.1", "message": "fix", "description": "", "author": "", "tags": ["t"]})

    client.post("/api/packages/bump-pkg", data={"metadata": meta_v1}, files={"file": ("f.zip", zip_data, "application/zip")})
    response = client.post("/api/packages/bump-pkg", data={"metadata": meta_v2}, files={"file": ("f.zip", zip_data, "application/zip")})

    assert response.status_code == 200
    assert response.json()["version"] == "1.0.1"


def test_push_empty_tags_rejected(client):
    meta = _json.dumps({"version": "1.0.0", "message": "init", "description": "", "author": "", "tags": []})
    response = client.post(
        "/api/packages/no-tags",
        data={"metadata": meta},
        files={"file": ("f.zip", _make_zip(), "application/zip")},
    )
    assert response.status_code == 400


def test_push_same_version_rejected(client):
    zip_data = _make_zip()
    meta = _json.dumps({"version": "1.0.0", "message": "init", "description": "", "author": "", "tags": ["t"]})

    client.post("/api/packages/dup-pkg", data={"metadata": meta}, files={"file": ("f.zip", zip_data, "application/zip")})
    response = client.post("/api/packages/dup-pkg", data={"metadata": meta}, files={"file": ("f.zip", zip_data, "application/zip")})

    assert response.status_code == 409


def test_push_older_version_rejected(client):
    zip_data = _make_zip()
    meta_v2 = _json.dumps({"version": "2.0.0", "message": "v2", "description": "", "author": "", "tags": ["t"]})
    meta_v1 = _json.dumps({"version": "1.0.0", "message": "old", "description": "", "author": "", "tags": ["t"]})

    client.post("/api/packages/downgrade-pkg", data={"metadata": meta_v2}, files={"file": ("f.zip", zip_data, "application/zip")})
    response = client.post("/api/packages/downgrade-pkg", data={"metadata": meta_v1}, files={"file": ("f.zip", zip_data, "application/zip")})

    assert response.status_code == 409


def test_push_tags_replaced_on_new_version(client):
    zip_data = _make_zip()
    meta_v1 = _json.dumps({"version": "1.0.0", "message": "init", "description": "", "author": "", "tags": ["old-tag"]})
    meta_v2 = _json.dumps({"version": "1.0.1", "message": "update", "description": "", "author": "", "tags": ["new-tag"]})

    client.post("/api/packages/tag-pkg", data={"metadata": meta_v1}, files={"file": ("f.zip", zip_data, "application/zip")})
    client.post("/api/packages/tag-pkg", data={"metadata": meta_v2}, files={"file": ("f.zip", zip_data, "application/zip")})

    response = client.get("/api/packages/tag-pkg")
    tags = response.json()["tags"]
    assert "new-tag" in tags
    assert "old-tag" not in tags


def test_push_zip_stored_and_downloadable(client):
    zip_data = _make_zip()
    meta = _json.dumps({"version": "1.0.0", "message": "init", "description": "", "author": "", "tags": ["t"]})

    client.post("/api/packages/stored-pkg", data={"metadata": meta}, files={"file": ("f.zip", zip_data, "application/zip")})

    response = client.get("/api/packages/stored-pkg/1.0.0")
    assert response.status_code == 200
    assert response.content == zip_data


def test_push_invalid_metadata_json_rejected(client):
    response = client.post(
        "/api/packages/bad-meta",
        data={"metadata": "not-valid-json"},
        files={"file": ("f.zip", _make_zip(), "application/zip")},
    )
    assert response.status_code == 422


def test_push_missing_version_rejected(client):
    meta = _json.dumps({"message": "no version", "description": "", "author": "", "tags": ["t"]})
    response = client.post(
        "/api/packages/missing-ver",
        data={"metadata": meta},
        files={"file": ("f.zip", _make_zip(), "application/zip")},
    )
    assert response.status_code == 422


def test_push_invalid_semver_rejected(client):
    meta = _json.dumps({"version": "not-semver", "message": "bad", "description": "", "author": "", "tags": ["t"]})
    response = client.post(
        "/api/packages/bad-semver",
        data={"metadata": meta},
        files={"file": ("f.zip", _make_zip(), "application/zip")},
    )
    assert response.status_code == 422
