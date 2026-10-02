#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
.venv/bin/python tools/proof_receipt.py begin safety
.venv/bin/python tools/formal_safety.py
mkdir -p build/safety
COPYFILE_DISABLE=1 tar --no-xattrs -cf - build/safety-inputs |
docker run --rm --network none -i ghcr.io/librelane/librelane:3.0.14 bash -c '
  mkdir /work && cd /work && tar -xf - &&
  yosys -Q -T -p "read_verilog -formal build/safety-inputs/engine_safety.v; prep -top echo_engine -flatten; async2sync; chformal -lower; sat -verify -seq 4 -tempinduct -maxsteps 8 -prove-asserts" &&
  yosys -Q -T -p "read_verilog -formal build/safety-inputs/controller.v; prep -top tt_um_qd39l_echoscope -flatten; memory_map; async2sync; chformal -lower; opt_clean; sat -verify -seq 4 -tempinduct -maxsteps 12 -prove-asserts -set-assumes -dump_vcd /tmp/counterexample.vcd"
' | tee build/safety/formal.log
bash scripts/formal_mutations.sh
.venv/bin/python tools/proof_receipt.py seal safety
