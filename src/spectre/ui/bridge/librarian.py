"""Librarian bridge mixin: patch files, user flash slots, and origin tracking."""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from PyQt6.QtCore import pyqtProperty, pyqtSignal, pyqtSlot

from ...core.categories import code_from_index
from ...core.patch_state import PatchState
from ...vector.motion import RecorderState
from .base import BridgeBaseMixin

logger = logging.getLogger(__name__)


class LibrarianBridgeMixin(BridgeBaseMixin):
    """Patch librarian catalog, flash slot read/write/backup, and .spectre files."""

    currentRefChanged = pyqtSignal()
    librarianChanged = pyqtSignal()
    libraryErrorChanged = pyqtSignal()

    _ENGINE_VIEWS = ("JUNO PCM", "VECTOR", "WAVETABLE", "VA")

    def _set_current_slot_ref(self, msb: int, lsb: int, pc: int, kind: str) -> None:
        """Record which synth slot the temp buffer was auditioned from."""
        if msb == 87 and lsb in (0, 1):
            source = "synth-user"
        elif msb == 86 and lsb == 0:
            source = "synth-user"
        else:
            source = "factory"
        self._current_ref = {"source": source, "kind": kind,
                             "msb": msb, "lsb": lsb, "pc": pc}
        self.currentRefChanged.emit()

    def _clear_current_ref(self) -> None:
        self._current_ref = None
        self.currentRefChanged.emit()

    @pyqtProperty(str, notify=currentRefChanged)
    def currentRefLabel(self) -> str:
        ref = self._current_ref or {}
        if ref.get("source") == "synth-user":
            slot = 501 + int(ref.get("lsb", 0)) * 128 + int(ref.get("pc", 0))
            return f"User slot {slot} · {self._patch_name}"
        if ref.get("source") == "factory":
            return f"Factory · {self._patch_name}"
        if ref.get("source") == "file":
            return f"Pi file · {self._patch_name}"
        return f"Unsaved sound · {self._patch_name}"

    @pyqtProperty(bool, notify=currentRefChanged)
    def currentIsUserSlot(self) -> bool:
        return (self._current_ref or {}).get("source") == "synth-user"

    @pyqtProperty(int, notify=currentRefChanged)
    def currentMsb(self) -> int:
        return int((self._current_ref or {}).get("msb", -1))

    @pyqtProperty(int, notify=currentRefChanged)
    def currentLsb(self) -> int:
        return int((self._current_ref or {}).get("lsb", -1))

    @pyqtProperty(int, notify=currentRefChanged)
    def currentPc(self) -> int:
        return int((self._current_ref or {}).get("pc", -1))

    @pyqtSlot(int, str, int)
    def setToneWave(self, tone_number: int, bank: str, wave_num: int) -> None:
        """Assign waveform to tone (1..4) and send SysEx to Roland hardware."""
        if 1 <= tone_number <= 4:
            self._tone_waves[tone_number - 1] = (bank.upper(), wave_num)
            t = self.patch_state.tones[tone_number - 1]
            t.wave_bank_l = bank.upper()
            t.wave_num_l = wave_num
            self._cached_tone_wave_data = [
                self._wave_catalog.get_wave(b, n) for b, n in self._tone_waves
            ]
            if self.engine.juno:
                try:
                    self.engine.juno.set_tone_wave(tone_number, bank=bank.upper(), wave_num=wave_num)
                except Exception as e:
                    logger.error(f"Error setting wave on synth: {e}")
            self.toneWavesChanged.emit()

    @pyqtSlot(str, int, result="QVariantMap")
    def getWaveInfo(self, bank: str, wave_num: int) -> dict:
        """Get wave metadata from catalog."""
        return self._wave_catalog.get_wave(bank, wave_num)

    @pyqtSlot(str)
    @pyqtSlot(str, str)
    def setPatchName(self, name: str, mode: str = "PATCH") -> None:
        """Set active patch name and sound mode."""
        self._patch_name = name
        self._sound_mode = mode
        self.patch_state.common.name = name
        self.patch_state.sound_mode = mode
        self.patchInfoChanged.emit(self._patch_name, self._sound_mode)
        if self.engine.juno:
            try:
                self.engine.juno.set_patch_name(name)
            except Exception as e:
                logger.warning(f"Could not set patch name on synth: {e}")

    def _librarian(self):
        repo = getattr(self, "_librarian_repo", None)
        if repo is None:
            logger.warning("Librarian repository not attached.")
        return repo

    def _fresh_live_state(self, name: str):
        """Capture the sounding temp buffer with app-side extras overlaid."""
        from ...core.patch_state import PatchState  # noqa: F401 (type use below)

        juno = self.juno
        if juno is None or not hasattr(juno, "read_full_patch"):
            raise ConnectionError("No synthesizer connected.")
        state = juno.read_full_patch(timeout=1.5)
        state.common.name = str(name)[:12]
        # Preserve app-side assignments the hardware image does not carry.
        try:
            state.macros = self.patch_state.macros
            state.macro_bases = dict(self.patch_state.macro_bases)
        except Exception:
            pass
        return state

    @staticmethod
    def _drop_backup(path) -> None:
        """Delete an auto-backup file (verified writes need no residue)."""
        try:
            if path:
                Path(path).unlink(missing_ok=True)
        except OSError as e:
            logger.debug(f"backup cleanup failed for {path}: {e}")

    def _live_spectre_extras(self) -> dict:
        extras: dict = {"engine_mode": getattr(self, "_active_view", "JUNO PCM")}
        try:
            extras["vector"] = {"x": float(self.engine.x),
                                "y": float(self.engine.y),
                                "w": float(self.engine.w)}
        except Exception:
            pass
        try:
            # Tempo is global (owned by the song), so patches don't carry it
            extras["motion"] = {"speed": float(self.engine.motion.speed)}
        except Exception:
            pass
        return extras

    @pyqtProperty(str, notify=libraryErrorChanged)
    def libraryError(self) -> str:
        """Why the librarian model failed to bind ('' when healthy)."""
        return getattr(self, "_library_error", "")

    @pyqtSlot()
    def openSavePatchModal(self) -> None:
        """Request UI to open the Save Patch dialog."""
        logger.debug("UI requested openSavePatchModal")
        self.requestOpenSavePatchModal.emit()

    @pyqtSlot(str, result="QVariantList")
    def getUserSlots(self, kind: str = "patch") -> list:
        """List user flash slots with live names. Only patches for now."""
        juno = self.juno
        if juno is None or kind != "patch":
            return []
        slots = []
        for idx in range(256):
            msb, lsb, pc = 87, (0 if idx < 128 else 1), idx % 128
            try:
                raw = juno.request_data((0x30 if idx < 128 else 0x31, idx % 128,
                                         0x00, 0x00), (0x00, 0x00, 0x00, 0x0C),
                                        timeout=1.0)
                nm = bytes(raw[:12]).decode("latin1", errors="replace").strip() if raw else "?"
            except Exception:
                nm = "?"
            slots.append({"number": 501 + idx, "msb": msb, "lsb": lsb, "pc": pc,
                          "name": nm, "free": nm in ("INIT PATCH", "")})
        return slots

    @pyqtSlot(result="QVariantList")
    def getUserSlotIndex(self) -> list:
        """Instant DB-backed slot list for the save-dialog picker.

        Live reads take ~13 s for 256 slots and would freeze the touch UI
        (MIDI request/response cannot safely overlap), so the picker reads
        the index. Our own device writes refresh it via upsert_synth_user.
        """
        repo = self._librarian()
        if repo is None:
            return []
        try:
            rows = repo.search("", source="synth-user", kind="patch", limit=300)
        except Exception as e:
            logger.debug(f"getUserSlotIndex failed: {e}")
            return []
        slots = []
        for r in rows:
            try:
                number = 501 + int(r.get("lsb", 0)) * 128 + int(r.get("pc", 0))
            except (TypeError, ValueError):
                continue
            slots.append({"number": number, "msb": r.get("msb"), "lsb": r.get("lsb"),
                          "pc": r.get("pc"), "name": r.get("name", ""),
                          "free": (r.get("name", "") or "").strip() in ("INIT PATCH", "")})
        slots.sort(key=lambda s: s["number"])
        return slots

    @pyqtSlot(result=int)
    def refreshUserSlotNames(self) -> int:
        """(Re)read all 256 user slot names+categories into the index.

        Only slots whose content changed are rewritten. Blocking (~10-15 s
        for a full pass); the dialog runs it deferred with a busy overlay.
        Returns refreshed count, -1 when no synth/repo. Aborts after 5
        consecutive read failures (cable pulled mid-pass).
        """
        from ...core.categories import decode_common_block

        repo = self._librarian()
        juno = self.juno
        if repo is None or juno is None:
            return -1
        n = fails = 0
        for idx in range(256):
            msb, lsb, pc = 87, (0 if idx < 128 else 1), idx % 128
            try:
                raw = juno.request_data(
                    (0x30 if idx < 128 else 0x31, idx % 128, 0x00, 0x00),
                    (0x00, 0x00, 0x00, 0x50), timeout=1.0)
            except Exception:
                raw = None
            if not raw or len(raw) < 80:
                fails += 1
                if fails >= 5:
                    logger.warning("refreshUserSlotNames: aborting after 5 failures")
                    break
                continue
            fails = 0
            name, cat = decode_common_block(bytes(raw))
            key = f"synth:patch:{msb}:{lsb}:{pc}"
            try:
                cur = repo.get(key)
            except Exception:
                cur = None
            if cur is None or cur.get("name") != name or cur.get("category") != cat:
                try:
                    repo.upsert_synth_user(msb, lsb, pc, name, cat)
                    n += 1
                except Exception as e:
                    logger.debug(f"slot upsert failed for {key}: {e}")
        self.librarianChanged.emit()
        return n

    @pyqtSlot(result=str)
    def currentCategoryCode(self) -> str:
        """Roland 3-letter category of the live temp sound (prefills save)."""
        juno = self.juno
        if juno is None:
            return ""
        try:
            base = juno.get_active_patch_base(timeout=1.0)
            from ...core.sysex import OFFSET_PATCH_COMMON as _OFF
            from ...core.sysex import add_address as _add
            raw = juno.request_data(_add(base, _OFF), (0x00, 0x00, 0x00, 0x50), timeout=1.0)
            if raw and len(raw) >= 80:
                return code_from_index(raw[0x0C])
        except Exception as e:
            logger.debug(f"currentCategoryCode failed: {e}")
        return ""

    @pyqtSlot(str, str, str, bool, str, result=str)
    def saveCurrentToFile(self, name: str, category: str = "",
                          tagsCsv: str = "", favorite: bool = False,
                          filename: str = "") -> str:
        """Always-on Pi save. Returns the file path, or '' + logs on failure.

        In PERFORM mode writes kind='performance' (mixer refs + part file
        links + active-part image); otherwise kind='patch'.
        """
        repo = self._librarian()
        if repo is None:
            return ""
        try:
            is_perf = str(self._sound_mode).upper() == "PERFORM"
            kind = "performance" if is_perf else "patch"
            tags = [t.strip()[:32] for t in (tagsCsv or "").split(",") if t.strip()][:16]
            origin = self._current_ref or {}
            synth_ref = None
            if not is_perf and origin.get("source") in ("factory", "synth-user"):
                synth_ref = {"source": origin["source"], "msb": origin.get("msb"),
                             "lsb": origin.get("lsb"), "pc": origin.get("pc")}
            if is_perf:
                active = max(1, min(16, int(getattr(self.patch_state, "active_perf_part", 1))))
                part = self.patch_state.perf_parts[active - 1]
                try:
                    state = self._fresh_live_state(
                        part.patch_name or part.name or name or self._patch_name)
                except Exception:
                    # Offline: snapshot the in-memory workstation state.
                    from ...core.spectre_format import patch_state_from_dict, patch_state_to_dict
                    state = patch_state_from_dict(patch_state_to_dict(self.patch_state))
                state.perf_parts = list(self.patch_state.perf_parts)
                state.perf_name = str(
                    name or getattr(self.patch_state, "perf_name", "") or "SPECTRE PERF")[:12]
                state.active_perf_part = active
                state.sound_mode = "PERFORM"
                file_name = state.perf_name
                extras = self._live_spectre_extras()
                try:
                    snaps = self._capture_part_snapshots()
                    self._part_snapshots = dict(snaps)
                    if snaps:
                        extras["part_snapshots"] = snaps
                    self.refreshPartFileStatus()
                except Exception as e:
                    logger.debug(f"save performance: snapshots failed: {e}")
                # A performance is the whole song: sounds + sequence + tempo.
                if hasattr(self, "sequencer"):
                    try:
                        extras["sequencer"] = self.sequencer.song.to_dict()
                    except Exception as e:
                        logger.debug(f"save performance: sequence failed: {e}")
            else:
                state = self._fresh_live_state(name or self._patch_name)
                file_name = state.common.name
                extras = self._live_spectre_extras()
            out = repo.save_current_as(
                state, file_name, category=category or "", tags=tags,
                favorite=bool(favorite), spectre=extras,
                synth_ref=synth_ref,
                filename=filename or None,
                kind=kind,
            )
            self._current_ref = {"source": "file", "kind": kind, "path": str(out)}
            self.currentRefChanged.emit()
            self.librarianChanged.emit()
            try:
                self._patch_name = state.perf_name if is_perf else state.common.name
                self.patchInfoChanged.emit(self._patch_name, self._sound_mode)
            except Exception:
                pass
            return str(out)
        except Exception as e:
            logger.warning(f"saveCurrentToFile failed: {e}")
            return ""

    @pyqtSlot(int, int, int, str, result=str)
    def saveCurrentToDevice(self, msb: int, lsb: int, pc: int, name: str) -> str:
        """Save the live sound to a user flash slot. Returns '' on success.

        Occupied slots are auto-backed to a Pi .spectre file first; the
        backup is deleted once the write verifies (no disk orphans).
        A failed verify keeps the backup and names it in the error.
        """
        repo = self._librarian()
        juno = self.juno
        if repo is None:
            return "librarian unavailable"
        if juno is None or not hasattr(juno, "write_user_patch"):
            return "no synthesizer connected"
        try:
            msb, lsb, pc = int(msb), int(lsb), int(pc)
            JunoClient = juno.__class__
            JunoClient.user_slot_base(msb, lsb, pc)  # validates
        except ValueError as e:
            return str(e)
        try:
            live = self._fresh_live_state(name or self._patch_name)
        except Exception as e:
            return f"could not read live sound: {e}"
        err = self._write_user_slot(live, msb, lsb, pc)
        if not err:
            self._set_current_slot_ref(msb, lsb, pc, "patch")
        return err

    def _write_user_slot(self, state, msb: int, lsb: int, pc: int) -> str:
        """Write + verify a sound into a user slot. Returns '' on success.

        An occupied slot is backed up to a Pi .spectre file first; the backup
        is deleted once the write verifies, and kept (and named) if it fails.
        """
        repo = self._librarian()
        juno = self.juno
        if repo is None:
            return "librarian unavailable"
        if juno is None or not hasattr(juno, "write_user_patch"):
            return "no synthesizer connected"
        backup_path = None
        try:
            try:
                previous = juno.read_user_patch(msb, lsb, pc, timeout=1.5)
                if (previous.common.name or "").strip() not in ("INIT PATCH", ""):
                    backup_path = repo.save_current_as(
                        previous, f"BACKUP_{msb}-{lsb}-{pc}_{previous.common.name}",
                        category=code_from_index(previous.common.category),
                        tags=["backup", "auto"],
                        synth_ref={"source": "synth-user", "msb": msb, "lsb": lsb, "pc": pc},
                    )
            except Exception as e:
                return f"backup failed, aborting: {e}"
            mismatches = juno.write_user_patch(state, msb, lsb, pc, timeout=1.5)
            if mismatches:
                kept = f" (slot backup kept at {Path(backup_path).name})" if backup_path else ""
                return "verify failed: " + ", ".join(mismatches) + kept
            self._drop_backup(backup_path)
            try:
                repo.upsert_synth_user(msb, lsb, pc, state.common.name,
                                       code_from_index(state.common.category))
            except Exception as e:
                logger.debug(f"synth-user index refresh failed: {e}")
            self.librarianChanged.emit()
            return ""
        except Exception as e:
            logger.warning(f"user slot write failed: {e}")
            return str(e)

    @pyqtSlot(int, int, int, str, result=bool)
    def renameUserSlot(self, msb: int, lsb: int, pc: int, name: str) -> bool:
        """Rename a user flash slot (factory ROM can never be renamed)."""
        repo = self._librarian()
        juno = self.juno
        if juno is None or not hasattr(juno, "rename_user_slot"):
            return False
        try:
            ok = bool(juno.rename_user_slot(int(msb), int(lsb), int(pc), str(name)))
        except (ValueError, TypeError):
            return False
        except Exception as e:
            logger.warning(f"renameUserSlot failed: {e}")
            return False
        if ok and repo is not None:
            # Re-read for the index (flash can stay busy briefly after a
            # write: retry before giving up so the list never goes stale).
            cur = None
            for _ in range(3):
                try:
                    cur = juno.read_user_patch(int(msb), int(lsb), int(pc), timeout=1.5)
                    break
                except Exception as e:
                    logger.debug(f"rename index re-read retry: {e}")
                    time.sleep(0.5)
            if cur is not None:
                try:
                    repo.upsert_synth_user(int(msb), int(lsb), int(pc), cur.common.name,
                                           code_from_index(cur.common.category))
                except Exception as e:
                    logger.warning(f"rename index refresh failed: {e}")
            else:
                logger.warning("rename index refresh failed: slot unreadable after rename")
            self.librarianChanged.emit()
        return ok

    @pyqtSlot(str, str, result=bool)
    def renameLibraryFile(self, path: str, name: str) -> bool:
        """Rename a Pi .spectre file (meta travels with the file)."""
        repo = self._librarian()
        if repo is None:
            return False
        try:
            from ...core.spectre_format import load_spectre, save_spectre

            loaded = load_spectre(path)
            loaded["meta"]["name"] = str(name)
            save_spectre(path, loaded["patch_state"], meta=loaded["meta"],
                         spectre=loaded["spectre"], synth_ref=loaded["synth_ref"],
                         kind=loaded["kind"], extra=loaded["extra"])
            repo.touch_file_row(path)
            repo._conn.commit()
            self.librarianChanged.emit()
            return True
        except Exception as e:
            logger.warning(f"renameLibraryFile failed for {path}: {e}")
            return False

    @pyqtSlot(int, int, int, result=str)
    def reinitUserSlot(self, msb: int, lsb: int, pc: int) -> str:
        """Restore a user flash slot to INIT (backup + temp-swap dance).

        The live temp buffer is captured, restored afterwards and verified,
        so the user's current edit survives. Backups are deleted once every
        step verifies; failures keep theirs and name them. Returns '' on
        success.
        """
        repo = self._librarian()
        juno = self.juno
        if repo is None:
            return "librarian unavailable"
        if juno is None or not hasattr(juno, "write_user_patch"):
            return "no synthesizer connected"
        slot_backup = temp_backup = None
        try:
            msb, lsb, pc = int(msb), int(lsb), int(pc)
            juno.__class__.user_slot_base(msb, lsb, pc)
            try:
                previous = juno.read_user_patch(msb, lsb, pc, timeout=1.5)
                if (previous.common.name or "").strip() not in ("INIT PATCH", ""):
                    slot_backup = repo.save_current_as(
                        previous, f"BACKUP_{msb}-{lsb}-{pc}_{previous.common.name}",
                        category=code_from_index(previous.common.category),
                        tags=["backup", "auto"],
                        synth_ref={"source": "synth-user", "msb": msb, "lsb": lsb, "pc": pc},
                    )
                temp_backup = repo.save_current_as(
                    self._fresh_live_state(self._patch_name),
                    f"BEFORE-REINIT_{previous.common.name}",
                    tags=["backup", "auto"],
                )
            except Exception as e:
                return f"backup failed, aborting: {e}"
            try:
                temp_image = juno.read_full_patch(timeout=1.5)
            except Exception as e:
                self._drop_backup(slot_backup)
                self._drop_backup(temp_backup)
                return f"could not capture live sound: {e}"
            if not juno.init_patch():
                self._drop_backup(slot_backup)
                self._drop_backup(temp_backup)
                return "could not initialize temp buffer"
            try:
                fresh = juno.read_full_patch(timeout=1.5)
            except Exception as e:
                juno.write_patch_regions(temp_image, juno.get_active_patch_base())
                return f"could not read init image: {e}"
            fresh.common.name = "INIT PATCH"
            mismatches = juno.write_user_patch(fresh, msb, lsb, pc, timeout=1.5)
            restore_fail, restore_mm = juno.restore_temp_patch(temp_image, timeout=1.5)
            if mismatches:
                kept = f" (slot backup kept at {Path(slot_backup).name})" if slot_backup else ""
                self._drop_backup(temp_backup)  # temp untouched, its backup redundant
                return "slot verify failed: " + ", ".join(mismatches) + kept
            if restore_fail or restore_mm:
                kept = ""
                if temp_backup:
                    kept = f" (live edit backup kept at {Path(temp_backup).name})"
                return "slot written BUT temp restore needs re-sync" + kept
            self._drop_backup(slot_backup)
            self._drop_backup(temp_backup)
            self._drop_backup(slot_backup)
            self._drop_backup(temp_backup)
            try:
                repo.upsert_synth_user(msb, lsb, pc, "INIT PATCH", "")
            except Exception as e:
                logger.debug(f"reinit index refresh failed: {e}")
            self.librarianChanged.emit()
            return ""
        except Exception as e:
            logger.warning(f"reinitUserSlot failed: {e}")
            return str(e)

    @pyqtSlot(result="QVariantList")
    def listUsbDrives(self) -> list:
        """Removable media roots for import/export (eglfs has no file dialog)."""
        import getpass
        from pathlib import Path as _P

        roots = []
        try:
            user = getpass.getuser()
        except Exception:
            user = ""
        for base in (f"/media/{user}", "/run/media/{user}", "/media", "/mnt"):
            try:
                p = _P(base)
                if not p.is_dir():
                    continue
                for child in sorted(p.iterdir()):
                    try:
                        if child.is_dir() and os.access(child, os.R_OK | os.W_OK):
                            roots.append(str(child))
                    except OSError:
                        continue
            except OSError:
                continue
        return roots

    @pyqtSlot(str, str, str, result=str)
    def exportLibraryFile(self, path: str, driveDir: str, filename: str = "") -> str:
        """Copy a Pi patch file to USB. Returns '' on success."""
        import shutil
        from pathlib import Path as _P

        try:
            src = _P(path)
            if src.suffix not in (".spectre", ".syx") or not src.is_file():
                return "not a patch file"
            dest_dir = _P(driveDir)
            if not dest_dir.is_dir():
                return "USB drive not found"
            dest = dest_dir / (filename or src.name)
            if dest.suffix != src.suffix:
                dest = dest.with_suffix(src.suffix)
            shutil.copy2(src, dest)
            return ""
        except Exception as e:
            logger.warning(f"exportLibraryFile failed: {e}")
            return str(e)

    @pyqtSlot(str, str, result=str)
    def importUsbFile(self, driveDir: str, filename: str) -> str:
        """Import a .spectre/.syx from USB into the Pi library. Returns path or ''."""
        repo = self._librarian()
        if repo is None:
            return ""
        try:
            from pathlib import Path as _P

            src = _P(driveDir) / filename
            out = repo.import_file(src)
            self.librarianChanged.emit()
            return str(out)
        except Exception as e:
            logger.warning(f"importUsbFile failed: {e}")
            return ""

    @pyqtSlot(str, result=bool)
    def deleteLibraryFile(self, path: str) -> bool:
        """Delete a Pi patch file (flash slots are reinitialized, never deleted)."""
        repo = self._librarian()
        if repo is None:
            return False
        try:
            ok = bool(repo.delete_file(path))
        except Exception as e:
            logger.warning(f"deleteLibraryFile failed: {e}")
            return False
        if ok:
            self.librarianChanged.emit()
        return ok

    @pyqtSlot(str, result="QVariantList")
    def listUsbFiles(self, driveDir: str) -> list:
        """List importable patch files at a USB drive root."""
        from pathlib import Path as _P

        try:
            root = _P(driveDir)
            if not root.is_dir():
                return []
            out = []
            for child in sorted(root.iterdir()):
                try:
                    if child.is_file() and child.suffix in (".spectre", ".syx"):
                        out.append({"name": child.name, "suffix": child.suffix})
                except OSError:
                    continue
            return out
        except Exception as e:
            logger.debug(f"listUsbFiles failed: {e}")
            return []

    @pyqtSlot(str, result=int)
    def importUsbAll(self, driveDir: str) -> int:
        """Import every .spectre/.syx at a USB drive root. Returns count."""
        repo = self._librarian()
        if repo is None:
            return 0
        try:
            from pathlib import Path as _P

            root = _P(driveDir)
            if not root.is_dir():
                return 0
            count = 0
            for child in sorted(root.iterdir()):
                try:
                    if child.is_file() and child.suffix in (".spectre", ".syx"):
                        repo.import_file(child)
                        count += 1
                except Exception as e:
                    logger.debug(f"import skipped {child}: {e}")
            self.librarianChanged.emit()
            return count
        except Exception as e:
            logger.warning(f"importUsbAll failed: {e}")
            return 0

    @pyqtSlot(str, str, result=str)
    def exportLiveSyx(self, driveDir: str, filename: str = "") -> str:
        """Export the live temp sound as .syx to USB. Returns '' on success."""
        juno = self.juno
        if juno is None or not hasattr(juno, "encode_patch_sysex"):
            return "no synthesizer connected"
        try:
            from pathlib import Path as _P

            dest_dir = _P(driveDir)
            if not dest_dir.is_dir():
                return "USB drive not found"
            state = juno.read_full_patch(timeout=1.5)
            blob = juno.encode_patch_sysex(state)
            safe = "".join(c if (c.isalnum() or c in ("-", "_", " ")) else "_"
                           for c in (filename or state.common.name)).strip() or "Untitled"
            dest = dest_dir / f"{safe}.syx"
            dest.write_bytes(blob)
            return ""
        except Exception as e:
            logger.warning(f"exportLiveSyx failed: {e}")
            return str(e)

    @pyqtSlot(str, result=str)
    def applySyxFile(self, path: str) -> str:
        """Push a .syx file into the live temp buffer and sync. Returns '' on success."""
        juno = self.juno
        if juno is None or not hasattr(juno, "apply_sysex_blob"):
            return "no synthesizer connected"
        try:
            from pathlib import Path as _P

            blob = _P(path).read_bytes()
            if not blob or blob[0] != 0xF0:
                return "not a .syx file"
            applied = juno.apply_sysex_blob(blob)
            if applied == 0:
                return "no valid DT1 messages found"
            try:
                self.syncPatchFromSynth()
            except Exception as e:
                logger.debug(f"applySyxFile: sync failed: {e}")
            self._current_ref = {"source": "file", "kind": "patch", "path": str(path)}
            self.currentRefChanged.emit()
            return ""
        except Exception as e:
            logger.warning(f"applySyxFile failed: {e}")
            return str(e)

    @pyqtSlot(result=int)
    def rescanLibrary(self) -> int:
        repo = self._librarian()
        if repo is None:
            return 0
        try:
            stats = repo.rescan_files()
        except Exception as e:
            logger.warning(f"rescanLibrary failed: {e}")
            return 0
        self.librarianChanged.emit()
        return int(stats.get("added", 0) + stats.get("updated", 0) + stats.get("removed", 0))

    @pyqtSlot(int)
    def openWaveBrowser(self, tone_index: int) -> None:
        """Request the UI to open the Wave Browser modal for a target tone (1-4)."""
        logger.debug(f"UI requested wave browser for Tone {tone_index}")
        self.requestOpenWaveBrowser.emit(tone_index)

    @pyqtSlot()
    def openScreensOverlay(self) -> None:
        """Request UI to open the Screens Launcher overlay."""
        self.requestOpenScreensOverlay.emit()

    @pyqtSlot()
    def openInitPatchModal(self) -> None:
        """Request UI to open the Patch Initialization confirmation modal."""
        logger.debug("UI requested openInitPatchModal")
        self.requestOpenInitPatchModal.emit()

    def _reset_engine_to_patch_state(self) -> None:
        """Sync tone wave caches from patch_state, centre the vector, reset tone levels."""
        self._tone_waves = [
            (t.wave_bank_l, t.wave_num_l) for t in self.patch_state.tones
        ]
        self._cached_tone_wave_data = [
            self._wave_catalog.get_wave(b, n) for b, n in self._tone_waves
        ]
        self.engine.set_coordinates(0.5, 0.5)
        self.engine.tone_levels = tuple(t.level for t in self.patch_state.tones)

    @pyqtSlot()
    def initPatch(self) -> None:
        """Initialize the active sound in RAM to the golden JUNO SPECTRE template."""
        logger.info("Initializing active patch in RAM to JUNO SPECTRE template...")

        # Pause motion playback without destroying the recorded trajectory, and hold
        # engine-driven SysEx for the whole critical section. Recording is left alone.
        motion_was_playing = self.engine.motion.state == RecorderState.PLAYING
        if motion_was_playing:
            self.engine.motion.pause()
            self.transportStateChanged.emit(self.engine.motion.state.value)

        try:
            with self.engine.hold_hardware_writes():
                # 1. Restore the golden image on hardware (one DT1 per region, zero residue).
                #    Falls back to the per-parameter reset sequence if the asset is missing.
                hw_ok = False
                if self.engine.juno:
                    try:
                        hw_ok = self.engine.juno.init_patch()
                    except Exception as e:
                        logger.error(f"Error sending init_patch to synth: {e}")
                if not hw_ok and not self.engine.juno:
                    logger.info("No synth connected; resetting in-memory state only.")

                # 2. Reset in-memory state from the SAME golden image the hardware received,
                #    so UI and synth provably match (decoded blob, or hand-built fallback).
                self.patch_state = PatchState.from_template_file() or PatchState.create_init_patch()

                # 3. Update patch name & mode
                self._patch_name = self.patch_state.common.name
                self._sound_mode = self.patch_state.sound_mode

                # 4. Wave caches, vector position and tone levels follow the template
                self._reset_engine_to_patch_state()
        finally:
            if motion_was_playing and self.engine.motion.state != RecorderState.PLAYING:
                self.engine.motion.play()
                self.transportStateChanged.emit(self.engine.motion.state.value)

        # 6. Emit all signals to trigger live UI refresh across all tabs and screens
        #    (macro deck values are derived getters, so they refresh automatically)
        self._emit_all_state_signals()
        self._clear_current_ref()  # fresh RAM template: no slot origin
        self.patchInitialized.emit()
        logger.info("Active patch initialization complete.")

