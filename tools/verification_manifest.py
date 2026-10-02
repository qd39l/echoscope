"""Bind verification results to all inputs and reject stale evidence."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def snapshot(paths):
    result = {}
    for path in sorted(set(Path(p).resolve() for p in paths)):
        label = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else 'external/' + path.name
        if label in result:
            raise ValueError(f'Duplicate evidence label: {label}')
        result[label] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def require_unchanged(paths, before):
    if snapshot(paths) != before:
        raise ValueError('Verification inputs changed during the run')


def check_receipt(path, paths, outputs):
    receipt = json.loads(Path(path).read_text())
    if receipt['result'] != 'pass' or receipt['input_sha256'] != snapshot(paths):
        raise ValueError(f'Stale or unsuccessful verification receipt: {path}')
    if receipt['output_sha256'] != snapshot(outputs):
        raise ValueError(f'Verification outputs changed: {path}')
    return receipt
