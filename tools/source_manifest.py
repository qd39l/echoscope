#!/usr/bin/env python3
"""Hash the physical build inputs before hardening, using relative paths."""
import hashlib
import json
from pathlib import Path
import sys


def manifest(root: Path) -> dict[str, str]:
    files = [root / 'info.yaml', *sorted((root / 'src').glob('*.v')),
             root / 'src/config.json', root / 'src/area_no_synth.cells',
             root / 'src/config_merged.json', root / 'src/user_config.json']
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in files if p.is_file() and not p.name.startswith('._')}


def matches_build(root: Path, built: dict[str, str]) -> bool:
    """Keep original build hashes; allow the documented attribution-only edit.

    This exact hash pair was checked by comparing parsed YAML with only
    project.author removed. Any further metadata or physical input edit
    requires a fresh build. Do not replace the original evidence hashes.
    """
    current = manifest(root)
    if current == built:
        return True
    record_path = root / 'docs/verification/metadata-update.json'
    if not record_path.is_file():
        return False
    record = json.loads(record_path.read_text())
    if (record['changed_fields'] != ['project.author']
            or built.get('info.yaml') != record['build_info_sha256']
            or current.get('info.yaml') != record['public_info_sha256']):
        return False
    current['info.yaml'] = built['info.yaml']
    return current == built


if __name__ == '__main__':
    print(json.dumps(manifest(Path(sys.argv[1] if len(sys.argv) > 1 else '.')),
                     indent=2, sort_keys=True))
