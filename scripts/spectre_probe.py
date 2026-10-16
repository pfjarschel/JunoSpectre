#!/usr/bin/env python3
"""Interactive hardware probe and verification CLI for Juno Spectre.

Lists the MIDI ports and tests bidirectional SysEx communication with the
Roland JUNO-DS / XPS-30 (identity, patch name, sound mode, tone levels).
For the Launch Control XL3, use tools/lcxl3_probe.py.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from spectre.core.midi import MidiDeviceManager
from spectre.core.protocol import JunoClient

console = Console()


def probe_hardware() -> None:
    """Scan and display status of all connected MIDI devices and the Roland synth."""
    console.print(
        Panel.fit(
            "[bold cyan]Juno Spectre — Hardware Probe & SysEx Diagnostics[/bold cyan]\n"
            "[dim]Verifying Roland XPS-30 / Juno-DS[/dim]",
            border_style="cyan",
        )
    )

    inputs = MidiDeviceManager.get_input_names()
    outputs = MidiDeviceManager.get_output_names()

    # Port Table
    table = Table(title="Detected ALSA MIDI Ports", header_style="bold magenta")
    table.add_column("Type", style="dim", width=8)
    table.add_column("Port Name", style="bold")
    table.add_column("Classification")

    juno_in, juno_out = MidiDeviceManager.find_juno_ports()

    for inp in inputs:
        status = "[yellow]Generic MIDI[/yellow]"
        if inp == juno_in:
            status = "[green]Roland Synth (Input)[/green]"
        table.add_row("Input", inp, status)

    for out in outputs:
        status = "[yellow]Generic MIDI[/yellow]"
        if out == juno_out:
            status = "[green]Roland Synth (Output)[/green]"
        table.add_row("Output", out, status)

    console.print(table)

    if not juno_in or not juno_out:
        console.print("[bold red]Error:[/bold red] Roland JUNO-DS / XPS-30 ports not found!")
        return

    # Synth Communication Diagnostics
    console.print("\n[bold yellow]Querying Roland Synth via SysEx...[/bold yellow]")
    with MidiDeviceManager() as mgr:
        mgr.connect_juno()
        client = JunoClient(mgr)

        # 1. Identity Request
        ident = client.ping(timeout=1.0)
        if ident:
            console.print("  [green]✔[/green] Synth Identity Received:")
            console.print(f"    • Device ID: [bold]{hex(ident.device_id)}[/bold] ({ident.device_id})")
            console.print(
                f"    • Family Code: [bold]{[hex(x) for x in ident.family_code]}[/bold] "
                f"({'Roland JUNO-DS / XPS-30 Series' if ident.is_juno_ds_or_xps else 'Unknown'})"
            )
            console.print(
                f"    • Software Revision: [bold]{'.'.join(str(x) for x in ident.software_revision)}[/bold]"
            )
        else:
            console.print("  [red]✖[/red] No Identity Reply received.")

        # 2. Sound Mode
        try:
            mode = client.get_sound_mode(timeout=1.0)
            console.print(f"  [green]✔[/green] Active Sound Mode: [bold cyan]{mode.name}[/bold cyan] ({int(mode)})")
        except Exception as e:
            console.print(f"  [red]✖[/red] Failed to query Sound Mode: {e}")
            return

        # 3. Patch Name
        try:
            patch_name = client.get_patch_name(timeout=1.0)
            console.print(f"  [green]✔[/green] Active Patch Name: [bold green]\"{patch_name}\"[/bold green]")
        except Exception as e:
            console.print(f"  [red]✖[/red] Failed to read patch name: {e}")

        # 4. Tone TVA Levels
        try:
            levels = client.get_tone_levels(timeout=1.0)
            t_table = Table(title=f"Temporary Buffer Tone TVA Levels for \"{patch_name}\"")
            for i in range(1, 5):
                t_table.add_column(f"Tone {i}", justify="center")
            t_table.add_row(*(f"[bold cyan]{lvl}[/bold cyan]" for lvl in levels))
            console.print(t_table)
        except Exception as e:
            console.print(f"  [red]✖[/red] Failed to query Tone levels: {e}")


def main() -> None:
    argparse.ArgumentParser(description="Juno Spectre Hardware Probe & Diagnostic Tool").parse_args()
    probe_hardware()


if __name__ == "__main__":
    main()
