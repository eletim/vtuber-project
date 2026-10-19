#!/usr/bin/env python3
"""Clean v8 hair boundaries while preserving the approved initial composite.

The repair deliberately reuses painted pixels from the approved v8 appearance
and the illustrated v7 underlayers.  It does not synthesize, blur, or flat-fill
hidden artwork.
"""
from __future__ import annotations

import copy
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import binary_dilation

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_psd import composite, parse_psd
from psd_writer import write_psd


V8_SOURCE = ROOT / "assets/parts/v8/koma_expression_repaired_v8.psd"
V7_UNDERLAYERS = ROOT / "assets/parts/v7/koma_illustrated_underlayers_v7.psd"
OUTPUT_DIR = ROOT / "assets/parts/v8"
OUTPUT_PSD = OUTPUT_DIR / "koma_hair_head_cleaned_v8.psd"
OUTPUT_PREVIEW = OUTPUT_DIR / "hair_head_comparison_v8.png"
OUTPUT_AUDIT = OUTPUT_DIR / "hair_head_audit_v8.json"
REVIEW_REFERENCE_DIR = OUTPUT_DIR / "review_references"
REVIEW_REFERENCES = {
    "side_hair_hidden": REVIEW_REFERENCE_DIR / "side_hair_hidden_v8.png",
    "side_hair_displaced": REVIEW_REFERENCE_DIR / "side_hair_displaced_v8.png",
}

BANGS = ("front_bangs.illustrated_underpaint", "front_bangs")
SIDES = (
    "hair_side_left.illustrated_underpaint",
    "hair_side_left",
    "hair_side_right.illustrated_underpaint",
    "hair_side_right",
)
ACCESSORY = ("hair_accessory.illustrated_underpaint", "hair_accessory")
CROWN = ("hair_crown.illustrated_underpaint", "hair_crown")
REAR = ("hair_back_left", "hair_back_right")
HAIR_BASE = "hair_base_FULL_beneath_hair_parts"
SCALP = "scalp_reveal_when_bangs_move"
BOUNDARY_RESTORATION = "hair_boundary_fixed_underpainting"

NON_HAIR_UNDERLAYERS = (
    "neck",
    "neck.illustrated_underpaint",
    "left_arm_sleeve",
    "left_arm_sleeve.illustrated_underpaint",
    "right_arm_sleeve",
    "right_arm_sleeve.illustrated_underpaint",
    "vest_left",
    "vest_left.illustrated_underpaint",
    "vest_right",
    "vest_right.illustrated_underpaint",
    "blouse",
    "skirt_and_belt",
    "face_skin_FULL_beneath_eyes_mouth",
    "neck_base_FULL_beneath_neck",
    "left_sleeve_base_FULL_beneath_left_sleeve",
    "right_sleeve_base_FULL_beneath_right_sleeve",
    "torso_clothing_base_FULL_beneath_torso_parts",
)


def _record(layers, name):
    return next(record for record in layers if record["name"] == name)


def _group_opacity(layers, names):
    """Return the effective alpha of a top-to-bottom layer group."""
    alpha = np.zeros(layers[0]["data"].shape[:2], dtype=np.uint8)
    for name in reversed(names):
        source = _record(layers, name)["data"][:, :, 3].astype(np.uint16)
        alpha = np.uint8(
            source + (alpha.astype(np.uint16) * (255 - source) + 127) // 255
        )
    return alpha


def _shift(image, dx, dy):
    """Translate an RGBA layer without wrapping pixels across the canvas."""
    shifted = np.zeros_like(image)
    height, width = image.shape[:2]
    source_x0, source_x1 = max(0, -dx), min(width, width - dx)
    source_y0, source_y1 = max(0, -dy), min(height, height - dy)
    target_x0, target_x1 = max(0, dx), min(width, width + dx)
    target_y0, target_y1 = max(0, dy), min(height, height + dy)
    shifted[target_y0:target_y1, target_x0:target_x1] = image[
        source_y0:source_y1, source_x0:source_x1
    ]
    return shifted


def _moved_layers(layers, moves):
    result = copy.deepcopy(layers)
    for name, (dx, dy) in moves.items():
        record = _record(result, name)
        record["data"] = _shift(record["data"], dx, dy)
    return result


def _displaced(layers, moves):
    return composite(_moved_layers(layers, moves))


def _repair_v7_boundary_remnants(base, occluded, painted_v7):
    """Patch ragged v7 boundary neighborhoods with offset painted v7 hair."""
    red, green, blue = [base[:, :, channel].astype(np.int16) for channel in range(3)]
    spread = np.maximum.reduce((red, green, blue)) - np.minimum.reduce(
        (red, green, blue)
    )
    light_halo = (red > 190) & (green > 185) & (blue > 175) & (spread < 60)
    dark_fragment = (red < 110) & (green < 100) & (blue < 95)
    gray_fragment = (spread < 28) & (red < 200)
    yellow_remnant = (red > 170) & (green > 165) & (blue < 120)
    green_remnant = (green > 120) & (green > red + 3) & (green > blue + 15)
    seeds = (
        occluded
        & (base[:, :, 3] > 0)
        & (light_halo | dark_fragment | gray_fragment | yellow_remnant | green_remnant)
    )
    repair = binary_dilation(seeds, iterations=8) & occluded & (base[:, :, 3] > 0)
    if not np.any(repair):
        return 0

    # Sample the same v7 painting four pixels toward the character center. The
    # offset keeps detailed strand texture while ensuring the hidden artwork is
    # not a fixed copy of the visible side-hair silhouette.
    offset = 4
    height, width = repair.shape
    shifted = np.zeros_like(painted_v7)
    shifted[:, : width - offset] = painted_v7[:, offset:]
    shifted_right = np.zeros_like(painted_v7)
    shifted_right[:, offset:] = painted_v7[:, : width - offset]
    right_half = np.broadcast_to(np.arange(width)[None, :] >= width // 2, (height, width))
    shifted[right_half] = shifted_right[right_half]
    base[:, :, :3][repair] = shifted[:, :, :3][repair]
    return int(np.count_nonzero(repair))


def clean_layers(v8_layers, v7_layers):
    """Return cleaned layers and pixel-provenance counts."""
    v8_names = [record["name"] for record in v8_layers]
    v7_names = [record["name"] for record in v7_layers]
    if len(v8_names) != len(v7_names) or set(v8_names) != set(v7_names):
        raise ValueError("v7 and v8 layer structures do not match")

    layers = copy.deepcopy(v8_layers)
    approved = composite(v8_layers)
    changed = {}

    # First remove pixels that make no contribution because the illustrated
    # v7 underdrawing beneath them already produces the exact approved result.
    # This trims coarse extraction overlap from every movable hair group.
    groups = {
        "bangs": BANGS,
        "side_hair": SIDES,
        "accessory": ACCESSORY,
        "crown": CROWN,
        "rear_hair": REAR,
    }
    # Bangs are excluded: pixels that are redundant in the approved pose still
    # define the continuous movable fringe above the separate scalp reveal.
    prunable_groups = {
        key: value for key, value in groups.items() if key != "bangs"
    }
    for label, names in prunable_groups.items():
        without_group = composite(layers, hide=names)
        redundant = np.all(without_group == approved, axis=2)
        pruned = 0
        for name in names:
            data = _record(layers, name)["data"]
            removable = redundant & (data[:, :, 3] > 0)
            pruned += int(np.count_nonzero(removable))
            data[removable] = 0
        changed[f"{label}_redundant_boundary"] = pruned

    # The side-hair extraction also contains exact copies of painted skin and
    # garment pixels. Move those pixels into a fixed underpainting layer so
    # shoulder/vest fragments do not travel with the hair.
    for name in SIDES:
        data = _record(layers, name)["data"]
        non_hair = np.zeros(data.shape[:2], dtype=bool)
        for underlayer_name in NON_HAIR_UNDERLAYERS:
            underlayer = _record(layers, underlayer_name)["data"]
            non_hair |= (
                (data[:, :, 3] > 0)
                & (underlayer[:, :, 3] > 0)
                & np.all(data[:, :, :3] == underlayer[:, :, :3], axis=2)
            )
        data[non_hair] = 0

    after_side_cleanup = composite(layers)
    restoration_mask = np.any(after_side_cleanup != approved, axis=2)
    for name in SIDES:
        _record(layers, name)["data"][restoration_mask] = 0
    restoration = np.zeros_like(approved)
    restoration[:, :, :3][restoration_mask] = approved[:, :, :3][restoration_mask]
    restoration[:, :, 3][restoration_mask] = 255
    side_bottom = max(
        index for index, record in enumerate(layers) if record["name"] in SIDES
    )
    layers.insert(
        side_bottom + 1,
        {"name": BOUNDARY_RESTORATION, "data": restoration, "visible": True},
    )
    changed["fixed_side_hair_boundary"] = int(np.count_nonzero(restoration_mask))

    if not np.array_equal(composite(layers), approved):
        raise AssertionError("fixed side-hair boundary changed approved appearance")

    base = _record(layers, HAIR_BASE)["data"]

    # Replace the saturated yellow/green segmentation remnants embedded in the
    # v7 underpaint boundaries with the paired approved top-layer pixels. The
    # repaired pixels are all fully covered by that top layer in the default
    # pose, so this also preserves the approved composite exactly.
    boundary_pairs = {
        "bangs_boundary": ("front_bangs.illustrated_underpaint", "front_bangs"),
        "side_hair_left_boundary": (
            "hair_side_left.illustrated_underpaint",
            "hair_side_left",
        ),
        "side_hair_right_boundary": (
            "hair_side_right.illustrated_underpaint",
            "hair_side_right",
        ),
        "accessory_boundary": (
            "hair_accessory.illustrated_underpaint",
            "hair_accessory",
        ),
        "crown_boundary": ("hair_crown.illustrated_underpaint", "hair_crown"),
    }
    for label, (underpaint_name, top_name) in boundary_pairs.items():
        underpaint = _record(layers, underpaint_name)["data"]
        top = _record(layers, top_name)["data"]
        red, green, blue = [
            underpaint[:, :, channel].astype(np.int16) for channel in range(3)
        ]
        yellow_remnant = (red > 200) & (green > 195) & (blue < 40)
        green_remnant = (green > 150) & (green > red + 10) & (green > blue + 40)
        boundary = (
            (underpaint[:, :, 3] > 0)
            & (top[:, :, 3] == 255)
            & (yellow_remnant | green_remnant)
        )
        underpaint[:, :, :3][boundary] = top[:, :, :3][boundary]
        changed[label] = int(np.count_nonzero(boundary))

    # Repair only pixels completely hidden by their movable group. This keeps
    # the approved pose exact while leaving detailed, painted hair beneath.
    sources = {
        "bangs": approved,
        "side_hair": composite(v7_layers, hide=SIDES),
        "accessory": composite(v7_layers, hide=ACCESSORY),
        "crown": composite(v7_layers, hide=CROWN),
        "rear_hair": composite(v7_layers, hide=REAR),
    }
    for label, names in groups.items():
        mask = (_group_opacity(layers, names) == 255) & (base[:, :, 3] > 0)
        before = base[:, :, :3].copy()
        base[:, :, :3][mask] = sources[label][:, :, :3][mask]
        changed[label] = int(np.count_nonzero(np.any(before != base[:, :, :3], axis=2)))

    # The v7 hidden side-hair state is the authoritative underdrawing, but its
    # old extraction boundary contains neon marker remnants. Replace only the
    # fully occluded remnants with nearby pixels from the same painted v7 hair
    # base; no synthesized color, flat fill, or blur is introduced.
    changed["v7_side_underlayer_boundary"] = _repair_v7_boundary_remnants(
        base,
        _group_opacity(layers, SIDES) == 255,
        composite(v7_layers),
    )

    # The v7 scalp reveal is genuine illustrated hairline/forehead artwork.
    # Retain the portion actually occluded by opaque bangs, then put it beneath
    # the movable front/side hair and above face/base layers. Clipping at the
    # opaque silhouette prevents the broad source layer from covering crown or
    # facial detail that it was never meant to replace.
    scalp = _record(layers, SCALP)
    original_scalp_alpha = scalp["data"][:, :, 3].copy()
    occluded_by_bangs = _group_opacity(layers, BANGS) == 255
    scalp["data"][:, :, 3] = np.where(
        occluded_by_bangs, original_scalp_alpha, 0
    ).astype(np.uint8)
    changed["hairline_underpainting"] = int(
        np.count_nonzero(scalp["data"][:, :, 3])
    )
    layers.remove(scalp)
    scalp["visible"] = True
    insert_at = next(
        index
        for index, record in enumerate(layers)
        if record["name"] == BOUNDARY_RESTORATION
    ) + 1
    layers.insert(insert_at, scalp)

    cleaned = composite(layers)
    if not np.array_equal(cleaned, approved):
        raise AssertionError("cleaned initial composite differs from approved v8")
    return layers, changed


def _audit_scenes(layers, approved, *, accept_review_references=False):
    expected_alpha = approved[:, :, 3]
    side_moves = {
        "hair_side_left": (-4, 0),
        "hair_side_left.illustrated_underpaint": (-4, 0),
        "hair_side_right": (4, 0),
        "hair_side_right.illustrated_underpaint": (4, 0),
    }
    rear_moves = {"hair_back_left": (-8, 0), "hair_back_right": (8, 0)}
    side_moved_layers = _moved_layers(layers, side_moves)
    rear_moved_layers = _moved_layers(layers, rear_moves)
    scenes = {
        "bangs_hidden": composite(layers, hide=BANGS),
        "side_hair_hidden": composite(layers, hide=SIDES),
        "accessory_hidden": composite(layers, hide=ACCESSORY),
        "crown_hidden": composite(layers, hide=CROWN),
        "rear_hair_hidden": composite(layers, hide=REAR),
        "bangs_displaced": _displaced(layers, {name: (0, -8) for name in BANGS}),
        "side_hair_displaced": composite(side_moved_layers),
        "rear_hair_displaced": composite(rear_moved_layers),
        "accessory_displaced": _displaced(
            layers, {name: (8, 0) for name in ACCESSORY}
        ),
    }
    checks = {}
    for name, image in scenes.items():
        holes = int(np.count_nonzero((image[:, :, 3] == 0) & (expected_alpha > 0)))
        checks[name] = {"lost_alpha_pixels": holes, "pass": holes == 0}

    for scene_name in ("side_hair_hidden", "rear_hair_hidden"):
        changed_pixels = int(
            np.count_nonzero(
                np.any(scenes[scene_name][:, :, :3] != approved[:, :, :3], axis=2)
            )
        )
        checks[scene_name]["changed_rgb_pixels_vs_default"] = changed_pixels
        checks[scene_name]["pass"] &= changed_pixels > 0

    displacement_specs = {
        "side_hair_displaced": (SIDES, side_moved_layers, scenes["side_hair_hidden"]),
        "rear_hair_displaced": (REAR, rear_moved_layers, scenes["rear_hair_hidden"]),
    }
    for scene_name, (names, moved_layers, hidden) in displacement_specs.items():
        original_opacity = _group_opacity(layers, names)
        moved_opacity = _group_opacity(moved_layers, names)
        vacated = (original_opacity > 0) & (moved_opacity == 0)
        moved = scenes[scene_name]
        matches_hidden = np.all(moved == hidden, axis=2)
        matches_default = np.all(moved == approved, axis=2)
        vacated_pixels = int(np.count_nonzero(vacated))
        matching_underpainting = int(np.count_nonzero(vacated & matches_hidden))
        retained_default = int(np.count_nonzero(vacated & matches_default))
        retained_fraction = retained_default / max(vacated_pixels, 1)
        checks[scene_name].update(
            {
                "vacated_original_silhouette_pixels": vacated_pixels,
                "vacated_pixels_matching_hidden_underpainting": matching_underpainting,
                "vacated_pixels_still_matching_default": retained_default,
                "retained_default_fraction": retained_fraction,
            }
        )
        checks[scene_name]["pass"] &= (
            vacated_pixels > 0
            and matching_underpainting == vacated_pixels
            and retained_fraction < 0.01
        )

    if accept_review_references:
        REVIEW_REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
        for scene_name, path in REVIEW_REFERENCES.items():
            Image.fromarray(scenes[scene_name], "RGBA").save(path)
    for scene_name, path in REVIEW_REFERENCES.items():
        if not path.is_file():
            raise AssertionError(f"missing reviewed image reference: {path}")
        reference = np.asarray(Image.open(path).convert("RGBA"), dtype=np.uint8)
        if reference.shape != scenes[scene_name].shape:
            raise AssertionError(f"reviewed image reference has wrong size: {path}")
        differing_pixels = int(
            np.count_nonzero(np.any(reference != scenes[scene_name], axis=2))
        )
        checks[scene_name]["review_reference"] = str(path.relative_to(ROOT))
        checks[scene_name]["review_reference_pixel_diff"] = differing_pixels
        checks[scene_name]["pass"] &= differing_pixels == 0
    return scenes, checks


def _write_preview(approved, scenes, destination):
    entries = [("approved default", approved)] + list(scenes.items())
    tile_width, tile_height = 320, 410
    columns = 3
    rows = (len(entries) + columns - 1) // columns
    panel = Image.new("RGB", (tile_width * columns, tile_height * rows), (250, 246, 242))
    draw = ImageDraw.Draw(panel)
    for index, (name, array) in enumerate(entries):
        image = Image.fromarray(array, "RGBA").crop((100, 0, 980, 760))
        image.thumbnail((tile_width, tile_height - 28), Image.Resampling.LANCZOS)
        background = Image.new("RGBA", image.size, (250, 246, 242, 255))
        background.alpha_composite(image)
        x = index % columns * tile_width
        y = index // columns * tile_height
        panel.paste(background.convert("RGB"), (x, y + 26))
        draw.text((x + 6, y + 6), name.replace("_", " "), fill=(48, 38, 38))
    panel.save(destination)


def build_candidate(
    output_psd=OUTPUT_PSD,
    preview=OUTPUT_PREVIEW,
    audit_path=OUTPUT_AUDIT,
    *,
    accept_review_references=False,
):
    v8_layers, size = parse_psd(V8_SOURCE)
    v7_layers, v7_size = parse_psd(V7_UNDERLAYERS)
    if size != v7_size:
        raise ValueError(f"source size mismatch: {size} != {v7_size}")

    layers, changed = clean_layers(v8_layers, v7_layers)
    approved = composite(v8_layers)
    cleaned = composite(layers)
    output_psd = Path(output_psd)
    preview = Path(preview)
    audit_path = Path(audit_path)
    for path in (output_psd, preview, audit_path):
        path.parent.mkdir(parents=True, exist_ok=True)

    write_psd(
        output_psd,
        cleaned,
        [(record["name"], record["data"]) for record in layers],
        hidden_names=[record["name"] for record in layers if not record["visible"]],
    )
    reloaded, reloaded_size = parse_psd(output_psd)
    if reloaded_size != size or len(reloaded) != 50:
        raise AssertionError("candidate PSD did not reload with the expected structure")
    if not np.array_equal(composite(reloaded), approved):
        raise AssertionError("reloaded candidate does not match approved appearance")

    scenes, scene_checks = _audit_scenes(
        reloaded, approved, accept_review_references=accept_review_references
    )
    if not all(check["pass"] for check in scene_checks.values()):
        raise AssertionError("a hidden/displaced hair scene failed its audit")
    _write_preview(approved, scenes, preview)

    report = {
        "source_v8": str(V8_SOURCE.relative_to(ROOT)),
        "underpainting_v7": str(V7_UNDERLAYERS.relative_to(ROOT)),
        "output_psd": (
            str(output_psd.relative_to(ROOT))
            if output_psd.is_relative_to(ROOT)
            else str(output_psd)
        ),
        "layer_count": len(reloaded),
        "initial_rgb_pixel_diff": 0,
        "initial_alpha_pixel_diff": 0,
        "changed_painted_pixels": changed,
        "pixel_sources": [
            "approved v8 composite",
            "illustrated v7 scalp reveal",
            "illustrated v7 hair-underlayer composites",
            "four-pixel-offset painted hair from the illustrated v7 composite",
        ],
        "flat_fill_or_blur_used": False,
        "scene_checks": scene_checks,
        "art_ready_for_cubism": False,
    }
    audit_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"PASS: {output_psd} ({len(reloaded)} layers; approved default preserved)")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--accept-review-references",
        action="store_true",
        help="replace side-hair visual baselines after explicit artwork review",
    )
    arguments = parser.parse_args()
    build_candidate(accept_review_references=arguments.accept_review_references)
