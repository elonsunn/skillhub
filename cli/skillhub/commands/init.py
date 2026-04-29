import click
from pathlib import Path


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

    template = """name: my-skill-package
version: 1.0.0
description: Describe your skill package
author: your-name
tags:
  - skill
  - automation
server: http://localhost:8000

# Package scope control (optional).
# Default behavior: keep both lists empty to package everything under this config dir.
# Choose only one mode when customizing:
# 1) including mode: add paths to include only selected files/folders.
# 2) excluding mode: add paths to exclude specific files/folders.
including: []
excluding: []

ignore:
  - .env
  - "*.env"
  - config.local.*
  - secrets.*
  - .DS_Store
  - __pycache__/
  - "*.pyc"
"""
    yaml_path.write_text(template)
    click.echo(f"Created skillhub.yaml in {config_dir}")
