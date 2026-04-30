import yaml
from click.testing import CliRunner
from skillhub.cli import cli


def test_build_success(config_dir, skillhub_yaml):
    (config_dir / "agents").mkdir()
    (config_dir / "agents" / "reviewer.md").write_text("agent")
    result = CliRunner().invoke(cli, ["build"])
    assert result.exit_code == 0, result.output
    assert "Built" in result.output
    assert "test-pkg.zip" in result.output


def test_build_empty_tags_error(config_dir):
    (config_dir / "skillhub.yaml").write_text(
        yaml.dump({"name": "p", "version": "1.0.0", "tags": [], "author": "a"})
    )
    result = CliRunner().invoke(cli, ["build"])
    assert result.exit_code != 0
    assert "tags must not be empty" in result.output
