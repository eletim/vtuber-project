#!/usr/bin/env bash
# Import the approved VTuber artwork, validating every file before Git LFS push.
set -euo pipefail
if [[ $# -ne 2 ]]; then
  echo "Usage: bash scripts/import_v8_assets.sh /path/to/vtuber-project /path/to/koma_v8_psd_expression_fix_bundle.zip" >&2
  exit 2
fi
repo_dir="$(cd "$1" && pwd)"
archive="$(realpath "$2")"
cd "$repo_dir"
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "ERROR: not a Git repository" >&2; exit 2
fi
if [[ -n "$(git status --porcelain)" ]]; then
  echo "ERROR: working tree has changes; commit/stash them before importing" >&2; exit 2
fi
if ! git lfs version >/dev/null 2>&1; then
  echo "ERROR: Git LFS not installed. On Ubuntu: sudo apt install git-lfs" >&2; exit 2
fi
if [[ ! -f "$archive" ]]; then
  echo "ERROR: archive does not exist" >&2; exit 2
fi
git fetch origin assets/import-v8
if git show-ref --verify --quiet refs/heads/assets/import-v8; then
  git switch assets/import-v8
  git pull --ff-only origin assets/import-v8
else
  git switch --track -c assets/import-v8 origin/assets/import-v8
fi
git lfs install --local
python3 - "$archive" <<'PY'
from pathlib import Path
from zipfile import ZipFile
import sys
import hashlib
root=Path.cwd()
expected={}
for line in (root/"docs/v8-approved-assets.sha256").read_text().splitlines():
    sha, relative=line.split(maxsplit=1)
    relative=relative.strip()
    if not relative.startswith("assets/") or Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise SystemExit("Invalid manifest path: "+relative)
    expected[relative]=sha.lower()
if len(expected)!=9:
    raise SystemExit("Expected exactly 9 manifest entries")
with ZipFile(sys.argv[1]) as z:
    missing=set(expected)-set(z.namelist())
    if missing: raise SystemExit("Archive missing "+str(sorted(missing)))
    checked={}
    for relative,sha in expected.items():
        content=z.read(relative)
        if hashlib.sha256(content).hexdigest()!=sha:
            raise SystemExit("SHA256 mismatch: "+relative)
        checked[relative]=content
    for relative,content in checked.items():
        p=root/relative
        if p.exists() and hashlib.sha256(p.read_bytes()).hexdigest()!=expected[relative]:
            raise SystemExit("Refusing to overwrite differing artwork: "+relative)
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes(content)
        print("Verified "+relative+" ("+str(len(content))+" bytes)")
PY
git add -- assets/original/koma_confirmed.png \
  assets/expression_references/eyes_closed_mouth_open.png \
  assets/expression_references/eyes_open_mouth_closed.png \
  assets/parts/v7/koma_illustrated_underlayers_v7.psd \
  assets/parts/v8/koma_expression_repaired_v8.psd \
  assets/parts/v8/koma_expression_v8.gif \
  assets/parts/v8/expression_comparison_v8.png \
  assets/parts/v8/audit_report.json \
  assets/parts/v8/README.md
if [[ "$(git check-attr filter -- assets/parts/v8/koma_expression_repaired_v8.psd)" != *"filter: lfs" ]]; then
  echo "ERROR: PSD is not tracked with Git LFS" >&2; exit 1
fi
if ! git diff --cached --quiet; then
  git commit -m "assets: import approved PSD v7/v8 and expression artwork"
  git push -u origin assets/import-v8
fi
git lfs ls-files
git status --short
echo "DONE: uploaded to assets/import-v8. Check the PR before merging."
