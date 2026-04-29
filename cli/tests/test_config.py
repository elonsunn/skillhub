import pytest
import yaml
import click
from skillhub.utils.config import load_config, save_config, get_server_url


def test_load_config_success(tmp_path):
    d = tmp_path / ".github"
    d.mkdir()
    (d / "skillhub.yaml").write_text("name: mypkg\nversion: 1.0.0\n")
    config = load_config(d)
    assert config["name"] == "mypkg"
    assert config["version"] == "1.0.0"


def test_load_config_missing_raises(tmp_path):
    d = tmp_path / ".github"
    d.mkdir()
    with pytest.raises(click.ClickException, match="No skillhub.yaml found"):
        load_config(d)


def test_load_config_invalid_yaml_raises(tmp_path):
    d = tmp_path / ".github"
    d.mkdir()
    (d / "skillhub.yaml").write_text(": bad: yaml: [")
    with pytest.raises(click.ClickException, match="Invalid skillhub.yaml"):
        load_config(d)


def test_save_config_roundtrip(tmp_path):
    d = tmp_path / ".github"
    d.mkdir()
    data = {"name": "mypkg", "tags": ["ai"]}
    save_config(d, data)
    loaded = yaml.safe_load((d / "skillhub.yaml").read_text())
    assert loaded["name"] == "mypkg"
    assert loaded["tags"] == ["ai"]


def test_get_server_url_env_wins(monkeypatch):
    monkeypatch.setenv("SKILLHUB_SERVER", "http://env:8000")
    assert get_server_url({"server": "http://other"}) == "http://env:8000"


def test_get_server_url_falls_back_to_config(monkeypatch):
    monkeypatch.delenv("SKILLHUB_SERVER", raising=False)
    assert get_server_url({"server": "http://config"}) == "http://config"


def test_get_server_url_missing_raises(monkeypatch):
    monkeypatch.delenv("SKILLHUB_SERVER", raising=False)
    with pytest.raises(click.ClickException, match="Please set server address"):
        get_server_url({})
