"""Local avatar host and shared human/AI control bus."""
import argparse
import asyncio
import json
import math
import time
import uuid
from collections import OrderedDict
from voice import Voicevox, VoiceError, validate_wav
from pathlib import Path
from aiohttp import web, WSMsgType

ROOT = Path(__file__).resolve().parent
EXPRESSIONS = ('neutral', 'soft_smile', 'big_smile', 'worried', 'surprised', 'bashful', 'displeased', 'thinking')
EMOTION_EXPRESSIONS = {'neutral':'neutral', 'happy':'soft_smile', 'thoughtful':'thinking', 'surprised':'surprised'}
LIMITS = {'ParamAngleX': (-15,15,0), 'ParamAngleY': (-10,10,0),
          'ParamAngleZ': (-8,8,0), 'ParamBodyAngleX': (-5,5,0),
          'ParamEyeLOpen': (0,1,1), 'ParamEyeROpen': (0,1,1),
          'ParamMouthOpenY': (0,1,0), 'ParamBreath': (0,1,0.5),
          'ParamArmLOpen': (-1,1,0), 'ParamArmROpen': (-1,1,0),
          'ParamShoulderY': (-1,1,0), 'ParamBodyShiftX': (-1,1,0),
          'ParamSkirtSway': (-1,1,0)}


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
    active_speech = [None]
    synthesis = [None]
    retired_requests = OrderedDict()
    state['speech'] = {'phase':'idle'}
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

    def validate_expression(expression, duration):
        if not isinstance(expression, str) or expression not in EXPRESSIONS:
            raise ValueError('unknown expression')
        if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(duration) or not 0.1 <= duration <= 30:
            raise ValueError('expression duration must be within 0.1–30 seconds')
        return expression, duration

    def set_expression(expression='neutral', source='idle', owner='idle', duration=0):
        now = time.time()
        state['expression'] = {'id':expression, 'source':source, 'owner':owner,
                               'started_at':now, 'until':now+duration if duration else 0}

    def clear_speech_expression():
        if state['expression']['owner'] == 'speech':
            set_expression()

    set_expression()

    def retire(request_id):
        if request_id:
            retired_requests[request_id] = None
            while len(retired_requests) > 128:
                retired_requests.popitem(last=False)

    def reset_speech():
        generation[0] += 1
        job = synthesis[0]
        if job:
            retire(job['request_id'])
            job['task'].cancel()
            synthesis[0] = None
        if active_speech[0]:
            retire(active_speech[0]['request_id'])
        active_speech[0] = None
        clear_speech_expression()
        state['parameters']['ParamMouthOpenY'] = 0
        state['performance'].update(emotion='neutral', started_at=time.time(), until=0)
        state['speech'] = {'phase':'idle'}

    def request_identity(data, optional=False):
        value = data.get('request_id')
        if value is None:
            return None if optional else uuid.uuid4().hex
        if not isinstance(value, str) or not value.strip() or len(value) > 128:
            raise web.HTTPBadRequest(text='request_id must contain 1–128 characters')
        return value

    async def voice_status(request):
        if not hasattr(voice, 'status'):
            return web.json_response({'available':False, 'provider':'VOICEVOX',
                                      'message':'音声プロバイダーの接続確認に対応していません。'})
        return web.json_response(await voice.status())

    async def cancel_speech(request):
        try:
            data = await request.json()
        except ValueError:
            raise web.HTTPBadRequest(text='cancel must be valid JSON')
        if not isinstance(data, dict):
            raise web.HTTPBadRequest(text='cancel must be an object')
        request_id = request_identity(data, optional=True)
        current = synthesis[0] or active_speech[0]
        # A cancellation may arrive before its HTTP synthesis request. Keep a
        # bounded tombstone without cancelling a different, newer utterance.
        retire(request_id)
        if request_id and (not current or current['request_id'] != request_id):
            return web.json_response({'cancelled':False, 'ignored':True})
        cancelled_id = request_id or (current['request_id'] if current else None)
        reset_speech()
        await send({'type':'cancel_speech', 'reason':'stopped', 'request_id':cancelled_id})
        await publish()
        return web.json_response({'cancelled':True})

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
        expression = validate_expression(data['expression'], data.get('expression_duration', 4)) if 'expression' in data else None
        if expression:
            set_expression(expression[0], data['source'], 'manual', expression[1])
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
        set_expression()
        state['performance'].update(emotion='neutral',started_at=time.time(),until=0)
        reset_speech()
        await send({'type':'cancel_speech', 'reason':'mode_change'})
        await publish()
        return web.json_response(state)

    async def api_control(request):
        try:
            await control(await request.json())
        except ValueError as e:
            raise web.HTTPBadRequest(text=str(e))
        return web.json_response(state)

    async def api_expression(request):
        try:
            data = await request.json()
        except ValueError:
            raise web.HTTPBadRequest(text='expression must be valid JSON')
        if not isinstance(data, dict) or data.get('source') not in ('human', 'ai'):
            raise web.HTTPBadRequest(text='source must be human or ai')
        if data['source'] != state['mode']:
            raise web.HTTPConflict(text='inactive control source')
        try:
            expression, duration = validate_expression(data.get('expression'), data.get('duration', 4))
        except ValueError as error:
            raise web.HTTPBadRequest(text=str(error))
        set_expression(expression, data['source'], 'manual', duration)
        await publish()
        return web.json_response(state['expression'])

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
        try:
            data = await request.json()
        except ValueError:
            raise web.HTTPBadRequest(text='speech must be valid JSON')
        if state['mode'] != 'ai':
            raise web.HTTPConflict(text='select AI mode first')
        text = data.get('text') if isinstance(data,dict) else None
        if not isinstance(text,str) or not text.strip() or len(text)>2000:
            raise web.HTTPBadRequest(text='text must contain 1–2000 characters')
        if 'expression' in data:
            try:
                validate_expression(data['expression'], 4)
            except ValueError as error:
                raise web.HTTPBadRequest(text=str(error))
        request_id = request_identity(data)
        if request_id in retired_requests or any(item and item['request_id'] == request_id for item in (synthesis[0], active_speech[0])):
            raise web.HTTPConflict(text='この音声リクエストは停止済み、または処理済みです。')
        reset_speech()
        ticket = generation[0]
        owner = controllers[-1] if controllers else None
        task = asyncio.create_task(voice.synthesize(text))
        job = {'task':task, 'request_id':request_id, 'owner':owner}
        synthesis[0] = job
        state['speech'] = {'phase':'synthesizing', 'request_id':request_id}
        await send({'type':'cancel_speech', 'reason':'superseded', 'request_id':request_id})
        await publish()
        try:
            wav = await task
            duration = validate_wav(wav)
        except asyncio.CancelledError:
            raise web.HTTPConflict(text='音声合成を停止しました。') from None
        except Exception as error:
            if ticket != generation[0]:
                raise web.HTTPConflict(text='speech was superseded or cancelled') from None
            state['speech'] = {'phase':'error', 'request_id':request_id,
                               'error':error.code if isinstance(error, VoiceError) else 'engine_unavailable'}
            retire(request_id)
            await publish()
            message = str(error) if isinstance(error, VoiceError) else '音声合成に接続できません。VOICEVOXの接続を確認してください。'
            raise web.HTTPServiceUnavailable(text=message) from None
        finally:
            if synthesis[0] is job:
                synthesis[0] = None
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
        active_speech[0] = {'clip_id':clip_id, 'request_id':request_id, 'emotion':emotion,
                            'expression':data.get('expression', EMOTION_EXPRESSIONS[emotion]),
                            'duration':duration, 'sequence':-1, 'owner':owner}
        state['speech'] = {'phase':'ready', 'request_id':request_id, 'clip_id':clip_id}
        event = {'type':'speech', 'text':text, 'url':f'/speech/{clip_id}.wav', 'credit':voice.credit,
                 'request_id':request_id, 'clip_id':clip_id, 'emotion':emotion,
                 'expression':active_speech[0]['expression'], 'duration':duration}
        for peer in tuple(peers):
            if ticket != generation[0] or not active_speech[0] or active_speech[0]['clip_id'] != clip_id:
                raise web.HTTPConflict(text='speech was superseded or cancelled')
            try:
                await peer.send_json({**event, 'play':peer is owner})
            except (ConnectionError, RuntimeError):
                peers.discard(peer)
        if ticket != generation[0] or not active_speech[0] or active_speech[0]['clip_id'] != clip_id:
            raise web.HTTPConflict(text='speech was superseded or cancelled')
        return web.json_response({**event, 'queued_clients':len(peers), 'playback_clients':int(owner is not None)})

    async def playback(request):
        """Synchronize shared gestures to actual audio playback, not synthesis time."""
        data = await request.json()
        if not isinstance(data, dict):
            raise web.HTTPBadRequest(text='playback must be an object')
        phase = data.get('state')
        position = data.get('position')
        sequence = data.get('sequence')
        rate = data.get('playback_rate', 1)
        if isinstance(rate, bool) or not isinstance(rate, (int, float)) or not math.isfinite(rate) or not 0.25 <= rate <= 4:
            raise web.HTTPBadRequest(text='playback_rate must be within 0.25–4')
        if phase not in ('playing', 'paused', 'ended'):
            raise web.HTTPBadRequest(text='unknown playback state')
        if isinstance(position, bool) or not isinstance(position, (int, float)) or not math.isfinite(position) or position < 0:
            raise web.HTTPBadRequest(text='position must be a finite nonnegative number')
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
            raise web.HTTPBadRequest(text='sequence must be a nonnegative integer')
        clip = active_speech[0]
        if state['mode'] != 'ai' or not clip or data.get('clip_id') != clip['clip_id']:
            raise web.HTTPConflict(text='speech is no longer active')
        if sequence <= clip['sequence']:
            return web.json_response({'ignored':True})
        if position > clip['duration'] + 0.5:
            raise web.HTTPBadRequest(text='position exceeds clip duration')
        clip['sequence'] = sequence
        position = min(position, clip['duration'])
        now = time.time()
        state['speech'] = {'phase':phase, 'request_id':clip['request_id'], 'clip_id':clip['clip_id']}
        if phase == 'playing' and position < clip['duration']:
            if state['expression']['owner'] != 'manual':
                set_expression(clip['expression'], 'ai', 'speech', (clip['duration']-position)/rate)
            state['performance'].update(emotion=clip['emotion'], started_at=now-position/rate,
                                        until=now+(clip['duration']-position)/rate)
        else:
            clear_speech_expression()
            state['parameters']['ParamMouthOpenY'] = 0
            state['performance'].update(emotion='neutral', started_at=now, until=0)
        await publish()
        return web.json_response(state['performance'])

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
            current = synthesis[0] or active_speech[0]
            if current and current.get('owner') is ws:
                request_id = current['request_id']
                reset_speech()
                await send({'type':'cancel_speech', 'reason':'controller_disconnected', 'request_id':request_id})
                await publish()
        return ws

    async def expiry(app):
        async def loop():
            while True:
                await asyncio.sleep(0.1)
                changed = False
                if state['expression']['until'] and time.time() > state['expression']['until']:
                    set_expression()
                    changed = True
                if deadline[0] and time.monotonic()>deadline[0]:
                    deadline[0] = 0
                    state.update(source='idle', parameters={k:v[2] for k,v in LIMITS.items()})
                    changed = True
                if changed:
                    await publish()
        task=asyncio.create_task(loop())
        yield
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        for ws in tuple(peers):
            await ws.close()

    async def shutdown(app):
        job = synthesis[0]
        reset_speech()
        if job:
            await asyncio.gather(job['task'], return_exceptions=True)
        for ws in tuple(peers):
            await ws.close()

    app.on_shutdown.append(shutdown)
    app.cleanup_ctx.append(expiry)
    app.router.add_get('/api/state', api_state)
    app.router.add_post('/api/mode', api_mode)
    app.router.add_post('/api/control', api_control)
    app.router.add_post('/api/expression', api_expression)
    app.router.add_get('/api/voice', voice_status)
    app.router.add_post('/api/speech', speech)
    app.router.add_post('/api/speech/cancel', cancel_speech)
    app.router.add_post('/api/playback', playback)
    app.router.add_post('/api/performance', performance)
    app.router.add_get('/ws', socket)
    app.router.add_get('/speech/{clip}.wav', audio)
    async def index(request):
        return web.FileResponse(ROOT/'web/index.html')
    app.router.add_get('/', index)
    app.router.add_static('/web/', ROOT/'web')
    app.router.add_static('/model/', ROOT/'model')
    if (ROOT/'vendor').is_dir():
        app.router.add_static('/vendor/', ROOT/'vendor')
    return app


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8766)
    args=parser.parse_args()
    web.run_app(create_app(), host='127.0.0.1', port=args.port)
