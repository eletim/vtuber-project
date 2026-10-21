#!/usr/bin/env python3
"""Patch only the approved surprised-mouth skin RGB, without PSD round-tripping.

The image-tool artwork is prepared and reviewed separately. This script never
paints, smooths, changes geometry, or infers which lip pixels may be changed.
A frozen RGBA sprite and an explicit protected-lip mask are required. By default
it validates in memory; --apply writes only the new PSD, versioned PNG and manifest.
The v15 source PSD, all other PNGs, and delivered v16 artifacts remain intact.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import struct
import tempfile
import zlib

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BASELINE = '78ede7b'
SOURCE = ROOT / 'assets/parts/v15/koma_expression_motion_v15.psd'
SOURCE_SHA256 = 'aeedcf0e025b7d18f61586be3e070b12987be9890c01bec26475677b300a3c10'
OUT = ROOT / 'assets/parts/v17'
PSD = OUT / 'koma_expression_skin_v17.psd'
MODEL = ROOT / 'runtime/model'
MANIFEST = MODEL / 'model.json'
ORIGINAL_SPRITE = MODEL / 'expressions/surprised/mouth_closed.png'
SPRITE = MODEL / 'expressions/surprised/mouth_closed_skin_v17.png'
CANDIDATE = OUT / 'sources/surprised_mouth_closed.png'
PROTECTED_MASK = OUT / 'sources/protected_lip_mask.png'
TARGET = 'surprised.mouth.closed'
TARGET_RECT = (510, 321, 601, 390)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


@dataclass(frozen=True)
class Channel:
    channel_id: int
    length_offset: int  # Within its original layer record.
    payload: bytes


@dataclass(frozen=True)
class Record:
    name: str
    bbox: tuple[int, int, int, int]
    visible: bool
    section: int | None
    raw: bytes
    channels: tuple[Channel, ...]

    def metadata_bytes(self):
        """Original record, excluding only the mutable channel byte lengths."""
        raw = bytearray(self.raw)
        for channel in self.channels:
            struct.pack_into('>I', raw, channel.length_offset, 0)
        return bytes(raw)


@dataclass(frozen=True)
class Document:
    data: bytes
    size: tuple[int, int]
    mask_length_offset: int
    mask_end: int
    info_start: int
    info_end: int
    signed_count: int
    records: tuple[Record, ...]
    record_data_end: int
    pixel_data_end: int

    def named(self, name):
        found = [record for record in self.records if record.name == name]
        require(len(found) == 1, f'Expected exactly one PSD layer named {name!r}')
        return found[0]


def inspect_psd(data: bytes) -> Document:
    """Read original record/channel bytes and folder tags, without reencoding.

    This deliberately supports only this project's 8-bit RGBA PSD subset.
    Unsupported/truncated files fail before any writes happen.
    """
    require(len(data) >= 26 and data[:6] == b'8BPS\0\1', 'Expected version 1 PSD')
    channels, height, width, depth, mode = struct.unpack_from('>HIIHH', data, 12)
    require((channels, depth, mode) == (4, 8, 3), 'Expected 8-bit RGBA PSD')
    pos = 26

    def u32(offset):
        require(0 <= offset <= len(data)-4, 'Truncated PSD length')
        return struct.unpack_from('>I', data, offset)[0]

    for _ in range(2):  # Color-mode data and image resources.
        pos += 4 + u32(pos)
    mask_offset = pos
    mask_end = pos + 4 + u32(pos)
    require(mask_end <= len(data), 'Truncated PSD layer/mask data')
    info_start = pos + 8
    info_end = info_start + u32(pos+4)
    require(info_start+2 <= info_end <= mask_end, 'Invalid PSD layer-info length')
    signed_count = struct.unpack_from('>h', data, info_start)[0]
    require(signed_count != 0, 'PSD has no layers')
    pos = info_start + 2
    pending = []
    for _ in range(abs(signed_count)):
        start = pos
        require(pos+18 <= info_end, 'Truncated PSD layer record')
        top, left, bottom, right, count = struct.unpack_from('>iiiiH', data, pos)
        require(0 <= left <= right <= width and 0 <= top <= bottom <= height,
                'Layer bounds outside canvas')
        pos += 18
        require(pos+count*6+16 <= info_end, 'Truncated PSD channel metadata')
        channel_info = []
        for _ in range(count):
            channel_id, length = struct.unpack_from('>hI', data, pos)
            require(channel_id in (0, 1, 2, -1), 'Unsupported PSD channel')
            channel_info.append((channel_id, pos+2-start, length))
            pos += 6
        require(data[pos:pos+8] == b'8BIMnorm', 'Unsupported PSD blend mode')
        opacity, clipping, flags, _ = data[pos+8:pos+12]
        require(opacity == 255 and clipping == 0, 'Unsupported PSD opacity/clipping')
        extra_end = pos+16+u32(pos+12)
        pos += 16
        require(extra_end <= info_end, 'Truncated PSD layer metadata')
        require(u32(pos) == 0 and u32(pos+4) == 0, 'Unsupported PSD layer mask/ranges')
        pos += 8
        name_length = data[pos]
        name = data[pos+1:pos+1+name_length].decode('ascii', errors='replace')
        pos += (name_length+1+3)//4*4
        section = None
        while pos < extra_end:
            require(pos+12 <= extra_end and data[pos:pos+4] == b'8BIM', 'Invalid PSD tagged block')
            key, length = data[pos+4:pos+8], u32(pos+8)
            value = data[pos+12:pos+12+length]
            require(pos+12+length <= extra_end, 'Truncated PSD tagged block')
            if key == b'luni':
                require(length >= 4, 'Invalid PSD Unicode name')
                units = struct.unpack_from('>I', value)[0]
                require(4+units*2 <= length, 'Truncated PSD Unicode name')
                name = value[4:4+units*2].decode('utf-16-be')
            elif key == b'lsct':
                require(length >= 4, 'Invalid PSD folder section')
                section = struct.unpack_from('>I', value)[0]
                require(section in (1, 2, 3), 'Unsupported PSD folder section')
                require(length < 12 or value[4:12] == b'8BIMpass', 'Unsupported PSD folder blend')
            pos += 12+length+(length % 2)
        require(pos == extra_end, 'Invalid PSD layer metadata padding')
        pending.append((name, (left, top, right, bottom), not bool(flags & 2),
                        section, data[start:pos], channel_info))
    record_data_end = pos
    records = []
    for name, bbox, visible, section, raw, channel_info in pending:
        payloads = []
        require(len({cid for cid, _, _ in channel_info}) == len(channel_info), 'Duplicate PSD channel')
        for channel_id, length_offset, length in channel_info:
            require(length >= 2 and pos+length <= info_end, 'Truncated PSD pixel channel')
            payloads.append(Channel(channel_id, length_offset, data[pos:pos+length]))
            pos += length
        records.append(Record(name, bbox, visible, section, raw, tuple(payloads)))
    require(info_end-pos in (0, 1) and not any(data[pos:info_end]), 'Unexpected PSD layer-info suffix')
    document = Document(data, (width, height), mask_offset, mask_end, info_start,
                        info_end, signed_count, tuple(records), record_data_end, pos)
    tree_signature(document)  # Reject unbalanced folders before patching.
    return document


def tree_signature(document: Document):
    """Nested metadata-only top-first tree, preserving names and visibility."""
    stack = [[]]
    for record in document.records:
        if record.section == 3:
            stack.append([])
        elif record.section in (1, 2):
            require(len(stack) > 1, 'Unbalanced PSD folder end')
            children = tuple(reversed(stack.pop()))
            stack[-1].append(('group', record.name, record.visible, record.section == 1, children))
        else:
            stack[-1].append(('pixel', record.name, record.visible, record.bbox))
    require(len(stack) == 1, 'Unbalanced PSD folder start')
    return tuple(reversed(stack[0]))


def decode_record(record: Record):
    left, top, right, bottom = record.bbox
    width, height = right-left, bottom-top
    result = np.zeros((height, width, 4), dtype=np.uint8)
    require({c.channel_id for c in record.channels} == {-1, 0, 1, 2}, 'Expected four RGBA channels')
    for channel in record.channels:
        compression = struct.unpack_from('>H', channel.payload)[0]
        require(compression in (0, 2), 'Unsupported PSD channel compression')
        raw = zlib.decompress(channel.payload[2:]) if compression == 2 else channel.payload[2:]
        require(len(raw) == height*width, 'Invalid PSD decompressed channel length')
        result[:, :, {-1: 3, 0: 0, 1: 1, 2: 2}[channel.channel_id]] = np.frombuffer(raw, np.uint8).reshape(height, width)
    return result


def validate_candidate(original, candidate, protected):
    require(candidate.dtype == np.uint8 and candidate.shape == original.shape, 'Candidate must have exactly the original RGBA dimensions')
    require(protected.shape == original.shape[:2] and protected.dtype == np.bool_, 'Protected mask dimensions/type mismatch')
    require(bool(protected.any()), 'Protected lip mask must not be empty')
    require(np.array_equal(candidate[:, :, 3], original[:, :, 3]), 'Candidate changes original alpha')
    require(np.array_equal(candidate[protected], original[protected]), 'Candidate changes protected lip RGBA pixels')
    transparent = original[:, :, 3] == 0
    require(np.array_equal(candidate[transparent], original[transparent]), 'Candidate changes transparent pixels')
    changed = np.any(candidate[:, :, :3] != original[:, :, :3], axis=2)
    require(bool(changed.any()), 'Candidate contains no RGB correction')
    return {'changed_rgb_pixels': int(changed.sum()), 'protected_lip_pixels': int(protected.sum()),
            'protected_lip_changes': 0, 'alpha_changes': 0, 'transparent_pixel_changes': 0}


def patch_psd(source: bytes, candidate, protected, *, target=TARGET):
    """Return surgically patched bytes plus validation; no filesystem writes."""
    document = inspect_psd(source)
    layer = document.named(target)
    require(layer.section is None, 'Target must be a pixel layer')
    measurements = validate_candidate(decode_record(layer), candidate, protected)
    record_bytes, payload_bytes = [], []
    for record in document.records:
        raw = bytearray(record.raw)
        for channel in record.channels:
            payload = channel.payload
            if record is layer and channel.channel_id in (0, 1, 2):
                payload = b'\0\2' + zlib.compress(candidate[:, :, channel.channel_id].tobytes(), 9)
                struct.pack_into('>I', raw, channel.length_offset, len(payload))
            payload_bytes.append(payload)
        record_bytes.append(bytes(raw))
    info = struct.pack('>h', document.signed_count) + b''.join(record_bytes) + b''.join(payload_bytes)
    info += b'\0'*(len(info) % 2)
    mask = struct.pack('>I', len(info)) + info + source[document.info_end:document.mask_end]
    result = (source[:document.mask_length_offset] + struct.pack('>I', len(mask)) + mask
              + source[document.mask_end:])
    measurements.update(verify_patch(source, result, candidate, protected, target=target))
    return result, measurements


def verify_patch(source: bytes, result: bytes, candidate, protected, *, target=TARGET):
    before, after = inspect_psd(source), inspect_psd(result)
    require(before.size == after.size and before.signed_count == after.signed_count, 'PSD canvas/layer count changed')
    require(tree_signature(before) == tree_signature(after), 'PSD folder tree or layer metadata changed')
    require(source[:before.mask_length_offset] == result[:after.mask_length_offset], 'PSD header/resources changed')
    require(source[before.info_end:before.mask_end] == result[after.info_end:after.mask_end], 'Global layer-mask data changed')
    require(source[before.mask_end:] == result[after.mask_end:], 'Saved neutral merged preview changed')
    unchanged = 0
    for old, new in zip(before.records, after.records):
        require(old.metadata_bytes() == new.metadata_bytes(), f'Layer metadata changed: {old.name}')
        require([c.channel_id for c in old.channels] == [c.channel_id for c in new.channels], 'Channel order changed')
        for old_channel, new_channel in zip(old.channels, new.channels):
            if old.name == target and old_channel.channel_id in (0, 1, 2):
                continue
            require(old_channel.payload == new_channel.payload, f'Preserved channel changed: {old.name}/{old_channel.channel_id}')
        if old.name != target:
            require(old.raw == new.raw, f'Preserved layer record changed: {old.name}')
            unchanged += old.section is None
    original, corrected = decode_record(before.named(target)), decode_record(after.named(target))
    require(np.array_equal(corrected, candidate), 'Patched PSD target differs from candidate')
    validate_candidate(original, corrected, protected)
    return {'canvas': list(before.size), 'total_layer_records': len(before.records),
            'pixel_layers': sum(r.section is None for r in before.records),
            'unchanged_other_pixel_layers': unchanged,
            'folder_tree_and_all_layer_metadata_exact': True,
            'unchanged_channels_byte_exact': True, 'neutral_merged_bytes_exact': True}


def load_rgba(data):
    with Image.open(BytesIO(data)) as image:
        require(image.mode == 'RGBA', 'Candidate/runtime PNG must be RGBA')
        return np.asarray(image).copy()


def atomic_write(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name+'.', suffix='.tmp', delete=False) as file:
        temporary = Path(file.name)
        try:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def build(candidate_path=CANDIDATE, protected_path=PROTECTED_MASK, *, apply=False,
          candidate_sha256=None, protected_sha256=None):
    candidate_bytes = Path(candidate_path).read_bytes()
    mask_bytes = Path(protected_path).read_bytes()
    if candidate_sha256:
        require(sha256(candidate_bytes) == candidate_sha256, 'Frozen candidate SHA-256 mismatch')
    if protected_sha256:
        require(sha256(mask_bytes) == protected_sha256, 'Frozen protected mask SHA-256 mismatch')
    candidate = load_rgba(candidate_bytes)
    with Image.open(BytesIO(mask_bytes)) as image:
        require(image.mode == 'L', 'Protected lip mask must be a grayscale L PNG')
        protected = np.asarray(image) > 0
    source = SOURCE.read_bytes()
    require(sha256(source) == SOURCE_SHA256, 'The preserved v15 PSD does not match the approved baseline')
    before = inspect_psd(source)
    require(before.named(TARGET).bbox == TARGET_RECT, 'Unexpected original mouth rect')
    require(len(before.records) == 129 and sum(r.section is None for r in before.records) == 115,
            'Unexpected original layer count')
    old_runtime_bytes = ORIGINAL_SPRITE.read_bytes()
    old_runtime = load_rgba(old_runtime_bytes)
    original = decode_record(before.named(TARGET))
    require(np.array_equal(old_runtime, original), 'Original runtime sprite differs from the preserved PSD')
    manifest_bytes = MANIFEST.read_bytes()
    manifest = json.loads(manifest_bytes)
    old_pointer, new_pointer = str(SOURCE.relative_to(ROOT)), str(PSD.relative_to(ROOT))
    require(manifest['expression_source_psd'] in (old_pointer, new_pointer), 'Unexpected expression source PSD pointer')
    expression = next(e for e in manifest['expressions'] if e['id'] == 'surprised')
    part = next(p for p in expression['parts'] if p['name'] == 'mouth.closed')
    require(tuple(part['rect']) == TARGET_RECT and MODEL/part['file'] in (ORIGINAL_SPRITE, SPRITE), 'Unexpected runtime mouth mapping')
    original_pointer = manifest['expression_source_psd']
    old_token, new_token = json.dumps(original_pointer).encode(), json.dumps(new_pointer).encode()
    require(manifest_bytes.count(old_token) == 1, 'PSD pointer is not a unique manifest string')
    updated_manifest = manifest_bytes.replace(old_token, new_token, 1)
    old_sprite_token = json.dumps(part['file']).encode()
    new_sprite_file = str(SPRITE.relative_to(MODEL))
    require(updated_manifest.count(old_sprite_token) == 1, 'Mouth sprite pointer is not a unique manifest string')
    updated_manifest = updated_manifest.replace(old_sprite_token, json.dumps(new_sprite_file).encode(), 1)
    manifest['expression_source_psd'] = new_pointer
    part['file'] = new_sprite_file
    require(manifest == json.loads(updated_manifest), 'Manifest changed beyond its two authorized pointers')
    result, checks = patch_psd(source, candidate, protected)
    if PSD.exists():
        require(PSD.read_bytes() == result, 'Refusing to overwrite a different existing v17 PSD')
    if SPRITE.exists():
        require(SPRITE.read_bytes() == candidate_bytes, 'Refusing to overwrite a different existing v17 sprite')
    report = {'status': 'PASS', 'applied': bool(apply), 'target_layer': TARGET,
              'target_rect': list(TARGET_RECT), 'source_psd': old_pointer, 'output_psd': new_pointer,
              'source_sha256': sha256(source), 'output_sha256': sha256(result),
              'candidate_sha256': sha256(candidate_bytes), 'protected_mask_sha256': sha256(mask_bytes),
              'runtime_sprite': str(SPRITE.relative_to(ROOT)),
              'manifest_only_changed_fields': ['expression_source_psd', 'expressions[surprised].parts[mouth.closed].file'], **checks}
    if apply:
        # All inputs and output bytes are validated before these three writes.
        # Each write is atomic. Re-running the same frozen inputs is idempotent.
        atomic_write(PSD, result)
        atomic_write(SPRITE, candidate_bytes)
        atomic_write(MANIFEST, updated_manifest)
        require(SOURCE.read_bytes() == source and ORIGINAL_SPRITE.read_bytes() == old_runtime_bytes,
                'Preserved PSD or original sprite changed during application')
        require(SPRITE.read_bytes() == candidate_bytes and MANIFEST.read_bytes() == updated_manifest,
                'Runtime application verification failed')
        require(PSD.read_bytes() == result, 'PSD application verification failed')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, default=CANDIDATE)
    parser.add_argument('--protected-mask', type=Path, default=PROTECTED_MASK)
    parser.add_argument('--candidate-sha256')
    parser.add_argument('--protected-mask-sha256')
    parser.add_argument('--apply', action='store_true', help='Write the new PSD and the two authorized runtime files')
    parser.add_argument('--report', type=Path, help='Optional separate JSON audit report')
    args = parser.parse_args()
    report = build(args.candidate, args.protected_mask, apply=args.apply,
                   candidate_sha256=args.candidate_sha256, protected_sha256=args.protected_mask_sha256)
    output = json.dumps(report, ensure_ascii=False, indent=2)+'\n'
    if args.report:
        require(args.report.resolve() not in {p.resolve() for p in (SOURCE, PSD, ORIGINAL_SPRITE, SPRITE, MANIFEST, args.candidate, args.protected_mask)},
                'Report path must not replace an input or production output')
        atomic_write(args.report, output.encode())
    print(output, end='')
