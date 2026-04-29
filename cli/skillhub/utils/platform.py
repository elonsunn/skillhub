from pathlib import Path


def find_config_dir(start: Path = None) -> Path:
    if start is None:
        start = Path.cwd()
    current = start
    while True:
        if (current / ".github").is_dir():
            return current / ".github"
        if (current / ".claude").is_dir():
            return current / ".claude"
        parent = current.parent
        if parent == current:
            config_dir = start / ".github"
            config_dir.mkdir()
            return config_dir
        current = parent
