"""Git release-based self updater for Juno Spectre appliance deployments.

The appliance updates by checking out tagged releases from origin (detached
HEAD), never arbitrary development commits, and can roll back to the previous
tag when a release misbehaves on hardware.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

GIT_TIMEOUT = 15
FETCH_TIMEOUT = 60


class UpdaterError(RuntimeError):
    """Raised when a git updater operation fails."""


class GitUpdater:
    """Safe, blocking git operations backing the appliance update flow."""

    def __init__(self, repo_root: Path):
        self.repo_root = Path(repo_root)

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
        self._git("checkout", "--quiet", "--detach", target)
        return {"from": info["current"], "to": target, "changed": True}

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
        self._git("checkout", "--quiet", "--detach", target)
        return {"from": current or "development", "to": target, "changed": True}
