import sys
import click
from packaging.version import Version
from skillhub.utils.platform import find_config_dir
from skillhub.utils.config import load_config, save_config, get_server_url
from skillhub.utils.packaging import build_zip
from skillhub.utils import api


@click.command()
@click.option("-m", "--message", required=True, help="Commit message for this version")
def push(message):
    config_dir = find_config_dir()
    config = load_config(config_dir)

    if not config.get("tags"):
        raise click.ClickException("tags must not be empty in skillhub.yaml")

    server = get_server_url(config)
    name = config["name"]

    existing = api.get_package(server, name)
    if existing is not None:
        latest_str = max(
            (v["version"] for v in existing["versions"]),
            key=lambda v: Version(v),
        )
        parsed = Version(latest_str)
        new_version = f"{parsed.major}.{parsed.minor}.{parsed.micro + 1}"
    else:
        new_version = config["version"]

    config["version"] = new_version
    save_config(config_dir, config)

    zip_path = build_zip(config_dir, config)

    metadata = {
        "version": new_version,
        "message": message,
        "description": config.get("description", ""),
        "author": config.get("author", ""),
        "tags": config.get("tags", []),
    }

    try:
        api.push_package(server, name, zip_path, metadata)
    except api.SkillHubAPIError as e:
        click.echo(f"Error: {e.detail}", err=True)
        click.echo(
            f"Warning: local skillhub.yaml version was updated to {new_version} "
            "but push failed. You may need to revert it manually.",
            err=True,
        )
        sys.exit(1)

    click.echo(f"Pushed {name}@{new_version}")
