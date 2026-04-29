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
