import yaml
from unittest.mock import patch
from click.testing import CliRunner
from skillhub.cli import cli


def _server_pkg(latest_version):
    return {
        "name": "test-pkg",
        "versions": [{"version": latest_version, "message": "prior", "created_at": "2026-01-01"}],
    }


def test_push_new_package_uses_yaml_version(config_dir, skillhub_yaml):
    with patch("skillhub.utils.api.get_package", return_value=None), \
         patch("skillhub.utils.api.push_package", return_value={"name": "test-pkg", "version": "1.0.0"}):
        result = CliRunner().invoke(cli, ["push", "-m", "initial release"])
    assert result.exit_code == 0, result.output
    assert "Pushed test-pkg@1.0.0" in result.output


def test_push_existing_package_bumps_patch(config_dir, skillhub_yaml):
    with patch("skillhub.utils.api.get_package", return_value=_server_pkg("1.0.2")), \
         patch("skillhub.utils.api.push_package", return_value={"name": "test-pkg", "version": "1.0.3"}):
        result = CliRunner().invoke(cli, ["push", "-m", "update"])
    assert result.exit_code == 0, result.output
    assert "Pushed test-pkg@1.0.3" in result.output
    assert yaml.safe_load((config_dir / "skillhub.yaml").read_text())["version"] == "1.0.3"


def test_push_empty_tags_error(config_dir):
    (config_dir / "skillhub.yaml").write_text(
        yaml.dump({"name": "p", "version": "1.0.0", "tags": [], "author": "a",
                   "server": "http://s"})
    )
    result = CliRunner().invoke(cli, ["push", "-m", "msg"])
    assert result.exit_code != 0
    assert "tags must not be empty" in result.output


def test_push_api_error_shows_warning(config_dir, skillhub_yaml):
    from skillhub.utils.api import SkillHubAPIError
    with patch("skillhub.utils.api.get_package", return_value=None), \
         patch("skillhub.utils.api.push_package",
               side_effect=SkillHubAPIError(409, "Version conflict")):
        result = CliRunner().invoke(cli, ["push", "-m", "fail"])
    assert result.exit_code != 0
    assert "Warning: local skillhub.yaml version was updated" in result.output
    assert "Version conflict" in result.output


def test_push_requires_message():
    result = CliRunner().invoke(cli, ["push"])
    assert result.exit_code != 0
