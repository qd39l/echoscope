`default_nettype none
// Second-order Rule 30 on a periodic 32-cell ring.
// Both directions share the same nonlinear rule network.
module echo_step (
    input wire [31:0] past,
    input wire [31:0] present,
    input wire reverse,
    output wire [31:0] next_past,
    output wire [31:0] next_present
);
    wire [31:0] source = reverse ? past : present;
    wire [31:0] other = reverse ? present : past;
    wire [31:0] left = {source[30:0], source[31]};
    wire [31:0] right = {source[0], source[31:1]};
    wire [31:0] result = (left ^ (source | right)) ^ other;
    assign next_past = reverse ? result : present;
    assign next_present = reverse ? past : result;
endmodule
