// Pin-only bridge: commands on stdin, one uo_out byte per clock on stdout.
#include "Vtt_um_qd39l_echoscope.h"
#include "verilated.h"
#include <cstdio>
#include <vector>
int main(int argc, char **argv) {
    VerilatedContext context;
    context.commandArgs(argc, argv);
    Vtt_um_qd39l_echoscope dut{&context};
    unsigned cycles, ui, address, enabled, reset_n;
    while (std::scanf("%u %u %u %u %u", &cycles, &ui, &address, &enabled, &reset_n) == 5) {
        if (cycles > 1260000 || ui > 255 || address > 31 || enabled > 1 || reset_n > 1) return 2;
        dut.clk=0; dut.ui_in=ui; dut.uio_in=address; dut.ena=enabled; dut.rst_n=reset_n;
        dut.eval();
        std::vector<unsigned char> pixels(cycles);
        for (unsigned i=0; i<cycles; ++i) {
            context.timeInc(20); dut.clk=1; dut.eval();
            context.timeInc(20); dut.clk=0; dut.eval();
            pixels[i]=dut.uo_out;
        }
        if (std::fwrite(pixels.data(), 1, pixels.size(), stdout) != pixels.size()) return 3;
        std::fflush(stdout);
    }
    dut.final();
}
