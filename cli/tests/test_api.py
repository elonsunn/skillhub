import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from skillhub.utils.api import (
    SkillHubAPIError,
    list_packages,
    get_package,
    download_package,
    push_package,
)


def _resp(status, json_data=None, content=b""):
    m = MagicMock()
    m.status_code = status
    m.ok = status < 400
    m.json.return_value = json_data or {}
    m.content = content
    m.text = str(json_data)
    return m


def test_error_attributes():
    err = SkillHubAPIError(404, "Not found")
    assert err.status_code == 404
    assert err.detail == "Not found"


def test_list_packages_success():
    with patch("requests.get", return_value=_resp(200, [{"name": "pkg"}])) as mock_get:
        result = list_packages("http://s", search="pkg", tag="ai")
    assert result == [{"name": "pkg"}]
    mock_get.assert_called_once_with(
        "http://s/api/packages", params={"search": "pkg", "tag": "ai"}
    )


def test_list_packages_error_raises():
    with patch("requests.get", return_value=_resp(500, {"detail": "oops"})):
        with pytest.raises(SkillHubAPIError) as exc:
            list_packages("http://s")
    assert exc.value.status_code == 500


def test_get_package_success():
    with patch("requests.get", return_value=_resp(200, {"name": "pkg", "versions": []})):
        result = get_package("http://s", "pkg")
    assert result["name"] == "pkg"


def test_get_package_404_returns_none():
    with patch("requests.get", return_value=_resp(404)):
        assert get_package("http://s", "missing") is None


def test_download_package_returns_bytes():
    with patch("requests.get", return_value=_resp(200, content=b"zipdata")):
        assert download_package("http://s", "pkg", "1.0.0") == b"zipdata"


def test_push_package_success(tmp_path):
    zip_path = tmp_path / "pkg.zip"
    zip_path.write_bytes(b"data")
    with patch("requests.post", return_value=_resp(200, {"name": "pkg", "version": "1.0.1"})) as mock_post:
        result = push_package("http://s", "pkg", zip_path, {"version": "1.0.1"})
    assert result["version"] == "1.0.1"
    assert mock_post.called
