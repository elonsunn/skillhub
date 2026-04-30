from app.database import Package, Tag, Version


def _seed_pkg(db_session, name="my-skill", description="A skill", author="alice",
              tag="copilot", version="1.0.0"):
    pkg = Package(name=name, description=description, author=author)
    db_session.add(pkg)
    db_session.flush()
    db_session.add(Tag(package_id=pkg.id, tag_name=tag))
    db_session.add(Version(
        package_id=pkg.id, version=version,
        message="initial release", file_path=f"{name}/{version}.zip",
    ))
    db_session.commit()
    return pkg


def test_index_returns_200(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "SkillHub" in response.text


def test_index_renders_all_tags(client, db_session):
    _seed_pkg(db_session, name="pkg-a", tag="copilot")
    _seed_pkg(db_session, name="pkg-b", tag="review")
    response = client.get("/")
    assert "copilot" in response.text
    assert "review" in response.text
