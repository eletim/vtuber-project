#!/usr/bin/env python3
"""Package the mouth-rendering correction without overwriting v15 delivery."""
from pathlib import Path
import argparse
from package_runtime_v15 import build

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination',type=Path)
    args=parser.parse_args()
    build(args.destination,version='v16',guide='docs/mouth-rendering-v16.md')
