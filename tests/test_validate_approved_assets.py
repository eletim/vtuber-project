#!/usr/bin/env python3
"""Regression checks for approved-asset pointer and PSD validation."""
from pathlib import Path
import sys
import tempfile

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from psd_writer import write_psd
from validate_approved_assets import ValidationError, reject_pointer, validate_psd


def expect_rejected(action, message):
    try:
        action()
    except ValidationError:
        return
    raise AssertionError(message)


def main():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        pointer = root / "pointer.psd"
        pointer.write_bytes(
            b"version https://git-lfs.github.com/spec/v1\n"
            b"oid sha256:" + b"0" * 64 + b"\nsize 123\n"
        )
        expect_rejected(
            lambda: reject_pointer(pointer), "Git LFS pointer was accepted"
        )

        malformed = root / "malformed.psd"
        malformed.write_bytes(b"8BPS\x00\x01truncated")
        expect_rejected(
            lambda: validate_psd(malformed), "malformed PSD was accepted"
        )

        canvas = np.zeros((2, 2, 4), dtype=np.uint8)
        canvas[:, :] = (10, 20, 30, 255)
        layered = root / "layered.psd"
        layers = [(f"layer-{index}", canvas.copy()) for index in range(49)]
        write_psd(layered, canvas, layers)
        assert validate_psd(layered, expected_layers=49) == 49
        expect_rejected(
            lambda: validate_psd(layered, expected_layers=48),
            "wrong PSD layer count was accepted",
        )

    print("PASS: pointer, malformed PSD and layer-count validation")


if __name__ == "__main__":
    main()
