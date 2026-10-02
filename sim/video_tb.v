`timescale 1ns/1ps
// Same pin-only protocol as video_driver.cpp, including powered netlists.
module video_tb;
    reg clk=0, rst_n=0, ena=1;
    reg [7:0] ui_in=0, uio_in=0;
    wire [7:0] uo_out, uio_out, uio_oe;
    supply1 VPWR;
    supply0 VGND;
    integer count, controls, address, enabled, reset_n, result, i;
    tt_um_qd39l_echoscope dut (
`ifdef GL_TEST
        .VPWR(VPWR), .VGND(VGND),
`endif
        .clk(clk), .rst_n(rst_n), .ena(ena), .ui_in(ui_in), .uio_in(uio_in),
        .uo_out(uo_out), .uio_out(uio_out), .uio_oe(uio_oe)
    );
    initial begin
        forever begin
            result=$fscanf(32'h80000000,"%d %d %d %d %d",count,controls,address,enabled,reset_n);
            if (result!=5) $finish;
            if (count<0 || count>1260000) $fatal(1,"invalid clock count");
            ui_in=controls; uio_in=address; ena=enabled; rst_n=reset_n;
            for(i=0;i<count;i=i+1) begin
                #20 clk=1;
                #20 clk=0;
                if ((^uo_out)===1'bx) $fatal(1,"unknown VGA output");
                $fwrite(32'h80000001,"%c",uo_out);
            end
            $fflush(32'h80000001);
        end
    end
endmodule
