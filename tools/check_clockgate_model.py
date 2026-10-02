"""Validate the formal ICG translation against the supplied PDK UDP model."""
import argparse
import json
import os
from pathlib import Path
import subprocess
from verification_manifest import ROOT, snapshot, require_unchanged

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--pdk-root',default=os.environ.get('PDK_ROOT',ROOT/'.pdk'))
args=parser.parse_args()
lib=Path(args.pdk_root)/'sky130A/libs.ref/sky130_fd_sc_hd/verilog'
sources=[ROOT/'test/formal_clockgate.v', ROOT/'test/clockgate_tb.v',
         lib/'primitives.v',lib/'sky130_fd_sc_hd.v']
inputs=sources+[ROOT/'tools/check_clockgate_model.py',ROOT/'tools/verification_manifest.py']
before=snapshot(inputs)
out=ROOT/'build/clockgate-model'
out.mkdir(parents=True,exist_ok=True)
(out/'report.json').unlink(missing_ok=True)
subprocess.run(['iverilog','-g2012','-s','clockgate_tb','-DFUNCTIONAL','-DUSE_POWER_PINS','-DUNIT_DELAY=#1',
                '-o',str(out/'sim.vvp'),*map(str,sources)],check=True)
result=subprocess.run(['vvp',str(out/'sim.vvp')],check=True,capture_output=True,text=True)
assert 'PASS: 256 gate-enable sequences, 8192 observations' in result.stdout
require_unchanged(inputs,before)
(out/'report.json').write_text(json.dumps(dict(result='pass',input_sha256=before,
    sequences=256,observations=8192),indent=2)+'\n')
print(result.stdout)
