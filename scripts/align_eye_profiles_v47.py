from pathlib import Path
import json
for file,ys in [('left-neutral.json',[96,97,89,82,76,73,72,71,72]),('right/right-neutral.json',[80,77,73,71,71,72,73,73])]:
 p=Path('runtime/model/eyes_v46')/file;m=json.loads(p.read_text());m['closed']=[[x,y] for (x,_),y in zip(m['closed'],ys)];m['authoredClosure']=True;p.write_text(json.dumps(m,indent=2)+'\n')
