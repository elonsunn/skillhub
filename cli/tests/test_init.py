import yaml
from click.testing import CliRunner
from skillhub.cli import cli


def test_init_creates_yaml(config_dir):
    result = CliRunner().invoke(cli, ["init"])
    assert result.exit_code == 0, result.output
    assert "Created skillhub.yaml" in result.output
    data = yaml.safe_load((config_dir / "skillhub.yaml").read_text())
    assert data["name"] == "my-skill-package"
    assert data["version"] == "1.0.0"
    assert data["server"] == "http://localhost:8000"
    assert data["tags"] == ["skill", "automation"]
    assert "excluding" not in data
    assert data["ignore"] == [".env", "*.env", "config.json"]


def test_init_including_empty_when_dir_is_empty(config_dir):
    result = CliRunner().invoke(cli, ["init"])
    assert result.exit_code == 0, result.output
    data = yaml.safe_load((config_dir / "skillhub.yaml").read_text())
    assert data["including"] == []


def test_init_auto_populates_including(config_dir):
    (config_dir / "skills").mkdir()
    (config_dir / "skills" / "my-tool").mkdir()
    (config_dir / "skills" / "my-tool" / "SKILL.md").write_text("skill")
    (config_dir / "agents").mkdir()
    (config_dir / "agents" / "reviewer").mkdir()
    (config_dir / "agents" / "reviewer" / "config.yaml").write_text("agent")
    (config_dir / "SETUP.md").write_text("setup")

    result = CliRunner().invoke(cli, ["init"])
    assert result.exit_code == 0, result.output
    data = yaml.safe_load((config_dir / "skillhub.yaml").read_text())
    assert "agents/reviewer" in data["including"]
    assert "skills/my-tool" in data["including"]
    assert "SETUP.md" in data["including"]


def test_init_does_not_include_skillhub_yaml_in_scan(config_dir):
    (config_dir / "skills" / "foo").mkdir(parents=True)
    result = CliRunner().invoke(cli, ["init"])
    assert result.exit_code == 0, result.output
    data = yaml.safe_load((config_dir / "skillhub.yaml").read_text())
    assert "skillhub.yaml" not in data["including"]


def test_init_fails_if_yaml_exists(config_dir):
    (config_dir / "skillhub.yaml").write_text("name: existing")
    result = CliRunner().invoke(cli, ["init"])
    assert result.exit_code != 0
    assert "skillhub.yaml already exists" in result.output


def test_init_creates_local_github_when_parent_has_one(tmp_path, monkeypatch):
    (tmp_path / ".github").mkdir()
    nested = tmp_path / "child" / "project"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)

    result = CliRunner().invoke(cli, ["init"])
    assert result.exit_code == 0, result.output
    assert (nested / ".github" / "skillhub.yaml").exists()
    assert not (tmp_path / ".github" / "skillhub.yaml").exists()
