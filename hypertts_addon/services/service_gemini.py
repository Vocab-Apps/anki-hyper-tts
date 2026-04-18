import os
import sys
import wave
import base64
import tempfile
import requests
import aqt.sound


from hypertts_addon import voice
from hypertts_addon import service
from hypertts_addon import errors
from hypertts_addon import constants
from hypertts_addon import options
from hypertts_addon import logging_utils
logger = logging_utils.get_child_logger(__name__)

# Gemini speech-generation REST API:
#   https://ai.google.dev/gemini-api/docs/speech-generation#rest
# Model catalogue (ListModels):
#   https://ai.google.dev/api/models#method:-models.list
# Prebuilt voice names and supported languages:
#   https://ai.google.dev/gemini-api/docs/speech-generation#voices

class Gemini(service.ServiceBase):
    CONFIG_API_KEY = 'api_key'

    def __init__(self):
        service.ServiceBase.__init__(self)

    def cloudlanguagetools_enabled(self):
        return True

    @property
    def service_type(self) -> constants.ServiceType:
        return constants.ServiceType.tts

    @property
    def service_fee(self) -> constants.ServiceFee:
        return constants.ServiceFee.paid

    def configuration_options(self):
        return {
            self.CONFIG_API_KEY: str,
        }

    def voice_list(self):
        return self.basic_voice_list()

    def get_tts_audio(self, source_text, voice: voice.VoiceBase, voice_options):
        api_key = self.get_configuration_value_mandatory(self.CONFIG_API_KEY)

        model = voice_options.get('model', voice.options['model']['default'])
        prompt = voice_options.get('prompt', voice.options['prompt']['default'])

        audio_format_str = voice_options.get(options.AUDIO_FORMAT_PARAMETER, options.AudioFormat.mp3.name)
        audio_format = options.AudioFormat[audio_format_str]

        if audio_format != options.AudioFormat.mp3:
            raise errors.ServiceInputError(source_text, voice,
                f'Gemini service only supports mp3 output; {audio_format.name} is not supported')

        text = f'{prompt}: {source_text}' if prompt else source_text

        payload = {
            'contents': [{'parts': [{'text': text}]}],
            'generationConfig': {
                'responseModalities': ['AUDIO'],
                'speechConfig': {
                    'voiceConfig': {
                        'prebuiltVoiceConfig': {'voiceName': voice.voice_key['name']}
                    }
                }
            },
            'model': model,
        }

        logger.debug(f'requesting audio with payload {payload}')

        response = requests.post(
            f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',
            headers={
                'x-goog-api-key': api_key,
                'Content-Type': 'application/json',
            },
            json=payload,
            timeout=constants.RequestTimeout,
        )

        if response.status_code == 429:
            logger.warning(f'HTTP {response.status_code}, headers: {dict(response.headers)}, body: {response.text}')
            raise errors.RateLimitError(source_text, voice, f'Gemini rate limit: {response.status_code} {response.text}')

        if response.status_code != 200:
            logger.warning(f'HTTP {response.status_code}, headers: {dict(response.headers)}, body: {response.text}')
            data = response.json()
            error_message = data.get('error', {}).get('message', str(data))
            raise errors.RequestError(source_text, voice, error_message)

        data = response.json()
        try:
            encoded = data['candidates'][0]['content']['parts'][0]['inlineData']['data']
        except (KeyError, IndexError):
            raise errors.RequestError(source_text, voice, f'Gemini returned no audio: {data}')

        pcm_bytes = base64.b64decode(encoded)

        return self._encode_pcm_to_mp3(pcm_bytes)

    def _encode_pcm_to_mp3(self, pcm_bytes):
        # Gemini returns raw signed little-endian PCM at 24kHz / 16-bit / mono.
        # Per PCM_TO_MP3.md: wrap the bytes in a WAV container via stdlib `wave`,
        # then hand off to Anki's bundled `lame` via aqt.sound._encode_mp3.
        wav_fh, wav_path = tempfile.mkstemp(prefix='hypertts_gemini_', suffix='.wav')
        os.close(wav_fh)
        mp3_fh, mp3_path = tempfile.mkstemp(prefix='hypertts_gemini_', suffix='.mp3')
        os.close(mp3_fh)
        try:
            with wave.open(wav_path, 'wb') as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(24000)
                w.writeframes(pcm_bytes)
            aqt.sound._encode_mp3(wav_path, mp3_path)
            with open(mp3_path, 'rb') as f:
                return f.read()
        finally:
            for p in (wav_path, mp3_path):
                if os.path.exists(p):
                    os.remove(p)
