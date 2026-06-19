"""msfs-peripherals-bridge.

Map Linux USB flight-sim peripherals (Fulcrum One yoke, VirtualFly TQ6+,
Saitek trim wheel & rudder pedals, ...) to Microsoft Flight Simulator
SimVars and events, with per-aircraft mapping profiles.

The simulator runs under Proton/Wine; a small bridge process inside the
Wine prefix exposes SimConnect over a local socket (see ``bridge/``).
"""

__version__ = "0.1.0"
