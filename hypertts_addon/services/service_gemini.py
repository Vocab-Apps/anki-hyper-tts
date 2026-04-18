import os
import sys
import wave
import base64
import tempfile
import subprocess
import requests


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
            raise errors.RateLimitError(source_text, voice, f'Gemini rate limit: {response.status_code} {response.text}')

        if response.status_code != 200:
            logger.warning(f'HTTP {response.status_code}: {response.text}')
            data = response.json()
            error_message = data.get('error', {}).get('message', str(data))
            raise errors.RequestError(source_text, voice, error_message)

        data = response.json()
        try:
            encoded = data['candidates'][0]['content']['parts'][0]['inlineData']['data']
        except (KeyError, IndexError):
            raise errors.RequestError(source_text, voice, f'Gemini returned no audio: {data}')

        pcm_bytes = base64.b64decode(encoded)

        return self._encode_pcm(pcm_bytes, audio_format)

    def _encode_pcm(self, pcm_bytes, audio_format):
        ext_map = {
            options.AudioFormat.mp3: ('.mp3', ['-c:a', 'libmp3lame', '-q:a', '2']),
            options.AudioFormat.ogg_opus: ('.ogg', ['-c:a', 'libopus']),
        }
        ext, codec_args = ext_map[audio_format]

        wav_fh, wav_path = tempfile.mkstemp(prefix='hypertts_gemini_', suffix='.wav')
        os.close(wav_fh)
        out_fh, out_path = tempfile.mkstemp(prefix='hypertts_gemini_', suffix=ext)
        os.close(out_fh)
        try:
            with wave.open(wav_path, 'wb') as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(24000)
                w.writeframes(pcm_bytes)
            subprocess.run(
                ['ffmpeg', '-y', '-i', wav_path, *codec_args, out_path],
                check=True, capture_output=True,
            )
            with open(out_path, 'rb') as f:
                return f.read()
        finally:
            for p in (wav_path, out_path):
                if os.path.exists(p):
                    os.remove(p)
