import click
from skillhub.utils.platform import find_config_dir


@click.command(name="setup")
@click.argument("path")
def setup(path):
    config_dir = find_config_dir()
    matches = sorted(
        f for f in config_dir.rglob("SETUP.md")
        if path in str(f.relative_to(config_dir).parent)
    )
    if not matches:
        click.echo("No setup guide found.")
        return
    for match in matches:
        click.echo(f"=== {match.relative_to(config_dir)} ===")
        click.echo(match.read_text())
    click.echo("Send this to your AI assistant to complete configuration.")
