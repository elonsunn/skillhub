import click
from skillhub.utils.platform import find_config_dir
from skillhub.utils.config import save_config


@click.command()
def init():
    config_dir = find_config_dir()
    if (config_dir / "skillhub.yaml").exists():
        raise click.ClickException("skillhub.yaml already exists.")

    name = click.prompt("Package name")
    description = click.prompt("Description")
    author = click.prompt("Author")
    tags_input = click.prompt("Tags (comma-separated)")
    tags = [t.strip() for t in tags_input.split(",") if t.strip()]
    server = click.prompt("Server URL")

    config = {
        "name": name,
        "version": "1.0.0",
        "description": description,
        "author": author,
        "tags": tags,
        "server": server,
        "ignore": [
            ".env",
            "*.env",
            "config.local.*",
            "secrets.*",
            ".DS_Store",
            "__pycache__/",
            "*.pyc",
        ],
    }
    save_config(config_dir, config)
    click.echo(f"Created skillhub.yaml in {config_dir}")
