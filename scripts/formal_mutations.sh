#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
.venv/bin/python tools/formal_safety.py
mkdir -p build/safety
COPYFILE_DISABLE=1 tar --no-xattrs -cf - build/safety-inputs |
docker run --rm --network none -i ghcr.io/librelane/librelane:3.0.14 bash -c '
  set -e
  mkdir /work && cd /work && tar -xf -
  yosys -Q -T -p "read_verilog -formal build/safety-inputs/mutant_engine.v; prep -top echo_engine -flatten; async2sync; chformal -lower; sat -seq 4 -prove-asserts" > engine.log
  grep -q "SAT proof finished - model found: FAIL!" engine.log
  echo "PASS: missing state-bank enable rejected with a bounded counterexample"
  yosys -Q -T -p "read_verilog -formal build/safety-inputs/mutant_controller.v; prep -top tt_um_qd39l_echoscope -flatten; memory_map; async2sync; chformal -lower; opt_clean; sat -seq 40 -prove-asserts -set-assumes -set rst_n 1 -set-at 1 rst_n 0 -set ena 1 -set ui_in 0" > controller.log
  grep -q "SAT proof finished - model found: FAIL!" controller.log
  echo "PASS: active-video command acceptance rejected with a bounded counterexample"
' | tee build/safety/mutations.log
