import io
import zipfile
from unittest.mock import patch
from click.testing import CliRunner
from skillhub.cli import cli


def _make_zip(*files):
    """files: list of (arcname, content_str)"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for arcname, content in files:
            zf.writestr(arcname, content)
    return buf.getvalue()


def test_pull_extracts_files(config_dir, skillhub_yaml):
    zip_bytes = _make_zip(("skills/tool/SKILL.md", "# Tool"))
    with patch("skillhub.utils.api.download_package", return_value=zip_bytes):
        result = CliRunner().invoke(cli, ["pull", "some-pkg"])
    assert result.exit_code == 0, result.output
    assert (config_dir / "skills" / "tool" / "SKILL.md").read_text() == "# Tool"


def test_pull_uses_latest_by_default(config_dir, skillhub_yaml):
    zip_bytes = _make_zip(("agents/r.md", "agent"))
    with patch("skillhub.utils.api.download_package", return_value=zip_bytes) as mock_dl:
        CliRunner().invoke(cli, ["pull", "some-pkg"])
    mock_dl.assert_called_once_with("http://localhost:8000", "some-pkg", "latest")


def test_pull_specific_version(config_dir, skillhub_yaml):
    zip_bytes = _make_zip(("agents/r.md", "agent"))
    with patch("skillhub.utils.api.download_package", return_value=zip_bytes) as mock_dl:
        CliRunner().invoke(cli, ["pull", "some-pkg", "--version", "1.2.0"])
    mock_dl.assert_called_once_with("http://localhost:8000", "some-pkg", "1.2.0")


def test_pull_conflict_error(config_dir, skillhub_yaml):
    (config_dir / "skills").mkdir()
    (config_dir / "skills" / "tool").mkdir()
    (config_dir / "skills" / "tool" / "SKILL.md").write_text("existing")
    zip_bytes = _make_zip(("skills/tool/SKILL.md", "new"))
    with patch("skillhub.utils.api.download_package", return_value=zip_bytes):
        result = CliRunner().invoke(cli, ["pull", "some-pkg"])
    assert result.exit_code != 0
    assert "conflicting files" in result.output
    assert "skills/tool/SKILL.md" in result.output


def test_pull_shows_setup_notice(config_dir, skillhub_yaml):
    zip_bytes = _make_zip(
        ("skills/ppt/SKILL.md", "skill"),
        ("skills/ppt/SETUP.md", "setup instructions"),
    )
    with patch("skillhub.utils.api.download_package", return_value=zip_bytes):
        result = CliRunner().invoke(cli, ["pull", "some-pkg"])
    assert result.exit_code == 0
    assert "SETUP.md" in result.output
    assert "skillhub setup" in result.output


def test_pull_api_error(config_dir, skillhub_yaml):
    from skillhub.utils.api import SkillHubAPIError
    with patch("skillhub.utils.api.download_package",
               side_effect=SkillHubAPIError(404, "Package not found")):
        result = CliRunner().invoke(cli, ["pull", "no-such-pkg"])
    assert result.exit_code != 0
    assert "Package not found" in result.output


def test_pull_rejects_path_traversal(config_dir, skillhub_yaml):
    zip_bytes = _make_zip(("../outside.txt", "malicious"))
    with patch("skillhub.utils.api.download_package", return_value=zip_bytes):
        result = CliRunner().invoke(cli, ["pull", "some-pkg"])
    assert result.exit_code != 0
    assert "unsafe path" in result.output
