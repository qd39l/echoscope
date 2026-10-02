# Reproducible toolchain

| Component | Pinned version |
| --- | --- |
| LibreLane Docker image | `ghcr.io/librelane/librelane:3.0.14` |
| PDK | SKY130A, open_pdks `8afc8346a57fe1ab7934ba5a6056ea8b43078e71` |
| tt-support-tools | `01d5d2814fa9dd61e9d211e0b235a4a592a9316a` |
| Cocotb | 2.0.1 |
| Python | 3.11 |
| CI shuttle action | `TinyTapeout/tt-gds-action@ttsky26d` |

`scripts/setup.sh` creates a local virtual environment, installs the pinned
test/physical dependencies, and checks out the support-tools revision. It does
not download the PDK or start Docker. On macOS, if Cairo is not discovered,
set `DYLD_FALLBACK_LIBRARY_PATH` to the Homebrew library directory.

To initialize the PDK and seed the persistent Docker cache on a new machine:

```sh
export PDK_ROOT="$PWD/.pdk"
.venv/bin/ciel enable --pdk-family sky130 8afc8346a57fe1ab7934ba5a6056ea8b43078e71
docker pull ghcr.io/librelane/librelane:3.0.14
docker volume create ttsky26d-pdk-3.0.14
tar -C .pdk -cf - . | docker run --rm --network none -i \
  -v ttsky26d-pdk-3.0.14:/pdk ghcr.io/librelane/librelane:3.0.14 tar -C /pdk -xf -
```

Subsequent builds mount that volume read-only. `make gl-test` additionally
needs `PDK_ROOT` pointing to the local PDK, because Icarus runs on the host.
An existing PDK may be used without copying or changing it:

```sh
make gl-test PDK_ROOT=/path/to/existing/pdk
```

The 40 ns timing target uses the stock LibreLane SDC, which reserves 20% of
the period (8 ns) at the input and output boundaries. It is an explicit
25 MHz boundary assumption, not a guarantee for arbitrary external wiring.
Button/address inputs use two-stage synchronizers. Multi-bit controls must be
held stable as described in the datasheet; synchronization is not a mechanical
switch debouncer.

The base template disables full KLayout DRC in the main flow; `make precheck`
runs the separate Tiny Tapeout checks. Every claimed check is enumerated in
the verification report, rather than inferred from the existence of GDS.

The final area mapping uses the checked-in synthesis exclusion list described
in [area_cell_policy.md](area_cell_policy.md). Clock gating is restricted by
a minimum bank size of 64 to the 128-bit world-state bank. These are plain
flops, initialized through 32 serial shifts with the gate open. The controller
remains on the main clock. Initialization reuses an otherwise unused opcode
and direction combination; `fsm_encoding="none"` preserves the compact binary
opcode instead of expanding it into additional flops. The earlier experiment gating
synchronously reset registers failed gate-level tests and was rejected. Design
repair uses `max_ss_100C_1v60` and `min_ff_n40C_1v95`, followed by extracted
signoff across all nine configured PVT/interconnect corners. Setup, hold,
maximum capacitance, and maximum slew violations are configured as failures
at every corner. The base timing period and external I/O assumptions remain
unchanged.

On macOS, `make precheck PDK_ROOT=/path/to/pdk` runs the **unmodified** pinned
Tiny Tapeout checker in the host Python environment. A small executable bridge
runs Magic, KLayout, and Yosys from the cached Linux container and returns their
reports to the checker. It translates file paths, uses no network or host bind
mount, and substitutes no check results. Python geometry dependencies are the
support-tools pins (gdstk 0.9.60, KLayout Python 0.29.12, NumPy 1.26.4); the
syntax check uses native container Yosys instead of its WebAssembly packaging.
The official GitHub action remains the independent hosted submission check.

Every local hardening run records SHA-256 hashes of the exact input files
inside the container. Finalization refuses to package a layout if those inputs
have changed, except for the exact documented attribution-only hash pair in
[publication notes](publication.md). The local provenance explicitly records whether a Git commit and
remote exist and whether the checkout is dirty; it does not invent a CI run.

## Additional release verification

`make release-check PDK_ROOT=/path/to/pdk` runs the RTL and powered-netlist
suites, full pin-only video regressions, original proofs, controller/engine
inductive proofs, clock-gate model comparison, extracted timing audit,
official precheck, evidence collection and privacy checks. Keep the working
tree stable during this run: receipts deliberately reject changed inputs.
The PDK path must include both standard-cell Verilog and technology files.

The formal safety harness instruments disposable copies in `build/safety-inputs`;
it does not change fabrication sources. The engine properties permit arbitrary
reset, enable and commands. Controller properties assume normal VGA mode and
are asserted after reset; other inputs and enable pauses remain arbitrary.
They prove unbounded scheduling invariants by induction. The original engine
proofs provide the arbitrary-state operation semantics used in the composition.
Negative controls remove state-bank enable gating or accept commands during
active video; the same assertions must produce bounded counterexamples.

`make equivalence` is required by `release-check` and evidence collection. The pinned
container includes EQY/Yosys but no GNU make, so `run_eqy_strategies.py` executes
all generated SAT strategy scripts and checks every generated status. It does
not alter solver commands or manufacture pass results. Each partition has a
600-second limit. Missing results, errors, unknowns and timeouts return failure.
EQY's setup-only `-m` invocation leaves an `UNKNOWN` marker before any strategy
runs; the completed verdict is `build/equivalence/strategy-results.json`,
validated against every generated strategy status and the source receipt.
The explicit clock-phase wrapper models input setup time; it is not evidence
for arbitrary asynchronous changes at a clock edge. The SKY130 clock-gate
latch is modeled explicitly, and its logical translation is checked against
the supplied PDK simulation primitive. No whole-netlist equivalence claim
should be made unless every partition passes with current input hashes.
