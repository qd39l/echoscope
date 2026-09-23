#!/usr/bin/env python3
"""Collect reviewable evidence, refusing stale or failed final artifacts."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

from audit_physical_pins import main as audit_pins
from source_manifest import matches_build

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'runs/wokwi'
FINAL = RUN / 'final'
OUT = ROOT / 'docs/verification'
TOP = 'tt_um_qd39l_echoscope'


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(name: str, data) -> None:
    (OUT / name).write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')


def check_xml(path: Path, expected_pass: int, expected_skip: int):
    tree = ET.parse(path)
    cases = list(tree.iter('testcase'))
    assert not list(tree.iter('failure')) and not list(tree.iter('error')), path
    skipped = len(list(tree.iter('skipped')))
    assert len(cases) - skipped == expected_pass and skipped == expected_skip, path
    # Avoid publishing host filesystem names in otherwise portable evidence.
    for case in cases:
        if 'file' in case.attrib:
            file = Path(case.attrib['file'])
            if file.is_absolute():
                case.attrib['file'] = str(file.relative_to(ROOT))
    return tree


def main():
    audit_pins()
    m = json.loads((FINAL / 'metrics.json').read_text())
    for key in ('timing__setup_vio__count', 'timing__hold_vio__count',
                'design__max_slew_violation__count', 'design__max_cap_violation__count',
                'route__drc_errors', 'magic__drc_error__count',
                'design__lvs_error__count', 'antenna__violating__nets',
                'antenna__violating__pins', 'design__critical_disconnected_pin__count'):
        assert m[key] == 0, (key, m[key])
    assert m['timing__setup__ws'] >= 0 and m['timing__hold__ws'] >= 0
    hashes = json.loads((RUN / 'source_manifest.json').read_text())
    assert matches_build(ROOT, hashes), 'Source changed since physical build'
    assert digest(ROOT / 'test/gate_level_netlist.v') == digest(FINAL / f'pnl/{TOP}.pnl.v'), 'GL test used another netlist'
    # Clock gating is permitted only for the serially initialized world bank.
    netlist = (FINAL / f'pnl/{TOP}.pnl.v').read_text()
    assert len(re.findall(r'sky130_fd_sc_hd__dlclkp_\d+\s+\S+\s*\(', netlist)) == 1
    bank_bits = []
    for cell, body in re.findall(r'(sky130_fd_sc_hd__\w+)\s+\S+\s*\((.*?)\);', netlist, re.S):
        q = re.search(r'\.Q\(\\([ab]_(?:now|past)\[\d+\])\s*\)', body)
        if q:
            assert '__dfxtp_' in cell, (cell, q[1])
            bank_bits.append(q[1])
    assert len(set(bank_bits)) == 128
    assert digest(ROOT / f'build/precheck/check/{TOP}.gds') == digest(FINAL / f'gds/{TOP}.gds'), 'Precheck used another layout'
    rtl = check_xml(ROOT / 'build/verification/rtl-results.xml', 6, 0)
    gl = check_xml(ROOT / 'build/verification/gate-results.xml', 5, 1)
    precheck_root = ROOT / 'build/precheck/tt/precheck/reports'
    precheck = check_xml(precheck_root / 'results.xml', 15, 0)
    proof_root = ROOT / 'build/proof'
    assert (proof_root / 'formal.log').read_text().count('SAT proof finished - no model found: SUCCESS!') == 6
    proof_hashes = json.loads((proof_root / 'source_manifest.json').read_text())
    assert all(digest(ROOT / name) == value for name, value in proof_hashes.items())
    OUT.mkdir(parents=True, exist_ok=True)
    rtl.write(OUT / 'rtl-tests.xml', encoding='unicode')
    gl.write(OUT / 'gate-tests.xml', encoding='unicode')
    precheck.write(OUT / 'precheck.xml', encoding='unicode')
    write_json('metrics.json', m)
    write_json('source_manifest.json', hashes)
    write_json('formal.json', {'proofs_passed': ['abstract_inverse_both_directions',
               'serial_evolve', 'serial_perturb', 'serial_clone', 'serial_identity_scan',
               'serial_initialization_from_arbitrary_storage'],
               'source_sha256': proof_hashes})
    write_json('artifacts.json', {kind: digest(FINAL / f'{kind}/{TOP}.{suffix}')
               for kind, suffix in (('gds','gds'),('lef','lef'),('pnl','pnl.v'))})
    shutil.copyfile(precheck_root / 'results.md', OUT / 'precheck.md')
    synthesis = next(RUN.glob('*yosys-synthesis/reports/stat.rpt'))
    timing = next(RUN.glob('*stapostpnr/summary.rpt'))
    shutil.copyfile(synthesis, OUT / 'synthesis-stats.txt')
    shutil.copyfile(timing, OUT / 'timing-summary.txt')
    print('PASS: final physical, simulation, formal, and precheck evidence collected')


if __name__ == '__main__':
    main()
