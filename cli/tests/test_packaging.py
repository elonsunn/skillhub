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


def test_excluding_removes_paths(pkg_dir):
    names = _names(build_zip(pkg_dir, {"name": "mypkg", "tags": ["t"], "excluding": ["agents"]}))
    assert "agents/reviewer.md" not in names
    assert "copilot-instructions.md" in names


def test_both_including_and_excluding_raises(pkg_dir):
    with pytest.raises(click.ClickException, match="Cannot use both"):
        build_zip(pkg_dir, {"name": "mypkg", "tags": ["t"], "including": ["skills"], "excluding": ["agents"]})


def test_ignore_rules_applied(pkg_dir):
    (pkg_dir / ".env").write_text("SECRET=abc")
    names = _names(build_zip(pkg_dir, {"name": "mypkg", "tags": ["t"], "ignore": [".env"]}))
    assert ".env" not in names
    assert "copilot-instructions.md" in names


def test_zip_path_uses_package_name(pkg_dir):
    zip_path = build_zip(pkg_dir, {"name": "my-awesome-pkg", "tags": ["t"]})
    assert zip_path == pkg_dir.parent / "my-awesome-pkg.zip"
    assert zip_path.exists()
