`default_nettype none
module formal_serial (
    input wire clk, rst_n, ena, start, reverse,
    input wire [1:0] operation,
    input wire [4:0] cell_address,
    output wire proof_ok,
    output wire busy
);
    wire [31:0] ap, an, bp, bn;
    wire [31:0] na_p, na_n, nb_p, nb_n;
    reg [31:0] expected_ap, expected_an, expected_bp, expected_bn;
    wire [5:0] distance;
    wire equal;
    integer i;
    reg [5:0] expected_distance;
    always @* begin
        expected_distance = 0;
        for (i = 0; i < 32; i = i + 1)
            expected_distance = expected_distance + {5'd0, expected_an[i] ^ expected_bn[i]};
    end
    echo_engine engine(clk, rst_n, ena, start, reverse, operation, cell_address,
                       busy, , distance, equal, ap, an, bp, bn);
    echo_step ref_a(ap, an, reverse, na_p, na_n);
    echo_step ref_b(bp, bn, reverse, nb_p, nb_n);
    always @(posedge clk) if (start) begin
        expected_ap <= operation == 0 ? na_p : ap;
        expected_an <= operation == 0 ? na_n : an;
        expected_bp <= operation == 0 ? nb_p : operation == 2 ? ap : bp;
        expected_bn <= operation == 0 ? nb_n : operation == 2 ? an : operation == 1 ? bn ^ (32'd1 << cell_address) : bn;
    end
    assign proof_ok = !busy && ap == expected_ap && an == expected_an
                        && bp == expected_bp && bn == expected_bn
                        && distance == expected_distance
                        && equal == ((expected_ap == expected_bp) && (expected_an == expected_bn));
endmodule
