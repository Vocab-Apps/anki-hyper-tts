import base64
import requests


from hypertts_addon import voice
from hypertts_addon import service
from hypertts_addon import errors
from hypertts_addon import constants
from hypertts_addon import options
from hypertts_addon import logging_utils
logger = logging_utils.get_child_logger(__name__)


class Mistral(service.ServiceBase):
    CONFIG_API_KEY = 'api_key'
    DEFAULT_MODEL = 'voxtral-mini-tts-2603'

    def __init__(self):
        service.ServiceBase.__init__(self)

    def cloudlanguagetools_enabled(self):
        return False

    @property
    def service_type(self) -> constants.ServiceType:
        return constants.ServiceType.tts

    @property
    def service_fee(self) -> constants.ServiceFee:
        return constants.ServiceFee.paid

    def configuration_options(self):
        return {
            self.CONFIG_API_KEY: str
        }

    def configure(self, config):
        self._config = config
        self.api_key = self.get_configuration_value_mandatory(self.CONFIG_API_KEY)

    def voice_list(self):
        return self.basic_voice_list()

    def get_tts_audio(self, source_text, voice: voice.VoiceBase, voice_options):
        api_key = self.get_configuration_value_mandatory(self.CONFIG_API_KEY)

        model = voice_options.get('model', voice.options['model']['default'])
        audio_format_str = voice_options.get(
            options.AUDIO_FORMAT_PARAMETER,
            voice.options.get(options.AUDIO_FORMAT_PARAMETER, {}).get(
                'default', options.AudioFormat.mp3.name
            ),
        )
        audio_format = options.AudioFormat[audio_format_str]

        # Mistral supports mp3, wav, pcm, flac, opus. HyperTTS's audio pipeline
        # verifies output against Ogg-wrapped Opus for AudioFormat.ogg_opus, but
        # Mistral returns raw Opus (no Ogg container), so we only expose mp3
        # here. Any other format is rejected as a permanent input error rather
        # than being silently swapped.
        audio_format_map = {
            options.AudioFormat.mp3: 'mp3',
        }
        if audio_format not in audio_format_map:
            raise errors.ServiceInputError(
                source_text,
                voice,
                f'Mistral does not support audio format {audio_format.name}',
            )
        response_format = audio_format_map[audio_format]

        url = 'https://api.mistral.ai/v1/audio/speech'
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        data = {
            'model': model,
            'input': source_text,
            'voice_id': voice.voice_key['voice_id'],
            'response_format': response_format,
        }

        response = requests.post(
            url, json=data, headers=headers, timeout=constants.RequestTimeout
        )

        if response.status_code != 200:
            logger.warning(f'Mistral response content: {response.text}')
            logger.warning(
                f'Mistral response status: {response.status_code} '
                f'headers: {dict(response.headers)}'
            )

        if response.status_code == 429:
            raise errors.RateLimitError(
                source_text,
                voice,
                f'Mistral rate limit: {response.status_code} {response.text}',
            )

        # 403 groups with 401: Mistral returns 403 for both invalid keys and
        # moderated / rejected content — neither is retryable.
        if response.status_code in (401, 403):
            raise errors.ServicePermissionError(
                source_text,
                voice,
                f'Mistral authentication or permission failed: '
                f'{response.status_code} {response.text}',
            )

        # 400 must be PermanentError so batch retry stops (mirrors the OpenAI
        # service fix for Sentry ANKI-HYPER-TTS-JRS).
        if response.status_code == 400:
            raise errors.ServiceInputError(
                source_text,
                voice,
                f'Mistral bad request: {response.status_code} {response.text}',
            )

        response.raise_for_status()

        # Documented non-streaming response is a JSON envelope with base64
        # audio; accept raw audio bytes too in case the endpoint returns that.
        content_type = response.headers.get('Content-Type', '').lower()
        if 'application/json' in content_type:
            payload = response.json()
            encoded = payload.get('audio_data')
            if not encoded:
                raise errors.RequestError(
                    source_text,
                    voice,
                    f'Mistral response missing audio_data field: {payload}',
                )
            return base64.b64decode(encoded)

        return response.content
