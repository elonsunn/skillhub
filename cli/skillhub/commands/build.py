import click
from skillhub.utils.platform import find_config_dir
from skillhub.utils.config import load_config
from skillhub.utils.packaging import build_zip


@click.command()
def build():
    config_dir = find_config_dir()
    config = load_config(config_dir)
    if not config.get("tags"):
        raise click.ClickException("tags must not be empty in skillhub.yaml")
    if config.get("including") and config.get("excluding"):
        raise click.ClickException(
            "Cannot use both including and excluding in skillhub.yaml"
        )
    zip_path = build_zip(config_dir, config)
    click.echo(f"Built {zip_path}")
