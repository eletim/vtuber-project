"""Replaceable VOICEVOX HTTP voice provider; no browser-dependent voices."""
import os
import aiohttp

CREDIT = 'VOICEVOX:雨晴はう'

class Voicevox:
    def __init__(self):
        self.url = os.environ.get('VOICEVOX_URL', 'http://127.0.0.1:50021').rstrip('/')
        self.name = os.environ.get('VOICEVOX_SPEAKER', '雨晴はう')
        self.style = os.environ.get('VOICEVOX_STYLE', 'ノーマル')
        self.credit = f'VOICEVOX:{self.name}'

    async def synthesize(self, text):
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120)) as session:
            async with session.get(self.url+'/speakers') as response:
                response.raise_for_status()
                speakers = await response.json()
            speaker = next((style['id'] for item in speakers if item['name']==self.name
                            for style in item['styles'] if style['name']==self.style), None)
            if speaker is None:
                raise ValueError(f'VOICEVOXに {self.name} / {self.style} がありません')
            async with session.post(self.url+'/audio_query', params={'text':text,'speaker':speaker}) as response:
                response.raise_for_status()
                query = await response.json()
            async with session.post(self.url+'/synthesis', params={'speaker':speaker}, json=query) as response:
                response.raise_for_status()
                wav = await response.read()
            if not (wav.startswith(b'RIFF') and wav[8:12]==b'WAVE'):
                raise ValueError('VOICEVOXがWAVを返しませんでした')
            return wav
