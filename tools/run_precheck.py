#!/usr/bin/env python3
"""Run the unmodified TT checker, with Linux EDA executables in Docker.

Python geometry libraries run in the host venv. Only executable paths and
file paths cross the bridge; no checks or check results are substituted.
Containers have no network and no host bind mount. PDK files are read-only.
"""
from __future__ import annotations

import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "build/precheck"


def evidence_inputs():
    top = 'tt_um_qd39l_echoscope'
    return [ROOT/'info.yaml', ROOT/'tools/run_precheck.py', ROOT/'scripts/precheck.sh',
            ROOT/'tools/verification_manifest.py',
            *[ROOT/f'runs/wokwi/final/{kind}/{top}.{suffix}'
              for kind,suffix in [('gds','gds'),('lef','lef'),('pnl','pnl.v')]],
            *[p for folder in ('tt/precheck','tt/tech') for p in (ROOT/folder).rglob('*')
              if p.is_file() and '__pycache__' not in p.parts and 'reports' not in p.parts]]


def extract(data: bytes, destination: Path) -> None:
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        archive.extractall(destination, filter="data")


def bridge(tool: str, args: list[str]) -> int:
    config = json.loads(os.environ["ECHOSCOPE_PRECHECK_BRIDGE"])
    # Translate arguments, including paths embedded in a Yosys -p command.
    def translate(value: str) -> str:
        return value.replace(config["pdk_root"], "/pdk").replace(str(ROOT), "/work")

    binary = "yosys" if tool == "yowasp-yosys" else tool
    result = subprocess.run([
        "docker", "exec", "-e", "PDK_ROOT=/pdk", "-e", "PDK=sky130A",
        "-w", "/work/build/precheck/tt/precheck", config["container"],
        binary, *map(translate, args),
    ])
    # The native Python checker inspects the actual EDA-generated reports.
    reports = subprocess.check_output([
        "docker", "exec", config["container"], "tar", "-C",
        "/work/build/precheck/tt/precheck/reports", "-cf", "-", ".",
    ])
    extract(reports, WORK / "tt/precheck/reports")
    return result.returncode


def source_archive():
    archive = tempfile.TemporaryFile()
    with tarfile.open(fileobj=archive, mode="w") as tar:
        for path in ("tt", "check", "info.yaml"):
            tar.add(WORK / path, arcname=f"build/precheck/{path}")
    archive.seek(0)
    return archive


def main() -> int:
    from verification_manifest import snapshot, require_unchanged
    pdk_root = Path(os.environ.get("PDK_ROOT", ROOT / ".pdk")).absolute()
    if not (pdk_root / "sky130A/libs.tech/klayout/tech").is_dir():
        raise SystemExit("Set PDK_ROOT to a local SKY130 PDK cache (see docs/toolchain.md).")
    WORK.mkdir(parents=True, exist_ok=True)
    receipt = WORK/'receipt.json'
    receipt.unlink(missing_ok=True)
    paths = evidence_inputs()
    before = snapshot(paths)
    # Work on a disposable copy; leave the pinned support-tools checkout intact.
    for part in ("precheck", "tech"):
        destination = WORK / "tt" / part
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(ROOT / "tt" / part, destination,
                        ignore=shutil.ignore_patterns("__pycache__", "reports"))
    (WORK / "tt/precheck/reports").mkdir()
    check = WORK / "check"
    check.mkdir(exist_ok=True)
    top = "tt_um_qd39l_echoscope"
    for kind, suffix, target_suffix in (("gds", "gds", "gds"),
                                        ("lef", "lef", "lef"),
                                        ("pnl", "pnl.v", "v")):
        shutil.copyfile(ROOT / f"runs/wokwi/final/{kind}/{top}.{suffix}",
                        check / f"{top}.{target_suffix}")
    shutil.copyfile(ROOT / "info.yaml", WORK / "info.yaml")
    image = "ghcr.io/librelane/librelane:3.0.14"
    container = subprocess.check_output([
        "docker", "create", "--network", "none", "-v",
        "ttsky26d-pdk-3.0.14:/pdk:ro", image, "sleep", "infinity",
    ], text=True).strip()
    try:
        subprocess.run(["docker", "start", container], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["docker", "exec", container, "mkdir", "-p", "/work"], check=True)
        with source_archive() as archive:
            subprocess.run(["docker", "exec", "-i", container, "tar", "-C", "/work", "-xf", "-"],
                           stdin=archive, check=True)
        bin_dir = WORK / "bin"
        bin_dir.mkdir(exist_ok=True)
        for tool in ("magic", "klayout", "yowasp-yosys"):
            wrapper = bin_dir / tool
            # repr is Python escaping; no shell interpolation or path quoting.
            wrapper.write_text(f"#!{sys.executable}\nimport runpy, sys\n"
                               f"sys.argv = [{str(__file__)!r}, '--bridge', {tool!r}] + sys.argv[1:]\n"
                               f"runpy.run_path({str(__file__)!r}, run_name='__main__')\n")
            wrapper.chmod(0o755)
        env = os.environ.copy()
        env.update(PDK_ROOT=str(pdk_root), PDK="sky130A",
                   PATH=str(bin_dir) + os.pathsep + env["PATH"],
                   ECHOSCOPE_PRECHECK_BRIDGE=json.dumps({"container": container,
                                                        "pdk_root": str(pdk_root)}))
        result = subprocess.run([sys.executable, "precheck.py", "--gds", str(check / f"{top}.gds")],
                                cwd=WORK / "tt/precheck", env=env).returncode
        require_unchanged(paths,before)
        if result == 0:
            receipt.write_text(json.dumps(dict(result='pass',input_sha256=before,
                output_sha256=snapshot([WORK/'tt/precheck/reports/results.xml'])),indent=2)+'\n')
        return result
    finally:
        subprocess.run(["docker", "rm", "-f", container], stdout=subprocess.DEVNULL, check=False)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--bridge":
        sys.exit(bridge(sys.argv[2], sys.argv[3:]))
    sys.exit(main())
