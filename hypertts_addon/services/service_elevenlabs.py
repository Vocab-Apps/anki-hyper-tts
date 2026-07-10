import sys
import requests


from hypertts_addon import voice
from hypertts_addon import service
from hypertts_addon import errors
from hypertts_addon import constants
from hypertts_addon import options
from hypertts_addon import logging_utils
logger = logging_utils.get_child_logger(__name__)

class ElevenLabs(service.ServiceBase):
    CONFIG_API_KEY = 'api_key'

    # 192 kbps mp3 requires an ElevenLabs Creator tier (or above); 128 kbps is
    # available on every tier including Free. We request the higher bitrate and
    # transparently fall back to 128 kbps for accounts whose tier rejects it.
    MP3_OUTPUT_FORMAT_HQ = 'mp3_44100_192'
    MP3_OUTPUT_FORMAT_DEFAULT = 'mp3_44100_128'

    def __init__(self):
        service.ServiceBase.__init__(self)
        # flips to True once we observe this account cannot produce 192 kbps
        # mp3, so we stop probing the higher bitrate on every request
        self._mp3_hq_unsupported = False

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
            self.CONFIG_API_KEY: str
        }

    def configure(self, config):
        self._config = config
        self.api_key = self.get_configuration_value_mandatory(self.CONFIG_API_KEY)
        # re-probe the high-bitrate capability after a (re)configuration, e.g.
        # when the user switches key or upgrades their subscription tier
        self._mp3_hq_unsupported = False

    def voice_list(self):
        return self.basic_voice_list()

    def get_tts_audio(self, source_text, voice: voice.VoiceBase, voice_options):
        api_key = self.get_configuration_value_mandatory(self.CONFIG_API_KEY)

        voice_id = voice.voice_key['voice_id']
        base_url = f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}'

        # Handle audio format
        audio_format_str = voice_options.get(options.AUDIO_FORMAT_PARAMETER, voice.options.get(options.AUDIO_FORMAT_PARAMETER, {}).get('default', 'mp3'))

        headers = {
            "Accept": "audio/mpeg",
            "xi-api-key": api_key
        }

        use_speaker_boost_str = voice_options.get('use_speaker_boost', voice.options.get('use_speaker_boost', {}).get('default', 'false'))

        data = {
            "text": source_text,
            "model_id": voice.voice_key['model_id'],
            "voice_settings": {
                "stability": voice_options.get('stability', voice.options['stability']['default']),
                "similarity_boost": voice_options.get('similarity_boost', voice.options['similarity_boost']['default']),
                "style": voice_options.get('style', voice.options.get('style', {}).get('default', 0.0)),
                "speed": voice_options.get('speed', voice.options.get('speed', {}).get('default', 1.0)),
                "use_speaker_boost": use_speaker_boost_str == 'true'
            }
        }

        # Add language_code if provided and not empty
        language_code = voice_options.get('language_code', voice.options.get('language_code', {}).get('default', ''))
        if language_code:
            data['language_code'] = language_code

        if audio_format_str == 'ogg_opus':
            return self._request_audio(f'{base_url}?output_format=opus_48000_192', data, headers, source_text, voice)

        return self._request_mp3_audio(base_url, data, headers, source_text, voice)

    def _request_mp3_audio(self, base_url, data, headers, source_text, voice):
        # Request 192 kbps first, then fall back to the universally-available
        # 128 kbps when the account tier rejects the higher bitrate. As a
        # safety net we only treat it as tier-limited when the 128 kbps retry
        # actually succeeds -- a genuine error is surfaced unchanged.
        if not self._mp3_hq_unsupported:
            url = f'{base_url}?output_format={self.MP3_OUTPUT_FORMAT_HQ}'
            response = requests.post(url, json=data, headers=headers, timeout=constants.RequestTimeout)
            if response.status_code == 200:
                return response.content
            # A tier that cannot use 192 kbps is rejected with HTTP 403, e.g.
            # {"detail":{"code":"subscription_required","status":"output_format_not_allowed",
            #  "message":"Output format 'mp3_44100_192' is only available on the
            #  Creator tier and above."}}. Every other error (401 quota/auth,
            # 402 paid plan, 400 input, 429 rate limit, 5xx transient) is not
            # fixed by a lower bitrate, so surface it directly.
            if response.status_code != 403:
                self._raise_for_response(response, source_text, voice)
            logger.info(f'{self.name}: 192kbps mp3 not allowed on this tier; retrying at 128kbps')

        url = f'{base_url}?output_format={self.MP3_OUTPUT_FORMAT_DEFAULT}'
        response = requests.post(url, json=data, headers=headers, timeout=constants.RequestTimeout)
        if response.status_code == 200:
            # 128 kbps worked (possibly where 192 kbps did not): tier-limited
            self._mp3_hq_unsupported = True
            return response.content
        self._raise_for_response(response, source_text, voice)

    def _request_audio(self, url, data, headers, source_text, voice):
        response = requests.post(url, json=data, headers=headers, timeout=constants.RequestTimeout)
        if response.status_code == 200:
            return response.content
        self._raise_for_response(response, source_text, voice)

    def _raise_for_response(self, response, source_text, voice):
        error_message = f'{self.name}: error processing TTS request: {response.status_code} {response.text}'
        logger.warning(error_message)
        if response.status_code in (401, 402):
            raise errors.ServicePermissionError(source_text, voice, error_message)
        raise errors.RequestError(source_text, voice, error_message)
