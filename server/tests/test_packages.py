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
