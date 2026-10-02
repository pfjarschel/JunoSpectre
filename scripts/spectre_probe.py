#!/usr/bin/env python3
"""Interactive hardware probe and verification CLI for Juno Spectre.

Tests bidirectional SysEx communication with Roland JUNO-DS / XPS-30
and receives MIDI control events from Novation Launch Control XL.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from src.spectre.core.midi import MidiDeviceManager
from src.spectre.core.protocol import JunoClient, SoundMode

console = Console()


def probe_hardware() -> None:
    """Scan and display status of all connected MIDI devices and the Roland synth."""
    console.print(
        Panel.fit(
            "[bold cyan]Juno Spectre — Hardware Probe & SysEx Diagnostics[/bold cyan]\n"
            "[dim]Verifying Roland XPS-30 / Juno-DS & Novation Launch Control XL[/dim]",
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
    lcxl_in, _ = MidiDeviceManager.find_launch_control_ports()

    for inp in inputs:
        status = "[yellow]Generic MIDI[/yellow]"
        if inp == juno_in:
            status = "[green]Roland Synth (Input)[/green]"
        elif inp == lcxl_in:
            status = "[blue]Launch Control XL (Input)[/blue]"
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
            console.print(f"  [green]✔[/green] Synth Identity Received:")
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


def monitor_controllers(duration: float = 30.0) -> None:
    """Listen for incoming MIDI messages from Launch Control XL and XPS-30."""
    console.print(
        Panel.fit(
            f"[bold cyan]MIDI Monitor Active[/bold cyan]\n"
            f"[dim]Move knobs/faders on your Launch Control XL or play XPS-30 (Listening for {duration:.0f}s, Ctrl+C to exit)...[/dim]",
            border_style="cyan",
        )
    )

    with MidiDeviceManager() as mgr:
        try:
            mgr.connect_launch_control()
            console.print("[green]✔ Connected to Launch Control XL input[/green]")
        except Exception as e:
            console.print(f"[yellow]Launch Control XL note: {e}[/yellow]")

        try:
            mgr.connect_juno()
            console.print("[green]✔ Connected to Roland Synth input[/green]")
        except Exception as e:
            console.print(f"[yellow]Roland Synth note: {e}[/yellow]")

        start = time.time()
        try:
            while time.time() - start < duration:
                # Check Launch Control messages
                for msg in mgr.iter_lcxl_messages():
                    if msg.type == "control_change":
                        console.print(
                            f"[bold blue][LCXL CC][/bold blue] Ch:{msg.channel + 1:<2} "
                            f"CC#[bold yellow]{msg.control:<3}[/bold yellow] = Value:[bold green]{msg.value:<3}[/bold green]"
                        )
                    elif msg.type in ("note_on", "note_off"):
                        console.print(
                            f"[blue][LCXL Note][/blue] Ch:{msg.channel + 1:<2} "
                            f"Note:{msg.note:<3} Vel:{msg.velocity:<3}"
                        )
                    else:
                        console.print(f"[blue][LCXL][/blue] {msg}")

                # Check Synth messages
                for msg in mgr.iter_juno_messages():
                    if msg.type != "clock":
                        console.print(f"[magenta][Synth][/magenta] {msg}")

                time.sleep(0.005)
        except KeyboardInterrupt:
            console.print("\n[yellow]Monitoring stopped by user.[/yellow]")


def quick_bridge(duration: float = 60.0, fader_ccs: list[int] | None = None) -> None:
    """Directly map Launch Control XL Faders 1-4 to Roland Synth Tones 1-4 TVA Levels."""
    if fader_ccs:
        fader_cc_map = {cc: i + 1 for i, cc in enumerate(fader_ccs[:4])}
    else:
        # Support user's template (CC 5..8) as well as factory defaults (CC 77..80)
        fader_cc_map = {
            5: 1, 6: 2, 7: 3, 8: 4,
            77: 1, 78: 2, 79: 3, 80: 4,
        }

    mapped_str = ", ".join(f"CC {cc} -> Tone {tone}" for cc, tone in sorted(fader_cc_map.items()) if cc in (5, 6, 7, 8, 77, 78, 79, 80))
    console.print(
        Panel.fit(
            f"[bold green]Quick Vector/Level Bridge Test[/bold green]\n"
            f"[dim]Mappings active:[/dim] [yellow]{mapped_str}[/yellow]\n"
            f"[dim]Moving Faders 1-4 updates Tones 1-4 TVA Levels in the temporary edit buffer live.[/dim]\n"
            f"[dim]Running for {duration:.0f}s. Press Ctrl+C to exit.[/dim]",
            border_style="green",
        )
    )

    with MidiDeviceManager() as mgr:
        mgr.connect_launch_control()
        mgr.connect_juno()
        client = JunoClient(mgr)

        patch_name = client.get_patch_name()
        console.print(f"Target Synth Patch: [bold green]\"{patch_name}\"[/bold green]")
        
        levels = list(client.get_tone_levels())
        console.print(f"Current Tone Levels: [bold cyan]{levels}[/bold cyan]\n")

        last_sent_val = {1: levels[0], 2: levels[1], 3: levels[2], 4: levels[3]}
        last_sent_time = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}

        start = time.time()
        try:
            while time.time() - start < duration:
                for msg in mgr.iter_lcxl_messages():
                    if msg.type == "control_change":
                        if msg.control in fader_cc_map:
                            tone_idx = fader_cc_map[msg.control]
                            if msg.value != last_sent_val[tone_idx]:
                                client.set_tone_level(tone_idx, msg.value)
                                levels[tone_idx - 1] = msg.value
                                last_sent_val[tone_idx] = msg.value

                                bar = "█" * (msg.value // 4)
                                console.print(
                                    f"[bold blue][CC {msg.control:2d}][/bold blue] "
                                    f"[bold cyan]Tone {tone_idx}[/bold cyan] $\\to$ [bold yellow]{msg.value:3d}[/bold yellow] "
                                    f"[green]{bar:<32}[/green] [dim]Levels: {levels}[/dim]"
                                )
                        else:
                            console.print(
                                f"[dim][LCXL CC {msg.control} = {msg.value}][/dim]"
                            )
                time.sleep(0.001)
        except KeyboardInterrupt:
            console.print("\n[yellow]Bridge test stopped by user.[/yellow]")


def main() -> None:
    parser = argparse.ArgumentParser(description="Juno Spectre Hardware Probe & Diagnostic Tool")
    parser.add_argument(
        "--mode",
        choices=["probe", "monitor", "bridge"],
        default="probe",
        help="Operation mode: 'probe' (default), 'monitor', or 'bridge'",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=60.0,
        help="Duration in seconds for monitor or bridge modes (default: 60s)",
    )
    parser.add_argument(
        "--faders",
        type=str,
        default="5,6,7,8",
        help="Comma-separated CC numbers for Faders 1-4 (default: '5,6,7,8')",
    )
    args = parser.parse_args()

    fader_list = [int(x.strip()) for x in args.faders.split(",") if x.strip()]

    if args.mode == "probe":
        probe_hardware()
    elif args.mode == "monitor":
        monitor_controllers(duration=args.duration)
    elif args.mode == "bridge":
        quick_bridge(duration=args.duration, fader_ccs=fader_list)


if __name__ == "__main__":
    main()
