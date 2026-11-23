"""Render the documented example through the same painter as the live Pi."""
import argparse
import json
from pathlib import Path

import cairo

from cluster import Lettering, draw

EXAMPLE = {
    "speed_display_aaos": 0, "speed_unit": "km/h",
    "range_m_aaos": 488000, "distance_unit": "km",
    "soc_aaos": 57600, "usable_capacity_wh": 64000,
    "gear_selected": "P", "parking_brake": True, "battery_power_mw": 0,
}

CHARGING_EXAMPLE = {
    "charge_state": "charging", "charge_port_connected": True,
    "gear_selected": "P", "speed_display_aaos": 0,
    "soc_aaos": 96000, "usable_capacity_wh": 150000,
    "range_m_aaos": 384000, "distance_unit": "km", "battery_power_mw": 22_000_000,
    "charge_seconds_remaining": 4500, "charge_target_pct": 90,
}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("day", "night"))
    parser.add_argument("output", type=Path)
    parser.add_argument("--lettering", type=Path, help="Lettering frame from an AAOS test session")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--charging", nargs="?", const="charging", choices=("charging", "idle", "full", "fault"),
                       help="Show a parked charging state (defaults to active charging)")
    modes.add_argument("--welcome", action="store_true", help="Show the pre-drive greeting")
    args = parser.parse_args()
    face = Lettering(json.loads(args.lettering.read_bytes())) if args.lettering else None
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 1920, 480)
    fields = dict(EXAMPLE, before_drive=args.welcome)
    if args.charging:
        fields = dict(CHARGING_EXAMPLE, charge_state=args.charging)
        if args.charging == "full":
            fields["soc_aaos"] = fields["usable_capacity_wh"] * fields["charge_target_pct"] / 100
    draw(cairo.Context(surface), 1920, 480, fields, face, dark=args.mode == "night")
    surface.write_to_png(str(args.output))
