import zipfile
import click
import pathspec
from pathlib import Path

_ALWAYS_IGNORE = [
    "skillhub.yaml",
    ".DS_Store",
    "**/__pycache__/**",
    "*.pyc",
    ".git/",
]


def build_zip(config_dir: Path, config: dict) -> Path:
    including = config.get("including")

    ignore_spec = pathspec.PathSpec.from_lines(
        "gitignore", list(config.get("ignore", [])) + _ALWAYS_IGNORE
    )

    if including:
        candidates = []
        for inc in including:
            p = config_dir / inc
            if p.is_file():
                candidates.append(p)
            elif p.is_dir():
                candidates.extend(f for f in p.rglob("*") if f.is_file())
    else:
        candidates = [f for f in config_dir.rglob("*") if f.is_file()]

    files_to_zip = [
        f for f in candidates
        if not ignore_spec.match_file(str(f.relative_to(config_dir)))
    ]

    zip_path = config_dir.parent / f"{config['name']}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files_to_zip:
            zf.write(f, f.relative_to(config_dir))

    return zip_path
