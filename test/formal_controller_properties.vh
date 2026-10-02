// Injected into an otherwise unchanged copy of project.v by formal_safety.py.
// Environment: normal video mode; other controls, reset and ena are arbitrary.
reg f_seen_reset = 0;
reg [6:0] f_balance;
reg f_user_work;
wire [11:0] f_restore_time = (v - 10'd480) * 12'd800 + {2'b0,h};
wire [11:0] f_restore_group = (f_restore_time - 12'd1) / 12'd33;
wire [11:0] f_restore_phase = (f_restore_time - 12'd1) % 12'd33;
wire f_scan_work = v < 480 && h >= 64 && h < 576;
wire f_draw_work = v < 472 && v[2:0] == 7 && h >= 641 && h <= 672;
wire [6:0] f_visible_balance = {1'b0,v[8:3]} +
    ((v < 472 && v[2:0] == 7 && h >= 641) ? 7'd1 : 7'd0);

always @(posedge clk) begin
    assume(!ui_in[7]);
    if (!rst_n) f_seen_reset <= 1;
    if (!rst_n || !ready) begin
        f_balance <= 0;
        f_user_work <= 0;
    end else if (ena) begin
        if (start && !user_start && operation == 0)
            f_balance <= step_reverse ? f_balance - 1 : f_balance + 1;
        if (frame_command) f_user_work <= user_start;
    end
    if (f_seen_reset) begin
        assert(!diagnostic);
        assert(h <= 799 && v <= 524);
        if (ready) begin
            assert(f_balance <= 59);
            if (v < 480) begin
                assert(restore_left == 0);
                assert(f_balance == f_visible_balance);
                assert(busy == (f_scan_work || f_draw_work));
                if (f_scan_work) assert(f_engine_index == ((h - 64) >> 4));
                if (f_draw_work) assert(f_engine_index == h - 641);
            end else if (v < 483) begin
                if (f_restore_time == 0) begin
                    assert(!busy && restore_left == 0 && f_balance == 59);
                end else if (f_restore_time <= 1947) begin
                    assert(restore_left == 59 - f_restore_group - (f_restore_phase != 0));
                    assert(f_balance == restore_left);
                    assert(busy == (f_restore_phase != 0));
                    if (busy) assert(f_engine_index == f_restore_phase - 1);
                end else begin
                    assert(!busy && restore_left == 0 && f_balance == 0);
                end
            end else begin
                assert(restore_left == 0 && f_balance == 0);
                assert(busy == (v == 483 && h >= 1 && h <= 32 && f_user_work));
                if (busy) assert(f_engine_index == h - 1);
            end
            // By the command edge all raster transactions have completed,
            // exactly 59 evolves have been cancelled by 59 inverses, and
            // each visible line's identity scan has finished all 32 shifts.
            if (frame_command) assert(!busy && restore_left == 0 && f_balance == 0);
            if (start && row_scan) assert(operation == 3 && !step_reverse);
            if (start && draw_step) assert(operation == 0 && !step_reverse);
            if (start && restore_step) assert(operation == 0 && step_reverse);
            if (user_start) assert(frame_command);
        end
        if (!ena || !ready) begin
            assert(uo_out == 8'h88);
            assert(uio_out[7:6] == 0);
        end
        if (!ena) assert(uio_oe == 0);
    end
end
