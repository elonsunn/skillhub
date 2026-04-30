import click
from skillhub.utils.platform import find_config_dir
from skillhub.utils.config import load_config, get_server_url
from skillhub.utils import api


@click.command()
@click.argument("name")
@click.option("--version", default=None, help="Version to show contents for (default: latest)")
def info(name, version):
    try:
        config = load_config(find_config_dir())
    except click.ClickException:
        config = {}
    server = get_server_url(config)

    pkg = api.get_package(server, name)
    if pkg is None:
        raise click.ClickException(f"Package '{name}' not found")

    versions = pkg.get("versions", [])

    if version:
        ver_data = next((v for v in versions if v["version"] == version), None)
        if ver_data is None:
            raise click.ClickException(f"Version {version} not found for package '{name}'")
    else:
        ver_data = versions[0] if versions else None

    click.echo(f"{'name:':<13}{pkg['name']}")
    if pkg.get("description"):
        click.echo(f"{'description:':<13}{pkg['description']}")
    if pkg.get("author"):
        click.echo(f"{'author:':<13}{pkg['author']}")
    tags_str = ", ".join(pkg.get("tags", []))
    if tags_str:
        click.echo(f"{'tags:':<13}{tags_str}")

    if ver_data:
        click.echo()
        click.echo(f"{'version:':<13}{ver_data['version']}")
        contents = ver_data.get("contents", [])
        click.echo("contents:")
        if contents:
            for item in contents:
                click.echo(f"  {item}")
        else:
            click.echo("  (no contents recorded)")

    if versions:
        click.echo()
        click.echo("version history:")
        for v in versions:
            date = v.get("created_at", "")[:10] if v.get("created_at") else ""
            click.echo(f"  {v['version']:<12} {v['message']:<32} {date}")
