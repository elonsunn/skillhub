import click
from pathlib import Path


def _scan_including(config_dir: Path) -> list[str]:
    items = []
    for entry in sorted(config_dir.iterdir()):
        if entry.name == "skillhub.yaml":
            continue
        if entry.is_file():
            items.append(entry.name)
        elif entry.is_dir():
            for child in sorted(entry.iterdir()):
                items.append(f"{entry.name}/{child.name}")
    return items


@click.command()
def init():
    cwd = Path.cwd()
    github_dir = cwd / ".github"
    claude_dir = cwd / ".claude"

    if github_dir.is_dir():
        config_dir = github_dir
    elif claude_dir.is_dir():
        config_dir = claude_dir
    else:
        config_dir = github_dir
        config_dir.mkdir()

    yaml_path = config_dir / "skillhub.yaml"
    if yaml_path.exists():
        raise click.ClickException("skillhub.yaml already exists.")

    including = _scan_including(config_dir)
    if including:
        including_block = "\n" + "\n".join(f"  - {item}" for item in including)
    else:
        including_block = " []"

    template = f"""name: my-skill-package
version: 1.0.0
description: Describe your skill package
author: your-name
tags:
  - skill
  - automation
server: http://localhost:8000

including:{including_block}

ignore:
  - .env
  - "*.env"
  - config.json
"""
    yaml_path.write_text(template)
    click.echo(f"Created skillhub.yaml in {config_dir}")
