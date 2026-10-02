`default_nettype none
// Two-state, ideal-supply translation of the pinned PDK's dlclkp functional
// model: invert CLK, transparent-high latch on that inverted clock, AND CLK.
// The latch is deliberately retained, not replaced by a combinational gate.
module proof_dlclkp(input CLK, GATE, VPWR, VGND, VPB, VNB, output GCLK);
    reg held;
    always @* if (!CLK) held = GATE;
    assign GCLK = held & CLK;
endmodule
