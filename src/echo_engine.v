`default_nettype none
// Serial implementation of the 32-cell, second-order reversible Rule 30.
// Each transaction rotates every plane exactly 32 times, restoring bit order.
module echo_engine (
    input wire clk, rst_n, ena, start, reverse,
    input wire [1:0] operation,
    input wire [4:0] cell_address,
    output reg busy,
    output wire ready,
    output reg [5:0] distance,
    output reg equal,
    output reg [31:0] a_past, a_now, b_past, b_now
);
    reg direction;
    // Preserve the compact opcode; one-hot expansion can add a clock-tree level.
    (* fsm_encoding = "none" *) reg [1:0] op;
    reg [4:0] index, selected_cell;
    reg a_left, a_first, b_left, b_first;
    wire [1:0] a_source = direction ? a_past[1:0] : a_now[1:0];
    wire [1:0] b_source = direction ? b_past[1:0] : b_now[1:0];
    wire a_other = direction ? a_now[0] : a_past[0];
    wire b_other = direction ? b_now[0] : b_past[0];
    wire a_right = index == 31 ? a_first : a_source[1];
    wire b_right = index == 31 ? b_first : b_source[1];
    wire a_result = a_left ^ (a_source[0] | a_right) ^ a_other;
    wire b_result = b_left ^ (b_source[0] | b_right) ^ b_other;
    wire a_past_bit = op == 0 ? (direction ? a_result : a_now[0]) : a_past[0];
    wire a_now_bit = op == 0 ? (direction ? a_past[0] : a_result) : a_now[0];
    wire b_past_bit = op == 2 ? a_past[0] : op == 0 ? (direction ? b_result : b_now[0]) : b_past[0];
    wire b_now_bit = op == 2 ? a_now[0] : op == 1 ? (b_now[0] ^ (index == selected_cell))
                                  : op == 0 ? (direction ? b_past[0] : b_result) : b_now[0];
    // Startup flushes all four planes through their existing serial inputs.
    // These 128 flops have no reset pins; outputs stay masked until ready.
    // Reverse is meaningful only for evolve. Reserve reverse+scan for init.
    wire initializing = direction && op == 3;
    assign ready = !initializing;
    always @(posedge clk) begin
        if (initializing || (ena && busy)) begin
            a_past <= {initializing ? 1'b0 : a_past_bit, a_past[31:1]};
            a_now <= {initializing ? (index == 15) : a_now_bit, a_now[31:1]};
            b_past <= {initializing ? 1'b0 : b_past_bit, b_past[31:1]};
            b_now <= {initializing ? (index == 15 || index == 16) : b_now_bit, b_now[31:1]};
        end
    end
    always @(posedge clk) begin
        if (!rst_n) begin
            busy <= 1;
            distance <= 1;
            equal <= 0;
            direction <= 1;
            op <= 3;
            index <= 0;
            selected_cell <= 0;
            a_left <= 0;
            b_left <= 0;
            a_first <= 0;
            b_first <= 0;
        end else if (initializing) begin
            index <= index + 5'd1;
            if (index == 31) begin
                direction <= 0;
                busy <= 0;
            end
        end else if (ena) begin
            if (busy) begin
                distance <= distance + {5'd0, (a_now_bit ^ b_now_bit)};
                equal <= equal && (a_now_bit == b_now_bit) && (a_past_bit == b_past_bit);
                a_left <= a_source[0];
                b_left <= b_source[0];
                index <= index + 5'd1;
                if (index == 31) busy <= 0;
            end else if (start) begin
                busy <= 1;
                distance <= 0;
                equal <= 1;
                index <= 0;
                direction <= operation == 0 && reverse;
                op <= operation;
                selected_cell <= cell_address;
                a_left <= reverse ? a_past[31] : a_now[31];
                b_left <= reverse ? b_past[31] : b_now[31];
                a_first <= reverse ? a_past[0] : a_now[0];
                b_first <= reverse ? b_past[0] : b_now[0];
            end
        end
    end
endmodule
