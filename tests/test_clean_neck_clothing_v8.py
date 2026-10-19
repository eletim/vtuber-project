#!/usr/bin/env python3
"""Regression checks for the painted neck/clothing cleanup candidate."""
from pathlib import Path
import sys
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_psd import composite, parse_psd
from clean_neck_clothing_v8 import (
    BLOUSE,
    NECK,
    NECK_BASE,
    NECK_UNDERLAYER_NAME,
    OLD_REVEAL,
    OUTPUT_PSD,
    PAINTED_UNDERLAYER_SHA256,
    SOURCE,
    TORSO_BASE,
    TORSO_UNDERLAYER_NAME,
    VEST,
    WAIST,
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
        source, source_size = parse_psd(SOURCE)

        assert size == source_size == (1086, 1448)
        assert len(generated) == 53
        assert len(source) == 51
        assert np.array_equal(composite(generated), composite(source))
        assert report["initial_rgb_pixel_diff"] == 0
        assert report["initial_alpha_pixel_diff"] == 0
        assert report["flat_fill_or_blur_used"] is False
        assert report["approved_costume_redesigned"] is False

        names = [record["name"] for record in generated]
        records = {record["name"]: record for record in generated}
        assert not records[OLD_REVEAL]["visible"]
        assert names.index(OLD_REVEAL) < names.index("hair_side_left")
        assert names.index(NECK_UNDERLAYER_NAME) < names.index(NECK_BASE)
        assert names.index(TORSO_UNDERLAYER_NAME) < names.index(TORSO_BASE)

        changed = report["changed_painted_pixels"]
        assert changed["removed_approximate_reveal_pixels"] == 166699
        assert changed["painted_neck_collar_pixels"] > 0
        assert changed["painted_torso_clothing_pixels"] > 0
        assert changed["painted_vest_reveal_pixels"] > 0
        assert changed["painted_underlayer_sha256"] == PAINTED_UNDERLAYER_SHA256

        for label, names_for_part in (
            ("neck", NECK),
            ("vest", VEST),
            ("blouse", BLOUSE),
            ("waist", WAIST),
        ):
            hidden = report["scene_checks"][f"{label}_hidden"]
            displaced = report["scene_checks"][f"{label}_displaced"]
            assert hidden["lost_alpha_pixels"] == 0
            assert hidden["changed_rgb_pixels_vs_default"] > 0
            assert displaced["lost_alpha_pixels"] == 0
            assert displaced["vacated_original_silhouette_pixels"] > 0
            assert (
                displaced["vacated_pixels_matching_hidden_underpainting"]
                == displaced["vacated_original_silhouette_pixels"]
            )
            assert displaced["retained_default_fraction"] < 0.7
            assert len(names_for_part) > 0
        assert all(check["pass"] for check in report["scene_checks"].values())

        committed, _ = parse_psd(OUTPUT_PSD)
        assert np.array_equal(composite(committed), composite(generated))
        assert [record["name"] for record in committed] == names
        assert OUTPUT_PSD.read_bytes() == (temporary / "candidate.psd").read_bytes()
        print("PASS: reproducible painted neck/clothing cleanup and movement audit")


if __name__ == "__main__":
    main()
