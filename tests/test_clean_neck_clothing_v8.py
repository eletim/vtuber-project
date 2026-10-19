#!/usr/bin/env python3
"""Regression checks for the painted neck/clothing cleanup candidate."""
from pathlib import Path
import sys
import tempfile

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_psd import composite, parse_psd
from clean_neck_clothing_v8 import (
    BLOUSE,
    BLOUSE_UNDERLAYER_NAME,
    NECK,
    NECK_BASE,
    NECK_UNDERLAYER_NAME,
    OLD_REVEAL,
    OUTPUT_PSD,
    PAINTED_UNDERLAYER,
    PAINTED_UNDERLAYER_SHA256,
    SOURCE,
    SIDE_HAIR_UNDERLAYER,
    TORSO_BASE,
    VEST,
    WAIST,
    WAIST_UNDERLAYER_NAME,
    _group_opacity,
    _ownership_masks,
    _semantic_region_mask,
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
        assert OLD_REVEAL not in names
        assert "vest_occluded_fixed_painted_underlayer" not in names
        assert names.index(NECK_UNDERLAYER_NAME) < names.index(NECK_BASE)
        for underlayer_name in (
            BLOUSE_UNDERLAYER_NAME,
            WAIST_UNDERLAYER_NAME,
        ):
            assert names.index(underlayer_name) < names.index(TORSO_BASE)

        changed = report["changed_painted_pixels"]
        assert changed["removed_approximate_reveal_pixels"] == 166699
        assert changed["removed_vest_occluded_side_hair_residual_pixels"] == 10877
        assert changed["painted_neck_collar_pixels"] > 0
        assert changed["painted_blouse_pixels"] > 0
        assert changed["painted_waist_pixels"] > 0
        assert changed["painted_underlayer_sha256"] == PAINTED_UNDERLAYER_SHA256

        painted = np.asarray(Image.open(PAINTED_UNDERLAYER).convert("RGBA"))
        assert not np.any(
            (painted[:, :, 3] == 0)
            & np.any(painted[:, :, :3] != 0, axis=2)
        )
        assert not np.any(
            (painted[:, :, 3] > 0)
            & np.all(painted[:, :, :3] == 0, axis=2)
        )
        ownership = _ownership_masks(source)
        non_clothing = _semantic_region_mask(
            painted.shape[:2],
            (
                "left_arm_sleeve",
                "right_arm_sleeve",
                "left_hand",
                "right_hand",
                "hair_side_left",
                "hair_side_right",
                "hair_back_left",
                "hair_back_right",
                "face_base",
            ),
        )
        assert not np.any(ownership["neck"] & non_clothing)
        assert not np.any(ownership["blouse"] & non_clothing)
        assert not np.any(ownership["waist"] & non_clothing)
        underlayer_groups = (
            (NECK_UNDERLAYER_NAME, "neck", NECK),
            (BLOUSE_UNDERLAYER_NAME, "blouse", BLOUSE + VEST),
            (WAIST_UNDERLAYER_NAME, "waist", WAIST + VEST),
        )
        consumed = np.zeros(painted.shape[:2], dtype=bool)
        for underlayer_name, owner, source_names in underlayer_groups:
            alpha = records[underlayer_name]["data"][:, :, 3] > 0
            assert np.array_equal(alpha, ownership[owner])
            assert not np.any(alpha & consumed)
            assert not np.any(alpha & (_group_opacity(source, source_names) != 255))
            consumed |= alpha
        assert np.array_equal(consumed, painted[:, :, 3] > 0)

        hair_boundary = _semantic_region_mask(
            painted.shape[:2],
            (
                "hair_side_left",
                "hair_side_right",
                "hair_back_left",
                "hair_back_right",
            ),
        )
        vest_occluded = _group_opacity(source, VEST) == 255
        source_side_hair = next(
            record for record in source if record["name"] == SIDE_HAIR_UNDERLAYER
        )["data"]
        cleaned_side_hair = records[SIDE_HAIR_UNDERLAYER]["data"]
        residual = vest_occluded & ~hair_boundary
        assert not np.any(cleaned_side_hair[residual, 3])
        assert np.array_equal(
            cleaned_side_hair[~residual], source_side_hair[~residual]
        )

        for label in ("neck", "vest", "blouse", "waist"):
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
        assert all(check["pass"] for check in report["scene_checks"].values())

        committed, _ = parse_psd(OUTPUT_PSD)
        assert np.array_equal(composite(committed), composite(generated))
        assert [record["name"] for record in committed] == names
        assert OUTPUT_PSD.read_bytes() == (temporary / "candidate.psd").read_bytes()
        print("PASS: reproducible painted neck/clothing cleanup and movement audit")


if __name__ == "__main__":
    main()
