import sys
import click
from skillhub.utils.platform import find_config_dir
from skillhub.utils.config import load_config, get_server_url
from skillhub.utils import api


@click.command(name="list")
@click.option("--online", is_flag=True, default=False)
def list_cmd(online):
    if online:
        try:
            config = load_config(find_config_dir())
        except click.ClickException:
            config = {}
        server = get_server_url(config)
        try:
            packages = api.list_packages(server)
        except api.SkillHubAPIError as e:
            click.echo(f"Error: {e.detail}", err=True)
            sys.exit(1)
        for pkg in packages:
            tags_str = ", ".join(pkg.get("tags", []))
            click.echo(
                f"{pkg['name']}  {pkg['latest_version']}  "
                f"{pkg['author']}  [{tags_str}]  {pkg['description']}"
            )
    else:
        config_dir = find_config_dir()
        config = load_config(config_dir)
        if config.get("including"):
            scope = "including: " + ", ".join(config["including"])
        elif config.get("excluding"):
            scope = "excluding: " + ", ".join(config["excluding"])
        else:
            scope = "all"
        click.echo(f"Name:        {config.get('name', '')}")
        click.echo(f"Version:     {config.get('version', '')}")
        click.echo(f"Description: {config.get('description', '')}")
        click.echo(f"Author:      {config.get('author', '')}")
        click.echo(f"Tags:        {', '.join(config.get('tags', []))}")
        click.echo(f"Server:      {config.get('server', '')}")
        click.echo(f"Scope:       {scope}")
        for subdir in ["skills", "agents", "instructions"]:
            full = config_dir / subdir
            if full.is_dir():
                click.echo(f"\n{subdir}/")
                for item in sorted(full.iterdir()):
                    click.echo(f"  {item.name}")
