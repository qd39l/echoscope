`timescale 1ns/1ps
`default_nettype none
module tb;
    reg clk = 0;
    reg rst_n = 0;
    reg ena = 1;
    reg [7:0] ui_in = 0;
    reg [7:0] uio_in = 0;
    wire [7:0] uo_out, uio_out, uio_oe;
    supply1 VPWR;
    supply0 VGND;
    tt_um_qd39l_echoscope dut (
`ifdef GL_TEST
        .VPWR(VPWR), .VGND(VGND),
`endif
        .ui_in(ui_in), .uo_out(uo_out), .uio_in(uio_in),
        .uio_out(uio_out), .uio_oe(uio_oe), .ena(ena), .clk(clk), .rst_n(rst_n)
    );
    initial begin
        if ($test$plusargs("trace")) begin
            $dumpfile("tb.fst");
            $dumpvars(0,tb);
        end
    end
endmodule
