#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/proof
.venv/bin/python tools/proof_receipt.py begin formal
.venv/bin/python - <<'PY'
import hashlib, json
from pathlib import Path
names = ('src/echo_step.v', 'src/echo_engine.v', 'test/formal.v', 'test/formal_serial.v', 'test/formal_init.v')
Path('build/proof/source_manifest.json').write_text(json.dumps(
    {name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in names},
    indent=2) + '\n')
PY
# Prove the abstract inverse and that the serial engine implements it for
# arbitrary initial 128-bit twin-world state, direction and selected cell.
COPYFILE_DISABLE=1 tar --no-xattrs -cf - src/echo_step.v src/echo_engine.v test/formal.v test/formal_serial.v test/formal_init.v | \
docker run --rm --network none -i ghcr.io/librelane/librelane:3.0.14 \
  bash -c 'mkdir /tmp/proof && cd /tmp/proof && tar -xf - &&
    yosys -Q -T -p "read_verilog src/echo_step.v test/formal.v; prep -top formal_roundtrip -flatten; sat -verify -prove roundtrip_ok 1 -show-inputs" &&
    for op in 0 1 2 3; do
      yosys -Q -T -p "read_verilog src/echo_step.v src/echo_engine.v test/formal_serial.v; prep -top formal_serial -flatten; async2sync; sat -verify -seq 34 -prove-skip 33 -prove proof_ok 1 -set-def-inputs -set rst_n 1 -set ena 1 -set operation $op -set start 0 -set-at 1 start 1 -set-init engine.busy 0 -set-init engine.direction 0 -set-init-def -show-inputs" || exit
    done &&
    yosys -Q -T -p "read_verilog src/echo_engine.v test/formal_init.v; prep -top formal_init -flatten; sat -verify -seq 34 -prove-skip 33 -prove initialized 1 -set-def-inputs -set rst_n 1 -set-at 1 rst_n 0 -set-init-def -show-inputs"' | tee build/proof/formal.log
.venv/bin/python tools/proof_receipt.py seal formal
