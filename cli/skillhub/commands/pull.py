import sys
import click
import tempfile
import zipfile
from pathlib import Path
from skillhub.utils.platform import find_config_dir
from skillhub.utils.config import load_config, get_server_url
from skillhub.utils import api


@click.command()
@click.argument("name")
@click.option("--version", default=None, help="Version to pull (default: latest)")
def pull(name, version):
    config_dir = find_config_dir()
    try:
        config = load_config(config_dir)
    except click.ClickException:
        config = {}
    server = get_server_url(config)

    if version is None:
        version = "latest"

    try:
        zip_bytes = api.download_package(server, name, version)
    except api.SkillHubAPIError as e:
        click.echo(f"Error: {e.detail}", err=True)
        sys.exit(1)

    with tempfile.TemporaryDirectory() as tmp:
        zip_path = Path(tmp) / "package.zip"
        zip_path.write_bytes(zip_bytes)

        with zipfile.ZipFile(zip_path) as zf:
            file_names = [n for n in zf.namelist() if not n.endswith("/")]

        conflicts = [n for n in file_names if (config_dir / n).exists()]
        if conflicts:
            click.echo("Error: conflicting files already exist:", err=True)
            for c in conflicts:
                click.echo(f"  {c}", err=True)
            click.echo("Resolve conflicts and retry.", err=True)
            sys.exit(1)

        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(config_dir)

    setup_files = [n for n in file_names if Path(n).name == "SETUP.md"]
    if setup_files:
        click.echo(
            "Found setup guides in the following locations, "
            "run `skillhub setup <path>` to view configuration instructions:"
        )
        for s in setup_files:
            click.echo(f"  {s}")
