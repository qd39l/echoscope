`default_nettype none
module tt_um_qd39l_echoscope (
    input wire [7:0] ui_in,
    output wire [7:0] uo_out,
    input wire [7:0] uio_in,
    output wire [7:0] uio_out,
    output wire [7:0] uio_oe,
    input wire ena,
    input wire clk,
    input wire rst_n
);
    // ui[7] selects diagnostic mode ONLY during reset. All other controls
    // and the perturbation/address bus pass through two synchronizer stages.
    reg diagnostic;
    reg [6:0] ui_meta, control;
    reg [4:0] io_meta, address;
    always @(posedge clk) begin
        if (!rst_n) begin
            diagnostic <= ui_in[7];
            ui_meta <= 0;
            control <= 0;
            io_meta <= 0;
            address <= 0;
        end else begin
            ui_meta <= ui_in[6:0];
            control <= ui_meta;
            io_meta <= uio_in[4:0];
            address <= io_meta;
        end
    end

    reg [9:0] h, v;
    wire [31:0] a_past, a_now, b_past, b_now;
    reg [15:0] epoch;
    reg [3:0] last_buttons;
    reg difference_view, backwards, paused;
    wire frame_command = (v == 483 && h == 0);
    wire command_tick = diagnostic || frame_command;
    wire step_button = control[2] && !last_buttons[0];
    wire perturb = control[3] && !last_buttons[1];
    wire heal = control[4] && !last_buttons[2];
    wire scan = diagnostic && control[5] && !last_buttons[3];
    wire advance = diagnostic ? step_button : (!control[1] || step_button);

    // One cell per clock: all 32 cells finish inside horizontal blanking.
    // A scan uses 59 forward generations; 59 serial inverse generations
    // restore the canonical state before line 483 accepts a user command.
    // Scan the same fixed serial output for all 16 pixels in a cell.
    // Exactly 32 shifts restore every state plane before horizontal blanking.
    wire row_scan = !diagnostic && v < 480 && h == 63;
    wire display_cell = !diagnostic && v < 480 && h >= 64 && h < 576;
    wire engine_enable = ena && (!display_cell || h[3:0] == 15);
    wire draw_step = !diagnostic && h == 640 && v < 472 && v[2:0] == 7;
    reg [5:0] restore_left;
    wire restore_step = !diagnostic && restore_left != 0;
    wire user_command = command_tick && (heal || perturb || advance || scan);
    wire busy, ready;
    wire [5:0] engine_distance;
    wire engine_equal;
    wire start = ready && !busy && (row_scan || draw_step || restore_step || user_command);
    wire user_start = start && !row_scan && !draw_step && !restore_step;
    wire step_reverse = restore_step || (user_start && control[0]);
    // Operation encoding: 0 evolve, 1 perturb, 2 clone, 3 scan/identity.
    wire [1:0] operation = row_scan ? 2'd3 : user_start ? (heal ? 2'd2 : perturb ? 2'd1 : advance ? 2'd0 : 2'd3) : 2'd0;
    echo_engine engine (
        .clk(clk), .rst_n(rst_n), .ena(engine_enable), .start(start),
        .reverse(step_reverse), .operation(operation), .cell_address(address),
        .busy(busy), .ready(ready), .distance(engine_distance), .equal(engine_equal),
        .a_past(a_past), .a_now(a_now), .b_past(b_past), .b_now(b_now)
    );

    always @(posedge clk) begin
        if (!rst_n || !ready) begin
            h <= 0;
            v <= 0;
            epoch <= 0;
            restore_left <= 0;
            last_buttons <= 0;
            difference_view <= 0;
            backwards <= 0;
            paused <= 0;
        end else if (ena) begin
            if (!diagnostic) begin
                if (h == 799) begin
                    h <= 0;
                    v <= v == 524 ? 10'd0 : v + 10'd1;
                end else h <= h + 10'd1;
            end
            if (v == 480 && h == 0 && !diagnostic) restore_left <= 59;
            else if (start && restore_step) restore_left <= restore_left - 6'd1;
            if (command_tick) begin
                last_buttons <= control[5:2];
                difference_view <= control[5];
                backwards <= control[0];
                paused <= control[1];
            end
            if (user_start && operation == 0)
                epoch <= control[0] ? epoch - 16'd1 : epoch + 16'd1;
        end
    end

    // The serial engine measures its result as it writes it, avoiding a
    // parallel XOR tree and a separate readback multiplexer for the meter.
    reg [5:0] distance;
    always @(posedge clk) begin
        if (!rst_n || !ready) begin
            distance <= 1;
        end else if (ena && !diagnostic && v == 483 && h == 40)
            distance <= engine_distance;
    end

    // C4-D4-E4-G4-A4-C5-D5-E5 at 25 MHz (23-bit phase accumulator).
    reg [7:0] pitch;
    always @* begin
        case (distance[4:2])
            0: pitch = 88;
            1: pitch = 99;
            2: pitch = 111;
            3: pitch = 132;
            4: pitch = 148;
            5: pitch = 176;
            6: pitch = 197;
            7: pitch = 221;
        endcase
    end
    reg [22:0] phase;
    always @(posedge clk) begin
        if (!rst_n || !ready) phase <= 0;
        else if (ena) phase <= phase + {15'd0, pitch};
    end
    wire audio = phase[22] && (distance != 0) && !control[6] && !diagnostic;

    // 640x480 active, 800x525 total, negative sync; 25 MHz gives 59.524 Hz.
    // Tiny VGA: R1,G1,B1,VS,R0,G0,B0,HS. RGB and sync share one pipeline.
    wire active = h < 640 && v < 480;
    wire cell_a = a_now[0];
    wire cell_b = b_now[0];
    wire mismatch = cell_a ^ cell_b;
    wire grid = h[3:0] == 0 || v[2:0] == 7;
    reg [1:0] red, green, blue;
    always @* begin
        red = 0; green = 0; blue = 0;
        if (active) begin
            if (h >= 64 && h < 576) begin
                if (!grid) begin
                    if (difference_view) begin
                        red = mismatch ? 2'd3 : 2'd0;
                        green = mismatch ? 2'd2 : 2'd0;
                        blue = mismatch ? 2'd1 : 2'd0;
                    end else begin
                        red = cell_b ? 2'd3 : 2'd0;
                        green = cell_a ? 2'd3 : 2'd0;
                        blue = (cell_a || cell_b) ? 2'd3 : 2'd0;
                    end
                end else blue = 1;
            end else if ((h >= 56 && h < 60) || (h >= 580 && h < 584)) begin
                red = backwards ? 2'd3 : 2'd0;
                green = backwards ? 2'd0 : 2'd3;
                blue = paused ? 2'd3 : 2'd0;
            end else if (h >= 24 && h < 40 && v < 256 && v[3:0] < 12) begin
                // Binary generation ruler; least significant bit at the top.
                red = epoch[v[7:4]] ? 2'd2 : 2'd0;
                green = red;
                blue = red;
            end else if (h >= 600 && h < 616 && v < 256) begin
                // Divergence meter: one cell = eight vertical pixels.
                red = {1'b0,v[7:3]} < distance ? 2'd3 : 2'd0;
                green = red != 0 ? 2'd1 : 2'd0;
            end
        end
    end
    reg [7:0] video;
    always @(posedge clk) begin
        if (!rst_n || !ready) video <= 8'h88;
        else if (ena) video <= {!(h >= 656 && h < 752), blue[0], green[0], red[0],
                               !(v >= 490 && v < 492), blue[1], green[1], red[1]};
    end
    // During scan, capture bit 0 when busy first rises; each subsequent
    // clock rotates one bit out. Exactly 32 clocks restore the original state.
    wire [7:0] scan_bits = {4'b0000, b_now[0], b_past[0], a_now[0], a_past[0]};
    assign uo_out = ena && ready ? (diagnostic ? scan_bits : video) : 8'h88;
    assign uio_out = {ena && ready && audio, ena && ready && engine_equal && !busy, ena && (busy || !ready), 5'd0};
    assign uio_oe = ena ? 8'he0 : 8'h00;
    wire _unused = &{1'b0, uio_in[7:5], a_past[31:1], b_past[31:1], a_now[31:1], b_now[31:1]};
endmodule
