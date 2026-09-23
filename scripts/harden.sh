#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
image="ghcr.io/librelane/librelane:${LIBRELANE_TAG:-3.0.14}"
pdk_volume="ttsky26d-pdk-${LIBRELANE_TAG:-3.0.14}"
container_id=""
cleanup() {
  if [[ -n "$container_id" ]]; then docker rm -f "$container_id" >/dev/null 2>&1 || true; fi
}
trap cleanup EXIT
# Reuse the existing Docker-managed PDK; no host filesystem is bind-mounted.
docker run --rm --network none -v "$pdk_volume:/pdk:ro" "$image" \
  test -f /pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
container_id="$(docker create --network none -v "$pdk_volume:/pdk:ro" "$image" sleep infinity)"
docker start "$container_id" >/dev/null
docker exec "$container_id" mkdir -p /work/runs/wokwi
COPYFILE_DISABLE=1 tar --no-xattrs --exclude 'tt/.git' --exclude 'tt/__pycache__' -cf - src info.yaml tt tools/source_manifest.py | \
  docker exec -i "$container_id" tar -C /work -xf -
docker exec -w /work "$container_id" sh -c 'python tools/source_manifest.py > source_manifest.json'
mkdir -p runs
# Retrieve reports even on failure, so a failed physical run is diagnosable.
result=0
flow_args=(src/config_merged.json)
if [[ -n "${FLOW_TO:-}" ]]; then flow_args+=(--to "$FLOW_TO"); fi
docker exec -e PDK_ROOT=/pdk -e CI=1 -w /work "$container_id" \
  python -m librelane --pdk-root /pdk --pdk sky130A --run-tag wokwi \
  --force-run-dir runs/wokwi --hide-progress-bar "${flow_args[@]}" || result=$?
docker exec "$container_id" cp /work/source_manifest.json /work/runs/wokwi/source_manifest.json
if [[ -d runs/wokwi ]]; then
  mkdir -p build
  mv runs/wokwi "build/run-$(date +%Y%m%d-%H%M%S)"
fi
docker exec "$container_id" tar -C /work -cf - runs | tar -xf -
if [[ "$result" == 0 && -z "${FLOW_TO:-}" ]]; then
  .venv/bin/python tools/finalize_harden.py --project-root . \
    --pdk-version 8afc8346a57fe1ab7934ba5a6056ea8b43078e71
fi
exit "$result"
