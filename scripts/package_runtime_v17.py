#!/usr/bin/env python3
"""Package the image-tool skin correction without replacing prior deliveries."""
from pathlib import Path
import argparse
from package_runtime_v15 import build

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination',type=Path)
    args=parser.parse_args()
    build(args.destination,version='v17',guide='docs/mouth-skin-v17.md',
          artwork_folder='assets/parts/v17')
