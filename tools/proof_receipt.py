"""Capture inputs before a proof; seal only a successful, unchanged run."""
import argparse
import json
from pathlib import Path
from verification_manifest import ROOT, snapshot, require_unchanged


def inputs(kind):
    shared = [ROOT/'tools/proof_receipt.py', ROOT/'tools/verification_manifest.py']
    if kind == 'formal':
        names = ['src/echo_step.v','src/echo_engine.v','test/formal.v',
                 'test/formal_serial.v','test/formal_init.v','scripts/formal.sh']
    elif kind == 'safety':
        names = ['src/project.v','src/echo_engine.v','test/formal_engine_safety.vh',
                 'test/formal_controller_properties.vh','tools/formal_safety.py','scripts/formal_safety.sh',
                 'scripts/formal_mutations.sh']
    else:
        names = ['src/project.v','src/echo_engine.v','test/netlist.eqy',
                 'test/formal_clockgate.v','test/formal_physical.v','test/formal_environment.v','tools/run_eqy_strategies.py','scripts/equivalence.sh',
                 'runs/wokwi/final/pnl/tt_um_qd39l_echoscope.pnl.v']
    return shared + [ROOT/name for name in names]


def directory(kind):
    return ROOT/'build'/('proof' if kind == 'formal' else kind)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['begin','seal'])
    parser.add_argument('kind', choices=['formal','safety','equivalence'])
    args = parser.parse_args()
    out = directory(args.kind)
    out.mkdir(parents=True,exist_ok=True)
    capture = out/'input-manifest.json'
    receipt = out/'receipt.json'
    paths = inputs(args.kind)
    if args.action == 'begin':
        receipt.unlink(missing_ok=True)
        capture.write_text(json.dumps(snapshot(paths),indent=2)+'\n')
        return
    before = json.loads(capture.read_text())
    require_unchanged(paths,before)
    if args.kind == 'equivalence':
        result = out/'strategy-results.json'
        data = json.loads(result.read_text())
        assert data['result'] == 'pass' and data['partitions']
        assert all(v == 'PASS' for v in data['partitions'].values())
    else:
        result = out/'formal.log'
        marker = 'SAT proof finished - no model found: SUCCESS!' if args.kind == 'formal' else 'Induction step proven: SUCCESS!'
        assert result.read_text().count(marker) == (6 if args.kind == 'formal' else 2)
    outputs = [result]
    if args.kind == 'safety':
        mutations = out/'mutations.log'
        assert mutations.read_text().count('rejected with a bounded counterexample') == 2
        outputs.append(mutations)
    receipt.write_text(json.dumps(dict(result='pass',input_sha256=before,
                                      output_sha256=snapshot(outputs)),indent=2)+'\n')


if __name__ == '__main__':
    main()
