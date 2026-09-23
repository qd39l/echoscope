# Verification record

**Target:** TTSKY26d, SKY130A, 1×1, 25 MHz.

The final local implementation passes its physical and functional acceptance
checks. Clock gating is
restricted to the 128-bit world-state bank, which uses plain flops and serial
initialization. The controller holds outputs in a known state until the 32-clock
startup completes. Pixel reads rotate the state once per cell, restoring it
by the end of each line.
An earlier experiment that gated synchronously reset registers was rejected
by gate-level tests; an ungated alternative encountered severe routing congestion. See [PPA reasoning](ppa.md) for the alternatives and trade-offs.

The accepted serial-initialization/serial-VGA build uses placement density 68
and targeted exclusions of weak logic, delay and buffer cells. It occupies
**12,933.7 µm²** of standard cells, **78.42%** of the one-tile core. Routing,
Magic DRC, LVS, antenna, setup, hold, maximum slew and maximum capacitance
violation counts are all **zero**. Across all nine PVT/interconnect corners,
worst setup slack is **21.053 ns** and worst hold slack is **0.0371 ns**.
The earlier post-CTS repair warning refers to its requested extra hold margin;
final extracted timing meets the actual hold constraints at every corner.
The final powered netlist passes all five applicable gate-level tests (one
RTL-only test is intentionally skipped), and its GDS passes all 15 official
Tiny Tapeout prechecks. Earlier rejected experiments remain in the PPA comparison.

![Accepted one-tile routed layout](images/layout.png)

## Functional evidence

- Verilator lint passes with `-Wall`.
- Six RTL cocotb tests pass, covering public diagnostic pins, reset and enable,
  every perturbation cell, command priority, randomized commands, a 1,024-step
  forward/reverse round trip, busy pauses, and changes to controls during work.
- The raster test checks every output pixel over a full frame, including RGB,
  blanking, sync, and recovery of all 128 canonical state bits after drawing.
- A multi-frame test checks pause, forward/reverse, clone, perturbation,
  disagreement measurement, scan restoration, audio activity and mute.
- Six Yosys SAT proofs pass: the abstract inverse in either direction for all
  64-bit world states; and the serial engine's evolution, perturbation, clone,
  and identity scan for all 128-bit paired states. The serial proofs also
  check the final disagreement count, equality indication and idle state.
  Arbitrary input direction and address are latched at acceptance; neither is
  assumed constant while the operation runs. Completion proofs assume enable
  remains high and reset inactive. A separate startup proof establishes the
  exact seed after reset and 32 initialization edges, from arbitrary stored
  bits and with arbitrary enable. Reset, restart and pause/resume are also
  checked in simulation.
- The JavaScript browser model agrees with an independent scalar Python
  truth-table model on 256 randomized states × four operations.
- The accepted build's final powered netlist passes all five applicable
  tests, including the 1,024-step round trip, initialization interrupted by
  reset, initialization while disabled, and package-pin VGA reconstruction.
  A different physical build requires fresh netlist tests and layout prechecks.

The browser is a reference model, not an HDL simulator. The image in the README
is captured from the real RTL outputs. Board bring-up code is supplied, but no
fabricated device or FPGA board has been tested.

## Physical acceptance criteria

A successful build must meet all of these; producing a GDS file is insufficient:

- Exact 161 × 111.52 µm one-tile footprint and all template pin positions.
- All 40 used signal pins connected to routed cells; all 43 signal and two
  supply pin shapes present. Three unused `uio_in[7:5]` inputs are intentional.
- Zero detailed-routing, Magic DRC, LVS, antenna, and critical disconnected-pin errors.
- Nonnegative extracted setup and hold slack in all nine PVT/interconnect
  corners; zero maximum slew and maximum capacitance violations.
- Official Tiny Tapeout precheck passes all 15 applicable checks: Magic DRC;
  KLayout FEOL, BEOL, off-grid, pin-label overlap, zero area and macro/layer
  checks; template pins, boundary, supply pins, legal layers, cell names,
  urpm/nwell separation, analog-pin consistency, and Verilog syntax.
- Final powered netlist passes public-pin gate-level diagnostic tests and a
  package-pin VGA test covering a full frame and the next frame's state.

The stock 40 ns clock constraint includes 8 ns input/output delay budgets,
0.25 ns clock uncertainty, and the flow's 5% timing derate. Gate-level tests use
functional standard-cell models with unit delays, not SDF back-annotation;
extracted multi-corner STA supplies timing verification. The macro's physical
power connections are checked, but top-level shuttle integration remains the
Tiny Tapeout team's responsibility.

## Reproduction and boundaries

See [toolchain.md](toolchain.md) and the root Makefile. Full local build reports
are in `runs/wokwi/`, test results in `test/results.xml`, and official precheck
reports in `build/precheck/tt/precheck/reports/`. Compact final evidence is
stored in `docs/verification/`, including input hashes, artifact hashes,
test results, synthesis statistics and the nine-corner timing summary.
The exact attribution-only metadata change made for publication is recorded
separately in `verification/metadata-update.json`; see
[publication notes](publication.md). Original physical-build hashes are preserved.
The local package is `build/echoscope-ttsky26d-1x1.zip`. Packaging checks
that GDS, LEF, powered netlist and all three SPEFs match the accepted build.
GDS/OAS conversion preserves mask geometry on all 34 layers and all 19,819
unique label values and locations; the hashes are in `verification/package.json`.

The design has not been submitted to the shuttle, purchased,
or assigned a fabricated project index. Official hosted CI and shuttle
submission remain separate from the local validation recorded here. No
universal originality or measured silicon power claim is made.
