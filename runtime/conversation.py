"""Opt-in local-only conversation adapters. Never download or fall back.

Protocol: https://docs.ollama.com/api/chat and /api/show. Run Ollama with
OLLAMA_NO_CLOUD=1 as defense in depth. History is supplied by the runtime, never
persisted here; cancellation closes the in-flight local HTTP connection.
"""
import asyncio
import ipaddress
import json
import os
import re
from urllib.parse import urlsplit, urlunsplit

import aiohttp

MAX_INPUT_CHARS = 500
MAX_REPLY_CHARS = 300
MAX_HISTORY_TURNS = 2
MAX_HISTORY_CHARS = 1000
MAX_RESPONSE_BYTES = 1024 * 1024
MAX_OUTPUT_TOKENS = 128
REQUEST_TIMEOUT = 120
SYSTEM_PROMPT = (
    'あなたはVTuber「羽月こま」の会話AIです。自然で親しみやすい日本語で、'
    '原則1〜2文、100文字以内で返答してください。読み上げる本文だけを書き、'
    'Markdown、動作指示、思考過程は書かないでください。'
    '分からないことは分からないと伝え、できない操作を実行したと主張しないでください。'
)


class ConversationError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def local_url(value):
    """Reject remote hosts, URL secrets, redirects and localhost DNS rebinding."""
    try:
        if not isinstance(value, str) or any(c.isspace() for c in value):
            raise ValueError
        parts = urlsplit(value)
        if (parts.scheme != 'http' or parts.username is not None or parts.password is not None
                or parts.path not in ('', '/') or parts.query or parts.fragment):
            raise ValueError
        host = parts.hostname
        if host == 'localhost':
            host = '127.0.0.1'
        address = ipaddress.ip_address(host)
        if not address.is_loopback or '%' in host:
            raise ValueError
        port = parts.port if parts.port is not None else 80
        if not 1 <= port <= 65535:
            raise ValueError
        authority = f'[{address}]:{port}' if address.version == 6 else f'{address}:{port}'
        return urlunsplit(('http', authority, '', '', ''))
    except (TypeError, ValueError):
        raise ConversationError('invalid_config', '会話エンジンのURLは認証情報を含まないローカルHTTPアドレス（127.0.0.1 / ::1）にしてください。') from None


def validate_reply(text):
    if not isinstance(text, str) or not text.strip():
        raise ConversationError('invalid_response', '会話モデルが有効な返答本文を返しませんでした。')
    text = text.strip()
    if '<think>' in text.lower() or '</think>' in text.lower():
        raise ConversationError('invalid_response', '会話モデルの返答に思考タグが含まれるため、読み上げを中止しました。')
    if len(text) > MAX_REPLY_CHARS:
        raise ConversationError('reply_too_long', '会話モデルの返答が長すぎます。短い質問で再試行してください。')
    return text


class LocalProvider:
    provider = 'unconfigured'
    model_setting = 'KOMA_LLM_MODEL'

    def __init__(self, model=None, url=None):
        # No default model: simply starting the avatar cannot enable inference.
        self.model = os.environ.get('KOMA_LLM_MODEL', '') if model is None else model
        self.url = os.environ.get('KOMA_LLM_URL', 'http://127.0.0.1:8081') if url is None else url

    def configuration(self):
        if not self.model:
            raise ConversationError('unconfigured', f'会話AIは未設定です。ローカルモデルを用意し、{self.model_setting}を明示して起動してください。')
        if (not isinstance(self.model, str) or len(self.model) > 200
                or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:/-]*', self.model)
                or '://' in self.model or 'cloud' in self.model.lower()):
            raise ConversationError('invalid_config', f'{self.model_setting}にはローカルモデル名を指定してください。クラウドモデルは使用できません。')
        return local_url(self.url)

    async def _json(self, response):
        if response.status == 404:
            raise ConversationError('model_missing', '指定されたローカルモデルが見つかりません。モデル設定とインストール済みモデルを確認してください。')
        if 300 <= response.status < 400:
            raise ConversationError('invalid_config', '会話エンジンの転送応答を拒否しました。ローカルエンジンを直接指定してください。')
        if response.status >= 400:
            raise ConversationError('engine_error', 'ローカル会話エンジンがエラーを返しました。会話エンジンの状態を確認してください。')
        body = bytearray()
        async for chunk in response.content.iter_chunked(65536):
            body.extend(chunk)
            if len(body) > MAX_RESPONSE_BYTES:
                raise ConversationError('invalid_response', '会話エンジンの応答がサイズ上限を超えました。')
        try:
            data = json.loads(body)
        except (ValueError, UnicodeDecodeError, RecursionError):
            raise ConversationError('invalid_response', '会話エンジンが有効なJSONを返しませんでした。') from None
        if not isinstance(data, dict) or data.get('error'):
            raise ConversationError('invalid_response', '会話エンジンの応答形式が不正です。')
        return data

    async def status(self):
        info = {'provider': self.provider, 'configured': bool(self.model),
                'model': self.model if isinstance(self.model, str) and len(self.model) <= 200 else None,
                'max_input_chars': MAX_INPUT_CHARS}
        try:
            url = self.configuration()
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=4), trust_env=False) as session:
                await self._check_model(session, url)
            return {**info, 'available': True, 'status': 'ready',
                    'message': 'ローカル会話モデルに接続済み。返答を生成できます。'}
        except ConversationError as error:
            return {**info, 'available': False, 'status': error.code, 'error': error.code, 'message': str(error)}
        except (aiohttp.ClientError, asyncio.TimeoutError):
            return {**info, 'available': False, 'status': 'offline', 'error': 'offline',
                    'message': 'ローカル会話エンジンに接続できません。会話エンジンの起動と接続先を確認してください。'}

    async def reply(self, text, history=()):
        url = self.configuration()
        if not isinstance(text, str) or not text.strip() or len(text) > MAX_INPUT_CHARS:
            raise ConversationError('invalid_input', '入力は1〜500文字にしてください。')
        if (not isinstance(history, (list, tuple)) or len(history) > MAX_HISTORY_TURNS * 2
                or any(not isinstance(item, dict) or item.get('role') != ('user' if i % 2 == 0 else 'assistant')
                       or not isinstance(item.get('content'), str) or not 0 < len(item['content']) <= MAX_INPUT_CHARS
                       for i, item in enumerate(history))
                or len(history) % 2 or sum(len(item['content']) for item in history) > MAX_HISTORY_CHARS):
            raise ConversationError('invalid_input', '会話履歴が上限または形式に違反しています。履歴を消去してください。')
        payload = self.payload(text, history)
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT, connect=5), trust_env=False) as session:
                await self._check_model(session, url)
                async with session.post(url + self.chat_path, json=payload, allow_redirects=False) as response:
                    data = await self._json(response)
            return self.reply_content(data)
        except ConversationError:
            raise
        except asyncio.TimeoutError:
            raise ConversationError('timeout', '会話の返答生成が時間内に終わりませんでした。短い質問で再試行してください。') from None
        except aiohttp.ClientError:
            raise ConversationError('offline', 'ローカル会話エンジンとの接続が切れました。会話エンジンの起動を確認してください。') from None


class Ollama(LocalProvider):
    provider = 'Ollama'
    model_setting = 'OLLAMA_MODEL / KOMA_LLM_MODEL'
    chat_path = '/api/chat'

    def __init__(self, model=None, url=None):
        self.model = os.environ.get('KOMA_LLM_MODEL', os.environ.get('OLLAMA_MODEL', '')) if model is None else model
        self.url = os.environ.get('KOMA_LLM_URL', os.environ.get('OLLAMA_URL', 'http://127.0.0.1:11434')) if url is None else url

    async def _check_model(self, session, url):
        # /api/show is local metadata, not generation/pull. Recheck every turn so
        # a cloud alias cannot silently receive user text or session history.
        async with session.post(url + '/api/show', json={'model': self.model}, allow_redirects=False) as response:
            data = await self._json(response)
        if data.get('remote_host') or data.get('remote_model'):
            raise ConversationError('invalid_config', '指定モデルはリモート推論を使用します。ローカルモデルだけが利用できます。')
        details = data.get('details')
        if not isinstance(details, dict) or details.get('format') != 'gguf' or not isinstance(data.get('model_info'), dict) or not data['model_info']:
            raise ConversationError('invalid_response', 'ローカルGGUFモデルの情報を確認できません。Ollamaとモデル設定を確認してください。')
        capabilities = data.get('capabilities')
        if capabilities is not None and (not isinstance(capabilities, list) or 'completion' not in capabilities):
            raise ConversationError('invalid_config', '指定モデルは会話の文章生成に対応していません。')

    def payload(self, text, history):
        return {'model': self.model, 'stream': False, 'think': False, 'keep_alive': '5m',
                   'messages': [{'role': 'system', 'content': SYSTEM_PROMPT},
                                *({'role': item['role'], 'content': item['content']} for item in history),
                                {'role': 'user', 'content': text.strip()}],
                   'options': {'num_predict': MAX_OUTPUT_TOKENS, 'num_ctx': 4096, 'temperature': 0.7}}

    def reply_content(self, data):
        if data.get('done_reason') == 'length':
            raise ConversationError('reply_truncated', '会話モデルが返答を長さ上限までに完了できませんでした。短い質問で再試行してください。')
        message = data.get('message')
        if (data.get('remote_host') or data.get('remote_model') or data.get('done') is not True
                or not isinstance(message, dict) or message.get('role') != 'assistant'
                or message.get('tool_calls')):
            raise ConversationError('invalid_response', 'ローカル会話モデルが完了した返答本文を返しませんでした。')
        return validate_reply(message.get('content'))


class LlamaCpp(LocalProvider):
    """Direct llama-server, no API key and no persistent authentication identity."""
    provider = 'llama.cpp'
    chat_path = '/v1/chat/completions'

    async def _check_model(self, session, url):
        async with session.get(url + '/health', allow_redirects=False) as response:
            if response.status == 503:
                raise ConversationError('loading', 'ローカル会話モデルを読み込み中です。少し待って接続を確認してください。')
            health = await self._json(response)
        if health.get('status') != 'ok':
            raise ConversationError('invalid_response', 'llama.cppの準備完了を確認できません。')
        async with session.get(url + '/v1/models', allow_redirects=False) as response:
            data = await self._json(response)
        models = data.get('data')
        if not isinstance(models, list) or any(not isinstance(item, dict) for item in models):
            raise ConversationError('invalid_response', 'llama.cppのモデル一覧が不正です。')
        model = next((item for item in models if item.get('id') == self.model), None)
        if model is None:
            raise ConversationError('model_missing', '指定モデルが読み込まれていません。KOMA_LLM_MODELをllama-serverの--aliasと一致させてください。')
        if model.get('owned_by') != 'llamacpp' or model.get('remote_host') or model.get('remote_model'):
            raise ConversationError('invalid_response', 'ローカルllama.cppモデルの情報を確認できません。')

    def payload(self, text, history):
        return {'model': self.model, 'stream': False, 'max_tokens': MAX_OUTPUT_TOKENS,
                'temperature': 0.7, 'chat_template_kwargs': {'enable_thinking': False},
                'messages': [{'role':'system', 'content':SYSTEM_PROMPT},
                             *({'role':item['role'], 'content':item['content']} for item in history),
                             {'role':'user', 'content':text.strip()}]}

    def reply_content(self, data):
        choices = data.get('choices')
        if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
            raise ConversationError('invalid_response', '会話モデルが有効な返答を返しませんでした。')
        choice = choices[0]
        if choice.get('finish_reason') == 'length':
            raise ConversationError('reply_truncated', '会話モデルが返答を長さ上限までに完了できませんでした。短い質問で再試行してください。')
        message = choice.get('message')
        if (not isinstance(message, dict) or message.get('role') != 'assistant'
                or message.get('tool_calls') or choice.get('finish_reason') != 'stop'):
            raise ConversationError('invalid_response', '会話モデルが完了した返答本文を返しませんでした。')
        # Reasoning fields are deliberately ignored, never displayed or spoken.
        return validate_reply(message.get('content'))


class Unconfigured(LocalProvider):
    def __init__(self, invalid=False):
        self.model = ''
        self.invalid = invalid

    def configuration(self):
        if self.invalid:
            raise ConversationError('invalid_config', 'KOMA_LLM_PROVIDERはllamacppまたはollamaを指定してください。')
        raise ConversationError('unconfigured', '会話AIは未設定です。KOMA_LLM_PROVIDERとKOMA_LLM_MODELを明示して起動してください。')


def create_provider():
    provider = os.environ.get('KOMA_LLM_PROVIDER', '').lower()
    if provider == 'llamacpp':
        return LlamaCpp()
    if provider == 'ollama' or (not provider and os.environ.get('OLLAMA_MODEL')):
        return Ollama()
    return Unconfigured(invalid=bool(provider))
