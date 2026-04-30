import os
import click
import yaml
from pathlib import Path


def load_config(config_dir: Path) -> dict:
    yaml_path = config_dir / "skillhub.yaml"
    if not yaml_path.exists():
        raise click.ClickException("No skillhub.yaml found. Run `skillhub init` first.")
    try:
        with open(yaml_path) as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            raise click.ClickException("Invalid skillhub.yaml: expected a mapping")
        return data
    except yaml.YAMLError as e:
        raise click.ClickException(f"Invalid skillhub.yaml: {e}")


def save_config(config_dir: Path, data: dict) -> None:
    with open(config_dir / "skillhub.yaml", "w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


def get_server_url(config: dict) -> str:
    server = os.environ.get("SKILLHUB_SERVER")
    if server:
        return server
    server = config.get("server")
    if server:
        return server
    raise click.ClickException("No server URL configured. Set env e.g. SKILLHUB_SERVER=<url> uv run skillhub list.")
