"""Round-trip and independent toggles; visual acceptance is recorded separately."""
import sys
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from audit_psd import parse_psd, composite
from build_expressions_v9 import SOURCE, DEST, PARTS


def main():
    old, _ = parse_psd(SOURCE)
    new, _ = parse_psd(DEST/'koma_expressions_v9.psd')
    before, after = composite(old), composite(new)
    assert np.array_equal(before, after), 'neutral art changed'
    assert np.array_equal(after, np.asarray(Image.open(
        DEST/'koma_expressions_v9.psd').convert('RGBA'))), 'merged PSD differs'
    originals = {r['name']: r for r in old}
    names = [r['name'] for r in new]
    assert len(names) == len(set(names)) == len(old)+1
    modified = {p+'.open' for p in PARTS}
    for r in new:
        if r['name'] in originals and r['name'] not in modified:
            assert r['visible'] == originals[r['name']]['visible']
            assert np.array_equal(r['data'], originals[r['name']]['data'])
    # Every combination includes asymmetric blinking. Opening and closing one
    # feature must leave all pixels outside that feature's support unchanged.
    for bits in range(8):
        selected = [p for i,p in enumerate(PARTS) if bits & (1 << i)]
        frame = composite(new, hide=[p+'.open' for p in selected],
                          show=[p+'.closed' for p in selected])
        affected = np.zeros(before.shape[:2], dtype=bool)
        for r in new:
            if r['name'] in [p+s for p in selected for s in ('.open','.closed')]:
                affected |= r['data'][:,:,3] > 0
        assert np.array_equal(frame[~affected], before[~affected])
        assert np.array_equal(frame[:,:,3], before[:,:,3])
    print('PASS: exact neutral/PSD merged, inherited layers preserved, eight independent expression combinations')


if __name__ == '__main__':
    main()
