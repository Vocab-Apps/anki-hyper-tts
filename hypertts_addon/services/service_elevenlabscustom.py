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
    'language_code' : {
        'type': options.ParameterType.text.name,
        'default': ''
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
                    logger.error(f'ElevenLabsCustom: error when processing voice {voice_entry}: {e}')
                    logger.error(e, exc_info=True)

        # logger.debug(pprint.pformat(result))
        return result

    def voice_list(self):
        return self.voice_list_cached()


    def get_tts_audio(self, source_text, voice: voice.TtsVoice_v3, voice_options):

        voice_id = voice.voice_key['voice_id']
        url = f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}'

        headers = self.get_headers()
        headers['Accept'] = "audio/mpeg"

        data = {
            "text": source_text,
            "model_id": voice.voice_key['model_id'],
            "voice_settings": {
                "stability": voice_options.get('stability', voice.options['stability']['default']),
                "similarity_boost": voice_options.get('similarity_boost', voice.options['similarity_boost']['default'])
            }
        }
        
        # Add language_code if provided and not empty
        language_code = voice_options.get('language_code', voice.options.get('language_code', {}).get('default', ''))
        if language_code:
            data['language_code'] = language_code

        response = requests.post(url, json=data, headers=headers, timeout=constants.RequestTimeout)
        if response.status_code != 200:
            error_message = f'{self.name}: error processing TTS request: {response.status_code} {response.text}'
            if response.status_code in [401]:
                # API key issue, or quota exceeded
                logger.warning(error_message)
            else:
                logger.error(error_message)
            raise errors.RequestError(source_text, voice, error_message)
        response.raise_for_status()
        
        return response.content
