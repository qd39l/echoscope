## How it works

EchoScope is a butterfly-effect time machine. Two 32-cell worlds obey the
same reversible, second-order Rule 30. They start one bit apart. Cyan means
only world A is alive, magenta means only B, white means both, and black means
neither. An alternate amber view shows only disagreement.

The chip generates a 640x480 VGA picture containing 60 successive generations.
It borrows its own simulation state to draw those generations, then reverses
59 updates (32 clocks each) in vertical blanking to recover the starting point. There is no
framebuffer, history RAM, CPU, external memory, or software in the pixel path.
The worlds need only 128 state bits, regardless of how far you rewind.
Each displayed cell is read from a fixed serial output. The four state planes
rotate once per 16-pixel cell and return to their original ordering after
32 cells, eliminating wide pixel-selection multiplexers.

For each world, let P be the past and C the present. On a periodic ring,
F(C)[i] = C[i-1] XOR (C[i] OR C[i+1]). Forward evolution is
(P,C) -> (C,F(C) XOR P). Reverse evolution is
(P,C) -> (F(P) XOR C,P). This is exact mathematical reversibility of the
simulation, not a claim about thermodynamically reversible CMOS.

Reverse reconstructs earlier states under the same rule. A bit flip changes
the trajectory, including its reconstructed past; reversing does not undo an
intervention. Flipping the same cell twice at the same generation cancels it.
Cloning A into B is deliberately irreversible.

The left ruler displays the generation counter in binary (LSB at top, modulo
65536). The right meter shows how many present cells disagree at the top of
the picture. Rail colour shows forward (green), reverse (red), or adds blue
when paused. Audio maps disagreement into a C-major pentatonic scale.

## How to test

Supply a 25 MHz clock, hold reset low for at least six clocks, then release it
away from a rising clock edge (a falling edge is convenient).
Allow 32 more clocks for serial initialization before sending commands.
During initialization, RGB is black, sync is high, audio and equality are low,
and BUSY is high when ena is high. Initialization runs even while ena is low;
the external outputs remain disabled in that case.
Keep ui[7] low during reset for VGA mode. The design starts running with a
single-bit difference already injected. Inputs are active high:

| Input | Function |
| --- | --- |
| ui[0] | Reverse time |
| ui[1] | Pause animation |
| ui[2] | Single step on rising edge, including while paused |
| ui[3] | Flip world B's selected present cell on rising edge |
| ui[4] | Clone both state planes of A into B on rising edge |
| ui[5] | Show differences only / diagnostic scan |
| ui[6] | Mute audio |
| ui[7] | Diagnostic mode; sampled only while reset is low |
| uio[4:0] | Perturbation cell index, 0..31 |

Controls are synchronized, then sampled once per frame. Hold button levels
and the cell index stable for at least two frames (34 ms); provide external
debouncing for mechanical switches. Release a button for two frames before
the next press. Commands prioritize clone, then flip, then step; a clone or
flip consumes that frame's normal animation step. Toggling pause, reverse,
view, or mute does not erase either world. Reset restarts the experiment.

VGA refresh continues in hardware while paused. Pausing holds the canonical
world state, so subsequent frames repeat the same picture. Single steps and
interventions are accepted during vertical blanking and affect the next
complete picture. Automatic mode advances once per frame (59.524 steps/s);
there is no programmable animation-speed divider. For slower evolution, hold
pause high and pulse single-step from a host at the desired rate, respecting
the two-frame high/low protocol. Use pause, not `ena`, to hold a stable display:
deasserting `ena` intentionally stops the raster and drives sync inactive.

To demonstrate reversal: pause, make N forward steps, then N reverse steps.
The picture returns exactly. To see a butterfly effect: clone, flip a cell,
then single-step. The discrepancy expands through the two worlds.

Diagnostic mode replaces VGA with a four-lane serial scan. Select it by holding
ui[7] high during reset. ui[2], ui[3], ui[4] trigger step, flip, and clone;
ui[0] chooses step direction. Hold command high and low levels for at least
six clocks, and wait until uio[5] (BUSY) is low before a new command. An
accepted operation takes 32 processing clocks. Edges while busy are ignored.
For a simple conservative host, allow 40 clocks after each command. Commands
are latched at acceptance; changing direction or cell address during busy
cannot alter an in-progress operation.

To read all 128 state bits without changing them:

1. Ensure BUSY is low and raise ui[5] after holding it low for six clocks.
2. On the falling clock edge where BUSY first becomes high, capture uo[3:0].
   These are bit 0 of A past, A present, B past, B present, respectively.
3. Capture the next 31 falling edges for bits 1..31, least significant bit
   first. Each processing clock rotates the four state planes by one bit.
4. One more clock completes the 32nd rotation; BUSY falls and the original
   state is restored exactly. Lower ui[5] for six clocks before another scan.

uo[7:4] are zero in diagnostic mode. uio[4:0] select the perturbation cell and
are not a read address. uio[6] indicates equality of BOTH state planes when
BUSY is low and is forced low during a transaction. In video mode BUSY also
exposes the scan's internal work, and equality refers to its latest completed
row. Audio is disabled in diagnostic mode. Return to VGA using reset with
ui[7] low. The diagnostic priority is clone, flip, step, then scan.

The design requires ena high for operation. When ena is low, state is held,
the bidirectional pins are released, RGB is black, and sync outputs are high.
Reset takes priority over ena. Control logic resets synchronously and starts
a 32-clock seed-loading sequence. The 128 world-state flops have no reset pins;
their clock gate opens for initialization, and their contents are hidden until
all bits have been written. A reset during initialization restarts that sequence.
Keep mode and controls stable around reset and wait for startup to complete.

## External hardware

A Tiny Tapeout demo board, a Tiny VGA Pmod on the output connector, and a VGA
monitor accepting 640x480 at 59.524 Hz (25 MHz pixel clock). Timing totals are
800x525; HSYNC is low at pixels 656..751, VSYNC at lines 490..491. All RGB and
sync outputs share one registered pixel delay.

Optionally connect a TT Audio Pmod to uio[7]. Use its amplifier or an AC-coupled
high-impedance audio input; GPIO is not a headphone driver. Ground unused input
pins or configure the demo board to drive them. uio[0:4] are inputs, uio[5:7] are outputs while ena is high. Do not drive those
three pins from the demo board.

Pins follow the Tiny Tapeout common Tiny VGA and mono audio mapping.
