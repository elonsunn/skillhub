from unittest.mock import patch
from click.testing import CliRunner
from skillhub.cli import cli


def _pkg(versions=None):
    return {
        "name": "my-skill",
        "description": "A great skill",
        "author": "alice",
        "tags": ["copilot", "review"],
        "versions": versions or [
            {
                "version": "1.2.0",
                "message": "added formatter",
                "created_at": "2026-04-30T10:00:00",
                "contents": ["skills/skilla", "agents/my-agent"],
            },
            {
                "version": "1.1.0",
                "message": "initial release",
                "created_at": "2026-04-15T10:00:00",
                "contents": ["skills/skilla"],
            },
        ],
    }


def test_info_shows_package_metadata(config_dir, skillhub_yaml):
    with patch("skillhub.utils.api.get_package", return_value=_pkg()):
        result = CliRunner().invoke(cli, ["info", "my-skill"])
    assert result.exit_code == 0, result.output
    assert "my-skill" in result.output
    assert "A great skill" in result.output
    assert "alice" in result.output
    assert "copilot" in result.output


def test_info_shows_latest_version_contents(config_dir, skillhub_yaml):
    with patch("skillhub.utils.api.get_package", return_value=_pkg()):
        result = CliRunner().invoke(cli, ["info", "my-skill"])
    assert "1.2.0" in result.output
    assert "skills/skilla" in result.output
    assert "agents/my-agent" in result.output


def test_info_version_flag_shows_that_versions_contents(config_dir, skillhub_yaml):
    with patch("skillhub.utils.api.get_package", return_value=_pkg()):
        result = CliRunner().invoke(cli, ["info", "my-skill", "--version", "1.1.0"])
    assert result.exit_code == 0, result.output
    assert "1.1.0" in result.output
    assert "skills/skilla" in result.output
    assert "agents/my-agent" not in result.output


def test_info_shows_version_history(config_dir, skillhub_yaml):
    with patch("skillhub.utils.api.get_package", return_value=_pkg()):
        result = CliRunner().invoke(cli, ["info", "my-skill"])
    assert "1.2.0" in result.output
    assert "1.1.0" in result.output
    assert "added formatter" in result.output
    assert "initial release" in result.output


def test_info_package_not_found(config_dir, skillhub_yaml):
    with patch("skillhub.utils.api.get_package", return_value=None):
        result = CliRunner().invoke(cli, ["info", "ghost"])
    assert result.exit_code != 0
    assert "not found" in result.output.lower()


def test_info_version_not_found(config_dir, skillhub_yaml):
    with patch("skillhub.utils.api.get_package", return_value=_pkg()):
        result = CliRunner().invoke(cli, ["info", "my-skill", "--version", "9.9.9"])
    assert result.exit_code != 0
    assert "9.9.9" in result.output
    assert "not found" in result.output.lower()


def test_info_empty_contents_shows_placeholder(config_dir, skillhub_yaml):
    pkg = _pkg(versions=[{
        "version": "1.0.0", "message": "init",
        "created_at": "2026-01-01T00:00:00", "contents": [],
    }])
    with patch("skillhub.utils.api.get_package", return_value=pkg):
        result = CliRunner().invoke(cli, ["info", "my-skill"])
    assert "no contents recorded" in result.output.lower()
