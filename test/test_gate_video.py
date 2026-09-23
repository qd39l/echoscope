"""Sparse full-frame VGA checks using only package pins, also after synthesis."""
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer
from test import reset
from model import INITIAL, step


@cocotb.test()
async def video_pins_after_synthesis(dut):
    cocotb.start_soon(Clock(dut.clk, 40, unit='ns').start())
    await reset(dut, diagnostic=False, controls=2 | 64)
    # reset() waits for initialization, then six active rising edges. Registered video
    # at that falling edge belongs to pixel 5. Sample a whole frame's landmarks.
    points = {(0,y) for y in range(1,526)}
    for y in range(525):
        if y % 8 == 0 or y in (479,480,489,490,491,492,524):
            for x in (65,305,321,561,639,640,655,656,751,752,799):
                points.add((x,y))
    # Check every displayed cell in the next frame's first two generations.
    # This observes restoration of both present and past through package pins.
    for y in (525, 533):
        for cell in range(32):
            points.add((65 + 16 * cell, y))
    elapsed = 6
    states = [INITIAL]
    for _ in range(59): states.append(step(states[-1]))
    for x,y in sorted(points,key=lambda p:p[1]*800+p[0]):
        target = y*800+x+1
        await Timer((target-elapsed)*40,unit='ns')
        elapsed = target
        out = int(dut.uo_out.value)
        vy = y % 525
        assert bool(out&128) == (not 656 <= x < 752),(x,y,'hs')
        assert bool(out&8) == (not 490 <= vy < 492),(x,y,'vs')
        rgb = out & 0x77
        if x >= 640 or vy >= 480:
            assert rgb == 0,(x,y,'blank')
        elif 64 <= x < 576:
            cell=(x-64)//16
            a=(states[vy//8][1]>>cell)&1;b=(states[vy//8][3]>>cell)&1
            expected=0x40 if (x%16 == 0 or vy%8==7) else (b*0x11+a*0x22+(a|b)*0x44)
            assert rgb == expected,(x,y,rgb,expected)
        assert int(dut.uio_oe.value) == 0xe0
        assert not int(dut.uio_out.value)&128
