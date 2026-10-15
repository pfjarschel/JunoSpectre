"""Git release-based self updater for Juno Spectre appliance deployments.

The appliance updates by checking out tagged releases from origin (detached
HEAD), never arbitrary development commits, and can roll back to the previous
tag when a release misbehaves on hardware.

Before switching, the release's requirements are installed: system packages
from ``[tool.spectre.system-packages]`` in its pyproject.toml with the distro's
package manager (apt, dnf or pacman; Linux only), then its Python
``dependencies`` with pip when the app runs from a venv. Without a venv the
Python packages can only be checked, and a release missing any is refused.

Only stdlib imports here: scripts/setup_venv.sh runs this file directly
(``python updater.py install-deps``) before any dependency exists.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import sys
from importlib import metadata
from pathlib import Path
from typing import Callable, Optional

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10: skip the dependency preflight
    tomllib = None

logger = logging.getLogger(__name__)

GIT_TIMEOUT = 15
FETCH_TIMEOUT = 60
INSTALL_TIMEOUT = 900  # scipy etc. take minutes to download on a Pi


class UpdaterError(RuntimeError):
    """Raised when a git updater operation fails."""


def _dist_name(spec: str) -> str:
    return re.split(r"[\s<>=!~;\[(]", spec, maxsplit=1)[0]


def _in_venv() -> bool:
    return sys.prefix != sys.base_prefix


# Distro family (os-release ID / ID_LIKE) -> package manager, and the tools it needs.
_DISTRO_MANAGERS = (
    (("debian", "ubuntu", "raspbian"), "apt", ("apt-get", "dpkg-query")),
    (("fedora", "rhel", "centos"), "dnf", ("dnf", "rpm")),
    (("arch",), "pacman", ("pacman",)),
)


def detect_package_manager(
    os_release: Optional[str] = None,
    which: Callable[[str], Optional[str]] = shutil.which,
    ostree: Optional[bool] = None,
) -> Optional[str]:
    """apt, dnf, pacman, rpm-ostree (immutable Fedora: no live installs) or None."""
    if os_release is None:
        if not sys.platform.startswith("linux"):
            return None
        try:
            os_release = Path("/etc/os-release").read_text(encoding="utf-8")
        except OSError:
            return None
    fields = {}
    for line in os_release.splitlines():
        key, sep, value = line.partition("=")
        if sep:
            fields[key.strip()] = value.strip().strip('"')
    ids = [fields.get("ID", ""), *fields.get("ID_LIKE", "").split()]
    for family, manager, tools in _DISTRO_MANAGERS:
        if any(i in family for i in ids):
            if manager == "dnf" and (Path("/run/ostree-booted").exists() if ostree is None else ostree):
                return "rpm-ostree" if which("rpm") else None
            return manager if all(which(t) for t in tools) else None
    return None


class SystemPackages:
    """Query and install distro packages for one package manager."""

    def __init__(
        self,
        manager: Optional[str],
        runner,
        interactive: bool = False,
        which: Callable[[str], Optional[str]] = shutil.which,
    ):
        self.manager = manager
        self._run = runner
        self.interactive = interactive
        self._which = which

    @property
    def name_key(self) -> Optional[str]:
        # Immutable Fedora uses the Fedora package names.
        return "dnf" if self.manager == "rpm-ostree" else self.manager

    def resolve(self, entries: dict) -> tuple[list[str], set[str]]:
        """Package names for this manager, and the Python dists they provide."""
        packages, provides = [], set()
        for entry in entries.values():
            name = entry.get(self.name_key) if self.name_key else None
            # A program already on PATH counts, however it got there (conda, manual).
            if name and entry.get("command") and self._which(entry["command"]):
                continue
            if name:
                packages.append(name)
                if entry.get("python"):
                    provides.add(entry["python"].lower())
        return packages, provides

    def missing(self, packages: list[str]) -> list[str]:
        if not self.manager or not packages:
            return []
        if self.manager == "apt":
            cmd = ["dpkg-query", "-W", "-f=${Package} ${db:Status-Status}\n", *packages]
        elif self.manager == "pacman":
            cmd = ["pacman", "-Q", *packages]
        else:
            cmd = ["rpm", "-q", "--qf", "%{NAME} installed\n", *packages]
        proc = self._run(cmd, capture_output=True, text=True, timeout=GIT_TIMEOUT)
        installed = set()
        for line in proc.stdout.splitlines():
            parts = line.split()
            if len(parts) != 2:
                continue
            if self.manager == "pacman" or parts[1] == "installed":
                installed.add(parts[0].split(":")[0])
        return [p for p in packages if p not in installed]

    def _sudo(self) -> list[str]:
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            return []
        # The app has no terminal to ask for a password: never prompt there.
        return ["sudo"] if self.interactive else ["sudo", "-n"]

    def install(self, packages: list[str], install: Callable[[list[str], str], object]) -> None:
        if not packages:
            return
        names = " ".join(packages)
        if self.manager == "rpm-ostree":
            raise UpdaterError(
                f"immutable system: run 'rpm-ostree install {names}' and reboot"
            )
        sudo = self._sudo()
        if self.manager == "apt":
            cmd = [*sudo, "apt-get", "install", "-y", "--no-install-recommends", *packages]
            try:
                install(cmd, "apt install")
            except UpdaterError:
                # Stale package lists 404; refresh once and retry.
                install([*sudo, "apt-get", "update"], "apt update")
                install(cmd, "apt install")
        elif self.manager == "dnf":
            install([*sudo, "dnf", "install", "-y", *packages], "dnf install")
        elif self.manager == "pacman":
            install([*sudo, "pacman", "-S", "--needed", "--noconfirm", *packages],
                    "pacman install")


class GitUpdater:
    """Safe, blocking git operations backing the appliance update flow."""

    def __init__(
        self,
        repo_root: Path,
        runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
        in_venv: Optional[bool] = None,
        package_manager: Optional[str] = "auto",
        interactive: bool = False,
        which: Callable[[str], Optional[str]] = shutil.which,
    ):
        self.repo_root = Path(repo_root)
        self._run = runner
        self.in_venv = _in_venv() if in_venv is None else in_venv
        self.interactive = interactive
        if package_manager == "auto":
            package_manager = detect_package_manager()
        self.system = SystemPackages(package_manager, runner, interactive, which)

    def _git(
        self,
        *args: str,
        timeout: int = GIT_TIMEOUT,
        check: bool = True,
    ) -> subprocess.CompletedProcess:
        try:
            proc = subprocess.run(
                ["git", "-C", str(self.repo_root), *args],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except FileNotFoundError as exc:
            raise UpdaterError("git executable not found on this system") from exc
        except subprocess.TimeoutExpired as exc:
            raise UpdaterError(f"git {' '.join(args)} timed out") from exc
        if check and proc.returncode != 0:
            raise UpdaterError(
                (proc.stderr or proc.stdout).strip() or f"git {' '.join(args)} failed"
            )
        return proc

    @property
    def version(self) -> str:
        """Human readable build version, e.g. v0.2.0 or v0.2.0-3-gabcd or DEV."""
        proc = self._git("describe", "--tags", "--always", "--dirty", check=False)
        if proc.returncode != 0:
            return "DEV"
        return proc.stdout.strip() or "DEV"

    def releases(self) -> list[str]:
        """All release tags, newest first (version-aware sort)."""
        proc = self._git("tag", "--sort=-v:refname")
        return proc.stdout.split()

    def is_dirty(self) -> bool:
        """True when tracked files have local modifications."""
        proc = self._git("status", "--porcelain", "--untracked-files=no")
        return bool(proc.stdout.strip())

    def _current_release(self) -> str:
        proc = self._git("describe", "--tags", "--exact-match", check=False)
        return proc.stdout.strip() if proc.returncode == 0 else ""

    def _ensure_repo(self) -> None:
        proc = self._git("rev-parse", "--git-dir", check=False)
        if proc.returncode != 0:
            raise UpdaterError("this checkout is not a git repository")

    def requirements(self, ref: Optional[str] = None) -> dict:
        """Python and system requirements of the release at ref (None: working tree)."""
        empty = {"python": [], "system": {}}
        if tomllib is None:
            return empty
        if ref is None:
            path = self.repo_root / "pyproject.toml"
            text = path.read_text(encoding="utf-8") if path.is_file() else None
        else:
            proc = self._git("show", f"{ref}:pyproject.toml", check=False)
            text = proc.stdout if proc.returncode == 0 else None
        if text is None:
            return empty
        try:
            data = tomllib.loads(text)
        except tomllib.TOMLDecodeError:
            return empty
        system = data.get("tool", {}).get("spectre", {}).get("system-packages", {})
        return {
            "python": [s for s in data.get("project", {}).get("dependencies", []) if _dist_name(s)],
            "system": {k: v for k, v in system.items() if isinstance(v, dict)},
        }

    def missing_dependencies(self, ref: Optional[str] = None) -> list[str]:
        """Python packages the release at ref declares that this Python lacks.

        Only presence is checked, not versions: distro packages can report
        odd versions (Debian's mido says 0.0.0) while working fine.
        """
        missing = []
        for spec in self.requirements(ref)["python"]:
            name = _dist_name(spec)
            try:
                metadata.distribution(name)
            except metadata.PackageNotFoundError:
                missing.append(name)
        return missing

    def _install(self, cmd: list[str], what: str) -> subprocess.CompletedProcess:
        logger.info("Updater: %s", " ".join(cmd))
        try:
            if self.interactive:
                # Show progress and let sudo ask for a password on the terminal.
                proc = self._run(cmd, timeout=INSTALL_TIMEOUT)
            else:
                proc = self._run(cmd, capture_output=True, text=True, timeout=INSTALL_TIMEOUT)
        except subprocess.TimeoutExpired as exc:
            raise UpdaterError(f"{what} timed out") from exc
        if proc.returncode != 0:
            lines = (proc.stderr or proc.stdout or "").strip().splitlines()
            raise UpdaterError(
                f"{what} failed: {lines[-1] if lines else 'see the output above'}"
            )
        return proc

    def install_system_packages(self, ref: Optional[str] = None) -> list[str]:
        packages, _ = self.system.resolve(self.requirements(ref)["system"])
        missing = self.system.missing(packages)
        self.system.install(missing, self._install)
        return missing

    def install_python_packages(self, ref: Optional[str] = None) -> list[str]:
        req = self.requirements(ref)
        # Dists a system package provides here never come from pip (the Pi's
        # PyQt6 is built for its own Qt/eglfs; a wheel bundles another Qt).
        _, provided = self.system.resolve(req["system"])
        pip_specs = [s for s in req["python"] if _dist_name(s).lower() not in provided]
        if not self.in_venv:
            missing = self.missing_dependencies(ref)
            if missing:
                raise UpdaterError(
                    f"{ref or 'this checkout'} needs Python packages not installed here: "
                    f"{', '.join(missing)} (run scripts/setup_venv.sh so updates can install them)"
                )
            return []
        if not pip_specs:
            return []
        proc = self._install(
            [sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
             "--only-binary", ":all:", *pip_specs],
            "pip install",
        )
        for line in (proc.stdout or "").splitlines():
            if line.startswith("Successfully installed "):
                return line.split()[2:]
        return []

    def install_requirements(self, ref: Optional[str] = None) -> dict:
        """Install what the release at ref needs; raise before anything is switched.

        A release whose imports fail crash-loops the appliance at boot, so a
        failure here must stop the checkout.
        """
        system = self.install_system_packages(ref)
        return {"system": system, "pip": self.install_python_packages(ref)}

    def check(self, fetch: bool = True) -> dict:
        """Fetch tags from origin and report the release channel state."""
        self._ensure_repo()
        if fetch:
            self._git("fetch", "--tags", "--prune-tags", "origin", timeout=FETCH_TIMEOUT)
        current = self._current_release()
        tags = self.releases()
        latest = tags[0] if tags else ""
        available = bool(latest) and latest != current
        behind = 0
        if available:
            base = current or "HEAD"
            proc = self._git("rev-list", "--count", f"{base}..{latest}", check=False)
            if proc.returncode == 0:
                behind = int(proc.stdout.strip() or 0)
        return {
            "current": self.version,
            "current_release": current,
            "latest": latest,
            "available": available,
            "behind_commits": behind,
            "dirty": self.is_dirty(),
            "releases": tags[:8],
        }

    def apply(self, tag: Optional[str] = None) -> dict:
        """Check out the latest (or a specific) release tag as detached HEAD."""
        self._ensure_repo()
        if self.is_dirty():
            raise UpdaterError("local modifications detected: stash or commit before updating")
        info = self.check()
        target = tag or info["latest"]
        if not target:
            raise UpdaterError("no release tags available on origin")
        if tag is None and target == info["current_release"]:
            return {"from": target, "to": target, "changed": False}
        installed = self.install_requirements(target)
        self._git("checkout", "--quiet", "--detach", target)
        return {"from": info["current"], "to": target, "changed": True, "installed": installed}

    def rollback(self) -> dict:
        """Fall back to the newest release older than the current one."""
        self._ensure_repo()
        if self.is_dirty():
            raise UpdaterError("local modifications detected: stash or commit before rolling back")
        tags = self.releases()
        current = self._current_release()
        if not tags:
            raise UpdaterError("no release tags available to roll back to")
        if current in tags:
            idx = tags.index(current)
            if idx + 1 >= len(tags):
                raise UpdaterError("already on the oldest release, nothing to roll back to")
            target = tags[idx + 1]
        else:
            target = tags[0]
        installed = self.install_requirements(target)
        self._git("checkout", "--quiet", "--detach", target)
        return {
            "from": current or "development", "to": target, "changed": True,
            "installed": installed,
        }


def main(argv: list[str]) -> int:
    """``updater.py install-deps``: install this checkout's requirements."""
    if argv != ["install-deps"]:
        print("usage: updater.py install-deps", file=sys.stderr)
        return 2
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    updater = GitUpdater(Path(__file__).resolve().parents[3], interactive=sys.stdin.isatty())
    status = 0
    manager = updater.system.manager
    if manager is None:
        entries = updater.requirements()["system"]
        print("System packages: unsupported system, install these yourself if missing: "
              + ", ".join(entries))
    else:
        print(f"System packages: {manager}")
        try:
            new = updater.install_system_packages()
            print(f"  {' '.join(new) or 'nothing new'}")
        except UpdaterError as exc:
            # Keep going: the app starts without them, only some features need them.
            print(f"  error: {exc}", file=sys.stderr)
            status = 1
    try:
        new = updater.install_python_packages()
        done = "done" if updater.interactive else "up to date"
        print(f"Python packages: {' '.join(new) or done}")
    except UpdaterError as exc:
        print(f"Python packages: error: {exc}", file=sys.stderr)
        status = 1
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
