from pathlib import Path
import subprocess,sys,os,json
sys.stdout.reconfigure(encoding='utf-8')
out=Path('assets/parts/v48')
commands=[('js',['node','--test',*[str(p) for p in sorted(Path('runtime/tests').glob('*.test.js'))]]),('python',[sys.executable,'-u','-m','unittest','-v','test_runtime_server','test_acting_sync_v39','test_speech_broadcast_v20','test_speech_lifecycle_v20','test_conversation_v21','test_voice_runtime','test_expression_runtime','test_local_launcher_v21','test_eye_controls_v46'])]
report={}
for name,cmd in commands:

 with (out/f'{name}-final-tests.txt').open('w',encoding='utf-8') as stream: result=subprocess.run(cmd,stdout=stream,stderr=stream,timeout=180)
 log=(out/f'{name}-final-tests.txt').read_text(encoding='utf-8');report[name]={'exit_code':result.returncode,'log':f'{name}-final-tests.txt'};print(name,log[-700:],flush=True)
 if result.returncode:
  (out/'final-tests.json').write_text(json.dumps(report,indent=2));sys.exit(result.returncode)
(out/'final-tests.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
