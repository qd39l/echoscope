#!/usr/bin/env python3
"""Audit final Tiny Tapeout pins, routes, LVS, DRC, and template alignment."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "runs/wokwi/final"
DESIGN = "tt_um_qd39l_echoscope"
FINAL_DEF = FINAL / "def" / (DESIGN + ".def")
TEMPLATE_DEF = ROOT / "tt/tech/sky130A/def/tt_block_1x1_pg.def"


def pin_blocks(definition):
    section = re.search(r"^PINS\s+\d+\s*;(.*?)^END PINS", definition, re.M | re.S)
    if not section:
        raise AssertionError("DEF has no PINS section")
    result = {}
    for match in re.finditer(r"^\s*-\s+(\S+)(.*?);", section.group(1), re.M | re.S):
        name, body = match.groups()
        direction = re.search(r"\+ DIRECTION\s+(\S+)", body)
        layer = re.search(r"\+ LAYER\s+(\S+)", body)
        location = re.search(r"\+ (?:PLACED|FIXED)\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)", body)
        result[name] = {
            "direction": direction.group(1) if direction else None,
            "layer": layer.group(1) if layer else None,
            "location": tuple(map(int, location.groups())) if location else None,
            "has_port": "+ PORT" in body,
        }
    return result


def net_blocks(definition):
    section = re.search(r"^NETS\s+\d+\s*;(.*?)^END NETS", definition, re.M | re.S)
    if not section:
        raise AssertionError("DEF has no NETS section")
    return [m.group(0) for m in re.finditer(r"^\s*-\s+.*?;", section.group(1), re.M | re.S)]


def expected_signal_pins():
    pins = {"clk", "ena", "rst_n"}
    for bus in ("ui_in", "uo_out", "uio_in", "uio_out", "uio_oe"):
        pins.update("%s[%d]" % (bus, bit) for bit in range(8))
    return pins


def main():
    final_text = FINAL_DEF.read_text()
    template_text = TEMPLATE_DEF.read_text()
    final_pins = pin_blocks(final_text)
    template_pins = pin_blocks(template_text)
    signal_pins = expected_signal_pins()
    all_expected = signal_pins | {"VPWR", "VGND"}
    assert set(final_pins) == all_expected

    for name in signal_pins:
        actual = final_pins[name]
        reference = template_pins[name]
        assert actual["has_port"], "%s has no physical PORT geometry" % name
        assert actual["direction"] == reference["direction"], name
        assert actual["layer"] == reference["layer"], name
        assert actual["location"] == reference["location"], name

    for name in ("VPWR", "VGND"):
        assert final_pins[name]["has_port"], "%s has no physical PORT geometry" % name
        assert final_pins[name]["direction"] == "INOUT"
        assert final_pins[name]["layer"] == "met4"

    intentional_unused = {"uio_in[%d]" % bit for bit in range(5, 8)}
    nets = net_blocks(final_text)
    for pin in sorted(signal_pins - intentional_unused):
        matches = [block for block in nets if "( PIN %s )" % pin in block]
        assert len(matches) == 1, "%s does not occur in exactly one DEF net" % pin
        block = matches[0]
        assert "+ ROUTED" in block, "%s has no detailed route" % pin
        connections = re.findall(r"\(\s*(\S+)\s+(\S+)\s*\)", block)
        assert any(instance != "PIN" for instance, _ in connections), (
            "%s has no cell-side connection" % pin
        )

    lef = (FINAL / "lef" / (DESIGN + ".lef")).read_text()
    lef_pins = set(re.findall(r"^\s*PIN\s+(\S+)", lef, re.M))
    assert all_expected <= lef_pins

    pnl = (FINAL / "pnl" / (DESIGN + ".pnl.v")).read_text()
    for declaration in (
        "input clk;",
        "input ena;",
        "input rst_n;",
        "inout VPWR;",
        "inout VGND;",
        "input [7:0] ui_in;",
        "input [7:0] uio_in;",
        "output [7:0] uio_oe;",
        "output [7:0] uio_out;",
        "output [7:0] uo_out;",
    ):
        assert declaration in pnl, "missing powered-netlist declaration: " + declaration

    metrics = json.loads((FINAL / "metrics.json").read_text())
    for metric in (
        "route__drc_errors",
        "magic__drc_error__count",
        "antenna__violating__nets",
        "antenna__violating__pins",
        "design__critical_disconnected_pin__count",
        "design__lvs_device_difference__count",
        "design__lvs_error__count",
        "design__lvs_net_difference__count",
        "design__lvs_property_fail__count",
        "design__lvs_unmatched_device__count",
        "design__lvs_unmatched_net__count",
        "design__lvs_unmatched_pin__count",
    ):
        assert metrics[metric] == 0, "%s=%s" % (metric, metrics[metric])

    print("PASS: 43/43 signal pins and 2/2 power pins match the 1x1 template")
    print("PASS: 40 used signal pins have a routed cell-side connection")
    print("PASS: powered netlist, LEF ports, DRC, antenna, and LVS checks are clean")
    print("INFO: 3 unused top inputs; no critical disconnected pins")


if __name__ == "__main__":
    main()
