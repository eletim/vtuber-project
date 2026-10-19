#!/usr/bin/env python3
"""Regression checks for the painted hair/head cleanup candidate."""
from pathlib import Path
import sys
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_psd import composite, parse_psd
from clean_hair_head_v8 import (
    BOUNDARY_RESTORATION,
    OUTPUT_PSD,
    PAINTED_SIDE_UNDERLAYER_NAME,
    SCALP,
    V8_SOURCE,
    build_candidate,
)


def main():
    with tempfile.TemporaryDirectory() as directory:
        temporary = Path(directory)
        report = build_candidate(
            temporary / "candidate.psd",
            temporary / "comparison.png",
            temporary / "audit.json",
        )
        generated, size = parse_psd(temporary / "candidate.psd")
        approved, approved_size = parse_psd(V8_SOURCE)
        assert size == approved_size == (1086, 1448)
        assert len(generated) == 51
        assert len(approved) == 49
        generated_default = composite(generated)
        approved_default = composite(approved)
        assert np.array_equal(generated_default[:, :, 3], approved_default[:, :, 3])
        assert report["initial_rgb_pixel_diff"] == int(
            np.count_nonzero(
                np.any(
                    generated_default[:, :, :3] != approved_default[:, :, :3],
                    axis=2,
                )
            )
        )
        assert next(record for record in generated if record["name"] == SCALP)["visible"]

        names = [record["name"] for record in generated]
        assert names.index("hair_side_right.illustrated_underpaint") < names.index(SCALP)
        assert names.index("hair_side_right.illustrated_underpaint") < names.index(BOUNDARY_RESTORATION)
        assert names.index(BOUNDARY_RESTORATION) < names.index(SCALP)
        assert names.index(PAINTED_SIDE_UNDERLAYER_NAME) < names.index(
            "hair_base_FULL_beneath_hair_parts"
        )
        assert names.index(SCALP) < names.index("face_details_without_expression")
        assert report["flat_fill_or_blur_used"] is False
        assert report["changed_painted_pixels"]["hairline_underpainting"] > 0
        assert report["changed_painted_pixels"]["accessory_boundary"] > 0
        assert report["changed_painted_pixels"]["fixed_side_hair_boundary"] > 0
        assert report["changed_painted_pixels"]["painted_side_hair_underlayer"] > 0
        assert report["changed_painted_pixels"]["approved_default_boundary_cleanup"] > 0
        assert report["initial_alpha_pixel_diff"] == 0
        for name in ("side_hair_hidden", "rear_hair_hidden"):
            assert report["scene_checks"][name]["changed_rgb_pixels_vs_default"] > 0
        for name in ("side_hair_displaced", "rear_hair_displaced"):
            check = report["scene_checks"][name]
            assert check["vacated_original_silhouette_pixels"] > 0
            assert (
                check["vacated_pixels_matching_hidden_underpainting"]
                == check["vacated_original_silhouette_pixels"]
            )
            assert check["retained_default_fraction"] < 0.01
        for name in ("side_hair_hidden", "side_hair_displaced"):
            check = report["scene_checks"][name]
            assert check["review_reference"].endswith("_v8.png")
            assert len(check["review_reference_sha256"]) == 64
            assert check["review_reference_pixel_diff"] == 0
        assert all(check["pass"] for check in report["scene_checks"].values())

        committed, _ = parse_psd(OUTPUT_PSD)
        assert np.array_equal(composite(committed), composite(generated))
        assert [record["name"] for record in committed] == names
        assert OUTPUT_PSD.read_bytes() == (temporary / "candidate.psd").read_bytes()
        print("PASS: reproducible painted hair/head cleanup and reveal-state audit")


if __name__ == "__main__":
    main()
