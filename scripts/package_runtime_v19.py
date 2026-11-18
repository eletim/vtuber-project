#!/usr/bin/env python3
"""Package independently rendered body parts and the corresponding PSD controls."""
from pathlib import Path
import argparse
from package_runtime_v15 import build

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination',type=Path)
    args=parser.parse_args()
    build(args.destination,version='v19',guide='docs/separated-body-v19.md',
          artwork_folder='assets/parts/v19')
