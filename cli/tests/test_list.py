from unittest.mock import patch
from click.testing import CliRunner
from skillhub.cli import cli


def test_list_online_by_default(config_dir, skillhub_yaml):
    packages = [{"name": "pkg", "latest_version": "2.0.0", "author": "alice",
                 "tags": ["ai"], "description": "desc"}]
    with patch("skillhub.utils.api.list_packages", return_value=packages):
        result = CliRunner().invoke(cli, ["list"])
    assert result.exit_code == 0, result.output
    assert "NAME" in result.output
    assert "VERSION" in result.output
    assert "AUTHOR" in result.output
    assert "pkg" in result.output
    assert "2.0.0" in result.output


def test_list_installed_shows_skills_and_agents(config_dir, skillhub_yaml):
    (config_dir / "skills").mkdir()
    (config_dir / "skills" / "my-tool").mkdir()
    (config_dir / "agents").mkdir()
    (config_dir / "agents" / "my-agent").mkdir()

    result = CliRunner().invoke(cli, ["list", "--installed"])
    assert "TYPE" in result.output
    assert "SKILL NAME" in result.output
    assert "skills" in result.output
    assert "agents" in result.output
    assert "my-tool" in result.output
    assert "my-agent" in result.output


def test_list_uses_env_without_yaml(config_dir, monkeypatch):
    monkeypatch.setenv("SKILLHUB_SERVER", "http://remote:8000")
    packages = [{"name": "p", "latest_version": "1.0.0", "author": "b",
                 "tags": ["t"], "description": "d"}]
    with patch("skillhub.utils.api.list_packages", return_value=packages) as mock_list:
        CliRunner().invoke(cli, ["list"])
    mock_list.assert_called_once_with("http://remote:8000")
