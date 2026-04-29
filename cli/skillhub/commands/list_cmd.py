import sys
import click
from skillhub.utils.platform import find_config_dir
from skillhub.utils.config import load_config, get_server_url
from skillhub.utils import api


@click.command(name="list")
@click.option("--installed", is_flag=True, default=False, help="List installed skills")
def list_cmd(installed):
    if installed:
        config_dir = find_config_dir()
        rows = []
        for skill_type in ["skills", "agents"]:
            root = config_dir / skill_type
            if not root.is_dir():
                continue
            for item in sorted(root.iterdir()):
                if item.is_dir():
                    rows.append((skill_type, item.name))

        click.echo(f"{'TYPE':<10} {'SKILL NAME'}")
        click.echo(f"{'-' * 10} {'-' * 40}")
        for skill_type, skill_name in rows:
            click.echo(f"{skill_type:<10} {skill_name}")
        return

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

    click.echo(f"{'NAME':<24} {'VERSION':<12} {'AUTHOR':<18} {'TAGS':<24} DESCRIPTION")
    click.echo(f"{'-' * 24} {'-' * 12} {'-' * 18} {'-' * 24} {'-' * 40}")
    for pkg in packages:
        tags_str = ", ".join(pkg.get("tags", []))
        click.echo(
            f"{pkg.get('name', ''):<24} "
            f"{(pkg.get('latest_version') or ''):<12} "
            f"{pkg.get('author', ''):<18} "
            f"{tags_str:<24} "
            f"{pkg.get('description', '')}"
        )
