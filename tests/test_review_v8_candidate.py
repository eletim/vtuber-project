"""Regression coverage for PSD visual-review evidence, not beauty approval."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from review_v8_candidate import run_audit, translate_pixels


def main():
    src = np.zeros((4, 5, 4), dtype=np.uint8)
    src[1, 1] = [255, 55, 66, 255]
    assert np.array_equal(translate_pixels(src, 2, 1)[2, 3], src[1, 1])
    assert int(np.count_nonzero(translate_pixels(src, 2, 1)[:, :, 3])) == 1
    assert int(np.count_nonzero(translate_pixels(src, -2, -1)[:, :, 3])) == 0
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp)
        approved_psd = ROOT / "assets/parts/v8/koma_expression_repaired_v8.psd"
        report = run_audit(
            approved_psd,
            ROOT / "assets/original/koma_confirmed.png",
            output,
            groups=("hands",),
            baseline_psd=approved_psd,
        )
        # The original PNG contains an *opaque painted background* whereas
        # PSD canvas background is transparent; compare the actual art only.
        assert report["approved_initial_foreground_rgb_changed_pixels"] == 0
        assert report["baseline_alpha_changed_pixels"] == 0
        assert report["structural_check"] == "PASS"
        assert report["visual_review"].startswith("PENDING")
        assert report["cubism_rigging"] == "NOT_STARTED"
        assert (output / "hands_review_strip.png").is_file()
        assert (output / "expression_both_closed.png").is_file()
        with Image.open(output / "expression_cycle.gif") as gif:
            assert gif.n_frames == 4
    print("PASS: candidate review export, RGB-background handling, four expressions")


if __name__ == "__main__":
    main()