# Synthesis cell policy

The stock open_pdks synthesis exclusion list excludes most minimum-drive
standard cells, although they remain legal in the place-and-route resizer.
For this area-constrained macro, `src/area_no_synth.cells` permits the `_1`
variant only when its `_2` counterpart exists and is already permitted, and
the `_1` cell is absent from the PDK DRC exclusion list. All other exclusions
are retained. The PDK, DRC exclusion list, geometry checks and timing limits
are unchanged. We validate pin accessibility through actual routing and DRC.

Generated from the pinned open_pdks revision documented in toolchain.md.
The final `EXTRA_EXCLUDED_CELLS` configuration further excludes `a21oi_1`,
`nor2_1`, `dlygate*_1`, `buf_1`, and `clkdlybuf*` (all with the
`sky130_fd_sc_hd__` prefix). Extracted timing identified weak drivers in these
families; these overrides apply during synthesis and physical repair. The
list below describes the generated base policy before those overrides.

Additional cells allowed by the base synthesis policy:

```text
sky130_fd_sc_hd__a2111o_1
sky130_fd_sc_hd__a2111oi_1
sky130_fd_sc_hd__a211o_1
sky130_fd_sc_hd__a211oi_1
sky130_fd_sc_hd__a21bo_1
sky130_fd_sc_hd__a21boi_1
sky130_fd_sc_hd__a21o_1
sky130_fd_sc_hd__a21oi_1
sky130_fd_sc_hd__a221o_1
sky130_fd_sc_hd__a221oi_1
sky130_fd_sc_hd__a22o_1
sky130_fd_sc_hd__a22oi_1
sky130_fd_sc_hd__a2bb2o_1
sky130_fd_sc_hd__a2bb2oi_1
sky130_fd_sc_hd__a311o_1
sky130_fd_sc_hd__a311oi_1
sky130_fd_sc_hd__a31o_1
sky130_fd_sc_hd__a31oi_1
sky130_fd_sc_hd__a32o_1
sky130_fd_sc_hd__a32oi_1
sky130_fd_sc_hd__a41o_1
sky130_fd_sc_hd__a41oi_1
sky130_fd_sc_hd__and2_1
sky130_fd_sc_hd__and2b_1
sky130_fd_sc_hd__and3_1
sky130_fd_sc_hd__and3b_1
sky130_fd_sc_hd__and4_1
sky130_fd_sc_hd__and4b_1
sky130_fd_sc_hd__and4bb_1
sky130_fd_sc_hd__dfbbn_1
sky130_fd_sc_hd__dfrbp_1
sky130_fd_sc_hd__dfrtp_1
sky130_fd_sc_hd__dfsbp_1
sky130_fd_sc_hd__dfstp_1
sky130_fd_sc_hd__dfxbp_1
sky130_fd_sc_hd__dfxtp_1
sky130_fd_sc_hd__ebufn_1
sky130_fd_sc_hd__inv_1
sky130_fd_sc_hd__nand2_1
sky130_fd_sc_hd__nand2b_1
sky130_fd_sc_hd__nand3_1
sky130_fd_sc_hd__nand3b_1
sky130_fd_sc_hd__nand4_1
sky130_fd_sc_hd__nand4b_1
sky130_fd_sc_hd__nand4bb_1
sky130_fd_sc_hd__nor2_1
sky130_fd_sc_hd__nor2b_1
sky130_fd_sc_hd__nor3_1
sky130_fd_sc_hd__nor3b_1
sky130_fd_sc_hd__nor4_1
sky130_fd_sc_hd__nor4b_1
sky130_fd_sc_hd__nor4bb_1
sky130_fd_sc_hd__o2111a_1
sky130_fd_sc_hd__o2111ai_1
sky130_fd_sc_hd__o211a_1
sky130_fd_sc_hd__o211ai_1
sky130_fd_sc_hd__o21a_1
sky130_fd_sc_hd__o21ai_1
sky130_fd_sc_hd__o21ba_1
sky130_fd_sc_hd__o21bai_1
sky130_fd_sc_hd__o221a_1
sky130_fd_sc_hd__o221ai_1
sky130_fd_sc_hd__o22a_1
sky130_fd_sc_hd__o22ai_1
sky130_fd_sc_hd__o2bb2a_1
sky130_fd_sc_hd__o2bb2ai_1
sky130_fd_sc_hd__o311a_1
sky130_fd_sc_hd__o311ai_1
sky130_fd_sc_hd__o31a_1
sky130_fd_sc_hd__o31ai_1
sky130_fd_sc_hd__o32a_1
sky130_fd_sc_hd__o32ai_1
sky130_fd_sc_hd__o41a_1
sky130_fd_sc_hd__o41ai_1
sky130_fd_sc_hd__or2_1
sky130_fd_sc_hd__or2b_1
sky130_fd_sc_hd__or3_1
sky130_fd_sc_hd__or3b_1
sky130_fd_sc_hd__or4_1
sky130_fd_sc_hd__or4b_1
sky130_fd_sc_hd__or4bb_1
sky130_fd_sc_hd__xnor2_1
sky130_fd_sc_hd__xor2_1
```

Run `tools/build_area_cell_policy.py --pdk-root /path/to/pdk` to verify the
checked-in list, or add `--write` to regenerate it. The script derives the
list from the pinned PDK's Liberty cell names, `no_synth.cells`, and
`drc_exclude.cells`; it does not maintain an independent list of legal cells.
The upstream policies are maintained in
[open_pdks](https://github.com/RTimothyEdwards/open_pdks/tree/master/sky130/openlane/sky130_fd_sc_hd).
