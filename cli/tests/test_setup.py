from click.testing import CliRunner
from skillhub.cli import cli


def test_setup_prints_content(config_dir):
    (config_dir / "skills").mkdir()
    (config_dir / "skills" / "ppt-gen").mkdir()
    (config_dir / "skills" / "ppt-gen" / "SETUP.md").write_text("# Config\nDo stuff.")
    result = CliRunner().invoke(cli, ["setup", "ppt-gen"])
    assert result.exit_code == 0
    assert "# Config" in result.output
    assert "Send this to your AI assistant" in result.output


def test_setup_not_found(config_dir):
    result = CliRunner().invoke(cli, ["setup", "nonexistent"])
    assert result.exit_code == 0
    assert "No setup guide found." in result.output


def test_setup_multiple_matches(config_dir):
    (config_dir / "skills").mkdir()
    (config_dir / "skills" / "tool-a").mkdir()
    (config_dir / "skills" / "tool-a" / "SETUP.md").write_text("setup A")
    (config_dir / "skills" / "tool-b").mkdir()
    (config_dir / "skills" / "tool-b" / "SETUP.md").write_text("setup B")
    result = CliRunner().invoke(cli, ["setup", "skills"])
    assert result.exit_code == 0
    assert "setup A" in result.output
    assert "setup B" in result.output
    assert "Send this to your AI assistant" in result.output
