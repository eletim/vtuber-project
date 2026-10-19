#!/usr/bin/env python3
"""Complete the v8 neck and torso clothing artwork beneath movable parts.

The approved appearance is kept pixel-identical.  A separately painted
underlayer supplies continuous collar, blouse, corset, vest-edge, belt, and
waist artwork only where the approved movable parts fully occlude it.
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_psd import composite, parse_psd
from psd_writer import write_psd


SOURCE = ROOT / "assets/parts/v8/koma_hair_head_cleaned_v8.psd"
OUTPUT_DIR = ROOT / "assets/parts/v8"
OUTPUT_PSD = OUTPUT_DIR / "koma_neck_clothing_cleaned_v8.psd"
OUTPUT_PREVIEW = OUTPUT_DIR / "neck_clothing_comparison_v8.png"
OUTPUT_AUDIT = OUTPUT_DIR / "neck_clothing_audit_v8.json"
PAINTED_UNDERLAYER = OUTPUT_DIR / "neck_clothing_underpainting_v8.png"
REGION_CONFIG = ROOT / "config/koma_regions.json"
PAINTED_UNDERLAYER_SHA256 = (
    "56f2597ec839b80436587226aca335bce376af03220dbca382b74fa707aeb1dc"
)

NECK = ("neck", "neck.illustrated_underpaint")
VEST_LEFT = ("vest_left", "vest_left.illustrated_underpaint")
VEST_RIGHT = ("vest_right", "vest_right.illustrated_underpaint")
VEST = VEST_LEFT + VEST_RIGHT
BLOUSE = ("blouse",)
WAIST = ("skirt_and_belt",)
OLD_REVEAL = "blouse_reveal_when_vest_moves"
NECK_BASE = "neck_base_FULL_beneath_neck"
TORSO_BASE = "torso_clothing_base_FULL_beneath_torso_parts"
NECK_UNDERLAYER_NAME = "neck_collar_fixed_painted_underlayer"
BLOUSE_UNDERLAYER_NAME = "blouse_fixed_painted_underlayer"
WAIST_UNDERLAYER_NAME = "waist_fixed_painted_underlayer"


def _record(layers, name):
    return next(record for record in layers if record["name"] == name)


def _group_opacity(layers, names):
    """Return effective alpha for a top-to-bottom layer group."""
    alpha = np.zeros(layers[0]["data"].shape[:2], dtype=np.uint8)
    for name in reversed(names):
        source = _record(layers, name)["data"][:, :, 3].astype(np.uint16)
        alpha = np.uint8(
            source + (alpha.astype(np.uint16) * (255 - source) + 127) // 255
        )
    return alpha


def _semantic_region_mask(shape, names):
    """Rasterize authored garment boundaries from the region configuration."""
    config = json.loads(REGION_CONFIG.read_text())
    height, width = shape
    if config["reference_size"] != [width, height]:
        raise AssertionError("semantic region configuration has the wrong size")
    regions = {name: points for name, points in config["regions"]}
    canvas = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(canvas)
    for name in names:
        if name not in regions:
            raise AssertionError(f"missing semantic garment region: {name}")
        draw.polygon(tuple(map(tuple, regions[name])), fill=255)
    return np.asarray(canvas, dtype=np.uint8) == 255


def _ownership_masks(source_layers):
    """Return disjoint paint ownership from semantic garment boundaries."""
    shape = source_layers[0]["data"].shape[:2]
    non_clothing_parts = _semantic_region_mask(
        shape,
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
    neck_mask = (
        (_group_opacity(source_layers, NECK) == 255)
        & _semantic_region_mask(shape, ("neck",))
        & ~non_clothing_parts
    )
    foreign_parts = non_clothing_parts | _semantic_region_mask(shape, ("neck",))
    # A moved vest reveals the blouse or waist beneath it; it does not own a
    # rectangular copy of every source pixel extracted with the vest.  Include
    # vest opacity only as occlusion coverage for those two semantic garments.
    blouse_mask = (
        (_group_opacity(source_layers, BLOUSE + VEST) == 255)
        & _semantic_region_mask(shape, ("blouse",))
        & ~foreign_parts
        & ~neck_mask
    )
    waist_mask = (
        (_group_opacity(source_layers, WAIST + VEST) == 255)
        & _semantic_region_mask(shape, ("skirt_and_belt",))
        & ~foreign_parts
        & ~neck_mask
        & ~blouse_mask
    )
    return {
        "neck": neck_mask,
        "blouse": blouse_mask,
        "waist": waist_mask,
    }


def _shift(image, dx, dy):
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


def _load_painted_underlayer(shape):
    digest = hashlib.sha256(PAINTED_UNDERLAYER.read_bytes()).hexdigest()
    if digest != PAINTED_UNDERLAYER_SHA256:
        raise AssertionError("painted neck/clothing underlayer digest changed")
    painted = np.asarray(Image.open(PAINTED_UNDERLAYER).convert("RGBA"), dtype=np.uint8)
    if painted.shape != shape:
        raise AssertionError("painted neck/clothing underlayer has the wrong size")
    if np.any((painted[:, :, 3] == 0) & np.any(painted[:, :, :3] != 0, axis=2)):
        raise AssertionError("painted underlayer stores RGB outside consumed pixels")
    return painted, digest


def clean_layers(source_layers):
    """Return cleaned layers plus immutable pixel-provenance counts."""
    layers = copy.deepcopy(source_layers)
    approved = composite(source_layers)
    changed = {}

    obsolete_reveal = _record(layers, OLD_REVEAL)
    if obsolete_reveal["visible"]:
        raise AssertionError("obsolete approximate reveal unexpectedly visible")
    changed["removed_approximate_reveal_pixels"] = int(
        np.count_nonzero(obsolete_reveal["data"][:, :, 3])
    )
    layers.remove(obsolete_reveal)

    painted, digest = _load_painted_underlayer(approved.shape)
    if np.any((painted[:, :, 3] > 0) & (approved[:, :, 3] == 0)):
        raise AssertionError("painted neck/clothing underlayer exceeds silhouette")

    # Intersect opaque coverage with the authored garment polygons.  This
    # rejects rectangular extraction areas that happen to live in a source
    # layer but semantically belong to hair, skin, blouse, or sleeves.
    ownership = _ownership_masks(source_layers)
    neck_mask = ownership["neck"]
    blouse_mask = ownership["blouse"]
    waist_mask = ownership["waist"]
    consumed_mask = neck_mask | blouse_mask | waist_mask
    painted_mask = painted[:, :, 3] > 0
    if not np.array_equal(painted_mask, consumed_mask):
        raise AssertionError("painted underlayer contains unconsumed pixels")

    def painted_part(mask):
        part = np.zeros_like(painted)
        part[mask] = painted[mask]
        return part

    neck_paint = painted_part(neck_mask)
    blouse_paint = painted_part(blouse_mask)
    waist_paint = painted_part(waist_mask)

    neck_base_index = next(
        index for index, record in enumerate(layers) if record["name"] == NECK_BASE
    )
    layers.insert(
        neck_base_index,
        {"name": NECK_UNDERLAYER_NAME, "data": neck_paint, "visible": True},
    )
    for name, data in (
        (BLOUSE_UNDERLAYER_NAME, blouse_paint),
        (WAIST_UNDERLAYER_NAME, waist_paint),
    ):
        torso_base_index = next(
            index
            for index, record in enumerate(layers)
            if record["name"] == TORSO_BASE
        )
        layers.insert(
            torso_base_index,
            {"name": name, "data": data, "visible": True},
        )
    changed["painted_neck_collar_pixels"] = int(
        np.count_nonzero(neck_paint[:, :, 3])
    )
    changed["painted_blouse_pixels"] = int(
        np.count_nonzero(blouse_paint[:, :, 3])
    )
    changed["painted_waist_pixels"] = int(
        np.count_nonzero(waist_paint[:, :, 3])
    )
    changed["painted_underlayer_sha256"] = digest

    cleaned = composite(layers)
    if not np.array_equal(cleaned, approved):
        raise AssertionError("neck/clothing cleanup changed approved initial appearance")
    return layers, changed


def _audit_scenes(layers, default):
    expected_alpha = default[:, :, 3]
    moves = {
        "neck_displaced": {name: (6, 0) for name in NECK},
        "vest_displaced": {
            **{name: (-8, 0) for name in VEST_LEFT},
            **{name: (8, 0) for name in VEST_RIGHT},
        },
        "blouse_displaced": {"blouse": (0, -6)},
        "waist_displaced": {"skirt_and_belt": (0, 8)},
    }
    hidden_groups = {
        "neck_hidden": NECK,
        "vest_hidden": VEST,
        "blouse_hidden": BLOUSE,
        "waist_hidden": WAIST,
    }
    scenes = {}
    for name, names in hidden_groups.items():
        scenes[name] = composite(layers, hide=names)
    moved_layer_sets = {name: _moved_layers(layers, move) for name, move in moves.items()}
    scenes.update(
        {
            name: composite(records)
            for name, records in moved_layer_sets.items()
        }
    )

    checks = {}
    for name, image in scenes.items():
        holes = int(np.count_nonzero((image[:, :, 3] == 0) & (expected_alpha > 0)))
        changed_pixels = int(
            np.count_nonzero(np.any(image[:, :, :3] != default[:, :, :3], axis=2))
        )
        checks[name] = {
            "lost_alpha_pixels": holes,
            "changed_rgb_pixels_vs_default": changed_pixels,
            "pass": holes == 0 and changed_pixels > 0,
        }

    displacement_groups = {
        "neck_displaced": NECK,
        "vest_displaced": VEST,
        "blouse_displaced": BLOUSE,
        "waist_displaced": WAIST,
    }
    for scene_name, names in displacement_groups.items():
        original_opacity = _group_opacity(layers, names)
        moved_opacity = _group_opacity(moved_layer_sets[scene_name], names)
        vacated = (original_opacity == 255) & (moved_opacity == 0)
        hidden = scenes[scene_name.replace("displaced", "hidden")]
        moved = scenes[scene_name]
        matches_hidden = np.all(moved == hidden, axis=2)
        matches_default = np.all(moved == default, axis=2)
        vacated_count = int(np.count_nonzero(vacated))
        hidden_count = int(np.count_nonzero(vacated & matches_hidden))
        default_count = int(np.count_nonzero(vacated & matches_default))
        retained_fraction = default_count / max(vacated_count, 1)
        checks[scene_name].update(
            {
                "vacated_original_silhouette_pixels": vacated_count,
                "vacated_pixels_matching_hidden_underpainting": hidden_count,
                "vacated_pixels_still_matching_default": default_count,
                "retained_default_fraction": retained_fraction,
            }
        )
        checks[scene_name]["pass"] &= (
            vacated_count > 0
            and hidden_count == vacated_count
            and retained_fraction < 0.7
        )
    return scenes, checks


def _write_preview(default, scenes, destination):
    entries = [("cleaned default", default)] + list(scenes.items())
    tile_width, tile_height = 360, 500
    columns = 3
    rows = (len(entries) + columns - 1) // columns
    panel = Image.new("RGB", (tile_width * columns, tile_height * rows), (250, 246, 242))
    draw = ImageDraw.Draw(panel)
    for index, (name, array) in enumerate(entries):
        image = Image.fromarray(array, "RGBA").crop((180, 300, 910, 1320))
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
):
    source_layers, size = parse_psd(SOURCE)
    layers, changed = clean_layers(source_layers)
    approved = composite(source_layers)
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
    if reloaded_size != size or len(reloaded) != 53:
        raise AssertionError("candidate PSD did not reload with expected structure")
    if not np.array_equal(composite(reloaded), cleaned):
        raise AssertionError("reloaded candidate changed the cleaned appearance")

    scenes, scene_checks = _audit_scenes(reloaded, cleaned)
    if not all(check["pass"] for check in scene_checks.values()):
        raise AssertionError("a neck/clothing hidden or displaced scene failed audit")
    _write_preview(cleaned, scenes, preview)

    report = {
        "source_psd": str(SOURCE.relative_to(ROOT)),
        "painted_underlayer": str(PAINTED_UNDERLAYER.relative_to(ROOT)),
        "output_psd": (
            str(output_psd.relative_to(ROOT))
            if output_psd.is_relative_to(ROOT)
            else str(output_psd)
        ),
        "layer_count": len(reloaded),
        "initial_rgb_pixel_diff": int(
            np.count_nonzero(np.any(cleaned[:, :, :3] != approved[:, :, :3], axis=2))
        ),
        "initial_alpha_pixel_diff": int(
            np.count_nonzero(cleaned[:, :, 3] != approved[:, :, 3])
        ),
        "changed_painted_pixels": changed,
        "pixel_sources": [
            "approved v8 hair/head-cleaned candidate",
            "separately painted neck/clothing underlayer",
        ],
        "flat_fill_or_blur_used": False,
        "approved_costume_redesigned": False,
        "scene_checks": scene_checks,
        "art_ready_for_cubism": False,
    }
    audit_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(
        f"PASS: {output_psd} "
        f"({len(reloaded)} layers; approved appearance preserved)"
    )
    return report


if __name__ == "__main__":
    build_candidate()
