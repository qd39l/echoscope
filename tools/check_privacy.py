#!/usr/bin/env python3
"""Check publishable files and optionally reachable Git history for common leaks.

Heuristic review aid, not a guarantee: inspect new prose and images before release.
Findings identify the location and rule without echoing the sensitive value.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
RULES = {
    'host home directory': rb'/(?:Users|home)/[^/\s"\x27]+/',
    'macOS temporary directory': rb'/(?:private/)?var/folders/',
    'Windows home directory': rb'[A-Za-z]:[\\/]+Users[\\/]+',
    'private network address': rb'\b(?:192\.168|10\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b',
    'private key': rb'-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----',
    'GitHub token': rb'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b',
    'AWS access key': rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b',
    'API token': rb'\bsk-(?:proj-|ant-)?[A-Za-z0-9_-]{32,}\b',
    'credential in URL': rb'https?://[^\s/<>"\x27]+:[^\s/<>"\x27]+@',
}
EMAIL = re.compile(rb'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}')
PRIVATE_NAMES = re.compile(
    r'(^|/)(?:AGENTS(?:\.local)?\.md|\.env(?:\..*)?|id_rsa.*|id_ed25519.*|'
    r'\.aws|\.ssh|\.codex|\.agents|private)(?:/|$)|'
    r'\.(?:pem|key|p12|pfx|bundle)$|\.local(?:\.|$)'
)


def git(*args: str) -> bytes:
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def check_bytes(label: str, data: bytes) -> list[str]:
    findings = []
    for rule, pattern in RULES.items():
        for match in re.finditer(pattern, data):
            line = data.count(b'\n', 0, match.start()) + 1
            findings.append(f'{label}:{line}: {rule}')
    for match in EMAIL.finditer(data):
        if not match[0].endswith(b'@users.noreply.github.com'):
            line = data.count(b'\n', 0, match.start()) + 1
            findings.append(f'{label}:{line}: non-public email address')
    return findings


def check_name(name: str) -> list[str]:
    if Path(name).name in ('.env.example', '.env.template'):
        return []
    return [f'{name}: private/local filename'] if PRIVATE_NAMES.search(name) else []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--history', action='store_true', help='also scan branch, tag, and remote history and commit identities')
    args = parser.parse_args()
    findings = []
    names = set(git('ls-files', '--cached', '--others', '--exclude-standard', '-z').split(b'\0')) - {b''}
    for raw in sorted(names):
        name = raw.decode()
        findings.extend(check_name(name))
        path = ROOT / name
        if path.is_symlink():
            findings.extend(check_bytes(name, str(path.readlink()).encode()))
        elif path.is_file():
            findings.extend(check_bytes(name, path.read_bytes()))
    if args.history:
        # Check metadata as well as blobs: deleting a file does not erase history.
        public_author = re.search(r'^\s+author: "([^"]+)"', (ROOT / 'info.yaml').read_text(), re.M)[1]
        # App-owned snapshot refs and reflogs are local recovery state, not
        # publication branches. Never publish this repository with --mirror.
        refs = ('--branches', '--tags', '--remotes')
        for commit in git('rev-list', *refs).decode().splitlines():
            metadata = git('show', '-s', '--format=%an%n%cn%n%ae%n%ce%n%B', commit)
            findings.extend(check_bytes(f'commit {commit[:12]}', metadata))
            if any(name != public_author for name in metadata.decode().splitlines()[:2]):
                findings.append(f'commit {commit[:12]}: identity differs from public project author')
        objects = git('rev-list', '--objects', *refs).splitlines()
        for item in objects:
            oid, _, raw_name = item.partition(b' ')
            if git('cat-file', '-t', oid.decode()).strip() != b'blob':
                continue
            label = f'history {oid[:12].decode()} {raw_name.decode()}'
            findings.extend(check_name(raw_name.decode()))
            data = git('cat-file', 'blob', oid.decode())
            findings.extend(check_bytes(label, data))
            if raw_name == b'info.yaml':
                author = re.search(rb'^\s+author: "([^"]+)"', data, re.M)
                if author and author[1].decode() != public_author:
                    findings.append(f'{label}: attribution differs from public project author')
    for finding in findings:
        print(finding)
    if findings:
        print(f'FAIL: {len(findings)} finding(s); review locally before publishing.')
        return 1
    print(f'PASS: {len(names)} publishable files' + (' and branch/tag/remote history' if args.history else '') + ' checked for common privacy leaks')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
