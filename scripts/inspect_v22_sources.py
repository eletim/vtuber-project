from pathlib import Path
from psd_groups_v14 import parse_psd_groups, LayerGroup
root=Path(__file__).resolve().parents[1]
for name in ['v19/koma_separated_body_v19.psd','v8/koma_hair_head_cleaned_v8.psd']:
    nodes,size=parse_psd_groups(root/'assets/parts'/name)
    print(name,size)
    def walk(nodes,level=0):
        for n in nodes:
            print(' '*level,n.name,n.visible)
            if isinstance(n,LayerGroup): walk(n.children,level+1)
    walk(nodes)
