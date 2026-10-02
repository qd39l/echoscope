"""640x480 digital VGA sink. Reads package pins, never DUT coordinates/state.

The source clock is supplied to this digital model; a real VGA monitor instead
recovers its sampling clock. This does not model analog levels or monitor PLLs.
"""
from dataclasses import dataclass
from PIL import Image, ImageDraw
from model import step

WIDTH, HEIGHT, LINE, LINES = 640, 480, 800, 525
FRAME = LINE * LINES
SYNC = bytes(((0 if 656 <= x < 752 else 128) | (0 if 490 <= y < 492 else 8))
             for y in range(LINES) for x in range(LINE))
SYNC_LUT = bytes(i & 0x88 for i in range(256))
RGB_LUT = bytes(i & 0x77 for i in range(256))
VS_LUT = bytes(bool(i & 8) for i in range(256))
CHANNELS = [bytes((((i >> hi) & 1)*2 + ((i >> lo) & 1))*85 for i in range(256))
            for hi, lo in ((0, 4), (1, 5), (2, 6))]

@dataclass
class VideoFrame:
    pins: bytes

    def rgb(self):
        visible = b''.join(self.pins[y*LINE:y*LINE+WIDTH] for y in range(HEIGHT))
        rgb = bytearray(WIDTH*HEIGHT*3)
        for channel, lut in enumerate(CHANNELS):
            rgb[channel::3] = visible.translate(lut)
        return bytes(rgb)

    def image(self):
        return Image.frombytes('RGB', (WIDTH, HEIGHT), self.rgb())

class Monitor:
    def __init__(self):
        self.reset()

    def reset(self):
        self.buffer = bytearray()
        self.skip = None
        self.locked = False
        self.frames = 0
        self.acquisition_samples = 0

    def feed(self, samples):
        self.buffer.extend(samples)
        frames = []
        if self.skip is None:
            self.acquisition_samples += len(samples)
            edge = bytes(self.buffer).translate(VS_LUT).find(b'\x00\x01')
            if edge < 0:
                if self.acquisition_samples > 2*FRAME:
                    raise AssertionError('VGA receiver could not acquire VSYNC within two frames')
                # Retain one byte to detect an edge across feed() calls.
                self.buffer[:] = self.buffer[-1:]
                return frames
            # Rising VSYNC is line 492, followed by 33 back-porch lines.
            self.skip = edge + 1 + 33*LINE
        if not self.locked:
            if len(self.buffer) < self.skip:
                return frames
            del self.buffer[:self.skip]
            self.locked = True
        while len(self.buffer) >= FRAME:
            pins = bytes(self.buffer[:FRAME])
            del self.buffer[:FRAME]
            actual = pins.translate(SYNC_LUT)
            if actual != SYNC:
                pos = next(i for i, (a, b) in enumerate(zip(actual, SYNC)) if a != b)
                raise AssertionError(f'VGA sync mismatch at x={pos%LINE}, y={pos//LINE}')
            rgb = pins.translate(RGB_LUT)
            for y in range(LINES):
                blank = rgb[y*LINE+(WIDTH if y < HEIGHT else 0):(y+1)*LINE]
                if any(blank):
                    raise AssertionError(f'RGB nonzero during blanking on line {y}')
            frames.append(VideoFrame(pins))
            self.frames += 1
        return frames


def expected_image(state, epoch=0, paused=True, reverse=False, difference=False):
    """Independent image oracle: draw rectangles from the scalar world model."""
    image = Image.new('RGB', (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(image)
    distance = (state[1] ^ state[3]).bit_count()
    rail = (255 if reverse else 0, 0 if reverse else 255, 255 if paused else 0)
    for x in (56, 580):
        draw.rectangle((x, 0, x+3, HEIGHT-1), fill=rail)
    for bit in range(16):
        if epoch & (1 << bit):
            draw.rectangle((24, bit*16, 39, bit*16+11), fill=(170,170,170))
    if distance:
        draw.rectangle((600, 0, 615, distance*8-1), fill=(255,85,0))
    for row in range(60):
        for cell in range(32):
            a, b = (state[1] >> cell) & 1, (state[3] >> cell) & 1
            color = ((255,170,85) if a != b else (0,0,0)) if difference else (b*255,a*255,(a|b)*255)
            x, y = 64+cell*16, row*8
            draw.rectangle((x,y,x+15,y+7), fill=(0,0,85))
            draw.rectangle((x+1,y,x+15,y+6), fill=color)
        state = step(state)
    return image


def compare(frame, expected, output=None):
    actual = frame.image()
    if actual.tobytes() != expected.tobytes():
        from PIL import ImageChops
        if output is not None:
            output.mkdir(parents=True, exist_ok=True)
            actual.save(output/'actual.png')
            expected.save(output/'expected.png')
            ImageChops.difference(actual,expected).save(output/'difference.png')
        raise AssertionError(f'VGA image mismatch; difference bounds: {ImageChops.difference(actual,expected).getbbox()}')
