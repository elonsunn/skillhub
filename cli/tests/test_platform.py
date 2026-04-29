from skillhub.utils.platform import find_config_dir


def test_finds_github_dir(tmp_path):
    (tmp_path / ".github").mkdir()
    assert find_config_dir(tmp_path) == tmp_path / ".github"


def test_prefers_github_over_claude(tmp_path):
    (tmp_path / ".github").mkdir()
    (tmp_path / ".claude").mkdir()
    assert find_config_dir(tmp_path) == tmp_path / ".github"


def test_finds_claude_when_no_github(tmp_path):
    (tmp_path / ".claude").mkdir()
    assert find_config_dir(tmp_path) == tmp_path / ".claude"


def test_walks_up_to_parent(tmp_path):
    (tmp_path / ".github").mkdir()
    subdir = tmp_path / "src" / "app"
    subdir.mkdir(parents=True)
    assert find_config_dir(subdir) == tmp_path / ".github"


def test_creates_github_when_nothing_found(tmp_path):
    result = find_config_dir(tmp_path)
    assert result == tmp_path / ".github"
    assert result.is_dir()
