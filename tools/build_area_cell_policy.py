#!/usr/bin/env python3
"""Reproduce (or check) the small-drive synthesis policy from the pinned PDK."""
import argparse
import fnmatch
import os
from pathlib import Path
import re

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--pdk-root', type=Path, default=Path(os.getenv('PDK_ROOT', '.pdk')))
parser.add_argument('--write', action='store_true', help='update src/area_no_synth.cells')
args = parser.parse_args()
pdk = args.pdk_root / 'sky130A'
policy = pdk / 'libs.tech/openlane/sky130_fd_sc_hd'
lib = (pdk / 'libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib').read_text()
cells = set(re.findall(r'cell\s*\(\s*"?([^"\s)]+)', lib))
original = (policy / 'no_synth.cells').read_text().splitlines()
excluded = {line.strip() for line in original if line.strip() and not line.startswith('#')}
drc = (policy / 'drc_exclude.cells').read_text().splitlines()
allowed = {cell for cell in excluded if cell.endswith('_1') and cell in cells
           and cell[:-1] + '2' in cells and cell[:-1] + '2' not in excluded
           and not any(fnmatch.fnmatchcase(cell, pattern) for pattern in drc)}
expected = '\n'.join(line for line in original if line.strip() not in allowed) + '\n'
output = Path(__file__).resolve().parents[1] / 'src/area_no_synth.cells'
if args.write:
    output.write_text(expected)
else:
    assert output.read_text() == expected, 'Cell policy differs from pinned-PDK derivation'
print(f'PASS: {len(allowed)} additional drive-1 variants; all other exclusions retained')
