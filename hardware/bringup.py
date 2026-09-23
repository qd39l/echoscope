"""MicroPython diagnostic bring-up for an already selected EchoScope project.

Uses the Tiny Tapeout Demo Board API. Not yet qualified on fabricated silicon.
"""

class EchoScope:
    def __init__(self, tt):
        self.tt = tt
        from ttboard.mode import RPMode
        tt.mode = RPMode.ASIC_RP_CONTROL
        tt.clock_project_stop()
        tt.uio_oe_pico.value = 0x1f  # RP drives only cell/address inputs
        tt.uio_in.value = 16
        tt.ui_in.value = 0x80
        tt.reset_project(True)
        self.clocks()
        tt.reset_project(False)
        self.clocks(40)  # 32 startup shifts, then synchronization margin

    def clocks(self, n=6):
        # SDK's clock_project_once toggles twice from the current level.
        # Establish a low starting level so each read follows a falling edge.
        self.tt.clock_project_stop()
        self.tt.pins.project_clk_driven_by_RP2(True)
        self.tt.clk(0)
        for _ in range(n):
            self.tt.clock_project_once()

    def command(self, bit, reverse=False, cell=16):
        base = 0x80 | int(reverse)
        self.tt.uio_in.value = cell & 31
        self.tt.ui_in.value = base
        self.clocks()
        self.tt.ui_in.value = base | (1 << bit)
        self.clocks()
        self.tt.ui_in.value = base
        self.clocks(40)

    def step(self, reverse=False):
        self.command(2, reverse=reverse)

    def perturb(self, cell=16):
        self.command(3, cell=cell)

    def clone(self):
        self.command(4)

    def read_state(self):
        self.clocks(40)
        base = int(self.tt.ui_in.value) & ~32
        self.tt.ui_in.value = base
        self.clocks()
        self.tt.ui_in.value = base | 32
        for _ in range(8):
            self.clocks(1)
            if int(self.tt.uio_out.value) & 32:
                break
        else:
            raise RuntimeError('Scan not accepted')
        words = [0, 0, 0, 0]
        for bit in range(32):
            pins = int(self.tt.uo_out.value)
            for plane in range(4):
                words[plane] |= ((pins >> plane) & 1) << bit
            self.clocks(1)
        assert not int(self.tt.uio_out.value) & 32
        self.tt.ui_in.value = base
        self.clocks()
        return tuple(words)

    def self_test(self, steps=256):
        initial = self.read_state()
        for _ in range(steps):
            self.step()
        for _ in range(steps):
            self.step(reverse=True)
        assert self.read_state() == initial, 'Forward/reverse round trip failed'
        self.clone()
        same = self.read_state()
        assert same[:2] == same[2:], 'Clone failed'
        self.perturb(31)
        changed = self.read_state()
        assert changed[:3] == same[:3]
        assert changed[3] == same[3] ^ (1 << 31), 'Perturb failed'
        self.perturb(31)
        assert self.read_state() == same, 'Double perturb failed'
        return True

    def start_video(self, paused=False, muted=True):
        self.tt.clock_project_stop()
        self.tt.ui_in.value = (2 if paused else 0) | (64 if muted else 0)
        self.tt.uio_in.value = 16
        self.tt.reset_project(True)
        self.clocks()
        self.tt.reset_project(False)
        self.tt.clock_project_PWM(25_000_000)
