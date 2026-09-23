import os
import random
import sys
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from model import INITIAL, step, kick, clone


async def settle(dut, cycles=6):
    await ClockCycles(dut.clk, cycles)
    await FallingEdge(dut.clk)


async def reset(dut, diagnostic=True, controls=0):
    dut.ena.value = 1
    dut.ui_in.value = (128 if diagnostic else 0) | controls
    dut.uio_in.value = 16
    dut.rst_n.value = 0
    await settle(dut)
    dut.rst_n.value = 1
    await settle(dut, 32)
    await settle(dut)


async def read_state(dut):
    await settle(dut, 40)
    assert not int(dut.uio_out.value) & 32, "engine stuck busy"
    base = int(dut.ui_in.value) & ~32
    dut.ui_in.value = base
    await settle(dut)
    dut.ui_in.value = base | 32
    for _ in range(8):
        await settle(dut, 1)
        if int(dut.uio_out.value) & 32:
            break
    else:
        assert False, "scan not accepted"
    words = [0] * 4
    for bit in range(32):
        pins = int(dut.uo_out.value)
        assert pins < 16
        for plane in range(4):
            words[plane] |= ((pins >> plane) & 1) << bit
        await settle(dut, 1)
    assert not int(dut.uio_out.value) & 32
    dut.ui_in.value = base
    await settle(dut)
    return tuple(words)


async def press(dut, bit, reverse=False, cell=16):
    base = 128 | int(reverse)
    dut.uio_in.value = cell
    dut.ui_in.value = base
    await settle(dut)
    dut.ui_in.value = base | (1 << bit)
    await settle(dut)
    dut.ui_in.value = base
    await settle(dut, 40)


@cocotb.test()
async def diagnostic_reference_and_roundtrip(dut):
    """Only public pins: random operations, 1024-step reversal, all 128 scan bits."""
    cocotb.start_soon(Clock(dut.clk, 40, unit="ns").start())
    await reset(dut)
    assert int(dut.uio_oe.value) == 0xE0
    state = INITIAL
    assert await read_state(dut) == state
    rng = random.Random(20260922)
    for _ in range(100):
        op = rng.choice(["forward", "reverse", "kick", "clone"])
        if op == "kick":
            cell = rng.randrange(32)
            await press(dut, 3, cell=cell)
            state = kick(state, cell)
        elif op == "clone":
            await press(dut, 4)
            state = clone(state)
        else:
            rev = op == "reverse"
            await press(dut, 2, reverse=rev)
            state = step(state, rev)
        assert await read_state(dut) == state, op
        equal = state[:2] == state[2:]
        assert bool(int(dut.uio_out.value) & 64) == equal
    saved = state
    for reverse in (False, True):
        for _ in range(1024):
            await press(dut, 2, reverse)
        if not reverse:
            for _ in range(1024):
                state = step(state)
            assert await read_state(dut) == state
    assert await read_state(dut) == saved
    dut.ui_in.value = 128 | 4
    await settle(dut, 100)
    assert await read_state(dut) == step(saved), "held step retriggered"


@cocotb.test()
async def reset_enable_priority_and_all_cells(dut):
    cocotb.start_soon(Clock(dut.clk, 40, unit="ns").start())
    await reset(dut)
    await press(dut, 4)
    state = clone(INITIAL)
    for cell in range(32):
        await press(dut, 3, cell=cell)
        state = kick(state, cell)
        assert await read_state(dut) == state
    dut.ui_in.value = 128 | 4 | 8 | 16
    await settle(dut)
    state = clone(state)
    assert await read_state(dut) == state
    dut.ena.value = 0
    dut.ui_in.value = 128
    await settle(dut)
    assert int(dut.uio_oe.value) == 0
    assert int(dut.uo_out.value) == 0x88
    assert int(dut.uio_out.value) == 0
    dut.ena.value = 1
    await settle(dut)
    assert await read_state(dut) == state
    dut.ui_in.value = 0
    await settle(dut)
    assert await read_state(dut) == state, "ui[7] must be sampled only in reset"
    await reset(dut)
    assert await read_state(dut) == INITIAL

    # Catch a reset incorrectly blocked by an enable-controlled clock gate.
    dut.ui_in.value = 128 | 4
    await settle(dut, 8)
    assert int(dut.uio_out.value) & 32
    dut.ena.value = 0
    dut.ui_in.value = 128
    dut.rst_n.value = 0
    await settle(dut)
    dut.rst_n.value = 1
    await settle(dut)
    dut.ena.value = 1
    await settle(dut, 40)
    assert await read_state(dut) == INITIAL

    # Reset has priority even while the tile is disabled.
    await press(dut, 2)
    dut.ena.value = 0
    dut.rst_n.value = 0
    await settle(dut)
    dut.rst_n.value = 1
    await settle(dut)
    assert int(dut.uio_oe.value) == 0
    dut.ena.value = 1
    await settle(dut)
    assert await read_state(dut) == INITIAL


@cocotb.test(skip=os.environ.get("GATES") == "yes")
async def raster_reconstruction_and_frame_controls(dut):
    """Sample real RGB pins and canonical state over a complete video frame."""
    cocotb.start_soon(Clock(dut.clk, 40, unit="ns").start())
    await reset(dut, diagnostic=False, controls=2 | 64)
    while int(dut.dut.h.value) != 0 or int(dut.dut.v.value) != 0:
        await settle(dut, 1)
    base = INITIAL
    pixels = bytearray()
    hs_count = vs_count = 0
    for y in range(525):
        expected = base
        if y < 480:
            for _ in range(y // 8):
                expected = step(expected)
        for x in range(800):
            await settle(dut, 1)
            out = int(dut.uo_out.value)
            hs_count += not bool(out & 128)
            vs_count += not bool(out & 8)
            assert bool(out & 128) == (not 656 <= x < 752), (x, y)
            assert bool(out & 8) == (not 490 <= y < 492), (x, y)
            r = ((out & 1) * 2 + ((out >> 4) & 1)) * 85
            g = (((out >> 1) & 1) * 2 + ((out >> 5) & 1)) * 85
            b = (((out >> 2) & 1) * 2 + ((out >> 6) & 1)) * 85
            if x >= 640 or y >= 480:
                assert (r, g, b) == (0, 0, 0), (x, y)
            elif 64 <= x < 576:
                cell = (x - 64) // 16
                ca, cb = (expected[1] >> cell) & 1, (expected[3] >> cell) & 1
                color = (0, 0, 85) if x % 16 == 0 or y % 8 == 7 else (cb*255, ca*255, (ca|cb)*255)
                assert (r, g, b) == color, (x, y)
            if x < 640 and y < 480:
                pixels.extend((r, g, b))
        if y == 483:
            actual = tuple(int(getattr(dut.dut, n).value) for n in ("a_past", "a_now", "b_past", "b_now"))
            assert actual == base, "paused drawing changed the underlying world"
            assert int(dut.dut.distance.value) == 1
    assert hs_count == 96 * 525
    assert vs_count == 2 * 800
    from PIL import Image
    Path("output").mkdir(exist_ok=True)
    Image.frombytes("RGB", (640, 480), bytes(pixels)).save("output/rtl-frame.png")


@cocotb.test()
async def busy_freeze_reset_and_latched_command(dut):
    """Serial work survives ena pauses; controls are latched on acceptance."""
    cocotb.start_soon(Clock(dut.clk, 40, unit="ns").start())
    await reset(dut)
    dut.ui_in.value = 128 | 4
    await settle(dut, 8)
    assert int(dut.uio_out.value) & 32
    assert not int(dut.uio_out.value) & 64
    dut.ena.value = 0
    await settle(dut, 12)
    assert int(dut.uio_oe.value) == 0
    # Changing direction during a transaction must not change that operation.
    dut.ui_in.value = 128 | 1
    await settle(dut)
    dut.ena.value = 1
    await settle(dut, 40)
    assert await read_state(dut) == step(INITIAL)
    # Reset during an unfinished operation must restore the documented seed.
    dut.ui_in.value = 128 | 4
    await settle(dut, 8)
    assert int(dut.uio_out.value) & 32
    await reset(dut)
    assert await read_state(dut) == INITIAL
