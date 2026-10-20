"""Check independent ownership, hidden anatomy, expressions, and PSD round trip."""
from pathlib import Path
import sys
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from audit_psd import composite, parse_psd
from clean_neck_clothing_v8 import _group_opacity, _moved_layers
from clean_sleeves_arms_hands_v8 import (
    OUTPUT, SOURCE, build_candidate, clean_layers, ownership_masks, scenes,
)


def main():
    source, size = parse_psd(SOURCE)
    generated = clean_layers(source)
    masks = ownership_masks()
    scope = np.logical_or.reduce(list(masks.values()))
    original = composite(source)
    assert np.array_equal(composite(generated), original)
    assert len({r['name'] for r in generated}) == len(generated)
    # All old layers lose their in-scope duplicates, with no unrelated edits.
    for before, after in zip(source, generated[10:]):
        assert np.array_equal(before['data'][~scope], after['data'][~scope])
        if before['visible']:
            assert not np.any(after['data'][scope])
        else:
            assert np.array_equal(before['data'], after['data'])
    by_name = {r['name']: r for r in generated}
    for side in ('left', 'right'):
        for part in ('hand', 'arm_sleeve'):
            name = f'{side}_{part}'
            assert np.array_equal(by_name[name]['data'][masks[name]], original[masks[name]])
        names = [r['name'] for r in generated]
        assert names.index(f'{side}_arm_wrist_join') < names.index(f'{side}_inner_cuff')
        arm = by_name[f'{side}_arm_wrist_join']['data']
        torso = by_name[f'{side}_torso_join']['data']
        assert not np.any((arm[:, :, 3] > 0) & (torso[:, :, 3] > 0))
        # Skin is painted continuously along the forearm, not a zero-hole
        # result caused by keeping a fixed sleeve/hand copy underneath.
        for y in range(760, 1170, 10):
            x = round(np.interp(y, [760, 1160], [303, 198] if side == 'left' else [824, 913]))
            assert arm[y, x, 3] >= 250, (side, x, y)
    # The wrist must have one continuous contour, without the old flared
    # ends or detached duplicate outlines. Check the arm and hand themselves
    # so fixed torso/clothing layers cannot conceal a broken join.
    for side, start, stop in (('left', 1180, 1260), ('right', 1200, 1280)):
        limb = composite([by_name[f'{side}_hand'], by_name[f'{side}_arm_wrist_join']])
        edges = []
        for y in range(start, stop):
            xs = np.flatnonzero(limb[y, :, 3] >= 128)
            assert len(xs) > 0, (side, y, 'missing wrist')
            assert len(xs) == xs[-1] - xs[0] + 1, (side, y, 'doubled contour')
            edges.append((xs[0], xs[-1]))
        assert np.max(np.abs(np.diff(edges, axis=0))) <= 2, 'square/flared join'
        probes = ((160, 1210), (138, 1250)) if side == 'left' else ((958, 1238),)
        for x, y in probes:
            assert limb[y, x, 3] == 0, 'old cuff/flare retained as skin'
    views = scenes(generated)
    hidden = views['hands_hidden']
    for x, y in ((125, 1340), (990, 1350)):
        assert original[y, x, 3] > 0
        assert hidden[y, x, 3] == 0, 'fixed palm remained behind'
    for view in views.values():
        assert np.any(view != original)
    # Vacated pixels must reveal the same underlying art as hiding the part,
    # rather than exposing a stationary copy of the original silhouette.
    for side in ('left', 'right'):
        for names in ((f'{side}_hand',),
                      (f'{side}_arm_sleeve', f'{side}_inner_cuff')):
            dx = -8 if side == 'left' else 8
            moved = _moved_layers(generated, {n: (dx, -4) for n in names})
            vacated = ((_group_opacity(generated, names) == 255)
                       & (_group_opacity(moved, names) == 0))
            assert np.count_nonzero(vacated) > 0
            hidden_part = composite(generated, hide=names)
            assert np.array_equal(composite(moved)[vacated], hidden_part[vacated])
            other_half = slice(543, None) if side == 'left' else slice(None, 543)
            assert np.array_equal(hidden_part[:, other_half], original[:, other_half])
    # Expression switching and untouched regions remain identical.
    for eyes in (False, True):
        for mouth in (False, True):
            show = (['eye_screen_left.closed', 'eye_screen_right.closed'] if eyes else [])
            show += ['mouth.closed'] if mouth else []
            assert np.array_equal(composite(source, show=show), composite(generated, show=show))
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / 'candidate.psd'
        report = build_candidate(target)
        loaded, actual_size = parse_psd(target)
        assert actual_size == size
        for before, after in zip(generated, loaded):
            assert before['name'] == after['name']
            assert before['visible'] == after['visible']
            assert np.array_equal(before['data'], after['data'])
        # The retained PSD may use another zlib version. Compare decoded art,
        # names and visibility rather than the compressed byte representation.
        retained, retained_size = parse_psd(OUTPUT)
        assert retained_size == actual_size and len(retained) == len(loaded)
        for before, after in zip(retained, loaded):
            assert before['name'] == after['name']
            assert before['visible'] == after['visible']
            assert np.array_equal(before['data'], after['data'])
        assert report['initial_rgba_changed_pixels'] == 0
    print('PASS: sleeve/hand ownership, hidden arms, expressions, reproducible PSD')


if __name__ == '__main__':
    main()
