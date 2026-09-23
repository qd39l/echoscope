import sys
from pathlib import Path
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test import reset
from model import INITIAL, step, kick, clone


async def to_commit(dut):
    h, v = int(dut.dut.h.value), int(dut.dut.v.value)
    cycles = (483 * 800 + 100 - (v * 800 + h)) % 420000
    if not cycles:
        cycles = 420000
    await Timer(cycles * 40, unit='ns')


def state(dut):
    return tuple(int(getattr(dut.dut, n).value) for n in ('a_past','a_now','b_past','b_now'))


@cocotb.test()
async def frame_commands_audio_and_scan_restoration(dut):
    cocotb.start_soon(Clock(dut.clk, 40, unit='ns').start())
    await reset(dut, diagnostic=False, controls=2)
    await to_commit(dut)
    expected = INITIAL
    assert state(dut) == expected
    scenarios = [
        (2 | 4, lambda s: step(s)),   # step despite pause
        (2 | 4, lambda s: s),         # held step does not repeat
        (2 | 1, lambda s: s),         # release, set reverse
        (2 | 1 | 4, lambda s: step(s, True)),
        (2, lambda s: s),
        (2 | 8, lambda s: kick(s, 31)),
        (2, lambda s: s),
        (2 | 16 | 8 | 4, clone),     # simultaneous commands: clone wins
        (0, step),                   # automatic forward
        (1, lambda s: step(s, True)), # automatic reverse
    ]
    for controls, operation in scenarios:
        dut.ui_in.value = controls
        dut.uio_in.value = 31
        await to_commit(dut)
        expected = operation(expected)
        assert state(dut) == expected, controls
        assert int(dut.dut.distance.value) == (expected[1] ^ expected[3]).bit_count()
    assert int(dut.dut.distance.value) == 0
    assert (int(dut.uio_out.value) & 128) == 0
    # Reintroduce a disagreement; check audible activity and mute at the pins.
    dut.ui_in.value = 2 | 8
    await to_commit(dut)
    assert int(dut.dut.distance.value) == 1
    levels = set()
    for _ in range(100):
        await Timer(10000, unit='ns')
        levels.add((int(dut.uio_out.value) >> 7) & 1)
    # 1 ms need not contain both levels at C4; sample more than one period.
    for _ in range(500):
        await Timer(10000, unit='ns')
        levels.add((int(dut.uio_out.value) >> 7) & 1)
    assert levels == {0,1}
    dut.ui_in.value = 2 | 64
    await Timer(1000, unit='ns')
    assert (int(dut.uio_out.value) & 128) == 0
