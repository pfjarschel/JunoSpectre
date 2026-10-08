#!/usr/bin/env python3
"""Interactive hardware profile manager, MIDI learn tool, and smooth scaler visualizer.

Supports listing and inspecting profiles, interactive MIDI Learn, live scaling visualization,
and full real-time bridging between controller and Roland synthesizer.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rich.console import Console
from rich.panel import Panel
from rich.prompt import IntPrompt, Prompt
from rich.table import Table

from src.spectre.control import (
    MidiControllerEngine,
    ProfileManager,
    ScaleMode,
    SmoothScaler,
    build_standard_parameter_registry,
)
from src.spectre.core.midi import MidiDeviceManager
from src.spectre.core.protocol import JunoClient

console = Console()


def show_profiles() -> None:
    """List all available hardware controller profiles."""
    mgr = ProfileManager()
    profiles = mgr.list_profiles()

    table = Table(title="Installed Controller Profiles (config/hardware_profiles/)", header_style="bold magenta")
    table.add_column("Profile Name", style="bold green")
    table.add_column("Manufacturer", style="cyan")
    table.add_column("Model")
    table.add_column("Controls", justify="center")
    table.add_column("Bindings", justify="center")
    table.add_column("Keywords", style="dim")

    for p in profiles:
        kws = ", ".join(p.device_match_keywords)
        table.add_row(
            p.profile_name,
            p.manufacturer,
            p.model,
            str(len(p.controls)),
            str(len(p.default_bindings)),
            kws,
        )

    console.print(table)


def inspect_profile(profile_name: str) -> None:
    """Show detailed controls and default bindings of a profile."""
    mgr = ProfileManager()
    try:
        prof = mgr.load_profile(profile_name)
    except FileNotFoundError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        return

    console.print(
        Panel.fit(
            f"[bold green]{prof.profile_name}[/bold green] by [cyan]{prof.manufacturer}[/cyan]\n"
            f"[dim]{prof.description}[/dim]",
            title="Profile Details",
            border_style="green",
        )
    )

    # Controls Table
    c_table = Table(title=f"Defined Controls ({len(prof.controls)})", header_style="bold cyan")
    c_table.add_column("ID", style="bold")
    c_table.add_column("Name")
    c_table.add_column("Type")
    c_table.add_column("Msg")
    c_table.add_column("Number", justify="right")

    for c in prof.controls.values():
        c_table.add_row(c.id, c.name, c.control_type.value, c.message_type.value.upper(), str(c.number))
    console.print(c_table)

    # Bindings Table
    b_table = Table(title=f"Default Parameter Bindings ({len(prof.default_bindings)})", header_style="bold yellow")
    b_table.add_column("Control ID")
    b_table.add_column("Msg", justify="center")
    b_table.add_column("Number", justify="right")
    b_table.add_column("Target Category", style="dim")
    b_table.add_column("Target Parameter", style="bold")
    b_table.add_column("Scale Mode", style="cyan")

    for b in prof.default_bindings:
        b_table.add_row(
            b.control_id or "-",
            b.message_type.value.upper(),
            str(b.number),
            b.target.category.value,
            b.target.display_name or b.target.target_key,
            b.scale_mode.value,
        )
    console.print(b_table)


def demo_smooth_scaler() -> None:
    """Run simulated sweeps demonstrating proportional smooth scaling convergence."""
    console.print(
        Panel.fit(
            "[bold cyan]Smooth Scaler Mathematical Simulation[/bold cyan]\n"
            "[dim]Demonstrating parameter jump elimination and boundary convergence without dead zones.[/dim]",
            border_style="cyan",
        )
    )

    # Simulation 1: Moving Up (Physical=20, Synth=100)
    console.print("\n[bold yellow]Scenario 1: Moving Up (Physical starting at 20, Synth value at 100)[/bold yellow]")
    scaler = SmoothScaler(initial_physical=20, initial_synth=100.0, mode=ScaleMode.SMOOTH)
    table1 = Table(header_style="bold magenta")
    table1.add_column("Step")
    table1.add_column("Physical (P)")
    table1.add_column("Synth (V)")
    table1.add_column("Converged?")
    table1.add_column("Visual Gap (P: blue, V: green)")

    for p in [20, 35, 55, 75, 95, 110, 120, 125, 127]:
        v, changed, _ = scaler.process(p)
        p_bar = "█" * (p // 4)
        v_bar = "▓" * (v // 4)
        table1.add_row(
            f"Move to {p}",
            f"[blue]{p:3d}[/blue]",
            f"[green]{v:3d}[/green] ({scaler.synth_value_float:.1f})",
            "[bold green]YES[/bold green]" if scaler.is_converged else "[dim]No[/dim]",
            f"[blue]{p_bar:<32}[/blue] | [green]{v_bar:<32}[/green]",
        )
    console.print(table1)

    # Simulation 2: Moving Down (Physical=100, Synth=20)
    console.print("\n[bold yellow]Scenario 2: Moving Down (Physical starting at 100, Synth value at 20)[/bold yellow]")
    scaler2 = SmoothScaler(initial_physical=100, initial_synth=20.0, mode=ScaleMode.SMOOTH)
    table2 = Table(header_style="bold magenta")
    table2.add_column("Step")
    table2.add_column("Physical (P)")
    table2.add_column("Synth (V)")
    table2.add_column("Converged?")
    table2.add_column("Visual Gap (P: blue, V: green)")

    for p in [100, 85, 65, 45, 25, 15, 5, 0]:
        v, changed, _ = scaler2.process(p)
        p_bar = "█" * (p // 4)
        v_bar = "▓" * (v // 4)
        table2.add_row(
            f"Move to {p}",
            f"[blue]{p:3d}[/blue]",
            f"[green]{v:3d}[/green] ({scaler2.synth_value_float:.1f})",
            "[bold green]YES[/bold green]" if scaler2.is_converged else "[dim]No[/dim]",
            f"[blue]{p_bar:<32}[/blue] | [green]{v_bar:<32}[/green]",
        )
    console.print(table2)


def interactive_midi_learn() -> None:
    """Interactive MIDI Learn wizard in the terminal."""
    console.print(
        Panel.fit(
            "[bold green]Interactive MIDI Learn Wizard[/bold green]\n"
            "[dim]Select a synth parameter, then touch or turn any control on your hardware controller.[/dim]",
            border_style="green",
        )
    )

    targets = build_standard_parameter_registry()

    console.print("\n[bold cyan]Available Parameter Categories:[/bold cyan]")
    cats = ["tone_tvf", "tone_tva", "tone_pitch", "patch_common", "normalized_param"]
    for i, c in enumerate(cats, start=1):
        console.print(f"  [bold yellow]{i}[/bold yellow]. {c}")

    cat_idx = IntPrompt.ask("Select category number", default=1)
    chosen_cat = cats[max(0, min(len(cats) - 1, cat_idx - 1))]

    cat_targets = [t for t in targets if t.category.value == chosen_cat]
    console.print(f"\n[bold cyan]Parameters in {chosen_cat}:[/bold cyan]")
    for i, t in enumerate(cat_targets, start=1):
        console.print(f"  [bold yellow]{i}[/bold yellow]. {t.display_name or t.target_key}")

    t_idx = IntPrompt.ask("Select parameter number", default=1)
    target = cat_targets[max(0, min(len(cat_targets) - 1, t_idx - 1))]

    console.print(f"\n[bold green]Target Selected:[/bold green] [bold cyan]{target.display_name}[/bold cyan]")
    scale_mode_str = Prompt.ask(
        "Select scaling mode",
        choices=["smooth", "relative_center_reset", "relative_delta", "catch_up", "jump"],
        default="smooth",
    )
    scale_mode = ScaleMode(scale_mode_str)

    console.print(f"\n[bold yellow]Listening on MIDI input for {target.display_name}... (Move a knob or fader now, Ctrl+C to cancel)[/bold yellow]")

    engine = MidiControllerEngine()
    engine.learn.start_learning(target, scale_mode=scale_mode)

    with MidiDeviceManager() as mgr:
        try:
            mgr.connect_launch_control()
            console.print("[green]✔ Connected to controller port[/green]")
        except Exception as e:
            console.print(f"[yellow]Note connecting controller: {e}[/yellow]")

        start = time.time()
        learned_binding = None
        try:
            while time.time() - start < 30.0:
                for msg in mgr.iter_lcxl_messages():
                    binding, consumed = engine.learn.process_midi_message(msg)
                    if consumed and binding:
                        learned_binding = binding
                        break
                if learned_binding:
                    break
                time.sleep(0.005)
        except KeyboardInterrupt:
            console.print("\n[yellow]Canceled by user.[/yellow]")
            return

    if learned_binding:
        console.print(
            Panel.fit(
                f"[bold green]✔ Binding Learned Successfully![/bold green]\n"
                f"• Type: [cyan]{learned_binding.message_type.value.upper()}[/cyan]\n"
                f"• Number: [yellow]{learned_binding.number}[/yellow] (Channel: {learned_binding.channel})\n"
                f"• Target: [bold]{target.display_name}[/bold]\n"
                f"• Mode: [cyan]{scale_mode.value}[/cyan]",
                border_style="green",
            )
        )
    else:
        console.print("[red]Timed out waiting for MIDI message.[/red]")


def run_live_bridge(profile_name: str | None = None, duration: float = 60.0) -> None:
    """Run live real-time bridge with smooth scaling and bidirectional controller feedback."""
    console.print(
        Panel.fit(
            "[bold cyan]Juno Spectre — Live Control Dispatcher & Scaler Bridge[/bold cyan]\n"
            f"[dim]Running live bridge for {duration:.0f}s. Press Ctrl+C to stop.[/dim]",
            border_style="cyan",
        )
    )

    with MidiDeviceManager() as mgr:
        try:
            in_port, out_port = mgr.connect_launch_control()
            console.print(f"[green]✔ Connected Controller:[/green] In='{in_port}', Out='{out_port}'")
        except Exception as e:
            console.print(f"[bold red]Error connecting controller:[/bold red] {e}")
            return

        try:
            mgr.connect_juno()
            juno_client = JunoClient(mgr)
            console.print("[green]✔ Connected Roland Synthesizer[/green]")
        except Exception as e:
            console.print(f"[yellow]Roland synth not connected (running in offline controller monitor mode): {e}[/yellow]")
            juno_client = None

        engine = MidiControllerEngine(midi_mgr=mgr, juno_client=juno_client)

        if profile_name:
            prof = engine.load_profile(profile_name)
            console.print(f"[green]✔ Loaded specified profile:[/green] {prof.profile_name}")
        else:
            prof = engine.auto_detect_profile(in_port)
            if prof:
                console.print(f"[green]✔ Auto-detected profile:[/green] {prof.profile_name}")
            else:
                prof = engine.load_profile("novation_lc_xl")
                console.print(f"[yellow]Using default profile:[/yellow] {prof.profile_name}")

        # Synchronize synth values
        if juno_client:
            try:
                engine.sync_from_synth()
            except Exception as e:
                console.print(f"[yellow]Sync warning: {e}[/yellow]")

        start = time.time()
        try:
            while time.time() - start < duration:
                for event in engine.poll():
                    p = event.physical_value
                    v = event.synth_value
                    target_name = event.target.display_name if event.target else "Unknown"
                    conv_tag = "[bold green]1:1[/bold green]" if event.is_converged else "[yellow]scaling[/yellow]"

                    bar = "█" * (v // 4)
                    console.print(
                        f"[blue]P:{p:3d}[/blue] $\\to$ [green]V:{v:3d}[/green] {conv_tag:<8} "
                        f"| [bold cyan]{target_name:<20}[/bold cyan] "
                        f"[green]{bar:<32}[/green]"
                    )
                time.sleep(0.001)
        except KeyboardInterrupt:
            console.print("\n[yellow]Bridge stopped by user.[/yellow]")


def main() -> None:
    parser = argparse.ArgumentParser(description="Juno Spectre Controller Manager & Diagnostic CLI")
    parser.add_argument(
        "--mode",
        choices=["list-profiles", "inspect-profile", "test-scaler", "learn", "live"],
        default="list-profiles",
        help="Command mode to run (default: list-profiles)",
    )
    parser.add_argument("--profile", type=str, default=None, help="Profile name or filename to inspect or load")
    parser.add_argument("--duration", type=float, default=60.0, help="Duration for live bridge mode (seconds)")
    args = parser.parse_args()

    if args.mode == "list-profiles":
        show_profiles()
    elif args.mode == "inspect-profile":
        inspect_profile(args.profile or "novation_lc_xl")
    elif args.mode == "test-scaler":
        demo_smooth_scaler()
    elif args.mode == "learn":
        interactive_midi_learn()
    elif args.mode == "live":
        run_live_bridge(profile_name=args.profile, duration=args.duration)


if __name__ == "__main__":
    main()
