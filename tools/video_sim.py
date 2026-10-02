#!/usr/bin/env python3
"""Live RTL video and strict pin-only regression, also on powered netlists."""
import argparse
import json
import os
from pathlib import Path
import select
import subprocess
import time
import sys
import uuid

# Never execute a model/receiver bytecode cache copied from another checkout.
sys.dont_write_bytecode = True
sys.pycache_prefix = str(Path(__file__).resolve().parents[1]/'build'/('unused-pycache-'+uuid.uuid4().hex))

from model import INITIAL, step, kick, clone
from video_monitor import FRAME, Monitor, compare, expected_image
from verification_manifest import snapshot, require_unchanged

ROOT = Path(__file__).resolve().parents[1]


def build(backend='verilator', netlist=None, pdk_root=None):
    output = ROOT/'build/video'/backend
    output.mkdir(parents=True, exist_ok=True)
    sources = [ROOT/'src/project.v', ROOT/'src/echo_engine.v']
    if backend == 'verilator':
        executable = output/'Vtt_um_qd39l_echoscope'
        cmd = ['verilator', '--cc', '--exe', '--build', '-j', '2', '-Wall',
               '-Wno-DECLFILENAME', '--top-module', 'tt_um_qd39l_echoscope',
               '--Mdir', str(output), *map(str,sources), str(ROOT/'sim/video_driver.cpp')]
        launch = [str(executable)]
    else:
        executable = output/'video.vvp'
        cmd = ['iverilog', '-g2012', '-s', 'video_tb', '-o', str(executable)]
        if backend == 'gate':
            netlist = Path(netlist or ROOT/'runs/wokwi/final/pnl/tt_um_qd39l_echoscope.pnl.v').resolve()
            library = Path(pdk_root or os.environ.get('PDK_ROOT', ROOT/'.pdk'))/'sky130A/libs.ref/sky130_fd_sc_hd/verilog'
            sources = [library/'primitives.v', library/'sky130_fd_sc_hd.v', netlist]
            cmd += ['-DGL_TEST', '-DFUNCTIONAL', '-DUSE_POWER_PINS', '-DSIM', '-DUNIT_DELAY=#1']
        sources = [ROOT/'sim/video_tb.v', *sources]
        for path in sources:
            if not path.is_file():
                raise FileNotFoundError(f'Missing simulation input: {path}')
        cmd += list(map(str,sources))
        launch = ['vvp', str(executable)]
    inputs = sources + ([ROOT/'sim/video_driver.cpp'] if backend == 'verilator' else [])
    inputs += [ROOT/'tools/video_sim.py', ROOT/'tools/video_monitor.py', ROOT/'tools/model.py',
               ROOT/'tools/verification_manifest.py', ROOT/'test/requirements.txt']
    provenance = snapshot(inputs)
    with (output/'build.log').open('w') as log:
        result = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError((output/'build.log').read_text()[-8000:])
    # Always rebuild; do not trust simulator caches copied from other checkouts.
    require_unchanged(inputs, provenance)
    return launch, provenance, inputs


class Simulator:
    def __init__(self, launch):
        self.process = subprocess.Popen(launch, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=None, bufsize=0)
        self.monitor = Monitor()
        self.cycles = 0

    def close(self):
        self.process.stdin.close()
        try:
            self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            self.process.wait(timeout=3)
        self.process.stdout.close()

    def run(self, cycles, controls=66, address=16, enabled=1, reset_n=1):
        assert 0 < cycles <= 3*FRAME
        assert 0 <= controls <= 255 and 0 <= address <= 31
        command = f'{cycles} {controls} {address} {enabled} {reset_n}\n'.encode()
        self.process.stdin.write(command)
        data = bytearray()
        deadline = time.monotonic()+120
        while len(data) < cycles:
            remaining = deadline-time.monotonic()
            if remaining <= 0 or not select.select([self.process.stdout], [], [], remaining)[0]:
                raise TimeoutError('Simulator did not return its output samples within 120 seconds')
            block = os.read(self.process.stdout.fileno(), min(cycles-len(data), 65536))
            if not block:
                raise RuntimeError(f'Simulator exited during capture (status {self.process.poll()})')
            data.extend(block)
        self.cycles += cycles
        return bytes(data)

    def reset(self, controls=66):
        self.run(8, controls=controls, reset_n=0)
        self.monitor.reset()

    def next_frame(self, controls=66, address=16):
        # When locked, stop exactly at the end of a frame. All alignment is
        # recovered from pins; there are no references to DUT h/v or ready.
        for _ in range(4):
            count = FRAME-len(self.monitor.buffer) if self.monitor.locked else FRAME
            frames = self.monitor.feed(self.run(count,controls,address))
            if frames:
                assert len(frames) == 1
                return frames[0]
        raise AssertionError('No complete VGA frame after four acquisition attempts')


def regression(sim, output, backend, provenance, inputs, quick=False):
    output.mkdir(parents=True,exist_ok=True)
    sim.reset()
    frame = sim.next_frame()
    compare(frame, expected_image(INITIAL), output/'failure')
    frame.image().save(output/'reset.png')
    checked = 1
    state, epoch, last, display = INITIAL, 0, 66, 66
    saved = state
    # Each change is applied at active pixel 0. The command executes in that
    # frame's vertical blanking and must affect the NEXT visible frame only.
    scenarios = [66|4,66|4,66,67,67|4,67,66,66|8,66,66|32,
                 66|32|16|8|4,66|32,64,65,66]
    if not quick:
        import random
        rng = random.Random(260926)
        scenarios += [66 | rng.randrange(64) for _ in range(16)]
    for i, controls in enumerate(scenarios):
        address = (31-i)%32
        frame = sim.next_frame(controls,address)
        compare(frame,expected_image(state,epoch,bool(display&2),bool(display&1),bool(display&32)),output/'failure')
        checked += 1
        print(f'{backend}: checked scenario {i+1}/{len(scenarios)}',flush=True)
        if i in (4,9,11,14):
            name = f'frame-{i:02d}.png'
            frame.image().save(output/name)
        rising = controls & ~last
        if rising&16:
            state = clone(state)
        elif rising&8:
            state = kick(state,address)
        elif not controls&2 or rising&4:
            state = step(state,bool(controls&1))
            epoch = (epoch + (-1 if controls&1 else 1)) & 65535
        last, display = controls, controls
        if i == 5:
            assert state == saved, 'Reference forward/reverse round trip failed'
    compare(sim.next_frame(66),expected_image(state,epoch,bool(display&2),bool(display&1),bool(display&32)),output/'failure')
    checked += 1
    # Reset inside active video, then require a fresh sync acquisition.
    sim.run(12345, controls=66)
    sim.reset()
    compare(sim.next_frame(),expected_image(INITIAL),output/'failure')
    checked += 1
    # Disable midway through a line; outputs must be blank/inactive. Resuming
    # intentionally loses the interrupted raster. Reacquire subsequent frames.
    sim.run(173,controls=66)
    disabled=sim.run(97,controls=66,enabled=0)
    assert disabled == bytes([0x88])*97, 'Disabled VGA pins are not inactive'
    sim.monitor.reset()
    compare(sim.next_frame(),expected_image(INITIAL),output/'failure')
    checked += 1
    # Initialize with ena low, then acquire video after enabling.
    sim.run(8,controls=66,enabled=0,reset_n=0)
    assert sim.run(40,controls=66,enabled=0) == bytes([0x88])*40
    sim.monitor.reset()
    compare(sim.next_frame(),expected_image(INITIAL),output/'failure')
    checked += 1
    checked += boundary_checks(sim, output, backend)
    interruptions = interruption_checks(sim, output, backend)
    checked += interruptions
    require_unchanged(inputs, provenance)
    report = dict(backend=backend, frames_checked=checked, cycles=sim.cycles,
                  pixel_clock_hz=25_000_000, horizontal_hz=31250,
                  vertical_hz=25_000_000/FRAME, input_sha256=provenance,
                  scenarios=['pause','step','held button','reverse round trip','perturb',
                             'difference view','clone priority','automatic forward/reverse',
                             'reset in active video','disable/reacquire','initialize disabled',
                             'commands before/after frame acceptance'],
                  randomized_commands=0 if quick else 16, interruption_cases=interruptions,
                  full_regression=not quick,
                  result='pass', timing_model='unit-delay cells' if backend=='gate' else 'RTL')
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)
    return report


def boundary_checks(sim, output, backend):
    checked = 0
    # Exercise synchronized commands on both sides of the acceptance edge.
    # The frame boundary is recovered from sync; 483*800 is the documented
    # command location, not an internal counter observed by the test.
    for offset in (-4, -1, 1):
        sim.reset()
        sim.next_frame()
        before = 483*800 + offset
        sim.monitor.feed(sim.run(before,controls=66))
        frames = sim.monitor.feed(sim.run(FRAME-before,controls=70))
        assert len(frames)==1
        compare(frames[0],expected_image(INITIAL),output/'failure')
        # A late level stays high until next frame's command, so it is not lost.
        accepted = offset == -4
        compare(sim.next_frame(70),expected_image(step(INITIAL) if accepted else INITIAL,
                epoch=1 if accepted else 0),output/'failure')
        compare(sim.next_frame(66),expected_image(step(INITIAL),epoch=1),output/'failure')
        checked += 3
        print(f'{backend}: boundary offset {offset} passed',flush=True)
    return checked


def interruption_checks(sim, output, backend):
    # Boundary positions span scan acceptance, pixel-held serial shifts,
    # draw evolution, first/last restoration transactions and command entry.
    positions = [(0,63),(0,64),(0,575),(0,576), (7,640),(7,641),(7,672),
                 (480,0),(480,1),(480,33),(482,347),(482,348),(483,0),(483,32)]
    checked = 0
    sim.reset()
    sim.next_frame()
    for y,x in positions:
        # Each successful reception ends at active pixel zero. Keeping the
        # paused simulator alive also tests cumulative pause/resume recovery.
        if y*800+x:
            sim.run(y*800+x,controls=66)
        assert sim.run(19,controls=66,enabled=0) == bytes([0x88])*19
        sim.monitor.reset()
        compare(sim.next_frame(),expected_image(INITIAL),output/'failure')
        checked += 1
        print(f'{backend}: pause/resume at ({x},{y}) passed',flush=True)
    for y,x in ((0,575),(7,650),(480,17),(482,347)):
        sim.reset()
        sim.next_frame()
        sim.run(y*800+x,controls=66)
        sim.reset()
        compare(sim.next_frame(),expected_image(INITIAL),output/'failure')
        checked += 1
        print(f'{backend}: reset at ({x},{y}) passed',flush=True)
    return checked


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['test','serve'])
    parser.add_argument('--backend',choices=['verilator','icarus','gate'],default='verilator')
    parser.add_argument('--netlist')
    parser.add_argument('--pdk-root')
    parser.add_argument('--quick',action='store_true')
    parser.add_argument('--boundaries-only',action='store_true')
    parser.add_argument('--port',type=int,default=8766)
    args=parser.parse_args()
    output=ROOT/'build/video'/args.backend/('results-boundaries' if args.boundaries_only else 'results')
    if args.action=='test':
        (output/'report.json').unlink(missing_ok=True)
    launch,provenance,inputs=build(args.backend,args.netlist,args.pdk_root)
    sim=Simulator(launch)
    try:
        if args.action=='test' and args.boundaries_only:
            output=ROOT/'build/video'/args.backend/'results-boundaries'
            output.mkdir(parents=True,exist_ok=True)
            count=boundary_checks(sim,output,args.backend)
            require_unchanged(inputs,provenance)
            report=dict(backend=args.backend,frames_checked=count,result='pass',
                        scenarios=['commands before/after frame acceptance'],
                        input_sha256=provenance)
            (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        elif args.action=='test':
            regression(sim,output,args.backend,provenance,inputs,args.quick)
        else:
            from video_server import serve
            serve(sim,args.port,args.backend)
    finally:
        sim.close()

if __name__=='__main__': main()
