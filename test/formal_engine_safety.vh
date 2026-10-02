// One-step invariants complement the arbitrary-state transaction proofs.
reg f_valid = 0;
always @(posedge clk) begin
    f_valid <= 1;
    if (f_valid && $past(rst_n && !initializing && !ena)) begin
        assert($stable({a_past,a_now,b_past,b_now,busy,distance,equal,
                        direction,op,index,selected_cell,a_left,b_left,a_first,b_first}));
    end
    if (f_valid && $past(rst_n && !initializing && ena && busy)) begin
        assert(index == $past(index) + 5'd1);
        assert(busy == ($past(index) != 31));
        assert($stable({direction,op,selected_cell}));
    end
    if (f_valid && $past(rst_n && initializing)) begin
        assert(index == $past(index) + 5'd1);
        assert(ready == ($past(index) == 31));
    end
end
