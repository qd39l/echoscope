"""Execute EQY's generated SAT jobs when the pinned image lacks GNU make.

No solver commands or verdicts are changed. Every target emitted by EQY must
finish and contain PASS; UNKNOWN, FAIL, errors and timeouts fail this runner.
"""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys

root = Path(sys.argv[1]).resolve()
targets = (root/'summary_targets.list').read_text().splitlines()
assert targets and len(targets) == len(set(targets))


def run(target):
    status = root/target
    status.unlink(missing_ok=True)
    try:
        result = subprocess.run(['bash', 'run.sh'], cwd=status.parent, timeout=600)
        verdict = status.read_text().strip() if status.exists() else 'MISSING'
        if result.returncode:
            verdict = 'ERROR'
    except subprocess.TimeoutExpired:
        verdict = 'TIMEOUT'
    return target, verdict


with ThreadPoolExecutor(max_workers=2) as pool:
    verdicts = dict(pool.map(run, targets))
passed = all(v == 'PASS' for v in verdicts.values())
(root/'strategy-results.json').write_text(json.dumps(dict(
    result='pass' if passed else 'unproven', partitions=verdicts), indent=2)+'\n')
print(json.dumps(verdicts, indent=2))
raise SystemExit(0 if passed else 1)
