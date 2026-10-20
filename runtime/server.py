"""Local avatar host and shared human/AI control bus."""
import argparse
import asyncio
import json
import math
import time
import uuid
import io
import wave
from collections import OrderedDict
from voice import Voicevox
from pathlib import Path
from aiohttp import web, WSMsgType

ROOT = Path(__file__).resolve().parent
LIMITS = {'ParamAngleX': (-15,15,0), 'ParamAngleY': (-10,10,0),
          'ParamAngleZ': (-8,8,0), 'ParamBodyAngleX': (-5,5,0),
          'ParamEyeLOpen': (0,1,1), 'ParamEyeROpen': (0,1,1),
          'ParamMouthOpenY': (0,1,0), 'ParamBreath': (0,1,0.5)}


def validate_parameters(values):
    if not isinstance(values, dict) or set(values) - LIMITS.keys():
        raise ValueError('parameters must contain known parameter IDs')
    result = {}
    for key, value in values.items():
        if isinstance(value, bool) or not isinstance(value, (int,float)) or not math.isfinite(value):
            raise ValueError('parameter values must be finite numbers')
        lo, hi, _ = LIMITS[key]
        result[key] = max(lo, min(hi, value))
    return result


def create_app(voice=None):
    app = web.Application(client_max_size=65536)
    state = {'mode':'human', 'parameters':{k:v[2] for k,v in LIMITS.items()},
             'revision':0, 'source':'idle',
             'performance':{'enabled':True,'emotion':'neutral','started_at':time.time(),'until':0}}
    peers = set()
    controllers = []
    voice = voice or Voicevox()
    clips = OrderedDict()
    generation = [0]
    deadline = [0.0]

    async def send(event):
        for ws in tuple(peers):
            try:
                await ws.send_json(event)
            except (ConnectionError, RuntimeError):
                peers.discard(ws)

    async def publish():
        state['revision'] += 1
        await send({'type':'state', **state})

    async def control(data):
        if not isinstance(data,dict):
            raise ValueError('control must be an object')
        if data.get('source') not in ('human','ai'):
            raise ValueError('source must be human or ai')
        if data['source'] != state['mode']:
            raise web.HTTPConflict(text='inactive control source')
        parameters = validate_parameters(data.get('parameters', {}))
        ttl = data.get('ttl_ms', 2000)
        if isinstance(ttl, bool) or not isinstance(ttl, (int,float)) or not math.isfinite(ttl):
            raise ValueError('ttl_ms must be finite')
        state['parameters'].update(parameters)
        state['source'] = data['source']
        deadline[0] = time.monotonic()+max(100, min(10000, ttl))/1000
        await publish()

    async def api_state(request):
        return web.json_response(state)

    async def api_mode(request):
        data = await request.json()
        if not isinstance(data,dict) or data.get('mode') not in ('human','ai'):
            raise web.HTTPBadRequest(text='mode must be human or ai')
        state.update(mode=data['mode'], source='idle', parameters={k:v[2] for k,v in LIMITS.items()})
        deadline[0] = 0
        state['performance'].update(emotion='neutral',started_at=time.time(),until=0)
        generation[0] += 1
        await send({'type':'cancel_speech'})
        await publish()
        return web.json_response(state)

    async def api_control(request):
        try:
            await control(await request.json())
        except ValueError as e:
            raise web.HTTPBadRequest(text=str(e))
        return web.json_response(state)

    async def performance(request):
        data = await request.json()
        if not isinstance(data,dict):
            raise web.HTTPBadRequest(text='performance must be an object')
        emotion=data.get('emotion','neutral')
        if emotion not in ('neutral','happy','thoughtful','surprised'):
            raise web.HTTPBadRequest(text='unknown emotion')
        enabled=data.get('enabled',state['performance']['enabled'])
        if not isinstance(enabled,bool):
            raise web.HTTPBadRequest(text='enabled must be boolean')
        duration=data.get('duration',4)
        if isinstance(duration,bool) or not isinstance(duration,(int,float)) or not math.isfinite(duration) or not 0<duration<=30:
            raise web.HTTPBadRequest(text='duration must be within 0–30 seconds')
        now=time.time()
        state['performance']={'enabled':enabled,'emotion':emotion,'started_at':now,'until':now+duration}
        await publish()
        return web.json_response(state['performance'])

    async def speech(request):
        data = await request.json()
        if state['mode'] != 'ai':
            raise web.HTTPConflict(text='select AI mode first')
        text = data.get('text') if isinstance(data,dict) else None
        if not isinstance(text,str) or not text.strip() or len(text)>2000:
            raise web.HTTPBadRequest(text='text must contain 1–2000 characters')
        generation[0] += 1
        ticket = generation[0]
        await send({'type':'cancel_speech'})
        try:
            wav = await voice.synthesize(text)
        except Exception as error:
            raise web.HTTPServiceUnavailable(text='音声合成に接続できません。VOICEVOXを起動してください。 '+str(error))
        if ticket != generation[0] or state['mode'] != 'ai':
            raise web.HTTPConflict(text='speech was superseded or cancelled')
        clip_id = uuid.uuid4().hex
        clips[clip_id] = wav
        while len(clips)>8:
            clips.popitem(last=False)
        emotion=data.get('emotion','auto')
        if emotion=='auto':
            emotion='surprised' if any(c in text for c in ('びっくり','驚','！？','?!')) else 'happy' if any(c in text for c in ('嬉','うれし','楽し','ありがとう','こんにちは')) else 'thoughtful' if any(c in text for c in ('考え','どうしよう','うーん')) else 'neutral'
        if emotion not in ('neutral','happy','thoughtful','surprised'):
            emotion='neutral'
        try:
            with wave.open(io.BytesIO(wav)) as audio:
                duration=audio.getnframes()/audio.getframerate()
        except (wave.Error,EOFError):
            duration=5
        now=time.time()
        state['performance'].update(emotion=emotion,started_at=now,until=now+duration+.3)
        await publish()
        event = {'type':'speech', 'text':text, 'url':f'/speech/{clip_id}.wav', 'credit':voice.credit}
        owner = controllers[-1] if controllers else None
        for peer in tuple(peers):
            try:
                await peer.send_json({**event, 'play':peer is owner})
            except (ConnectionError, RuntimeError):
                peers.discard(peer)
        return web.json_response({**event, 'queued_clients':len(peers), 'playback_clients':int(owner is not None)})

    async def audio(request):
        wav = clips.get(request.match_info['clip'])
        if wav is None:
            raise web.HTTPNotFound(text='audio expired; request speech again')
        return web.Response(body=wav, content_type='audio/wav', headers={'Cache-Control':'no-store'})

    async def socket(request):
        ws = web.WebSocketResponse(heartbeat=20)
        await ws.prepare(request)
        peers.add(ws)
        if request.query.get("role") != "overlay":
            controllers.append(ws)
        await ws.send_json({'type':'state', **state})
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        await control(json.loads(msg.data))
                    except web.HTTPConflict:
                        # Frames already in flight at a mode switch are stale.
                        continue
                    except (ValueError, web.HTTPException) as e:
                        await ws.send_json({'type':'error','message':str(e)})
        finally:
            peers.discard(ws)
            if ws in controllers:
                controllers.remove(ws)
        return ws

    async def expiry(app):
        async def loop():
            while True:
                await asyncio.sleep(0.1)
                if deadline[0] and time.monotonic()>deadline[0]:
                    deadline[0] = 0
                    state.update(source='idle', parameters={k:v[2] for k,v in LIMITS.items()})
                    await publish()
        task=asyncio.create_task(loop())
        yield
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        for ws in tuple(peers):
            await ws.close()

    app.cleanup_ctx.append(expiry)
    app.router.add_get('/api/state', api_state)
    app.router.add_post('/api/mode', api_mode)
    app.router.add_post('/api/control', api_control)
    app.router.add_post('/api/speech', speech)
    app.router.add_post('/api/performance', performance)
    app.router.add_get('/ws', socket)
    app.router.add_get('/speech/{clip}.wav', audio)
    async def index(request):
        return web.FileResponse(ROOT/'web/index.html')
    app.router.add_get('/', index)
    app.router.add_static('/web/', ROOT/'web')
    app.router.add_static('/model/', ROOT/'model')
    app.router.add_static('/vendor/', ROOT/'vendor')
    return app


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8766)
    args=parser.parse_args()
    web.run_app(create_app(), host='127.0.0.1', port=args.port)
