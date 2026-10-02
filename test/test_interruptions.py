"""Systematic interruption coverage using only package pins, RTL and gates."""
import cocotb
from cocotb.clock import Clock
from test import settle, reset, press, read_state
from model import INITIAL, step, kick, clone


def known_outputs(dut):
    for name in ('uo_out', 'uio_out', 'uio_oe'):
        assert getattr(dut, name).value.is_resolvable, name


async def accept(dut, button, reverse, cell):
    dut.ui_in.value = 128 | int(reverse)
    dut.uio_in.value = cell
    await settle(dut)
    dut.ui_in.value = 128 | int(reverse) | (1 << button)
    for _ in range(8):
        await settle(dut, 1)
        known_outputs(dut)
        if int(dut.uio_out.value) & 32:
            return
    raise AssertionError('Operation was not accepted')


@cocotb.test()
async def every_serial_phase_survives_pause_and_reset(dut):
    """All 32 processing positions, five operations, pause and reset."""
    cocotb.start_soon(Clock(dut.clk, 40, unit='ns').start())
    operations = ((2, False), (2, True), (3, False), (4, False), (5, False))
    for button, reverse in operations:
        for phase in range(32):
            for restart in (False, True):
                await reset(dut)
                # A non-seed input makes a silent restart observable.
                await press(dut, 2)
                baseline = step(INITIAL)
                cell = phase
                expected = (step(baseline, reverse) if button == 2 else
                            kick(baseline, cell) if button == 3 else
                            clone(baseline) if button == 4 else baseline)
                await accept(dut, button, reverse, cell)
                if phase:
                    await settle(dut, phase)
                assert int(dut.uio_out.value) & 32, (button, phase)
                dut.ena.value = 0
                # Direction/address may change after acceptance. Keep the
                # accepted button high so there is no second command edge.
                dut.ui_in.value = 128 | int(not reverse) | (1 << button)
                dut.uio_in.value = 31 - cell
                if restart:
                    dut.rst_n.value = 0
                for _ in range(7):
                    await settle(dut, 1)
                    known_outputs(dut)
                    assert int(dut.uo_out.value) == 0x88
                    assert int(dut.uio_out.value) == 0
                    assert int(dut.uio_oe.value) == 0
                if restart:
                    dut.ui_in.value = 128
                    dut.rst_n.value = 1
                    await settle(dut, 32)
                    expected = INITIAL
                dut.ena.value = 1
                await settle(dut, 40)
                known_outputs(dut)
                dut.ui_in.value = 128
                await settle(dut)
                assert await read_state(dut) == expected, (button, reverse, phase, restart)


@cocotb.test()
async def reset_at_every_initialization_phase(dut):
    """Restart at each initialization position with tile enabled/disabled."""
    cocotb.start_soon(Clock(dut.clk, 40, unit='ns').start())
    for enabled in (0, 1):
        for phase in range(32):
            await reset(dut)
            await press(dut, 2)
            dut.ena.value = enabled
            dut.rst_n.value = 0
            await settle(dut)
            dut.rst_n.value = 1
            if phase:
                await settle(dut, phase)
            dut.rst_n.value = 0
            await settle(dut)
            dut.rst_n.value = 1
            for cycle in range(32):
                await settle(dut, 1)
                known_outputs(dut)
                assert int(dut.uio_oe.value) == (0xe0 if enabled else 0)
                if cycle < 31 or not enabled:
                    assert int(dut.uo_out.value) == 0x88
                    assert int(dut.uio_out.value) == (32 if enabled else 0)
            dut.ena.value = 1
            await settle(dut)
            assert await read_state(dut) == INITIAL, (enabled, phase)
