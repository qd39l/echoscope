"""Initialization must overwrite arbitrary storage before making it visible."""
import cocotb
from cocotb.clock import Clock
from test import settle, read_state, press
from model import INITIAL

@cocotb.test()
async def serial_initialization_masks_and_restarts(dut):
    cocotb.start_soon(Clock(dut.clk, 40, unit='ns').start())
    dut.ena.value = 1
    dut.ui_in.value = 128
    dut.uio_in.value = 16
    dut.rst_n.value = 0
    await settle(dut)
    # Restart once partway through initialization, including with ena low.
    for enabled, partial in ((1, True), (0, True), (1, False)):
        dut.ena.value = enabled
        dut.rst_n.value = 1
        for cycle in range(11 if partial else 32):
            await settle(dut, 1)
            if cycle < 31:
                assert int(dut.uo_out.value) == 0x88
                assert int(dut.uio_out.value) == (32 if enabled else 0)
            else:
                assert not int(dut.uio_out.value) & 32
            assert int(dut.uio_oe.value) == (0xe0 if enabled else 0)
        if partial:
            dut.rst_n.value = 0
            await settle(dut)
    assert await read_state(dut) == INITIAL
    await press(dut, 3, cell=31)
    dut.ena.value = 0
    dut.rst_n.value = 0
    await settle(dut)
    dut.rst_n.value = 1
    await settle(dut, 32)
    assert int(dut.uio_oe.value) == 0
    dut.ena.value = 1
    await settle(dut)
    assert await read_state(dut) == INITIAL
