# Why EchoScope targets one tile

The initial parallel implementation needed two tiles. The serial implementation
keeps the same 32-cell worlds, 60-row VGA image, exact reverse operation,
perturbation, cloning, and audio in a one-tile floorplan. Its main trade-off is
operation latency, which fits comfortably into video blanking.

**Result: 1×1 is sufficient.** The accepted local build occupies
**12,933.7 µm²** of standard cells (78.42% of its 16,493.3 µm² core), with zero
setup, hold, slew or capacitance violations across nine corners and zero
routing, DRC, LVS or antenna errors. It passes all 15 official prechecks and
all five applicable final-netlist tests. No feature reduction or timing-rule
relaxation was needed; there is no measured reason to buy a second tile.

The accepted layout's largest area categories are registers (5,436.5 µm²,
42.0%), combinational logic plus ordinary buffers/inverters (4,773.3 µm²,
36.9%), timing-repair buffers (1,811.7 µm², 14.0%), and clock buffers
(598.1 µm², 4.6%). The remaining 2.4% is tap cells, antenna protection and
the single clock gate. Filler is excluded.

## Architectural trade-off

| Property | Initial parallel architecture | Serial architecture |
| --- | --- | --- |
| World state | 128 bits | 128 bits |
| Processing clocks per generation | 1 | 32, plus one acceptance clock |
| Pixel clock | 25 MHz | 25 MHz |
| Active picture | 640×480, 32 cells × 60 generations | Same |
| Animation rate | 59.524 generations/s | Same |
| Row update budget | 160 clocks of horizontal blanking | Uses 33 clocks |
| Rewind after drawing | 59 parallel updates | 59 × 33 = 1,947 clocks |
| Rewind budget before commands | Three blank lines | 2,400 clocks |
| Diagnostic access | Wide byte-selection mux | Four serial lanes, 32 shifts |

A cell engine performs the nonlinear update one bit at a time, rotating the
four state planes. After 32 clocks their bit ordering returns to normal. The
same pass counts disagreement and compares both worlds, avoiding separate
parallel population-count and equality trees. Diagnostic scan reuses these
rotations and restores the state after reading it.

The design has no SRAM, framebuffer, CPU, or saved history. Reducing the number
of cells, rows, audio precision, or visible frame rate was not necessary.

## Measured experiments

These numbers come from actual SKY130 synthesis and place-and-route runs with
LibreLane 3.0.14, not a gate-count estimate. Areas exclude filler unless stated.
Intermediate candidates below are experimental and are not submission builds.

| Candidate | Synthesis cell area (µm²) | Outcome |
| --- | ---: | --- |
| Parallel, stock mapping | 22,057.4 | 1×1 placement impossible; 1×2 routes |
| Serial update, separate metrics | 16,158.0 | 1×1 placement exceeds capacity |
| Serial update, shared metrics | 14,589.0 | Still exceeds usable placement area |
| Best area strategy on that RTL | 14,523.9 | Strategy alone saves under 0.5% |
| Serial diagnostic scan, automatic gating at width 8 | 11,954.0 | Clock/hold repair prevents legal placement |
| Serial scan, gating at width 32 | 12,388.1 | Clock/hold repair prevents legal placement |
| Serial scan, smaller drive cells, automatic gating | 10,257.3 | Routes in 1×1; rejected by gate-level reset tests and slow-corner slew checks |
| Serial scan, smaller drive cells, no automatic gating | 11,200.7 | Reset tests pass; severe routing congestion, run stopped |
| Serial scan, asynchronous state reset, gating only world bank | 10,267.3¹ | Routes; best repair trial retains 10 slow-edge violations |
| Serial initialization, separate startup flag | 9,745.6¹ | Saves logic area but adds a clock-tree level; rejected |
| Serial initialization, compact binary opcode | 9,660.5¹ | Removes extra clock-tree level |
| Serial initialization and serial VGA reads | 9,330.2¹ | 1×1 routes at density 66; six RTL tests, five final-netlist tests and 15 prechecks pass; 15 slew violations remain |
| Final serial design with targeted stronger cells | 9,666.8¹ | Accepted 1×1: 12,933.7 µm² routed cells; all physical, timing and functional checks pass |

AREA 0/1/2/3, delay-oriented mapping, and ABC alternatives were compared.
One ABC MFS3 attempt failed internally and is not counted as a valid result.
The large improvement comes from changing the architecture and readback path,
not selecting a different ABC recipe.

The final design gates only the 128-bit world-state bank. A 64-bit
minimum bank size excludes the synchronous controller from gating. The bank
uses plain flops and a 32-clock serial seed-loading sequence, which runs even
when ena is low. Outputs are masked until every bit has been overwritten.
Initialization reuses the bit counter and an unused opcode/direction combination.
Explicit binary opcode encoding prevents synthesis from adding one-hot flops.
We checked the generated cells and tested reset during an unfinished, disabled operation.
The flow enables post-global-route design repair and explicitly repairs both
slow and fast timing corners. Final
routed metrics and the acceptance checks are recorded in [verification.md](verification.md).

### Is clock gating necessary?

No: the state registers can instead use feedback logic to hold their values.
A controlled synthesis with the **accepted final RTL and cell policy**, changing
only the two gating settings, measured **11,175.7 µm² without gating** versus
**9,684.3 µm² with gating**, including the gate. Disabling gating therefore
increases synthesis area by **15.4%**. Both versions contain 271 flops; the
added area is in their enable/hold logic and its mapping. Gating is retained.
This is a synthesis comparison, not a claim that an ungated final layout
cannot fit. Earlier controlled comparisons measured 13.5% for asynchronous
reset and 15.9% for serial startup before the final cell-policy refinements;
the exact configurations and measurements remain in the comparison evidence.

The first correctly reset, geometrically clean one-tile result uses placement
density 72%, routing adjustment 0.15, and a 10% slew repair margin. Its routed
standard-cell area is 13,910.8 µm², divided approximately as follows:

| Cell category | Area (µm²) | Share |
| --- | ---: | ---: |
| 272 registers, including 128 world-state bits | 6,089.6 | 43.8% |
| Combinational logic, ordinary buffers and inverters | 4,341.7 | 31.2% |
| Timing-repair buffers | 2,474.9 | 17.8% |
| Clock buffers | 703.2 | 5.1% |
| Tap cells, clock gate and antenna diode | 301.5 | 2.2% |

Filler is excluded. The gate itself occupies only 17.5 µm²; its indirect
clock-distribution and hold-repair cost matters more. This result has zero
route DRC, Magic DRC, LVS and antenna errors and positive setup/hold slack,
but **47 maximum-slew violations** in the worst slow corner. It is not an
accepted fabrication build. A two-tile reference also routes cleanly but
retains 34 slew violations, so increasing tile size alone does not resolve
the remaining electrical issue.
The [compact comparison evidence](ppa_evidence.json) records these measurements,
their exact configuration, and source hashes, including the controlled
clock-gating comparison.

The newer serial-initialization/serial-VGA density-66 result reduces routed
standard-cell area to **13,088.8 µm²**. Registers occupy 5,441.5 µm² (41.6%),
timing-repair buffers 2,190.9 µm² (16.7%), and clock buffers 598.1 µm² (4.6%).
The 128 plain world-state flops account for about 2,562.5 µm² before any
physical resizing. The rest of the registers serve the video, command,
serial engine and audio controls. Thus the world bank is the largest single
storage block, but removing it would not remove most of the final area.
This result passes geometry, precheck and final-netlist functional tests;
15 slow-edge violations remained. A targeted stronger-cell experiment then
tested the weak driver families identified by extracted timing reports.
That stronger-logic/delay-cell trial routes at 13,654.3 µm² and reduces the
remaining slew violations to five, all on one `buf_1`-driven net (0.832 ns
against the unchanged 0.750 ns limit). Excluding `buf_1` in the final trial resolves all remaining violations.

¹ Yosys treats the integrated clock gate as a black box in its area report.
Including the one gate's Liberty area (17.5168 µm²) gives **10,284.9 µm²**,
53.4% below the initial parallel design. The initial serial-VGA candidate is
**9,347.7 µm²** including its gate, **57.6% below** the parallel design before final drive-strength refinements.
The accepted configuration is **9,684.3 µm²** including its gate, **56.1%
below** the parallel design.
Final routed area includes clock
trees, hold buffers, diode repair and tap cells. The earlier gated estimates
also omit their clock-gate areas and were not accepted builds.

A second ungated strategy sweep with the small-cell policy measured 11,174–
11,203 µm² for AREA 0/1/2, NF and MFS3; it confirmed that recipe changes alone
were insufficient. Unlike the earlier-library MFS3 run, this run succeeded.

## Physical cell choice

The stock synthesis exclusion list is conservative about drive-1 cells, even
though the resizer can use many of them. Our [cell policy](area_cell_policy.md)
allows 83 additional drive-1 variants only when a permitted drive-2 equivalent
exists and the cell is absent from the PDK DRC exclusion list. It retains all
other exclusions. No geometric rule or timing constraint is relaxed.

The policy is reproducible with:

```sh
.venv/bin/python tools/build_area_cell_policy.py --pdk-root /path/to/pdk
```

The final configuration also excludes `a21oi_1`, `nor2_1`, `dlygate*_1`,
`buf_1` and `clkdlybuf*`. Stronger characterized alternatives remain available. Physical routing, Magic DRC,
KLayout precheck, LVS, extracted timing, and gate-level simulation determine
whether this mapping is acceptable.

## Interpreting power

OpenSTA's vectorless power figures are estimates under its default switching
assumptions. They do not model this design's actual raster-dependent activity,
package I/O power, the VGA resistor network, or the audio amplifier. We do not
claim a measured energy reduction from the area reduction. A smaller serial
engine does more cycles of work, and clock gating changes the state registers' activity. Dynamic power should be measured on a board or evaluated with an
activity-annotated flow before making a power-efficiency claim.

Local detailed experimental reports are retained under `build/`; the final
build is `runs/wokwi/`. `docs/verification/` retains compact results suitable
for review without depending on those large, ignored build directories.

During continuous video, a frame normally performs 480 identity scans (one per
displayed line), 59 drawing updates, 59 rewind updates and one animation update.
The state bank therefore receives 599 × 32 = 19,168 active processing edges per
420,000-clock frame, about **4.56%** of the pixel clocks. The earlier indexed-VGA
version needed only 0.91%; serial pixel reads trade increased bank activity for
less selection logic and wiring. This is an architectural clock-activity calculation, not
a measured power reduction; the raster controller and audio phase accumulator
continue running. A generation transaction takes 33 input clocks, **1.32 µs**,
including acceptance, within the 6.4 µs horizontal blanking interval.
