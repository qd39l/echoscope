#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
image=ghcr.io/librelane/librelane:3.0.14
container_id="$(docker create --network none -v ttsky26d-pdk-3.0.14:/pdk:ro "$image" sleep infinity)"
trap 'docker rm -f "$container_id" >/dev/null 2>&1 || true' EXIT
docker start "$container_id" >/dev/null
docker exec "$container_id" mkdir -p /work
COPYFILE_DISABLE=1 tar --no-xattrs --exclude 'tt/.git' --exclude 'tt/__pycache__' -cf - src info.yaml tt | docker exec -i "$container_id" tar -C /work -xf -
docker exec -i "$container_id" sh -c 'cat > /work/sweep.py' <<'PY'
import json, pathlib, subprocess
root=pathlib.Path('/work'); base=json.loads((root/'src/config_merged.json').read_text())
variants={'area0':{'SYNTH_STRATEGY':'AREA 0'},'area1':{'SYNTH_STRATEGY':'AREA 1'},'area2':{'SYNTH_STRATEGY':'AREA 2'},'area3':{'SYNTH_STRATEGY':'AREA 3'},'nf':{'SYNTH_STRATEGY':'AREA 0','SYNTH_ABC_AREA_USE_NF':True},'mfs3':{'SYNTH_STRATEGY':'AREA 0','SYNTH_ABC_USE_MFS3':True},'delay0':{'SYNTH_STRATEGY':'DELAY 0'},'clock8':{'SYNTH_STRATEGY':'AREA 2','SYNTH_CLOCKGATE_MIN_WIDTH':8,'SYNTH_CLOCKGATE_POSEDGE_ICG':'sky130_fd_sc_hd__dlclkp_1/GATE/CLK/GCLK'},'clock32':{'SYNTH_STRATEGY':'AREA 2','SYNTH_CLOCKGATE_MIN_WIDTH':32,'SYNTH_CLOCKGATE_POSEDGE_ICG':'sky130_fd_sc_hd__dlclkp_1/GATE/CLK/GCLK'}}
if __import__('os').environ.get('NO_GATING') == '1':
    variants.pop('clock8'); variants.pop('clock32')
summary={}
for name, overrides in variants.items():
    cfg=base|overrides
    (root/'src/config_merged.json').write_text(json.dumps(cfg))
    run=root/'runs'/name;run.mkdir(parents=True)
    with (run/'console.log').open('w') as log:
        status=subprocess.run(['python','-m','librelane','--pdk-root','/pdk','--pdk','sky130A','--run-tag',name,'--force-run-dir',str(run),'--hide-progress-bar','--to','Yosys.Synthesis','src/config_merged.json'],cwd=root,stdout=log,stderr=subprocess.STDOUT)
    if status.returncode:
        summary[name]={'status':'failed','overrides':overrides}
        print(name,'failed (report preserved)',flush=True)
        continue
    metrics=json.loads(next(run.glob('*yosys-synthesis/state_out.json')).read_text())['metrics']
    summary[name]={'area':metrics['design__instance__area'],'cells':metrics['design__instance__count'],'overrides':overrides}
    print(name,summary[name],flush=True)
(root/'runs/summary.json').write_text(json.dumps(summary,indent=2)+'\n')
PY
docker exec -e PDK_ROOT=/pdk -e CI=1 -e NO_GATING="${NO_GATING:-0}" -w /work "$container_id" python sweep.py
mkdir -p "${SYNTH_SWEEP_DIR:-build/ppa-synthesis}"
docker exec "$container_id" tar -C /work/runs -cf - . | tar -C "${SYNTH_SWEEP_DIR:-build/ppa-synthesis}" -xf -
