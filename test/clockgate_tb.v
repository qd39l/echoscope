`timescale 1ns/1ps
module clockgate_tb;
    reg clk=0, gate=0;
    wire reference, translated;
    integer sequence_id, tick;
    sky130_fd_sc_hd__dlclkp_1 ref_cell(.CLK(clk),.GATE(gate),.GCLK(reference),
        .VPWR(1'b1),.VPB(1'b1),.VGND(1'b0),.VNB(1'b0));
    proof_dlclkp proof_cell(.CLK(clk),.GATE(gate),.GCLK(translated),
        .VPWR(1'b1),.VPB(1'b1),.VGND(1'b0),.VNB(1'b0));
    initial begin
        // Every length-eight enable sequence, with enable changes both while
        // the clock is low and high. Check the actual PDK UDP against the
        // formal latch translation, including ignored high-phase changes.
        for (sequence_id=0;sequence_id<256;sequence_id=sequence_id+1) begin
            clk=1; gate=0; #2; clk=0; #2;
            for(tick=0;tick<8;tick=tick+1) begin
                gate=(sequence_id>>tick)&1; #2;
                if(reference !== translated) $fatal(1,"low phase mismatch");
                clk=1; #2;
                if(reference !== translated) $fatal(1,"rising edge mismatch: reference=%b translated=%b",reference,translated);
                gate=~gate; #2;
                if(reference !== translated) $fatal(1,"high phase mismatch");
                clk=0; #2;
                if(reference !== translated) $fatal(1,"falling edge mismatch");
            end
        end
        $display("PASS: 256 gate-enable sequences, 8192 observations");
        $finish;
    end
endmodule
