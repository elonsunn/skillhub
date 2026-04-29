import yaml
from click.testing import CliRunner
from skillhub.cli import cli


def test_init_creates_yaml(config_dir):
    result = CliRunner().invoke(cli, ["init"])
    assert result.exit_code == 0, result.output
    assert "Created skillhub.yaml" in result.output
    raw = (config_dir / "skillhub.yaml").read_text()
    data = yaml.safe_load(raw)
    assert data["name"] == "my-skill-package"
    assert data["version"] == "1.0.0"
    assert data["description"] == "Describe your skill package"
    assert data["author"] == "your-name"
    assert data["tags"] == ["skill", "automation"]
    assert data["server"] == "http://localhost:8000"
    assert data["including"] == []
    assert data["excluding"] == []
    assert "Package scope control" in raw
    assert "Default behavior" in raw
    assert ".env" in data["ignore"]


def test_init_fails_if_yaml_exists(config_dir):
    (config_dir / "skillhub.yaml").write_text("name: existing")
    result = CliRunner().invoke(cli, ["init"])
    assert result.exit_code != 0
    assert "skillhub.yaml already exists" in result.output


def test_init_template_has_default_tags(config_dir):
    CliRunner().invoke(cli, ["init"])
    data = yaml.safe_load((config_dir / "skillhub.yaml").read_text())
    assert data["tags"] == ["skill", "automation"]


def test_init_creates_local_github_when_parent_has_one(tmp_path, monkeypatch):
    (tmp_path / ".github").mkdir()
    nested = tmp_path / "child" / "project"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)

    result = CliRunner().invoke(cli, ["init"])
    assert result.exit_code == 0, result.output
    assert (nested / ".github" / "skillhub.yaml").exists()
    assert not (tmp_path / ".github" / "skillhub.yaml").exists()
