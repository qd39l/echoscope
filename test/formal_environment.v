`default_nettype none
// Explicit clock phases provide setup time to the clock-gating latch. One
// logical clock cycle spans four proof ticks; inputs change in the low phase.
// This models the synchronous I/O contract, not arbitrary zero-setup glitches.
module tt_um_qd39l_echoscope(input clk, ena, rst_n, input [7:0] ui_in, uio_in,
                           inout VPWR, VGND,
                           output [7:0] uo_out, uio_out, uio_oe);
    reg [1:0] phase = 0;
    reg enabled, reset_n;
    reg [7:0] controls, address;
    // The formal global tick always advances; clk is retained only to keep
    // the external port signature. This avoids arbitrary stalled proof time
    // hiding an unconstrained gate-latch value throughout the induction window.
    always @($global_clock) begin
        phase <= phase + 1;
        if (phase == 0) begin
            enabled <= ena;
            reset_n <= rst_n;
            controls <= ui_in;
            address <= uio_in;
        end
    end
    equivalence_core core(.clk(phase[1]), .ena(enabled), .rst_n(reset_n),
        .ui_in(controls), .uio_in(address), .uo_out(uo_out), .uio_out(uio_out),
        .uio_oe(uio_oe), .VPWR(VPWR), .VGND(VGND));
endmodule
