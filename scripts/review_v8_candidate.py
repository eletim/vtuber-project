#!/usr/bin/env python3
"""Export independent visual evidence from an existing, layered VTuber PSD.

This is deliberately a *review* tool, not a pass/fail art-quality classifier.
It does not modify the PSD, replace paint, or silently approve underlayers.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from audit_psd import composite, parse_psd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PSD = ROOT / "assets/parts/v8/koma_sleeves_arms_hands_cleaned_v8.psd"
DEFAULT_ORIGINAL = ROOT / "assets/original/koma_confirmed.png"

# Each group lists *movable* parts, not the fixed painted underlayer that ought
# to become visible when the group is displaced or hidden.
SCENES = {
    "bangs": ("front_bangs",),
    "side_hair_left": ("hair_side_left",),
    "side_hair_right": ("hair_side_right",),
    "rear_hair": ("hair_back_left", "hair_back_right"),
    "accessory": ("hair_accessory",),
    "crown": ("hair_crown",),
    "neck": ("neck",),
    "vest": ("vest_left", "vest_right"),
    "blouse": ("blouse",),
    "waist": ("skirt_and_belt",),
    "sleeves": ("left_arm_sleeve", "right_arm_sleeve"),
    "hands": ("left_hand", "right_hand"),
}

REGION_CROPS = {
    "bangs": (100, 0, 990, 830),
    "side_hair_left": (0, 80, 570, 1070),
    "side_hair_right": (510, 80, 1086, 1070),
    "rear_hair": (0, 20, 1086, 1170),
    "accessory": (160, 0, 900, 650),
    "crown": (130, 0, 970, 650),
    "neck": (260, 300, 830, 1060),
    "vest": (160, 470, 970, 1370),
    "blouse": (150, 450, 980, 1320),
    "waist": (150, 730, 1000, 1448),
    "sleeves": (0, 550, 1086, 1448),
    "hands": (0, 930, 1086, 1448),
}

# Translation is a modest stress test, not a Cubism deformation substitute.
MOVE = {
    "bangs": (6, 0),
    "side_hair_left": (-8, -3),
    "side_hair_right": (8, -3),
    "rear_hair": (5, 0),
    "accessory": (5, 4),
    "crown": (0, -5),
    "neck": (6, 0),
    "vest": (8, 0),
    "blouse": (0, -6),
    "waist": (0, 8),
    "sleeves": (8, -4),
    "hands": (8, -4),
}


def translate_pixels(data: np.ndarray, dx: int, dy: int) -> np.ndarray:
    """Translate a part without wrapping image content around the borders."""
    result = np.zeros_like(data)
    height, width = data.shape[:2]
    sx0, sy0 = max(0, -dx), max(0, -dy)
    sx1, sy1 = min(width, width - dx), min(height, height - dy)
    tx0, ty0 = max(0, dx), max(0, dy)
    tx1, ty1 = min(width, width + dx), min(height, height + dy)
    result[ty0:ty1, tx0:tx1] = data[sy0:sy1, sx0:sx1]
    return result


def moved_composite(layers: list, names: tuple[str, ...], dx: int, dy: int) -> np.ndarray:
    names = set(names)
    shifted = [
        {**record, "data": translate_pixels(record["data"], dx if not record["name"].startswith("left_") else -abs(dx), dy)}
        if record["name"] in names
        else record
        for record in layers
    ]
    return composite(shifted)


def on_background(rgba: np.ndarray, color=(241, 238, 234)) -> Image.Image:
    image = Image.fromarray(rgba, "RGBA")
    base = Image.new("RGBA", image.size, (*color, 255))
    base.alpha_composite(image)
    return base.convert("RGB")


def comparison_strip(original: np.ndarray, hidden: np.ndarray, moved: np.ndarray,
                     crop: tuple[int, int, int, int], label: str) -> Image.Image:
    """Use native pixels, not a tiny scaled montage that hides edge defects."""
    x0, y0, x1, y1 = crop
    width, height = x1 - x0, y1 - y0
    panel = Image.new("RGB", (width * 3, height + 30), (238, 234, 230))
    draw = ImageDraw.Draw(panel)
    for i, (name, frame) in enumerate((("approved", original), ("hidden", hidden), ("displaced", moved))):
        panel.paste(on_background(frame).crop(crop), (i * width, 30))
        draw.text((i * width + 8, 9), f"{label}: {name}", fill=(35, 25, 25))
    return panel


def run_audit(psd: Path, approved_path: Path, out: Path, groups: tuple[str, ...] | None = None, baseline_psd: Path | None = None) -> dict:
    psd = Path(psd)
    approved_path = Path(approved_path)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    layers, size = parse_psd(psd)
    initial = composite(layers)
    approved = np.asarray(Image.open(approved_path).convert("RGBA"))
    if approved.shape != initial.shape:
        raise ValueError("approved image size differs from PSD")
    available = {r["name"] for r in layers}
    labels = [r["name"] for r in layers]
    if len(labels) != len(set(labels)):
        raise ValueError("PSD has duplicate part names")
    # The confirmed 1086x1448 artwork is an opaque RGB illustration with a
    # painted background. Layered PSDs have *transparent* outer background.
    # Comparing their alpha channels would incorrectly fail every real PSD.
    foreground = initial[:, :, 3] > 0
    foreground_rgb_changed = int(np.count_nonzero(
        np.any(initial[:, :, :3] != approved[:, :, :3], axis=2) & foreground
    ))
    baseline_alpha_changed = None
    if baseline_psd is not None:
        baseline_layers, baseline_size = parse_psd(Path(baseline_psd))
        if size != baseline_size:
            raise ValueError("baseline PSD canvas size differs")
        baseline_alpha_changed = int(np.count_nonzero(
            initial[:, :, 3] != composite(baseline_layers)[:, :, 3]
        ))
    Image.fromarray(initial).save(out / "initial_full.png")

    expressions = {
        "normal": (),
        "eyes_closed": ("eye_screen_left.closed", "eye_screen_right.closed"),
        "mouth_closed": ("mouth.closed",),
        "both_closed": ("eye_screen_left.closed", "eye_screen_right.closed", "mouth.closed"),
    }
    if not all(name in available for show in expressions.values() for name in show):
        raise ValueError("approved expression layers are missing")
    expression_frames = []
    for label, show in expressions.items():
        frame = composite(layers, show=show)
        Image.fromarray(frame).save(out / f"expression_{label}.png")
        expression_frames.append(on_background(frame).resize((326, 434)))
    expression_frames[0].save(
        out / "expression_cycle.gif", save_all=True, append_images=expression_frames[1:],
        duration=[750, 750, 750, 900], loop=0, optimize=False,
    )

    group_report = {}
    for label in tuple(SCENES) if groups is None else groups:
        if label not in SCENES:
            raise ValueError(f"unknown group: {label}")
        names = SCENES[label]
        missing = [name for name in names if name not in available]
        if missing:
            raise ValueError(f"{label}: missing movable layer(s): {missing}")
        dx, dy = MOVE[label]
        hidden = composite(layers, hide=names)
        displaced = moved_composite(layers, names, dx, dy)
        Image.fromarray(hidden).save(out / f"{label}_hidden.png")
        Image.fromarray(displaced).save(out / f"{label}_displaced.png")
        comparison_strip(initial, hidden, displaced, REGION_CROPS[label], label).save(
            out / f"{label}_review_strip.png"
        )
        group_report[label] = {
            "movable_layers": list(names),
            "shift_pixels": [dx, dy],
            "changed_when_hidden": int(np.count_nonzero(np.any(hidden != initial, axis=2))),
            "changed_when_displaced": int(np.count_nonzero(np.any(displaced != initial, axis=2))),
            "alpha_lost_when_hidden": int(np.count_nonzero((initial[:, :, 3] > 0) & (hidden[:, :, 3] == 0))),
            "alpha_lost_when_displaced": int(np.count_nonzero((initial[:, :, 3] > 0) & (displaced[:, :, 3] == 0))),
            "visual_review": "PENDING",
        }
    report = {
        "psd": str(psd),
        "sha256": hashlib.sha256(psd.read_bytes()).hexdigest(),
        "size": list(size),
        "layer_count": len(layers),
        "approved_initial_foreground_rgb_changed_pixels": foreground_rgb_changed,
        "baseline_alpha_changed_pixels": baseline_alpha_changed,
        "structural_check": "PASS" if foreground_rgb_changed == 0 and (baseline_alpha_changed in (0, None)) else "FAIL",
        "visual_review": "PENDING — review full-resolution hidden/displaced strips",
        "cubism_rigging": "NOT_STARTED",
        "groups": group_report,
        "note": "Alpha gaps may be intentional for detached exterior shapes. Neither zero holes nor RGB match proves painted quality.",
    }
    (out / "review.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    if report["structural_check"] != "PASS":
        raise AssertionError("initial artwork differs from approved foreground or baseline PSD alpha")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--psd", type=Path, default=DEFAULT_PSD)
    parser.add_argument("--original", type=Path, default=DEFAULT_ORIGINAL)
    parser.add_argument("--out", type=Path, default=ROOT / "artifacts/v8_visual_review")
    parser.add_argument("--baseline-psd", type=Path, default=ROOT / "assets/parts/v8/koma_expression_repaired_v8.psd")
    parser.add_argument("--groups", nargs="*", choices=SCENES.keys(), default=None)
    args = parser.parse_args()
    report = run_audit(args.psd, args.original, args.out, None if args.groups is None else tuple(args.groups), args.baseline_psd)
    print(json.dumps({"status": report["visual_review"], "groups": list(report["groups"]), "output": str(args.out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()