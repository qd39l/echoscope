# Board bring-up

`bringup.py` uses the same public pin protocol as the cocotb and gate-level
tests. It is a proposed Tiny Tapeout Demo Board MicroPython driver; it has not
been run on fabricated EchoScope silicon or an FPGA board.

After selecting the EchoScope project in the demo-board firmware:

```python
from hardware.bringup import EchoScope
scope = EchoScope(tt)
scope.read_state()  # (0, 32768, 0, 98304)
scope.self_test()   # exact 256-step round trip, clone, and double flip
scope.start_video(paused=True, muted=True)
```

Wire the Tiny VGA Pmod to the output connector. Optionally wire TT Audio Pmod
to uio[7]. The RP must drive only uio[0:4]; uio[5:7] are chip outputs and must
never be driven by the RP. uio[5] is BUSY. The `uio_oe_pico=0x1f`
setting in the driver enforces those directions. Set all `ui_in` controls to
defined levels; their descriptions and timing contract are in `docs/info.md`.

In video mode, wait at least 34 ms after each control transition. Pause before
single-stepping; otherwise an extra automatic advance occurs on release.
Use a logic analyzer to check 800 clocks per line, 525 lines per frame, a
96-clock negative HSYNC, and two-line negative VSYNC. Frequency at 25 MHz:
31.25 kHz line rate and 59.5238 Hz frame rate. Some monitors may prefer the
nominal 25.175 MHz pixel clock, but this design's verified timing target is
25 MHz. Do not claim a higher clock without checking timing and hardware.

The manual clock interface is intentionally slow; video mode uses the board's
continuous PWM clock. Reset must overlap at least six input-clock edges and
be released away from a rising edge. The controller resets synchronously,
then loads the state bank serially for 32 clocks. Wait for this startup interval
before issuing commands. The manual driver changes reset with the clock low
and waits 40 clocks after release.
Project selection/shuttle allocation is deliberately left to the board setup;
there is no fabricated project index to hard-code yet.

The clock/reset calls were checked against the
[official SDK source](https://github.com/TinyTapeout/tt-micropython-firmware/blob/main/src/ttboard/demoboard.py).
The driver explicitly starts manual pulses low because `clock_project_once`
toggles twice from the current level. Board setup and RP pin directions follow
the [Tiny Tapeout demo-board guide](https://tinytapeout.com/guides/get-started-demoboard/).
