"""Write named 8-bit RGBA Photoshop PSD layers using ZIP-compressed channels."""
import struct
import zlib
from pathlib import Path
import numpy as np

def u16(n): return struct.pack(">H", n)
def i16(n): return struct.pack(">h", n)
def u32(n): return struct.pack(">I", n)
def i32(n): return struct.pack(">i", n)

def layer_name(name):
    b = name.encode("ascii", errors="replace")[:255]
    val = bytes([len(b)]) + b
    return val + b"\x00" * (-len(val) % 4)

def packbits(row):
    """Photoshop PackBits row: literal spans and runs, each at most 128 bytes."""
    output = bytearray()
    i = 0
    while i < len(row):
        end = i + 1
        while end < min(i + 128, len(row)) and row[end] == row[i]:
            end += 1
        if end - i >= 3:
            output.extend((257 - (end - i), row[i]))
            i = end
            continue
        start = i
        i = end
        while i < len(row) and i - start < 128:
            if i + 2 < len(row) and row[i] == row[i+1] == row[i+2]:
                break
            i += 1
        output.append(i - start - 1)
        output.extend(row[start:i])
    return bytes(output)


def write_psd(path, composite, layers, *, hidden_names=(), compression_level=1, merged_rle=False):
    """RGBA uint8 canvas plus (name, RGBA uint8 canvas) layers, top first."""
    h, w, channel_count = composite.shape
    if channel_count != 4 or composite.dtype != np.uint8:
        raise ValueError("Expected uint8 RGBA composite")
    hidden = set(hidden_names)
    records, payloads = [], []
    for name, layer in layers:
        if layer.shape != composite.shape or layer.dtype != np.uint8:
            raise ValueError(f"Invalid layer: {name}")
        ys, xs = np.nonzero(layer[:, :, 3])
        if not len(ys):
            top = left = 0
            bottom = right = 1
            small = np.zeros((1, 1, 4), dtype=np.uint8)
        else:
            top, left, bottom, right = int(ys.min()), int(xs.min()), int(ys.max()+1), int(xs.max()+1)
            small = np.ascontiguousarray(layer[top:bottom, left:right]).copy()
            small[small[:, :, 3] == 0, :3] = 0
        data = [u16(2) + zlib.compress(small[:, :, c].tobytes(), compression_level) for c in range(4)]
        rect = b"".join(map(i32, (top, left, bottom, right)))
        channels = u16(4) + b"".join(i16(i) + u32(len(d)) for i, d in zip((0, 1, 2, -1), data))
        extra = u32(0) + u32(0) + layer_name(name)
        records.append(rect + channels + b"8BIMnorm" + bytes((255, 0, 2 if name in hidden else 0, 0)) + u32(len(extra)) + extra)
        payloads.extend(data)
    layer_info = i16(len(layers)) + b"".join(records) + b"".join(payloads)
    if len(layer_info) % 2:
        layer_info += b"\x00"
    layer_mask = u32(len(layer_info)) + layer_info + u32(0)
    header = b"8BPS" + u16(1) + b"\x00"*6 + u16(4) + u32(h) + u32(w) + u16(8) + u16(3)
    # Raw planar merged RGBA for interoperability with image viewers.
    if merged_rle:
        rows = [packbits(composite[y, :, c].tobytes()) for c in range(4) for y in range(h)]
        merged = u16(1) + b''.join(u16(len(row)) for row in rows) + b''.join(rows)
    else:
        merged = u16(0) + b"".join(np.ascontiguousarray(composite[:,:,c]).tobytes() for c in range(4))
    Path(path).write_bytes(header + u32(0) + u32(0) + u32(len(layer_mask)) + layer_mask + merged)
