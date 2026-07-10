import sys
import requests
import pprint
import json
import cachetools


from hypertts_addon import voice
from hypertts_addon import languages
from hypertts_addon import service
from hypertts_addon import errors
from hypertts_addon import constants
from hypertts_addon import options
from hypertts_addon import logging_utils
logger = logging_utils.get_child_logger(__name__)

# elevenlabs v3 requires discrete values for stability
DEFAULT_STABILITY = 0.5
DEFAULT_SIMILARITY_BOOST = 0.75

VOICE_OPTIONS = {
    'stability' : {
        'type': options.ParameterType.number.name,
        'min': 0.0,
        'max': 1.0,
        'default': DEFAULT_STABILITY
    },
    'similarity_boost' : {
        'type': options.ParameterType.number.name,
        'min': 0.0,
        'max': 1.0,
        'default': DEFAULT_SIMILARITY_BOOST
    },
    'style' : {
        'type': options.ParameterType.number.name,
        'min': 0.0,
        'max': 1.0,
        'default': 0.0
    },
    'speed' : {
        'type': options.ParameterType.number.name,
        'min': 0.7,
        'max': 1.2,
        'default': 1.0
    },
    'use_speaker_boost' : {
        'type': options.ParameterType.list.name,
        'values': ['true', 'false'],
        'default': 'false'
    },
    'language_code' : {
        'type': options.ParameterType.text.name,
        'default': ''
    },
    'format' : {
        'type': options.ParameterType.list.name,
        'values': ['mp3', 'ogg_opus'],
        'default': 'mp3'
    },
}

GENDER_MAP = {
    'male': constants.Gender.Male,
    'female': constants.Gender.Female,
    'non-binary': constants.Gender.Any,
    'neutral': constants.Gender.Any
}

"""For custom voices user customer's own API keys"""
class ElevenLabsCustom(service.ServiceBase):
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
        # re-probe the high-bitrate capability after a (re)configuration, e.g.
        # when the user switches key or upgrades their subscription tier
        self._mp3_hq_unsupported = False

    def get_headers(self):
        api_key = self.get_configuration_value_mandatory(self.CONFIG_API_KEY)
        headers = {
            "Accept": "application/json",
            "xi-api-key": api_key
        }
        return headers

    def get_audio_language(self, language_id):
        logger.debug(f'processing language_id: {language_id}')
        override_map = {
            'pt': languages.AudioLanguage.pt_PT,
            'en-uk': languages.AudioLanguage.en_GB,
            'zh': languages.AudioLanguage.zh_CN,
            'id': languages.AudioLanguage.id_ID,
            'as': languages.AudioLanguage.as_IN, # Assamese
            'is': languages.AudioLanguage.is_IS, # Icelandic,
            'jv': languages.AudioLanguage.jv_ID, # Javanese,
            'sr': languages.AudioLanguage.sr_RS, # Serbian
            'sd': languages.AudioLanguage.sd_PK, # Sindhi
        }
        if language_id in override_map:
            return override_map[language_id]
        # try to reconstruct AudioLanguage
        language_id_components = language_id.split('-')
        if len(language_id_components) != 2:
            language_enum = languages.Language[language_id]
            audio_language_enum = languages.AudioLanguageDefaults[language_enum]
            return audio_language_enum
        else:
            modified_language_id = language_id_components[0] + '_' + language_id_components[1].upper()
            logger.debug(f'modified_language_id: {modified_language_id}')
            audio_language_enum = languages.AudioLanguage[modified_language_id]
            return audio_language_enum

    @cachetools.cached(cache=cachetools.TTLCache(maxsize=1, ttl=600))
    def voice_list_cached(self):
        try:
            return self._build_voice_list()
        except Exception as e:
            logger.warning(f'ElevenLabsCustom: failed to build voice list, returning empty list: {e}')
            return []

    def _build_voice_list(self):
        # get the list of models
        url = "https://api.elevenlabs.io/v1/models"
        response = requests.get(url, headers=self.get_headers(), timeout=constants.RequestTimeout)
        response.raise_for_status()
        model_data = response.json()

        # only retain models which can do text to speech
        model_data = [model for model in model_data if model['can_do_text_to_speech']]

        url = "https://api.elevenlabs.io/v1/voices"
        response = requests.get(url, headers=self.get_headers(), timeout=constants.RequestTimeout)
        response.raise_for_status()
        voice_data = response.json()['voices']

        result = []
        for model in model_data:
            model_id = model['model_id']
            model_name = model['name']
            model_short_name = model_name.replace('Eleven ', '').strip()
            for voice_entry in voice_data:
                try:
                    voice_name = voice_entry['name']
                    voice_id = voice_entry['voice_id']
                    voice_description = voice_entry.get('description', '')
                    voice_key = {
                        'voice_id': voice_id,
                        'model_id': model_id
                    }
                    audio_languages = []
                    for language_record in model['languages']:
                        logger.debug(f'processing voice: name: {voice_name} id: {voice_id} description: {voice_description} model_id: {model_id} language_record: {language_record}')
                        language_id = language_record['language_id']
                        audio_language_enum = self.get_audio_language(language_id)
                        audio_languages.append(audio_language_enum)
                    
                    # sometimes gender is not present, default to male
                    gender_str = voice_entry['labels'].get('gender', 'male')
                    gender = GENDER_MAP[gender_str]
                    name = f'{voice_name} ({model_short_name})'
                    result.append(voice.TtsVoice_v3(
                        name=name,
                        gender=gender,
                        audio_languages=audio_languages,
                        service=self.name,
                        voice_key=voice_key,
                        options=VOICE_OPTIONS,
                        service_fee=self.service_fee
                    ))
                except Exception as e:
                    logger.warning(f'ElevenLabsCustom: error when processing voice {e}: {voice_entry}')
                    logger.warning(e, exc_info=True)

        # logger.debug(pprint.pformat(result))
        return result

    def voice_list(self):
        return self.voice_list_cached()


    def get_tts_audio(self, source_text, voice: voice.TtsVoice_v3, voice_options):

        voice_id = voice.voice_key['voice_id']
        base_url = f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}'

        # Handle audio format
        audio_format_str = voice_options.get(options.AUDIO_FORMAT_PARAMETER, voice.options.get(options.AUDIO_FORMAT_PARAMETER, {}).get('default', 'mp3'))

        headers = self.get_headers()
        headers['Accept'] = "audio/mpeg"

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
        if response.status_code == 400:
            # ElevenLabs returns 400 for permanent input-validation failures
            # like unsupported language_code, voice_id not found, model_id
            # not compatible with language, etc. These should not be retried.
            # Sentry ANKI-HYPER-TTS-HGT.
            raise errors.ServiceInputError(source_text, voice, error_message)
        raise errors.RequestError(source_text, voice, error_message)
