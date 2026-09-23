`default_nettype none
module formal_roundtrip (
    input wire [31:0] past, present,
    input wire reverse,
    output wire roundtrip_ok
);
    wire [31:0] p1, n1, p2, n2;
    echo_step first(past, present, reverse, p1, n1);
    echo_step second(p1, n1, !reverse, p2, n2);
    assign roundtrip_ok = p2 == past && n2 == present;
endmodule
