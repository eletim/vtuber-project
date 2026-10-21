"""Replaceable VOICEVOX provider with explicit readiness and bounded fresh WAVs."""
import asyncio
import io
import os
import wave
import aiohttp

CREDIT = 'VOICEVOX:雨晴はう'
MAX_WAV_BYTES = 40 * 1024 * 1024

class VoiceError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def validate_wav(data):
    if not isinstance(data, bytes) or len(data) > MAX_WAV_BYTES:
        raise VoiceError('invalid_audio', '音声データが大きすぎるか、形式が不正です。')
    try:
        with wave.open(io.BytesIO(data)) as audio:
            frames, rate = audio.getnframes(), audio.getframerate()
            if audio.getcomptype() != 'NONE' or audio.getnchannels() not in (1, 2) or audio.getsampwidth() not in (1, 2, 3, 4) or frames <= 0 or not 8000 <= rate <= 192000:
                raise ValueError('unsupported or empty PCM')
            if len(audio.readframes(frames)) != frames * audio.getnchannels() * audio.getsampwidth():
                raise ValueError('truncated PCM')
            return frames / rate
    except (wave.Error, EOFError, ValueError, ZeroDivisionError):
        raise VoiceError('invalid_audio', 'VOICEVOXが有効なPCM WAVを返しませんでした。エンジンの状態を確認してください。') from None


class Voicevox:
    def __init__(self):
        self.url = os.environ.get('VOICEVOX_URL', 'http://127.0.0.1:50021').rstrip('/')
        self.name = os.environ.get('VOICEVOX_SPEAKER', '雨晴はう')
        self.style = os.environ.get('VOICEVOX_STYLE', 'ノーマル')
        self.credit = f'VOICEVOX:{self.name}'

    def speaker_id(self, speakers):
        try:
            speaker = next(style['id'] for item in speakers if item['name'] == self.name
                           for style in item['styles'] if style['name'] == self.style)
        except (StopIteration, KeyError, TypeError):
            raise VoiceError('speaker_missing', f'VOICEVOXに {self.name} / {self.style} がありません。話者設定を確認してください。') from None
        return speaker

    async def status(self):
        info = {'provider': 'VOICEVOX', 'speaker': self.name, 'style': self.style, 'credit': self.credit}
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=4)) as session:
                async with session.get(self.url + '/version') as response:
                    response.raise_for_status()
                    version = await response.json()
                async with session.get(self.url + '/speakers') as response:
                    response.raise_for_status()
                    self.speaker_id(await response.json())
            return {**info, 'available': True, 'version': str(version), 'message': 'VOICEVOX接続済み。入力した文章から新しく音声を合成できます。'}
        except VoiceError as error:
            return {**info, 'available': False, 'error': error.code, 'message': str(error)}
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
            return {**info, 'available': False, 'error': 'engine_unavailable', 'message': 'VOICEVOXに接続できません。エンジンを起動して「接続を確認」を押してください。'}

    async def synthesize(self, text):
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120, connect=5)) as session:
                async with session.get(self.url + '/speakers') as response:
                    response.raise_for_status()
                    speaker = self.speaker_id(await response.json())
                async with session.post(self.url + '/audio_query', params={'text': text, 'speaker': speaker}) as response:
                    response.raise_for_status()
                    query = await response.json()
                async with session.post(self.url + '/synthesis', params={'speaker': speaker}, json=query) as response:
                    response.raise_for_status()
                    chunks = bytearray()
                    async for chunk in response.content.iter_chunked(65536):
                        chunks.extend(chunk)
                        if len(chunks) > MAX_WAV_BYTES:
                            raise VoiceError('invalid_audio', 'VOICEVOXの音声がサイズ上限を超えました。文章を短くしてください。')
                    wav = bytes(chunks)
            validate_wav(wav)
            return wav
        except VoiceError:
            raise
        except asyncio.TimeoutError:
            raise VoiceError('timeout', '音声合成が時間内に終わりませんでした。短い文章で再試行してください。') from None
        except (aiohttp.ClientError, ValueError):
            raise VoiceError('engine_unavailable', 'VOICEVOXに接続できないか、エンジンでエラーが発生しました。接続を確認してください。') from None
