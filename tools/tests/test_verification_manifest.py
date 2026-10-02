"""A release must reject stale inputs, changed results, and failed receipts."""
import json
from pathlib import Path
import sys
import pytest
import os
import py_compile
import subprocess
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from verification_manifest import snapshot, check_receipt, require_unchanged


@pytest.mark.parametrize('mutation',['source','result','failed','missing'])
def test_reject_invalid_evidence(tmp_path,mutation):
    source=tmp_path/'source.v'; source.write_text('original RTL')
    output=tmp_path/'results.xml'; output.write_text('passing tests')
    receipt=tmp_path/'receipt.json'
    report=dict(result='pass',input_sha256=snapshot([source]),output_sha256=snapshot([output]))
    receipt.write_text(json.dumps(report))
    check_receipt(receipt,[source],[output])
    if mutation=='source':source.write_text('different RTL')
    elif mutation=='result':output.write_text('different results')
    elif mutation=='failed':
        report['result']='fail';receipt.write_text(json.dumps(report))
    else:output.unlink()
    with pytest.raises((ValueError,FileNotFoundError)):
        check_receipt(receipt,[source],[output])


def test_reject_edit_during_run(tmp_path):
    source=tmp_path/'source.v';source.write_text('before')
    captured=snapshot([source]);source.write_text('after')
    with pytest.raises(ValueError):require_unchanged([source],captured)


def test_fresh_prefix_rejects_stale_timestamp_bytecode(tmp_path):
    module=tmp_path/'sample.py';module.write_text('VALUE = "old"\n')
    stamp=module.stat()
    py_compile.compile(str(module),doraise=True)
    module.write_text('VALUE = "new"\n')
    os.utime(module,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
    # Same length and mtime can fool timestamp-based .pyc validation.
    env=dict(os.environ)
    env.pop('PYTHONPYCACHEPREFIX',None)
    command=[sys.executable,'-c','import sample; print(sample.VALUE)']
    assert subprocess.check_output(command,cwd=tmp_path,env=env,text=True).strip() == 'old'
    env.update(PYTHONPYCACHEPREFIX=str(tmp_path/'fresh-cache'),PYTHONDONTWRITEBYTECODE='1')
    assert subprocess.check_output(command,cwd=tmp_path,env=env,text=True).strip() == 'new'
