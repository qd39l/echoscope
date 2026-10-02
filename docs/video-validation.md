# VGA validation and live RTL monitor

The live monitor executes the real `src/project.v` and `src/echo_engine.v` with
Verilator. Browser controls drive the public input pins; the browser displays
PNG frames reconstructed from `uo_out`. There is no cellular-automaton model in
the browser. The existing `demo/` remains a separate mathematical reference.

## Run

After `./scripts/setup.sh`, with Verilator and a C++ compiler installed:

```sh
make video
```

Open `http://127.0.0.1:8766`. Pause, single-step, reverse, clone, flip any cell,
and switch to the amber disagreement view. Buttons are held for two simulated
frames and released for two frames. The canvas changes after the command's
vertical-blanking interval. Save frame downloads the displayed PNG.

The server binds only to loopback. One browser session controls one simulator.
Closing the tab stops clock requests; Ctrl-C stops the server and simulator.
Playback speed is separate from the modeled 25 MHz clock. Audio is muted in
this viewer; the existing cocotb regression checks audio separately.

## Automated checks

```sh
make video-test
make video-gl-test PDK_ROOT=/path/to/pdk
```

`video-test` runs receiver fault injection and a full-frame RTL regression.
The GitHub test workflow runs it and uploads the frame/report artifacts.
`video-gl-test` runs the full scenario set against the accepted powered netlist under `runs/wokwi/final/pnl/`
and the SKY130 functional unit-delay models. For another netlist:

```sh
.venv/bin/python tools/video_sim.py test --backend gate \
  --netlist path/to/design.pnl.v --pdk-root /path/to/pdk
```

An Icarus RTL backend is also available with `--backend icarus`.
Each invocation rebuilds the bridge rather than trusting a copied simulator
cache. Reports record hashes of the actual simulated sources, netlist and cell
models. Outputs go under `build/video/<backend>/results/`, with a JSON report,
selected PNG frames, and actual/expected/difference images on an image failure.

The independent receiver acquires frame alignment from the external VSYNC
edge and the specified 33-line back porch. It never reads the DUT's coordinates,
ready signal, internal state, or command flags. Once acquired it checks:

- Every HSYNC and VSYNC sample over all 800 × 525 clocks, including porches.
- Zero RGB throughout horizontal and vertical blanking.
- Every visible pixel against a rectangle-based renderer driven by the existing
  scalar truth-table model, including grid, rails, epoch ruler and meter.
- Pause, held buttons, forward/reverse round trip, clone priority, arbitrary
  perturbation addresses, difference view, and automatic evolution.
- Reset during active video, disable/re-enable with sync reacquisition, and
  serial initialization while disabled.
- Commands immediately before/after the synchronized frame-acceptance point.
- Reproducible randomized control combinations in the full RTL run.
- The same randomized scenarios in the full gate run, plus pause/resume at
  14 scan/evolve/restore/command boundaries and reset at four such boundaries.

The full regression checks 63 complete frames on each backend. Reports hash
the test driver, receiver and independent renderer as well as the simulator
inputs, and refuse a successful report if those files change during the run.

Fault-injection tests demonstrate detection of short/extra sync pulses, wrong
polarity, blanking leakage, missing/extra clocks, swapped colors, a one-pixel RGB
delay, and missing sync. Recovery is explicit on reset/disable: the receiver
must not silently relock during a continuous stream and hide malformed frames.

## What this proves and what remains

This is a digital, source-clock-sampled receiver. Real VGA does not transmit a
pixel clock: a monitor must recover sampling from sync. Neither this sink nor a
correct picture proves analog voltage, cable loading, oscillator jitter, or
compatibility with every monitor. Gate simulation uses unit delays, not SDF;
the recorded extracted nine-corner STA remains the ASIC timing evidence.

The accepted target remains **25 MHz**: 32 microseconds per line, 3.84
microseconds of low HSYNC, 16.8 milliseconds per frame, and 64 microseconds of
low VSYNC. Nominal 640×480 VGA uses 25.175 MHz; 25 MHz is about 0.695% lower and
should be explicitly qualified on the intended monitor. A change to 25.175 or
25.2 MHz requires new clock constraints/STA and actual board-clock verification;
this software work does not change the fabrication inputs or claim that change
has been qualified.

## FPGA and board acceptance

Use the same two RTL source files on an FPGA. Supply a properly constrained
25 MHz clock and synchronous reset; connect `uo_out` to the Tiny VGA Pmod in the
pin order in `info.yaml`. Set `ena=1`, hold `ui_in[7]=0` around reset, and hold
reset low for at least six clocks. Allow 32 initialization clocks after release.
Drive controls and the five-bit cell address at defined levels; debounce physical
buttons and obey the documented two-frame hold/release protocol. Do not derive
a fabric clock with a casual logic divider: use the board's supported clocking
resources and constrain both the input and generated clock.

The exact top-level wrapper, FPGA pin constraints, and programming command
must be selected for the actual board and adapter. Do not program a guessed pin
map. No FPGA or physical display result is claimed by the simulation reports.

Before hardware acceptance, record:

1. Board model/revision, adapter, cable and monitor model; RTL commit/hash and
   bitstream hash; clock source and achieved frequency.
2. FPGA implementation timing success, then measured pixel-clock frequency,
   HSYNC period/low width and VSYNC period/low width on an oscilloscope or logic
   analyzer. Verify stable sync across several minutes and control changes.
3. Correct colors and image alignment on a real monitor; no blanking leakage,
   rolling image, occasional unlock, or cropped active area.
4. A paused baseline photo/capture, one forward step, one reverse step returning
   to baseline, clone removing disagreement, a flip reintroducing it, and reset.
5. Power-up/reset repetition and disable/re-enable recovery. Check the analog
   RGB amplitude/termination through the actual VGA adapter, not FPGA GPIO alone.

An FPGA validates the interface and behavior; it does not replace the ASIC
physical/clock-gating checks. Keep these hardware results alongside the digital
regression and extracted timing reports before declaring the VGA path qualified.
