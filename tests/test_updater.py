"""Unit tests for the git release-based appliance self updater."""

import subprocess
from pathlib import Path

import pytest
import tomllib

from spectre.core.updater import GitUpdater, UpdaterError, detect_package_manager

ROOT = Path(__file__).resolve().parents[1]


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

    # Plain python3 install, no apt: never runs a real pip/apt in tests.
    return GitUpdater(work, in_venv=False, package_manager=None)


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


def test_apply_ignores_untracked_files(appliance):
    scratch = appliance.repo_root / "scratch.txt"
    scratch.write_text("scratch dev")
    assert appliance.is_dirty() is False
    result = appliance.apply()
    assert result["changed"] is True
    assert scratch.read_text() == "scratch dev"





def _publish_release(tmp_path, tag, dependencies, system=None):
    seed = tmp_path / "seed"
    deps = ", ".join(f'"{d}"' for d in dependencies)
    lines = [f'[project]\nname = "app"\ndependencies = [{deps}]\n',
             "[tool.spectre.system-packages]\n"]
    for key, entry in (system or {}).items():
        fields = ", ".join(f'{k} = "{v}"' for k, v in entry.items())
        lines.append(f"{key} = {{ {fields} }}\n")
    (seed / "pyproject.toml").write_text("".join(lines))
    _git(seed, "add", ".")
    _git(seed, "commit", "-m", f"release {tag}")
    _git(seed, "tag", tag)
    _git(seed, "push", "--tags", "origin", "main")


AUDIO = {
    "pyqt6": {"apt": "python3-pyqt6", "python": "PyQt6"},
    "portaudio": {"apt": "libportaudio2", "dnf": "portaudio", "pacman": "portaudio"},
}


class FakeRunner:
    """Stands in for subprocess.run for pip and package manager calls."""

    def __init__(self, installed=(), fail=()):
        self.calls = []
        self.kwargs = []
        self.installed = set(installed)
        self.fail = list(fail)  # command fragments; each entry fails once

    def __call__(self, cmd, **kwargs):
        self.calls.append(cmd)
        self.kwargs.append(kwargs)
        joined = " ".join(cmd)
        for word in self.fail:
            if word in joined:
                self.fail.remove(word)
                return subprocess.CompletedProcess(cmd, 1, "", "E: Unable to fetch\n")
        queried = [p for p in cmd[1:] if p in self.installed]
        if cmd[0] == "dpkg-query":
            return subprocess.CompletedProcess(cmd, 0, "".join(f"{p} installed\n" for p in queried), "")
        if cmd[0] == "rpm":
            out = "".join(
                f"{p} installed\n" if p in self.installed else f"package {p} is not installed\n"
                for p in cmd[4:]
            )
            return subprocess.CompletedProcess(cmd, 0, out, "")
        if cmd[:2] == ["pacman", "-Q"]:
            return subprocess.CompletedProcess(cmd, 0, "".join(f"{p} 1.0-1\n" for p in queried), "")
        if "pip" in cmd:
            return subprocess.CompletedProcess(cmd, 0, "Successfully installed numpy-2.2.4\n", "")
        return subprocess.CompletedProcess(cmd, 0, "", "")


def _venv_updater(appliance, runner, manager="apt", interactive=False):
    return GitUpdater(appliance.repo_root, runner=runner, in_venv=True,
                      package_manager=manager, interactive=interactive, which=lambda c: None)


def _installs(runner):
    return [c for c in runner.calls if c[0] == "sudo"]


def test_apply_refuses_release_with_missing_dependencies(appliance, tmp_path):
    _publish_release(tmp_path, "v0.3.0", ["pytest>=8", "no-such-package-xyz>=1.0"])
    with pytest.raises(UpdaterError, match="no-such-package-xyz"):
        appliance.apply()
    assert appliance.version == "v0.1.0"


def test_apply_accepts_release_with_installed_dependencies(appliance, tmp_path):
    # Versions are not compared: only presence matters.
    _publish_release(tmp_path, "v0.3.0", ["pytest>=999", "pytest[extra] ; python_version > '3'"])
    result = appliance.apply()
    assert result["to"] == "v0.3.0"
    assert appliance.missing_dependencies("v0.1.0") == []


def test_rollback_refuses_release_with_missing_dependencies(appliance, tmp_path):
    _publish_release(tmp_path, "v0.3.0", ["no-such-package-xyz"])
    _publish_release(tmp_path, "v0.4.0", ["pytest"])
    appliance.apply()
    with pytest.raises(UpdaterError, match="v0.3.0 needs"):
        appliance.rollback()
    assert appliance.version == "v0.4.0"


def test_venv_apply_installs_requirements_before_checkout(appliance, tmp_path):
    _publish_release(tmp_path, "v0.3.0", ["PyQt6>=6.5", "numpy>=1.24", "no-such-package-xyz"],
                     system=AUDIO)
    runner = FakeRunner(installed={"python3-pyqt6"})
    result = _venv_updater(appliance, runner).apply()

    assert result["to"] == "v0.3.0"
    assert result["installed"] == {"system": ["libportaudio2"], "pip": ["numpy-2.2.4"]}
    assert _installs(runner) == [["sudo", "-n", "apt-get", "install", "-y",
                                  "--no-install-recommends", "libportaudio2"]]
    pip = [c for c in runner.calls if "pip" in c][0]
    # apt provides PyQt6 on Debian: pip must not pull a wheel over it.
    assert pip[-2:] == ["numpy>=1.24", "no-such-package-xyz"]
    assert "--only-binary" in pip


def test_dnf_installs_fedora_names_and_pip_installs_pyqt6(appliance, tmp_path):
    _publish_release(tmp_path, "v0.3.0", ["PyQt6>=6.5"], system=AUDIO)
    runner = FakeRunner()
    _venv_updater(appliance, runner, manager="dnf").apply()
    assert _installs(runner) == [["sudo", "-n", "dnf", "install", "-y", "portaudio"]]
    # No dnf entry for PyQt6, so the wheel is fine there.
    assert [c for c in runner.calls if "pip" in c][0][-1] == "PyQt6>=6.5"


def test_pacman_skips_installed_packages(appliance, tmp_path):
    system = {**AUDIO, "rubberband": {"pacman": "rubberband"}}
    _publish_release(tmp_path, "v0.3.0", [], system=system)
    runner = FakeRunner(installed={"portaudio"})
    _venv_updater(appliance, runner, manager="pacman").apply()
    assert _installs(runner) == [["sudo", "-n", "pacman", "-S", "--needed", "--noconfirm",
                                  "rubberband"]]


def test_immutable_fedora_explains_instead_of_installing(appliance, tmp_path):
    _publish_release(tmp_path, "v0.3.0", [], system=AUDIO)
    runner = FakeRunner()
    updater = _venv_updater(appliance, runner, manager="rpm-ostree")
    with pytest.raises(UpdaterError, match="rpm-ostree install portaudio"):
        updater.apply()
    assert not _installs(runner)
    assert updater.version == "v0.1.0"


def test_command_on_path_satisfies_entry(appliance, tmp_path):
    system = {"rb": {"dnf": "rubberband", "command": "rubberband"}}
    _publish_release(tmp_path, "v0.3.0", [], system=system)
    runner = FakeRunner()
    updater = GitUpdater(appliance.repo_root, runner=runner, in_venv=True,
                         package_manager="rpm-ostree",
                         which=lambda c: "/home/me/miniforge3/bin/rubberband")
    assert updater.apply()["installed"]["system"] == []
    assert not [c for c in runner.calls if c[0] == "rpm"]


def test_immutable_fedora_with_packages_installed_updates(appliance, tmp_path):
    _publish_release(tmp_path, "v0.3.0", [], system=AUDIO)
    runner = FakeRunner(installed={"portaudio"})
    assert _venv_updater(appliance, runner, manager="rpm-ostree").apply()["to"] == "v0.3.0"


def test_no_package_manager_skips_system_packages(appliance, tmp_path):
    _publish_release(tmp_path, "v0.3.0", ["PyQt6>=6.5"], system=AUDIO)
    runner = FakeRunner()
    _venv_updater(appliance, runner, manager=None).apply()
    assert [c[0] for c in runner.calls] == [runner.calls[0][0]]  # only pip
    assert "pip" in runner.calls[0]


def test_interactive_sudo_may_prompt_and_shows_output(appliance, tmp_path):
    _publish_release(tmp_path, "v0.3.0", [], system=AUDIO)
    runner = FakeRunner()
    updater = _venv_updater(appliance, runner, manager="dnf", interactive=True)
    updater.check()  # fetch the new tag
    updater.install_system_packages("v0.3.0")
    install = runner.calls.index(["sudo", "dnf", "install", "-y", "portaudio"])
    assert "capture_output" not in runner.kwargs[install]


def test_venv_pip_failure_keeps_current_release(appliance, tmp_path):
    _publish_release(tmp_path, "v0.3.0", ["numpy"])
    runner = FakeRunner(fail=["pip"])
    updater = _venv_updater(appliance, runner)
    with pytest.raises(UpdaterError, match="pip install failed: E: Unable to fetch"):
        updater.apply()
    assert updater.version == "v0.1.0"


def test_apt_install_retries_after_update(appliance, tmp_path):
    _publish_release(tmp_path, "v0.3.0", [], system={"rb": {"apt": "rubberband-cli"}})
    runner = FakeRunner(fail=["apt-get install"])
    _venv_updater(appliance, runner).apply()
    assert [" ".join(c[2:4]) for c in _installs(runner)] == [
        "apt-get install", "apt-get update", "apt-get install"]


OS_RELEASES = {
    "raspbian": ('ID=debian\nVERSION_CODENAME=trixie\n', "apt"),
    "ubuntu": ('ID=ubuntu\nID_LIKE=debian\n', "apt"),
    "mint": ('ID=linuxmint\nID_LIKE="ubuntu debian"\n', "apt"),
    "fedora": ('ID=fedora\n', "dnf"),
    "arch": ('ID=arch\n', "pacman"),
    "manjaro": ('ID=manjaro\nID_LIKE=arch\n', "pacman"),
    "alpine": ('ID=alpine\n', None),
}


@pytest.mark.parametrize("distro", OS_RELEASES)
def test_detect_package_manager(distro):
    text, expected = OS_RELEASES[distro]
    assert detect_package_manager(text, which=lambda t: f"/usr/bin/{t}", ostree=False) == expected


def test_detect_immutable_fedora_and_missing_tools():
    aurora = 'ID=aurora\nID_LIKE="fedora"\nVARIANT_ID=aurora-dx\n'
    tools = lambda t: f"/usr/bin/{t}"
    assert detect_package_manager(aurora, which=tools, ostree=True) == "rpm-ostree"
    assert detect_package_manager(aurora, which=tools, ostree=False) == "dnf"
    assert detect_package_manager("ID=ubuntu\n", which=lambda t: None, ostree=False) is None


def test_requirements_txt_matches_pyproject():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    lines = (ROOT / "requirements.txt").read_text().splitlines()
    reqs = [ln.strip() for ln in lines if ln.strip() and not ln.startswith("#")]
    assert reqs == pyproject["project"]["dependencies"]


@pytest.mark.parametrize("manager,expected", [
    ("apt", {"python3-venv", "python3-pyqt6", "libportaudio2", "rubberband-cli"}),
    ("dnf", {"portaudio", "rubberband"}),
    ("pacman", {"portaudio", "rubberband"}),
])
def test_working_tree_system_packages(manager, expected):
    updater = GitUpdater(ROOT, in_venv=False, package_manager=manager, which=lambda c: None)
    packages, provided = updater.system.resolve(updater.requirements()["system"])
    assert set(packages) == expected
    assert provided == ({"pyqt6"} if manager == "apt" else set())


def test_restart_prefers_repo_venv(tmp_path):
    import sys

    from spectre.ui.bridge.system import REPO_ROOT, restart_executable

    assert (REPO_ROOT / "pyproject.toml").is_file()
    assert restart_executable(tmp_path) == sys.executable
    venv_python = tmp_path / ".venv" / "bin" / "python"
    venv_python.parent.mkdir(parents=True)
    venv_python.write_text("")
    venv_python.chmod(0o755)
    assert restart_executable(tmp_path) == str(venv_python)
