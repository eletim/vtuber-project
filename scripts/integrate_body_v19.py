#!/usr/bin/env python3
"""Merge the art-owned v19 fragment without changing any accepted face records."""
import argparse
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / 'runtime/model/model.json'
FRAGMENT = ROOT / 'assets/parts/v19/model-body-v19.json'
CORE = ('name', 'size', 'base', 'parts', 'mesh', 'skinning', 'expressions', 'expression_source_psd')


def integrate(check=False, sampling=None):
    model = json.loads(MODEL.read_text())
    original = {key: model[key] for key in CORE}
    fragment = json.loads(FRAGMENT.read_text())
    assert set(fragment) <= {'bodyLayers', 'bodyRig', 'source_psd'}, 'unexpected art fragment keys'
    assert {'bodyLayers', 'bodyRig', 'source_psd'} <= set(fragment)
    ids = set()
    roles = set()
    for layer in fragment['bodyLayers']:
        assert layer['id'] not in ids, layer['id']
        ids.add(layer['id'])
        roles.add(layer['role'])
        x0, y0, x1, y1 = layer['rect']
        assert 0 <= x0 < x1 <= model['size'][0] and 0 <= y0 < y1 <= model['size'][1], layer['id']
        for file in {layer['file'], *layer.get('expressionFiles', {}).values()}:
            assert file.startswith('body_v19/') and '..' not in Path(file).parts, file
            data = (MODEL.parent / file).read_bytes()
            assert data[:8] == b'\x89PNG\r\n\x1a\n', file
            assert struct.unpack('>II', data[16:24]) == (x1-x0, y1-y0), f'crop mismatch: {file}'
    assert roles == {'root', 'skirt', 'torso', 'armLeft', 'armRight', 'head'}
    heads = [layer for layer in fragment['bodyLayers'] if layer.get('features')]
    assert len(heads) == 1 and heads[0]['role'] == 'head'
    assert set(heads[0]['expressionFiles']) == {expression['id'] for expression in model['expressions']}
    assert 0 < fragment['bodyRig']['skirtRevealLimitPixels'] <= 3
    merged = {**model, **fragment, 'format': 'koma-part-mesh-3'}
    if sampling is not None:
        merged['bodySampling'] = sampling
    assert {key: merged[key] for key in CORE} == original, 'accepted face declarations changed'
    if check:
        assert merged == model, 'model.json is stale; integrate the latest art fragment'
    else:
        MODEL.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': 'PASS', 'mode': 'check' if check else 'integrate',
                      'layers': len(fragment['bodyLayers']), 'sampling': merged.get('bodySampling', 'linear'),
                      'face_records_unchanged': True}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--sampling', choices=('linear', 'coverage-2x'), help='Explicitly select the verified production sampling mode.')
    args = parser.parse_args()
    integrate(args.check, args.sampling)
