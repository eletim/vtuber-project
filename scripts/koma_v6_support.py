"""Helper geometry/feature adapters for the optimized Koma PSD builder."""
from pathlib import Path
import json
import cv2
import numpy as np
from build_psd import extract_foreground as foreground_alpha, load_labels
from build_expression_v3 import FEATURES, artwork as paint_rgba

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config/koma_regions.json").read_text(encoding="utf-8"))
REGIONS = CONFIG["regions"]
REF_W, REF_H = CONFIG["reference_size"]
FACE_OUTLINE = [(438,178),(520,164),(603,178),(666,213),(687,258),
    (690,310),(671,355),(632,398),(581,432),(535,444),
    (482,430),(434,400),(391,365),(360,318),(353,274),(381,225)]

def region_labels(size):
    w, h = size
    return load_labels(w, h, CONFIG)

def region_polygon_mask(size, vertices):
    w, h = size
    pts = np.asarray(vertices, dtype=np.float32).copy()
    pts[:, 0] *= w / REF_W
    pts[:, 1] *= h / REF_H
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.fillPoly(mask, [np.rint(pts).astype(np.int32)], 255)
    return mask > 0

def polygon_mask(w, h, vertices):
    return region_polygon_mask((w, h), vertices).astype(np.uint8) * 255
