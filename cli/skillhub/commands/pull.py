import sys
import shutil
import click
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
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

    try:
        zip_bytes = api.download_package(server, name, version=version)
    except api.SkillHubAPIError as e:
        click.echo(f"Error: {e.detail}", err=True)
        sys.exit(1)

    with tempfile.TemporaryDirectory() as tmp:
        zip_path = Path(tmp) / "package.zip"
        zip_path.write_bytes(zip_bytes)

        config_dir_resolved = config_dir.resolve()
        file_entries = []
        with zipfile.ZipFile(zip_path) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue

                normalized = info.filename.replace("\\", "/")
                rel_posix = PurePosixPath(normalized)

                if rel_posix.is_absolute() or ".." in rel_posix.parts:
                    click.echo(f"Error: package contains unsafe path: {info.filename}", err=True)
                    sys.exit(1)

                rel_path = Path(*rel_posix.parts)
                target = (config_dir / rel_path).resolve()
                try:
                    target.relative_to(config_dir_resolved)
                except ValueError:
                    click.echo(f"Error: package contains unsafe path: {info.filename}", err=True)
                    sys.exit(1)

                file_entries.append((info, rel_path))

        conflicts = [str(rel_path).replace("\\", "/") for _, rel_path in file_entries if (config_dir / rel_path).exists()]
        if conflicts:
            click.echo("Error: conflicting files already exist:", err=True)
            for c in conflicts:
                click.echo(f"  {c}", err=True)
            click.echo("Resolve conflicts and retry.", err=True)
            sys.exit(1)

        with zipfile.ZipFile(zip_path) as zf:
            for info, rel_path in file_entries:
                target = config_dir / rel_path
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info) as src, target.open("wb") as dst:
                    shutil.copyfileobj(src, dst)

    setup_files = [str(rel_path).replace("\\", "/") for _, rel_path in file_entries if rel_path.name == "SETUP.md"]
    if setup_files:
        click.echo(
            "Found setup guides in the following locations, "
            "run `skillhub setup <path>` to view configuration instructions:"
        )
        for s in setup_files:
            click.echo(f"  {s}")
