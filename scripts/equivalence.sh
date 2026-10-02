#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
.venv/bin/python tools/proof_receipt.py begin equivalence
container_id=""
trap 'if [[ -n "$container_id" ]]; then docker rm -f "$container_id" >/dev/null 2>&1 || true; fi' EXIT
container_id="$(docker create --network none -v ttsky26d-pdk-3.0.14:/pdk:ro ghcr.io/librelane/librelane:3.0.14 sleep infinity)"
docker start "$container_id" >/dev/null
docker exec "$container_id" mkdir /work
COPYFILE_DISABLE=1 tar --no-xattrs -cf - src/project.v src/echo_engine.v test/netlist.eqy test/formal_clockgate.v test/formal_physical.v test/formal_environment.v tools/run_eqy_strategies.py runs/wokwi/final/pnl/tt_um_qd39l_echoscope.pnl.v |
  docker exec -i "$container_id" tar -C /work -xf -
result=0
docker exec -w /work "$container_id" sh -c 'eqy -f -m -d equivalence test/netlist.eqy && python tools/run_eqy_strategies.py equivalence' || result=$?
mkdir -p build/equivalence
# Keep the captured inputs, but never mix logs/partitions from earlier runs.
.venv/bin/python - <<'PY'
from pathlib import Path
import shutil
for path in Path('build/equivalence').iterdir():
    if path.name != 'input-manifest.json':
        shutil.rmtree(path) if path.is_dir() else path.unlink()
PY
docker exec "$container_id" tar -C /work/equivalence -cf - . | tar -C build/equivalence -xf -
if [[ "$result" == 0 ]]; then .venv/bin/python tools/proof_receipt.py seal equivalence; fi
exit "$result"
