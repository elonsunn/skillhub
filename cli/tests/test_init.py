import yaml
from click.testing import CliRunner
from skillhub.cli import cli


def test_init_creates_yaml(config_dir):
    result = CliRunner().invoke(
        cli, ["init"],
        input="my-pkg\nMy description\nauthor\ntag1, tag2\nhttp://localhost:8000\n",
    )
    assert result.exit_code == 0, result.output
    assert "Created skillhub.yaml" in result.output
    data = yaml.safe_load((config_dir / "skillhub.yaml").read_text())
    assert data["name"] == "my-pkg"
    assert data["version"] == "1.0.0"
    assert data["description"] == "My description"
    assert data["author"] == "author"
    assert data["tags"] == ["tag1", "tag2"]
    assert data["server"] == "http://localhost:8000"
    assert ".env" in data["ignore"]


def test_init_fails_if_yaml_exists(config_dir):
    (config_dir / "skillhub.yaml").write_text("name: existing")
    result = CliRunner().invoke(cli, ["init"], input="p\nd\na\nt\nhttp://s\n")
    assert result.exit_code != 0
    assert "skillhub.yaml already exists" in result.output


def test_init_tags_comma_separated(config_dir):
    CliRunner().invoke(cli, ["init"], input="p\nd\na\npython, ai, copilot\nhttp://s\n")
    data = yaml.safe_load((config_dir / "skillhub.yaml").read_text())
    assert data["tags"] == ["python", "ai", "copilot"]
