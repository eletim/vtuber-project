"""Small, standards-ordered PSD writer for named expression folders.

The public tree is TOP FIRST. PSD records are written BOTTOM FIRST, unlike
the historical ``psd_writer.py``. That file is deliberately left unchanged.
Pixel data is 8-bit RGBA, normal blending, full opacity; groups pass through.
Unicode names, nested/hidden folders, ZIP pixel channels and merged RGBA are
supported. The negative layer count marks merged alpha as transparency.

Migration from the historical top-first flat writer::

    old, _ = audit_psd.parse_psd(old_path)
    base = [PixelLayer(r['name'], r['data'], r['visible']) for r in old]
    folders = [LayerGroup('01 smile / 笑顔', [PixelLayer('face', art)], False)]
    write_psd_groups(new_path, neutral_rgba, folders + base)

Folders are not radio buttons: enable ONE expression folder at a time, or
disable every expression folder for neutral. No undocumented layer-comp
metadata is emitted. This module is not a general Photoshop round-tripper.
"""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import struct
from typing import Sequence, Union
import zlib

import numpy as np

try:
    from .psd_writer import packbits
except ImportError:
    from psd_writer import packbits


def _u16(value): return struct.pack('>H', value)
def _i16(value): return struct.pack('>h', value)
def _u32(value): return struct.pack('>I', value)
def _i32(value): return struct.pack('>i', value)


@dataclass
class PixelLayer:
    name: str
    rgba: np.ndarray
    visible: bool = True


@dataclass
class LayerGroup:
    name: str
    children: Sequence['LayerNode']
    visible: bool = True
    expanded: bool = False


LayerNode = Union[PixelLayer, LayerGroup]


def _tag(key: bytes, value: bytes) -> bytes:
    return b'8BIM' + key + _u32(len(value)) + value + b'\0' * (-len(value) % 2)


def _names(name: str) -> bytes:
    if not isinstance(name, str) or not name:
        raise ValueError('Every layer or folder needs a nonempty string name')
    ascii_name = name.encode('ascii', errors='replace')[:255]
    pascal = bytes([len(ascii_name)]) + ascii_name
    pascal += b'\0' * (-len(pascal) % 4)
    unicode_name = name.encode('utf-16-be')
    # Photoshop stores UTF-16 code units, not Python code points.
    return pascal + _tag(b'luni', _u32(len(unicode_name) // 2) + unicode_name)


def _make_record(name, bbox, channels, visible, section=None):
    left, top, right, bottom = bbox
    extra = _u32(0) + _u32(0) + _names(name)
    if section is not None:
        divider = _u32(section)
        if section in (1, 2):
            divider += b'8BIMpass'
        extra += _tag(b'lsct', divider)
    rect = b''.join(_i32(x) for x in (top, left, bottom, right))
    channel_info = _u16(len(channels)) + b''.join(
        _i16(cid) + _u32(len(data)) for cid, data in channels)
    # Group pass-through belongs in lsct; its layer blend key stays normal.
    flags = 0 if visible else 2
    return (rect + channel_info + b'8BIMnorm' + bytes((255, 0, flags, 0))
            + _u32(len(extra)) + extra)


def _flatten(nodes, shape, hidden_names, compression_level):
    """Return record/channel pairs in actual PSD bottom-to-top order."""
    result = []
    for node in reversed(list(nodes)):
        if isinstance(node, tuple) and len(node) == 2:
            node = PixelLayer(*node)
        if isinstance(node, LayerGroup):
            channels = [(cid, _u16(0)) for cid in (-1, 0, 1, 2)]
            result.append((_make_record('</Layer group>', (0, 0, 0, 0),
                                        channels, True, 3), channels))
            result.extend(_flatten(node.children, shape, hidden_names, compression_level))
            result.append((_make_record(node.name, (0, 0, 0, 0), channels,
                                        node.visible and node.name not in hidden_names,
                                        1 if node.expanded else 2), channels))
        elif isinstance(node, PixelLayer):
            rgba = node.rgba
            if not isinstance(rgba, np.ndarray) or rgba.shape != shape or rgba.dtype != np.uint8:
                raise ValueError(f'Invalid RGBA pixel layer: {node.name}')
            ys, xs = np.nonzero(rgba[:, :, 3])
            if len(ys):
                top, left = int(ys.min()), int(xs.min())
                bottom, right = int(ys.max()) + 1, int(xs.max()) + 1
                small = np.ascontiguousarray(rgba[top:bottom, left:right]).copy()
                small[small[:, :, 3] == 0, :3] = 0
            else:
                top = left = 0
                bottom = right = 1
                small = np.zeros((1, 1, 4), dtype=np.uint8)
            channels = [(cid, _u16(2) + zlib.compress(small[:, :, c].tobytes(), compression_level))
                        for cid, c in ((0, 0), (1, 1), (2, 2), (-1, 3))]
            record = _make_record(node.name, (left, top, right, bottom), channels,
                                  node.visible and node.name not in hidden_names)
            result.append((record, channels))
        else:
            raise TypeError(f'Expected PixelLayer, LayerGroup or (name, RGBA), got {type(node)}')
    return result


def write_psd_groups(path, composite, layers, *, hidden_names=(), compression_level=1,
                     merged_rle=True):
    """Write a top-first layer tree without modifying any input array.

    ``composite`` is the exact saved default preview; callers must provide a
    composite matching the visible tree. Both each folder's own visibility
    and its ancestors' visibility apply. Only pixels are cropped, not edited.
    """
    if (not isinstance(composite, np.ndarray) or composite.ndim != 3
            or composite.shape[2] != 4 or composite.dtype != np.uint8):
        raise ValueError('Expected uint8 RGBA composite')
    h, w, _ = composite.shape
    if not (0 < w <= 30000 and 0 < h <= 30000):
        raise ValueError('PSD dimensions must be between 1 and 30000')
    if not 0 <= compression_level <= 9:
        raise ValueError('ZIP compression level must be 0..9')
    pairs = _flatten(layers, composite.shape, set(hidden_names), compression_level)
    if not 0 < len(pairs) <= 32767:
        raise ValueError('Expected between 1 and 32767 PSD layer records')
    info = (_i16(-len(pairs)) + b''.join(record for record, _ in pairs)
            + b''.join(data for _, channels in pairs for _, data in channels))
    info += b'\0' * (len(info) % 2)
    layer_mask = _u32(len(info)) + info + _u32(0)
    header = b'8BPS' + _u16(1) + b'\0' * 6 + _u16(4) + _u32(h) + _u32(w) + _u16(8) + _u16(3)
    if merged_rle:
        rows = [packbits(composite[y, :, c].tobytes()) for c in range(4) for y in range(h)]
        merged = _u16(1) + b''.join(_u16(len(row)) for row in rows) + b''.join(rows)
    else:
        merged = _u16(0) + b''.join(np.ascontiguousarray(composite[:, :, c]).tobytes() for c in range(4))
    Path(path).write_bytes(header + _u32(0) + _u32(0) + _u32(len(layer_mask)) + layer_mask + merged)


class _Reader:
    def __init__(self, data): self.stream = BytesIO(data)
    def get(self, count):
        data = self.stream.read(count)
        if len(data) != count: raise ValueError('Truncated PSD')
        return data
    def u16(self): return struct.unpack('>H', self.get(2))[0]
    def i16(self): return struct.unpack('>h', self.get(2))[0]
    def u32(self): return struct.unpack('>I', self.get(4))[0]


def parse_psd_groups(path):
    """Independently read this writer's subset as a TOP-FIRST layer tree.

    Return ``(tree, (width, height))``. Unlike the historical flat audit this
    parser observes Photoshop record order and folder sections. It rejects
    unsupported blend modes, masks, opacity and clipping rather than silently
    claiming to reproduce arbitrary Photoshop files.
    """
    f = _Reader(Path(path).read_bytes())
    if f.get(4) != b'8BPS' or f.u16() != 1: raise ValueError('Expected version 1 PSD')
    f.get(6)
    channels, h, w, depth, mode = f.u16(), f.u32(), f.u32(), f.u16(), f.u16()
    if (channels, depth, mode) != (4, 8, 3): raise ValueError('Expected 8-bit RGBA PSD')
    f.get(f.u32())  # Color data.
    f.get(f.u32())  # Image resources.
    layer_mask = _Reader(f.get(f.u32()))
    info = _Reader(layer_mask.get(layer_mask.u32()))
    count = abs(info.i16())
    records = []
    for _ in range(count):
        top, left, bottom, right = struct.unpack('>iiii', info.get(16))
        if not (0 <= left <= right <= w and 0 <= top <= bottom <= h):
            raise ValueError('Layer bounds outside canvas')
        ch = [(info.i16(), info.u32()) for _ in range(info.u16())]
        if info.get(4) != b'8BIM' or info.get(4) != b'norm':
            raise ValueError('Unsupported layer signature or blend mode')
        opacity, clipping, flags, _ = info.get(4)
        if opacity != 255 or clipping != 0: raise ValueError('Unsupported opacity or clipping')
        extra = _Reader(info.get(info.u32()))
        if extra.u32() != 0 or extra.u32() != 0: raise ValueError('Unsupported masks or blending ranges')
        name_len = extra.get(1)[0]
        name = extra.get(name_len).decode('ascii', errors='replace')
        extra.get(-(1 + name_len) % 4)
        section = None
        while extra.stream.tell() < len(extra.stream.getbuffer()):
            if extra.get(4) != b'8BIM': raise ValueError('Invalid tagged block signature')
            key, size = extra.get(4), extra.u32()
            data = extra.get(size)
            extra.get(size % 2)
            if key == b'luni':
                length = struct.unpack('>I', data[:4])[0]
                if len(data) < 4 + length * 2: raise ValueError('Invalid Unicode layer name')
                name = data[4:4 + length * 2].decode('utf-16-be')
            elif key == b'lsct':
                section = struct.unpack('>I', data[:4])[0]
                if len(data) >= 12 and data[4:12] != b'8BIMpass':
                    raise ValueError('Only pass-through groups are supported')
        records.append(dict(name=name, visible=not bool(flags & 2), section=section,
                            bbox=(left, top, right, bottom), channels=ch))
    for rec in records:
        left, top, right, bottom = rec['bbox']
        ww, hh = right - left, bottom - top
        rgba = np.zeros((h, w, 4), dtype=np.uint8) if rec['section'] is None else None
        for cid, size in rec.pop('channels'):
            payload = _Reader(info.get(size))
            compression = payload.u16()
            raw = payload.stream.read()
            if compression == 2: raw = zlib.decompress(raw)
            elif compression != 0: raise ValueError('Unsupported pixel compression')
            if len(raw) != ww * hh: raise ValueError('Invalid pixel channel length')
            if rgba is not None:
                if cid not in (0, 1, 2, -1): raise ValueError('Unsupported channel ID')
                rgba[top:bottom, left:right, {-1: 3, 0: 0, 1: 1, 2: 2}[cid]] = (
                    np.frombuffer(raw, np.uint8).reshape(hh, ww))
        rec['rgba'] = rgba
    # A bottom-first section opens with the hidden bounding divider, and
    # closes with the named folder record. Reverse each finished child list.
    stack = [[]]
    for rec in records:
        if rec['section'] == 3:
            stack.append([])
        elif rec['section'] in (1, 2):
            if len(stack) == 1: raise ValueError('Unbalanced PSD folder end')
            children = list(reversed(stack.pop()))
            stack[-1].append(LayerGroup(rec['name'], children, rec['visible'], rec['section'] == 1))
        elif rec['section'] is None:
            stack[-1].append(PixelLayer(rec['name'], rec['rgba'], rec['visible']))
        else:
            raise ValueError('Unsupported section divider')
    if len(stack) != 1: raise ValueError('Unbalanced PSD folder start')
    return list(reversed(stack[0])), (w, h)


def composite_psd_groups(layers, *, hide=(), show=(), size=None):
    """Render normal pixels/pass-through folders honoring parent visibility.

    ``size`` is optional ``(width, height)`` for a tree with no pixel layers.
    ``show`` cannot override a hidden ancestor unless that ancestor is also
    shown. ``hide`` wins over ``show``. Names should be unique for overrides.
    """
    hidden, shown = set(hide), set(show)
    def walk(nodes, parent_visible=True):
        for node in nodes:
            visible = parent_visible and node.name not in hidden and (node.visible or node.name in shown)
            if isinstance(node, LayerGroup):
                yield from walk(node.children, visible)
            else:
                yield node, visible
    flat = list(walk(layers))
    if flat:
        canvas = np.zeros_like(flat[0][0].rgba)
    elif size:
        canvas = np.zeros((size[1], size[0], 4), np.uint8)
    else:
        raise ValueError('Cannot infer canvas size without pixel layers')
    for node, visible in reversed(flat):
        if not visible: continue
        src = node.rgba
        if src.shape != canvas.shape or src.dtype != np.uint8: raise ValueError('Invalid layer shape/dtype')
        alpha = src[:, :, 3]
        opaque, partial = alpha == 255, (alpha > 0) & (alpha < 255)
        canvas[opaque] = src[opaque]
        if partial.any():
            sa = src[partial, 3:4].astype(np.float64) / 255
            da = canvas[partial, 3:4].astype(np.float64) / 255
            outa = sa + da * (1 - sa)
            color = (src[partial, :3] * sa + canvas[partial, :3] * da * (1 - sa)) / outa
            canvas[partial, :3] = np.rint(color).clip(0, 255).astype(np.uint8)
            canvas[partial, 3] = np.rint(outa[:, 0] * 255).clip(0, 255).astype(np.uint8)
    return canvas
