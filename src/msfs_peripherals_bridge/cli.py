"""Command-line interface (``msfs-bridge``)."""

from __future__ import annotations

import logging
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from . import __version__, backup, config
from .devices.calibration import load_calibration
from .mapping.loader import (
    apply_calibration,
    hide_device,
    load_device_catalog,
    load_hidden_devices,
    load_profile,
    load_profiles,
    select_profile,
    unhide_device,
)
from .models import Profile
from .simconnect.client import DEFAULT_HOST, DEFAULT_PORT, BridgeClient, DryRunDispatcher

app = typer.Typer(
    add_completion=False,
    help="Map Linux USB flight-sim peripherals to MSFS via a SimConnect bridge.",
)
console = Console()


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


@app.command()
def version() -> None:
    """Print the version and exit."""
    console.print(f"msfs-peripherals-bridge {__version__}")


@app.command(name="list-devices")
def list_devices() -> None:
    """Show catalog devices and whether they are connected right now."""
    catalog = load_device_catalog(config.devices_file())
    table = Table(title="Configured devices")
    table.add_column("id", style="cyan")
    table.add_column("name")
    table.add_column("USB")
    table.add_column("status")

    try:
        from .devices import evdev_reader

        present = evdev_reader.discover(catalog)
    except RuntimeError as exc:
        console.print(f"[yellow]Device scan skipped: {exc}[/yellow]")
        present = {}

    for dev in catalog.devices:
        status = "[green]connected[/green]" if dev.id in present else "[dim]absent[/dim]"
        table.add_row(dev.id, dev.name, f"{dev.vendor}:{dev.product}", status)
    console.print(table)


@app.command(name="deregister-device")
def deregister_device(
    device_id: str = typer.Argument(
        "", help="Catalog id to hide (omit with --list to see hidden ids)."
    ),
    restore: bool = typer.Option(False, "--restore", help="Un-hide the id instead of hiding it."),
    show_hidden: bool = typer.Option(False, "--list", help="List currently hidden ids and exit."),
) -> None:
    """Hide a device from your catalog list (non-destructive, per-user).

    Removes a device — including the bundled sample hardware a stranger inherits
    from ``config/devices.yaml`` — from *this user's* list without editing the
    versioned catalog or any profile. Reversible with ``--restore``; ``--list``
    shows what is currently hidden.
    """
    if show_hidden:
        hidden = sorted(load_hidden_devices())
        console.print(", ".join(hidden) if hidden else "[dim]no hidden devices[/dim]")
        return
    if not device_id:
        console.print("[red]Give a device id (or use --list).[/red]")
        raise typer.Exit(code=1)
    if restore:
        unhide_device(device_id)
        console.print(f"[green]Restored[/green] [cyan]{device_id}[/cyan] to the catalog list.")
        return
    hide_device(device_id)
    console.print(
        f"[green]Deregistered[/green] [cyan]{device_id}[/cyan] "
        "(reversible: --restore, or re-register in the device explorer)."
    )


@app.command()
def scan() -> None:
    """List every connected controller with its axes, buttons and hats.

    Use this to find the real USB id of a device that is not in the catalog
    yet (the Fulcrum yoke ids are placeholders) and to see how many analog
    axes / digital inputs each device exposes before mapping them.
    """
    from .devices import capabilities

    try:
        devices = capabilities.scan()
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    catalog = load_device_catalog(config.devices_file())
    known = {(d.usb_key) for d in catalog.devices}
    if not devices:
        console.print("[yellow]No controllers detected. Are the devices plugged in?[/yellow]")
        return

    for dev in devices:
        in_catalog = (int(dev.vendor, 16), int(dev.product, 16)) in known
        tag = "[green]in catalog[/green]" if in_catalog else "[yellow]NEW[/yellow]"
        console.print(f"\n[bold]{dev.name}[/bold]  USB {dev.usb}  {tag}  [dim]{dev.path}[/dim]")
        table = Table(box=None, pad_edge=False)
        table.add_column("axis", style="cyan")
        table.add_column("code")
        table.add_column("range")
        table.add_column("rest")
        for a in dev.analog_axes:
            table.add_row(a.name, str(a.code), f"{a.min}..{a.max}", str(a.value))
        console.print(table)
        console.print(
            f"  analog axes: [cyan]{len(dev.analog_axes)}[/cyan]   "
            f"hats: [cyan]{len(dev.hats)}[/cyan] "
            f"({', '.join(h.name for h in dev.hats) or '-'})   "
            f"buttons: [cyan]{len(dev.buttons)}[/cyan]"
        )


@app.command()
def inventory() -> None:
    """List ALL connected USB HID/joystick devices, registered or not.

    Unlike ``list-devices`` (catalog only) this also shows *unregistered*
    hardware — plug a new device in and read its USB id + name here, then add it
    to config/devices.yaml (see docs/MANUAL.md, step 6). Foreground of the
    planned GUI device explorer.
    """
    from .devices import inventory as inv

    catalog = load_device_catalog(config.devices_file())
    try:
        items = inv.inventory(catalog)
    except RuntimeError as exc:  # pragma: no cover - evdev missing
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    if not items:
        console.print("[yellow]No devices detected. Plugged in? udev rules applied?[/yellow]")
        return

    table = Table(title="Connected devices")
    table.add_column("USB", style="cyan")
    table.add_column("name")
    table.add_column("via")
    table.add_column("status")
    for it in items:
        status = (
            f"[green]registered[/green] ([cyan]{it.catalog_id}[/cyan])"
            if it.registered
            else "[yellow]unregistered[/yellow]"
        )
        table.add_row(it.usb, it.name or "[dim]?[/dim]", it.transport, status)
    console.print(table)


@app.command()
def monitor(
    device: str = typer.Argument(..., help="Catalog device id or /dev/input/eventX path."),
) -> None:
    """Live-print raw events from one device (like evtest) to identify codes."""
    from .devices import capabilities, evdev_reader

    path = _device_path(device)
    caps = capabilities.describe(path)
    console.print(f"Monitoring [bold]{caps.name}[/bold] ({caps.usb}). Ctrl-C to stop.\n")
    try:
        for ev in evdev_reader.read_device(device, path):
            console.print(f"{ev.kind.value:7} code={ev.code:<5} value={ev.value}")
    except KeyboardInterrupt:
        console.print("\nStopped.")


@app.command()
def calibrate(
    device: str = typer.Argument(..., help="Catalog device id to calibrate."),
    seconds: float = typer.Option(
        0.0, help="Auto-stop after N seconds. 0 = run until you press Ctrl-C."
    ),
) -> None:
    """Record axis ranges/centres and seen buttons/hats into calibration.yaml.

    Recording starts immediately (no prompt — works over Claude Code's `!`).
    Move every axis through its FULL travel, then press Ctrl-C to stop and save.
    """
    from .devices import calibration

    path = _device_path(device)
    limit = f"for {seconds:.0f}s" if seconds > 0 else "until you press Ctrl-C"
    console.print(
        f"[bold]Recording {device} {limit}.[/bold] Move EVERY axis through its full\n"
        "travel (and work hats/buttons). [bold]Press Ctrl-C when done.[/bold]"
    )
    result = calibration.record(device, path, seconds)

    cal_path = config.calibration_file()
    store = calibration.load_calibration(cal_path)
    # Preserve detents (snapshot --save-detent) and the human control labels
    # captured during identification — a fresh sweep would otherwise wipe them.
    previous = store.devices.get(device)
    if previous is not None:
        for code, ax in result.axes.items():
            if code in previous.axes and previous.axes[code].detent is not None:
                ax.detent = previous.axes[code].detent
        result.button_labels = {**previous.button_labels, **result.button_labels}
        result.hat_labels = {**previous.hat_labels, **result.hat_labels}
    store.devices[device] = result
    calibration.save_calibration(cal_path, store)

    console.print(f"\n[green]Saved[/green] to {cal_path}")
    for ax in result.axes.values():
        detent = f", detent {ax.detent}" if ax.detent is not None else ""
        console.print(
            f"  axis {ax.name or ax.code}: {ax.raw_min}..{ax.raw_max} (center {ax.center}{detent})"
        )
    console.print(f"  buttons seen: {result.buttons or '-'}")
    console.print(f"  hats seen: {result.hats or '-'}")


@app.command()
def snapshot(
    device: str = typer.Argument(..., help="Catalog device id or /dev/input/eventX path."),
    save_detent: bool = typer.Option(
        False, "--save-detent", help="Store the current axis positions as detents."
    ),
    save_center: bool = typer.Option(
        False, "--save-center", help="Store the current axis positions as centres."
    ),
) -> None:
    """Print the current raw value of every axis (one-shot, no movement needed).

    Position the levers where you want, then run this. With --save-detent it
    records the current positions as the detent ('0' notch) of each axis into
    config/calibration.yaml — e.g. put all TQ6+ levers on their detent first.
    """
    from .devices import calibration

    path = _device_path(device)
    table = Table(title=f"Axis snapshot — {device}")
    table.add_column("code", style="cyan")
    table.add_column("axis")
    table.add_column("value")
    for code, name, value in calibration.current_axis_values(path):
        table.add_row(str(code), name, str(value))
    console.print(table)

    if save_detent:
        cal_path = config.calibration_file()
        store = calibration.load_calibration(cal_path)
        captured = calibration.set_detents_from_current(store, device, path)
        calibration.save_calibration(cal_path, store)
        console.print(
            f"[green]Saved detents[/green] to {cal_path}: "
            + ", ".join(f"code {c}={v}" for c, v in captured.items())
        )

    if save_center:
        cal_path = config.calibration_file()
        store = calibration.load_calibration(cal_path)
        captured = calibration.set_centers_from_current(store, device, path)
        calibration.save_calibration(cal_path, store)
        console.print(
            f"[green]Saved centres[/green] to {cal_path}: "
            + ", ".join(f"code {c}={v}" for c, v in captured.items())
        )


def _device_path(device: str) -> str:
    """Resolve a catalog id or a raw event path to a /dev/input node."""
    if device.startswith("/dev/"):
        return device
    from .devices import evdev_reader

    catalog = load_device_catalog(config.devices_file())
    present = evdev_reader.discover(catalog)
    if device not in present:
        console.print(f"[red]Device '{device}' not found among connected devices.[/red]")
        raise typer.Exit(code=1)
    return present[device]


@app.command(name="list-profiles")
def list_profiles() -> None:
    """List the aircraft profiles found in the profiles directory."""
    profiles = load_profiles(config.profiles_dir())
    table = Table(title="Aircraft profiles")
    table.add_column("name", style="cyan")
    table.add_column("matches")
    table.add_column("devices")
    table.add_column("description")
    for p in profiles:
        table.add_row(
            p.name,
            ", ".join(p.aircraft_match) or "[dim]-[/dim]",
            ", ".join(p.bindings.keys()) or "[dim]-[/dim]",
            p.description,
        )
    console.print(table)


@app.command()
def validate() -> None:
    """Validate the device catalog and all profiles, then report."""
    catalog = load_device_catalog(config.devices_file())
    known = {d.id for d in catalog.devices}
    profiles = load_profiles(config.profiles_dir())
    calibration = load_calibration(config.calibration_file())
    problems = 0
    for p in profiles:
        for device_id in p.bindings:
            if device_id not in known:
                console.print(f"[red]Profile '{p.name}': unknown device id '{device_id}'[/red]")
                problems += 1
        # Every axis binding must resolve to a concrete raw range, either from
        # the profile itself or from calibration.yaml.
        try:
            apply_calibration(p, calibration)
        except ValueError as exc:
            console.print(f"[red]{exc}[/red]")
            problems += 1
    if problems:
        console.print(f"[red]{problems} problem(s) found.[/red]")
        raise typer.Exit(code=1)
    console.print(
        f"[green]OK[/green] - {len(catalog.devices)} devices, {len(profiles)} profiles valid."
    )


@app.command()
def run(
    profile: str | None = typer.Option(
        None, "--profile", "-p", help="Profile file (path or name) to load."
    ),
    aircraft: str | None = typer.Option(
        None, "--aircraft", "-a", help="Auto-select a profile by aircraft title."
    ),
    host: str = typer.Option(DEFAULT_HOST, help="SimConnect bridge host."),
    port: int = typer.Option(DEFAULT_PORT, help="SimConnect bridge port."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Log commands, don't send them."),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Start the mapping loop with a chosen or auto-selected profile."""
    _setup_logging(verbose)
    from . import runtime  # local import keeps evdev optional for other commands

    catalog = load_device_catalog(config.devices_file())
    chosen = _resolve_profile(profile, aircraft)
    if chosen is None:
        console.print("[red]No profile selected. Use --profile or --aircraft.[/red]")
        raise typer.Exit(code=1)
    console.print(f"Using profile [cyan]{chosen.name}[/cyan]")

    dispatcher: DryRunDispatcher | BridgeClient
    if dry_run:
        dispatcher = DryRunDispatcher()
    else:
        # reconnect=True: ride out a bridge restart (supervisor relaunch after an
        # MSFS CTD, or a faulted SimConnect link) without dropping device control.
        dispatcher = BridgeClient(host, port, reconnect=True)
        dispatcher.connect()

    try:
        runtime.run(chosen, catalog, dispatcher)
    except KeyboardInterrupt:
        console.print("\nStopped.")
    finally:
        dispatcher.close()


@app.command()
def read(
    name: str = typer.Argument(
        ..., help='SimVar to read, e.g. "AUTOPILOT HEADING LOCK DIR" or TITLE.'
    ),
    unit: str = typer.Option(
        "number", "--unit", "-u", help="SimVar unit (degrees, percent, bool…)."
    ),
    watch: bool = typer.Option(
        False, "--watch", "-w", help="Keep printing as the value changes (Ctrl-C to stop)."
    ),
    host: str = typer.Option(DEFAULT_HOST, help="SimConnect bridge host."),
    port: int = typer.Option(DEFAULT_PORT, help="SimConnect bridge port."),
    timeout: float = typer.Option(10.0, help="Seconds to wait for the first value."),
) -> None:
    """Read a SimVar from the running sim (needs the Wine bridge up).

    Subscribes to the variable and prints its value. Use it to read e.g. the
    autopilot heading bug ("AUTOPILOT HEADING LOCK DIR", unit degrees) so it can
    be assigned to a rocker switch. One-shot by default; --watch keeps streaming.
    """
    from .simconnect.protocol import Subscribe

    client = BridgeClient(host, port)
    try:
        client.connect()
    except OSError as exc:
        console.print(
            f"[red]Cannot reach the bridge at {host}:{port} — is it running? ({exc})[/red]"
        )
        raise typer.Exit(code=1) from exc

    client.send(Subscribe(name, unit))
    client.settimeout(None if watch else timeout)
    try:
        if watch:
            console.print(f"Watching [bold]{name}[/bold] ({unit}). Ctrl-C to stop.\n")
        for got_name, value in client.states():
            if got_name != name:
                continue
            console.print(f"{name} = [cyan]{value}[/cyan] {unit}")
            if not watch:
                return
        console.print("[yellow]Bridge closed the connection before sending a value.[/yellow]")
    except KeyboardInterrupt:
        console.print("\nStopped.")
    except TimeoutError:
        console.print(
            f"[red]No value within {timeout:.0f}s.[/red] Is MSFS running with a flight loaded, "
            f"and is '{name}' a readable SimVar?"
        )
        raise typer.Exit(code=1) from None
    finally:
        client.close()


def _resolve_profile(profile: str | None, aircraft: str | None) -> Profile | None:
    if profile:
        path = Path(profile)
        if not path.exists():
            path = config.profiles_dir() / f"{profile}.yaml"
        chosen: Profile | None = load_profile(path)
    elif aircraft:
        chosen = select_profile(load_profiles(config.profiles_dir()), aircraft)
    else:
        return None
    if chosen is None:
        return None
    calibration = load_calibration(config.calibration_file())
    return apply_calibration(chosen, calibration)


@app.command(name="export-config")
def export_config_cmd(
    dest: str = typer.Argument(..., help="Destination .zip for the backup."),
) -> None:
    """Back up all user data (profiles + arrangement + own devices) into a .zip."""
    res = backup.export_config(dest)
    console.print(
        f"[green]✓[/green] Backup: {res.path}  "
        f"({res.profiles} Profile, Kalibrierung: {'ja' if res.calibration else 'nein'}, "
        f"{res.user_files} GUI-Dateien)"
    )


@app.command(name="import-config")
def import_config_cmd(
    src: str = typer.Argument(..., help="Backup-Zip aus export-config."),
) -> None:
    """Restore an export-config backup (overwrites the matching files)."""
    try:
        res = backup.import_config(src)
    except (ValueError, OSError) as exc:
        console.print(f"[red]Import fehlgeschlagen:[/red] {exc}")
        raise typer.Exit(code=1) from None
    console.print(
        f"[green]✓[/green] Wiederhergestellt: {len(res.profiles)} Profile, "
        f"Kalibrierung: {'ja' if res.calibration else 'nein'}, "
        f"{len(res.user_files)} GUI-Dateien"
    )


@app.command(name="export-device")
def export_device_cmd(
    device_id: str = typer.Argument(..., help="Catalog id of the device, e.g. 'switch_panel'."),
    dest: str = typer.Argument(..., help="Destination .zip for the device package."),
    profile: str = typer.Option(
        ..., "--profile", "-p", help="Profil, aus dem das Mapping stammt (ohne .yaml)."
    ),
) -> None:
    """Share a single device: definition + mapping + arrangement + calibration in a .zip."""
    from . import device_package

    try:
        res = device_package.export_device_package(device_id, profile, dest)
    except (ValueError, OSError) as exc:
        console.print(f"[red]Export fehlgeschlagen:[/red] {exc}")
        raise typer.Exit(code=1) from None
    console.print(
        f"[green]✓[/green] Device package: {res.path}  "
        f"({res.bindings} Eingaben / {res.outputs} Anzeigen aus „{profile}“, "
        f"Anordnung: {'ja' if res.has_layout else 'nein'}, "
        f"Kalibrierung: {'ja' if res.has_calibration else 'nein'})"
    )


@app.command(name="import-device")
def import_device_cmd(
    src: str = typer.Argument(..., help="Device-package .zip from export-device."),
    profile: str = typer.Option(
        "",
        "--profile",
        "-p",
        help="Target profile for the mapping (without .yaml). Empty = skip the mapping.",
    ),
) -> None:
    """Load a device package: registers the device + takes over arrangement/calibration/mapping."""
    from . import device_package

    try:
        res = device_package.import_device_package(src, profile or None)
    except (ValueError, OSError) as exc:
        console.print(f"[red]Import fehlgeschlagen:[/red] {exc}")
        raise typer.Exit(code=1) from None
    into = f" → “{res.target_profile}”" if res.target_profile else " (mapping skipped)"
    console.print(
        f"[green]✓[/green] „{res.device_name}“ importiert: "
        f"{res.bindings} Eingaben / {res.outputs} Anzeigen{into}, "
        f"Anordnung: {'ja' if res.layout else 'nein'}, "
        f"Kalibrierung: {'ja' if res.calibration else 'nein'}"
    )


if __name__ == "__main__":  # pragma: no cover
    app()
