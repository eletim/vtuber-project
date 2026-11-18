#!/usr/bin/env python3
"""Package optional local conversation; no model binaries, keys or AI sample claim."""
import argparse
from pathlib import Path
from package_runtime_v20 import package
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('destination',type=Path)
    p.add_argument('--evidence',type=Path,default=Path(__file__).resolve().parents[1]/'assets/parts/v20',help='Verified v20 direct-readout WAV/provenance; not an AI reply sample')
    args=p.parse_args();package(args.destination,args.evidence,version='v21',guide='docs/local-conversation-v21.md')
