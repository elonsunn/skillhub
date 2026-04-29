import pytest
import yaml


@pytest.fixture
def config_dir(tmp_path, monkeypatch):
    """Create .github/ in tmp_path and chdir into tmp_path."""
    github_dir = tmp_path / ".github"
    github_dir.mkdir()
    monkeypatch.chdir(tmp_path)
    return github_dir


@pytest.fixture
def skillhub_yaml(config_dir):
    data = {
        "name": "test-pkg",
        "version": "1.0.0",
        "description": "Test package",
        "author": "tester",
        "tags": ["test"],
        "server": "http://localhost:8000",
    }
    yaml_path = config_dir / "skillhub.yaml"
    yaml_path.write_text(yaml.dump(data, default_flow_style=False))
    return yaml_path
