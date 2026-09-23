`default_nettype none
module formal_init(input wire clk, rst_n, ena, output wire initialized);
    wire busy, ready, equal;
    wire [5:0] distance;
    wire [31:0] ap, an, bp, bn;
    echo_engine engine(.clk(clk), .rst_n(rst_n), .ena(ena), .start(1'b0),
        .reverse(1'b0), .operation(2'b0), .cell_address(5'b0),
        .busy(busy), .ready(ready), .distance(distance), .equal(equal),
        .a_past(ap), .a_now(an), .b_past(bp), .b_now(bn));
    assign initialized = ready && !busy && !equal && distance == 1 &&
        ap == 0 && bp == 0 && an == 32'h00008000 && bn == 32'h00018000;
endmodule
