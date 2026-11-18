#!/usr/bin/env python3
"""Package richer arm/body motion with the unchanged accepted v17 artwork."""
from pathlib import Path
import argparse
from package_runtime_v15 import build

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination',type=Path)
    args=parser.parse_args()
    build(args.destination,version='v18',guide='docs/arm-body-motion-v18.md',
          artwork_folder='assets/parts/v17')
