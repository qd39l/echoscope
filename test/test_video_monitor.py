"""Fault injection proves the independent VGA sink rejects malformed signals."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from video_monitor import FRAME, LINE, Monitor, SYNC, VideoFrame, compare, expected_image
from model import INITIAL


def locked_monitor():
    monitor=Monitor()
    assert len(monitor.feed(SYNC*2)) == 1
    return monitor


def test_acquisition_across_arbitrary_chunks():
    monitor=Monitor()
    stream=bytes([0x88])*137 + SYNC*3
    frames=[]
    for i in range(0,len(stream),7919):
        frames.extend(monitor.feed(stream[i:i+7919]))
    assert len(frames)==2
    assert all(frame.pins==SYNC for frame in frames)


@pytest.mark.parametrize('fault', ['hs_short','hs_extra','vs_short','wrong_polarity',
                                  'blank_rgb','lost_clock','extra_clock'])
def test_rejects_signal_faults(fault):
    damaged=bytearray(SYNC)
    if fault=='hs_short': damaged[656] |= 128
    elif fault=='hs_extra': damaged[123] &= ~128
    elif fault=='vs_short': damaged[490*LINE] |= 8
    elif fault=='wrong_polarity': damaged=bytearray(x^128 for x in damaged)
    elif fault=='blank_rgb': damaged[640] |= 1
    elif fault=='lost_clock': del damaged[700]
    elif fault=='extra_clock': damaged.insert(700,damaged[700])
    with pytest.raises(AssertionError):
        locked_monitor().feed(damaged+SYNC)


def test_missing_sync_times_out():
    with pytest.raises(AssertionError,match='acquire'):
        Monitor().feed(bytes([0x88])*(2*FRAME+1))


def test_image_oracle_rejects_color_and_alignment_errors():
    image=expected_image(INITIAL)
    pixels=image.tobytes()
    pins=bytearray(SYNC)
    for y in range(480):
        for x in range(640):
            r,g,b=(v//85 for v in pixels[(y*640+x)*3:(y*640+x+1)*3])
            pins[y*LINE+x] |= ((r>>1)|((g>>1)<<1)|((b>>1)<<2)|
                               ((r&1)<<4)|((g&1)<<5)|((b&1)<<6))
    compare(VideoFrame(bytes(pins)),image)
    swapped=bytes((v&~0x33)|((v&0x11)<<1)|((v&0x22)>>1) for v in pins)
    delayed=bytes((pins[i]&0x88)|(pins[i-1]&0x77) for i in range(FRAME))
    for damaged in (swapped,delayed):
        with pytest.raises(AssertionError,match='image mismatch'):
            compare(VideoFrame(damaged),image)
