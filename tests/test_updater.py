"""Unit tests for the git release-based appliance self updater."""

import subprocess

import pytest

from src.spectre.core.updater import GitUpdater, UpdaterError


def _git(cwd, *args):
    subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture()
def appliance(tmp_path):
    """Create an origin repo with two releases and a working clone at the older tag."""
    origin = tmp_path / "origin.git"
    origin.mkdir()
    _git(origin, "init", "--bare", "-b", "main", ".")

    seed = tmp_path / "seed"
    seed.mkdir()
    _git(seed, "init", "-b", "main", ".")
    _git(seed, "config", "user.email", "test@example.com")
    _git(seed, "config", "user.name", "Test")
    (seed / "app.py").write_text("release one\n")
    _git(seed, "add", ".")
    _git(seed, "commit", "-m", "first release")
    _git(seed, "tag", "v0.1.0")
    _git(seed, "remote", "add", "origin", str(origin))
    _git(seed, "push", "--tags", "origin", "main")

    work = tmp_path / "work"
    _git(tmp_path, "clone", str(origin), str(work))
    _git(work, "checkout", "--detach", "v0.1.0")

    # Publish a newer release on origin
    (seed / "app.py").write_text("release two\n")
    _git(seed, "commit", "-am", "second release")
    _git(seed, "tag", "v0.2.0")
    _git(seed, "push", "--tags", "origin", "main")

    return GitUpdater(work)


def test_check_reports_newer_release_available(appliance):
    info = appliance.check()
    assert info["current"] == "v0.1.0"
    assert info["latest"] == "v0.2.0"
    assert info["available"] is True
    assert info["behind_commits"] >= 1
    assert info["dirty"] is False
    assert info["releases"] == ["v0.2.0", "v0.1.0"]


def test_apply_checks_out_latest_release(appliance):
    result = appliance.apply()
    assert result["changed"] is True
    assert result["to"] == "v0.2.0"
    assert appliance.version == "v0.2.0"
    assert appliance.check()["available"] is False


def test_apply_is_idempotent_on_current_release(appliance):
    appliance.apply()
    result = appliance.apply()
    assert result["changed"] is False


def test_apply_refuses_dirty_working_tree(appliance):
    tracked = appliance.repo_root / "app.py"
    tracked.write_text("local hack\n")
    with pytest.raises(UpdaterError, match="local modifications"):
        appliance.apply()
    assert appliance.version.startswith("v0.1.0")
    assert appliance.is_dirty() is True


def test_rollback_falls_back_to_previous_release(appliance):
    appliance.apply()
    result = appliance.rollback()
    assert result["from"] == "v0.2.0"
    assert result["to"] == "v0.1.0"
    assert appliance.version == "v0.1.0"


def test_rollback_from_oldest_release_raises(appliance):
    with pytest.raises(UpdaterError, match="oldest release"):
        appliance.rollback()


def test_check_without_tags_and_remote_is_not_available(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main", ".")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "f.txt").write_text("x\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "dev")

    updater = GitUpdater(repo)
    info = updater.check(fetch=False)
    assert info["available"] is False
    assert info["latest"] == ""


def test_check_fetch_failure_raises_updater_error(appliance):
    subprocess.run(
        ["git", "-C", str(appliance.repo_root), "remote", "set-url", "origin", "/nonexistent/remote.git"],
        check=True,
    )
    with pytest.raises(UpdaterError):
        appliance.check()
