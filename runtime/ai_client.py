"""Control Koma from an AI program without a renderer-specific dependency."""
import argparse
import json
import math
import time
from urllib.request import Request,urlopen


class KomaClient:
    def __init__(self,url='http://127.0.0.1:8766'):
        self.url=url.rstrip('/')

    def _post(self,path,data,timeout=5):
        request=Request(self.url+path,json.dumps(data).encode(),{'Content-Type':'application/json'})
        with urlopen(request,timeout=timeout) as response:
            return json.load(response)

    def select(self,mode='ai'):
        return self._post('/api/mode',{'mode':mode})

    def pose(self,**parameters):
        return self._post('/api/control',{'source':'ai','parameters':parameters,'ttl_ms':2000})

    def say(self,text,emotion="auto",request_id=None):
        payload={'text':text,'emotion':emotion}
        if request_id is not None: payload['request_id']=request_id
        return self._post('/api/speech',payload,timeout=125)

    def stop(self,request_id=None):
        return self._post('/api/speech/cancel',{} if request_id is None else {'request_id':request_id})

    def voice_status(self):
        with urlopen(self.url+'/api/voice',timeout=6) as response:
            return json.load(response)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',default='http://127.0.0.1:8766')
    parser.add_argument('--say')
    parser.add_argument('--emotion',choices=['auto','neutral','happy','thoughtful','surprised'],default='auto')
    parser.add_argument('--demo',action='store_true')
    parser.add_argument('--stop',action='store_true',help='Stop synthesis and playback without switching mode')
    parser.add_argument('--voice-status',action='store_true')
    args=parser.parse_args()
    client=KomaClient(args.url)
    if args.voice_status: print(client.voice_status())
    if args.stop: print(client.stop())
    if args.say or args.demo: client.select()
    if args.say:print(client.say(args.say,args.emotion))
    if args.demo:
        for i in range(120):
            t=i*.08
            client.pose(ParamAngleX=10*math.sin(t),ParamAngleZ=3*math.sin(t*.6),
                        ParamMouthOpenY=.5+.4*math.sin(t*9))
            time.sleep(.08)
        client.pose(ParamAngleX=0,ParamAngleZ=0,ParamMouthOpenY=0)
