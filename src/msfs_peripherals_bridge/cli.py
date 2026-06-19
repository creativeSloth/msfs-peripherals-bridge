"""Command-line interface (``msfs-bridge``)."""

from __future__ import annotations

import logging
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from . import __version__, config
from .mapping.loader import load_device_catalog, load_profile, load_profiles, select_profile
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
    seconds: float = typer.Option(8.0, help="Recording window length."),
) -> None:
    """Record axis ranges/centres and seen buttons/hats into calibration.yaml."""
    from .devices import calibration

    path = _device_path(device)
    console.print(
        f"[bold]Calibrating {device}[/bold] for {seconds:.0f}s.\n"
        "Move EVERY axis through its full travel, work the hat in all directions\n"
        "and press every button. Then let everything rest for the centre point."
    )
    typer.confirm("Ready?", default=True, abort=True)
    result = calibration.record(device, path, seconds)

    cal_path = config.calibration_file()
    store = calibration.load_calibration(cal_path)
    store.devices[device] = result
    calibration.save_calibration(cal_path, store)

    console.print(f"\n[green]Saved[/green] to {cal_path}")
    for ax in result.axes.values():
        console.print(
            f"  axis {ax.name or ax.code}: {ax.raw_min}..{ax.raw_max} (center {ax.center})"
        )
    console.print(f"  buttons seen: {result.buttons or '-'}")
    console.print(f"  hats seen: {result.hats or '-'}")


@app.command()
def snapshot(
    device: str = typer.Argument(..., help="Catalog device id or /dev/input/eventX path."),
    save_detent: bool = typer.Option(
        False, "--save-detent", help="Store the current axis positions as detents."
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
    problems = 0
    for p in profiles:
        for device_id in p.bindings:
            if device_id not in known:
                console.print(f"[red]Profile '{p.name}': unknown device id '{device_id}'[/red]")
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
        dispatcher = BridgeClient(host, port)
        dispatcher.connect()

    try:
        runtime.run(chosen, catalog, dispatcher)
    except KeyboardInterrupt:
        console.print("\nStopped.")
    finally:
        dispatcher.close()


def _resolve_profile(profile: str | None, aircraft: str | None) -> Profile | None:
    if profile:
        path = Path(profile)
        if not path.exists():
            path = config.profiles_dir() / f"{profile}.yaml"
        return load_profile(path)
    if aircraft:
        return select_profile(load_profiles(config.profiles_dir()), aircraft)
    return None


if __name__ == "__main__":  # pragma: no cover
    app()
