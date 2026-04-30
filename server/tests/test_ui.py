import json
from app.database import Package, Tag, Version


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


def test_skill_grid_returns_skills(client, db_session):
    _seed_pkg(db_session)
    response = client.get("/ui/skills")
    assert response.status_code == 200
    assert "my-skill" in response.text


def test_skill_grid_search_by_name(client, db_session):
    _seed_pkg(db_session, name="copilot-tools")
    _seed_pkg(db_session, name="review-agents")
    response = client.get("/ui/skills?search=copilot")
    assert "copilot-tools" in response.text
    assert "review-agents" not in response.text


def test_skill_grid_search_by_description(client, db_session):
    _seed_pkg(db_session, name="pkg-a", description="code review tools")
    _seed_pkg(db_session, name="pkg-b", description="presentation tools")
    response = client.get("/ui/skills?search=review")
    assert "pkg-a" in response.text
    assert "pkg-b" not in response.text


def test_skill_grid_filter_by_tag(client, db_session):
    _seed_pkg(db_session, name="pkg-a", tag="copilot")
    _seed_pkg(db_session, name="pkg-b", tag="review")
    response = client.get("/ui/skills?tag=copilot")
    assert "pkg-a" in response.text
    assert "pkg-b" not in response.text


def test_skill_grid_empty(client):
    response = client.get("/ui/skills")
    assert response.status_code == 200
    assert "No skills found" in response.text


def test_skill_detail_returns_fragment(client, db_session):
    _seed_pkg(db_session, name="my-skill", description="A great skill",
              author="alice", version="1.2.0")
    response = client.get("/ui/skills/my-skill")
    assert response.status_code == 200
    assert "my-skill" in response.text
    assert "alice" in response.text
    assert "1.2.0" in response.text
    assert "skillhub pull my-skill" in response.text
    assert "initial release" in response.text


def test_skill_detail_not_found(client):
    response = client.get("/ui/skills/nonexistent")
    assert response.status_code == 404


def test_empty_route_returns_empty(client):
    response = client.get("/ui/empty")
    assert response.status_code == 200
    assert response.text == ""


def test_skill_grid_filter_by_multiple_tags_and(client, db_session):
    # pkg-a: copilot + review (should appear)
    # pkg-b: copilot only (should be excluded — missing review)
    # pkg-c: review only (should be excluded — missing copilot)
    pkg_a = Package(name="pkg-a", description="", author="")
    pkg_b = Package(name="pkg-b", description="", author="")
    pkg_c = Package(name="pkg-c", description="", author="")
    db_session.add_all([pkg_a, pkg_b, pkg_c])
    db_session.flush()
    db_session.add(Tag(package_id=pkg_a.id, tag_name="copilot"))
    db_session.add(Tag(package_id=pkg_a.id, tag_name="review"))
    db_session.add(Tag(package_id=pkg_b.id, tag_name="copilot"))
    db_session.add(Tag(package_id=pkg_c.id, tag_name="review"))
    for pkg in [pkg_a, pkg_b, pkg_c]:
        db_session.add(Version(package_id=pkg.id, version="1.0.0", message="init", file_path=f"{pkg.name}/1.0.0.zip"))
    db_session.commit()
    response = client.get("/ui/skills?tag=copilot&tag=review")
    assert "pkg-a" in response.text
    assert "pkg-b" not in response.text
    assert "pkg-c" not in response.text


def test_skill_grid_no_tags_returns_all(client, db_session):
    _seed_pkg(db_session, name="pkg-a")
    _seed_pkg(db_session, name="pkg-b")
    response = client.get("/ui/skills")
    assert "pkg-a" in response.text
    assert "pkg-b" in response.text


def test_index_has_drawer_elements(client):
    response = client.get("/")
    assert 'id="drawer"' in response.text
    assert 'id="drawer-backdrop"' in response.text
    assert 'id="drawer-content"' in response.text


def test_skill_card_targets_drawer(client, db_session):
    _seed_pkg(db_session, name="my-skill")
    response = client.get("/ui/skills")
    assert 'hx-target="#drawer-content"' in response.text


def test_skill_detail_close_targets_drawer(client, db_session):
    _seed_pkg(db_session, name="my-skill")
    response = client.get("/ui/skills/my-skill")
    assert 'hx-target="#drawer-content"' in response.text


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
    pkg = Package(name="empty-frag", description="", author="")
    db_session.add(pkg)
    db_session.flush()
    db_session.add(Version(
        package_id=pkg.id, version="1.0.0",
        message="init", file_path="empty-frag/1.0.0.zip",
    ))
    db_session.commit()
    response = client.get("/ui/skills/empty-frag/1.0.0/contents")
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
