from unittest.mock import patch
from click.testing import CliRunner
from skillhub.cli import cli


def test_list_local_shows_info(config_dir, skillhub_yaml):
    result = CliRunner().invoke(cli, ["list"])
    assert result.exit_code == 0, result.output
    assert "test-pkg" in result.output
    assert "1.0.0" in result.output
    assert "tester" in result.output
    assert "Scope:       all" in result.output


def test_list_local_shows_skills_dir(config_dir, skillhub_yaml):
    (config_dir / "skills").mkdir()
    (config_dir / "skills" / "my-tool").mkdir()
    result = CliRunner().invoke(cli, ["list"])
    assert "skills/" in result.output
    assert "my-tool" in result.output


def test_list_online_calls_api(config_dir, skillhub_yaml):
    packages = [{"name": "pkg", "latest_version": "2.0.0", "author": "alice",
                 "tags": ["ai"], "description": "desc"}]
    with patch("skillhub.utils.api.list_packages", return_value=packages):
        result = CliRunner().invoke(cli, ["list", "--online"])
    assert result.exit_code == 0
    assert "pkg" in result.output
    assert "2.0.0" in result.output


def test_list_online_uses_env_without_yaml(config_dir, monkeypatch):
    monkeypatch.setenv("SKILLHUB_SERVER", "http://remote:8000")
    packages = [{"name": "p", "latest_version": "1.0.0", "author": "b",
                 "tags": ["t"], "description": "d"}]
    with patch("skillhub.utils.api.list_packages", return_value=packages) as mock_list:
        CliRunner().invoke(cli, ["list", "--online"])
    mock_list.assert_called_once_with("http://remote:8000")
