#!/usr/bin/env python3
"""Validate the five approved source assets without modifying them."""
from __future__ import annotations

import hashlib
import struct
import subprocess
import sys
import zlib
from pathlib import Path

from audit_psd import parse_psd


APPROVED_ASSETS = (
    "assets/original/koma_confirmed.png",
    "assets/expression_references/eyes_closed_mouth_open.png",
    "assets/expression_references/eyes_open_mouth_closed.png",
    "assets/parts/v7/koma_illustrated_underlayers_v7.psd",
    "assets/parts/v8/koma_expression_repaired_v8.psd",
)
V8_PSD = "assets/parts/v8/koma_expression_repaired_v8.psd"
LFS_POINTER_PREFIX = b"version https://git-lfs.github.com/spec/v1\n"


class ValidationError(Exception):
    """An approved asset does not satisfy the input baseline."""


def load_expected_hashes(manifest: Path) -> dict[str, str]:
    expected: dict[str, str] = {}
    try:
        lines = manifest.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValidationError(f"cannot read checksum manifest: {exc}") from exc

    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        fields = line.split(maxsplit=1)
        if len(fields) != 2 or len(fields[0]) != 64:
            raise ValidationError(f"invalid manifest line {line_number}")
        digest, relative = fields[0].lower(), fields[1].strip().lstrip("*")
        try:
            int(digest, 16)
        except ValueError as exc:
            raise ValidationError(f"invalid SHA-256 on manifest line {line_number}") from exc
        if relative in expected:
            raise ValidationError(f"duplicate manifest entry: {relative}")
        expected[relative] = digest

    missing = set(APPROVED_ASSETS) - expected.keys()
    if missing:
        raise ValidationError(f"manifest is missing approved assets: {sorted(missing)}")
    return expected


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def reject_pointer(path: Path) -> None:
    try:
        with path.open("rb") as stream:
            first_line = stream.readline(200).rstrip(b"\r\n")
    except OSError as exc:
        raise ValidationError(f"cannot read {path}: {exc}") from exc
    if first_line == LFS_POINTER_PREFIX.rstrip(b"\n"):
        raise ValidationError(f"Git LFS pointer is not approved asset data: {path}")


def verify_head_blob(repo: Path, relative: str, expected_hash: str) -> None:
    object_name = f"HEAD:{relative}"
    try:
        object_type = subprocess.run(
            ["git", "cat-file", "-t", object_name],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        blob = subprocess.run(
            ["git", "cat-file", "blob", object_name],
            cwd=repo,
            check=True,
            capture_output=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValidationError(f"cannot read committed Git object for {relative}") from exc
    if object_type != "blob" or hashlib.sha256(blob).hexdigest() != expected_hash:
        raise ValidationError(
            f"{relative} is not the full ordinary Git blob checked out from HEAD"
        )


def validate_psd(path: Path, expected_layers: int | None = None) -> int:
    try:
        layers, _ = parse_psd(path)
    except (KeyError, OSError, ValueError, struct.error, zlib.error) as exc:
        raise ValidationError(f"invalid layered PSD data: {path}: {exc}") from exc
    layer_count = len(layers)
    if not layer_count:
        raise ValidationError(f"PSD has no editable layers: {path}")
    if expected_layers is not None and layer_count != expected_layers:
        raise ValidationError(
            f"{path} has {layer_count} layers; expected {expected_layers}"
        )
    return layer_count


def validate(repo: Path) -> None:
    manifest = repo / "docs/v8-approved-assets.sha256"
    expected = load_expected_hashes(manifest)

    for relative in APPROVED_ASSETS:
        path = repo / relative
        if not path.is_file():
            raise ValidationError(f"approved asset is missing: {relative}")
        reject_pointer(path)
        actual = sha256_file(path)
        if actual != expected[relative]:
            raise ValidationError(f"SHA-256 mismatch: {relative}")
        verify_head_blob(repo, relative, expected[relative])
        print(f"OK checksum + ordinary Git blob: {relative}")

    for relative in APPROVED_ASSETS:
        if relative.endswith(".psd"):
            count = validate_psd(
                repo / relative, expected_layers=49 if relative == V8_PSD else None
            )
            print(f"OK editable PSD ({count} layers): {relative}")


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    try:
        validate(repo)
    except ValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print("PASS: all five approved input assets are usable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
