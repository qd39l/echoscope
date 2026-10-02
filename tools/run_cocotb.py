"""Run the complete RTL/gate suite and issue a source-bound result receipt."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from verification_manifest import ROOT, snapshot, require_unchanged


def inputs(gate=False, pdk_root=None):
    paths = [*ROOT.glob('test/test*.py'), ROOT/'test/tb.v', ROOT/'test/Makefile',
             ROOT/'test/requirements.txt', ROOT/'tools/model.py',
             ROOT/'tools/run_cocotb.py', ROOT/'tools/verification_manifest.py']
    if gate:
        library = Path(pdk_root)/'sky130A/libs.ref/sky130_fd_sc_hd/verilog'
        paths += [ROOT/'test/gate_level_netlist.v', library/'primitives.v', library/'sky130_fd_sc_hd.v']
    else:
        paths += [ROOT/'src/project.v', ROOT/'src/echo_engine.v']
    return paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gate', action='store_true')
    parser.add_argument('--pdk-root', default=os.environ.get('PDK_ROOT', ROOT/'.pdk'))
    args = parser.parse_args()
    kind = 'gate' if args.gate else 'rtl'
    directory = ROOT/'build/verification'
    directory.mkdir(parents=True, exist_ok=True)
    result = directory/f'{kind}-results.xml'
    receipt = directory/f'{kind}-receipt.json'
    result.unlink(missing_ok=True)
    receipt.unlink(missing_ok=True)
    if args.gate:
        shutil.copyfile(ROOT/'runs/wokwi/final/pnl/tt_um_qd39l_echoscope.pnl.v', ROOT/'test/gate_level_netlist.v')
    paths = inputs(args.gate, args.pdk_root)
    before = snapshot(paths)
    modules = 'test,test_gate_video,test_init,test_interruptions' if args.gate else 'test,test_frames,test_init,test_interruptions'
    command = ['make', '-C', str(ROOT/'test'), f'COCOTB_TEST_MODULES={modules}',
               f'COCOTB_RESULTS_FILE={result}', 'COCOTB_TEST_FILTER=', 'COCOTB_TESTCASE=']
    command += ['GATES=yes', f'PDK_ROOT={Path(args.pdk_root).resolve()}'] if args.gate else ['GATES=no']
    # Copied .pyc files can retain another checkout's code and co_filename.
    # A fresh prefix prevents reading any existing bytecode, not just writing it.
    with tempfile.TemporaryDirectory(prefix='echoscope-python-') as cache:
        env = dict(os.environ,PYTHONPYCACHEPREFIX=cache,PYTHONDONTWRITEBYTECODE='1')
        subprocess.run(command, check=True,env=env)
    require_unchanged(paths, before)
    tree = ET.parse(result)
    cases = list(tree.iter('testcase'))
    assert len(cases) == 8 and not list(tree.iter('failure')) and not list(tree.iter('error'))
    skipped = len(list(tree.iter('skipped')))
    assert skipped == int(args.gate)
    receipt.write_text(json.dumps(dict(result='pass', input_sha256=before,
        output_sha256=snapshot([result]), tests_passed=8-skipped, tests_skipped=skipped,
        modules=modules.split(',')), indent=2)+'\n')
    print(f'PASS: {kind} suite and provenance receipt')


if __name__ == '__main__':
    main()
