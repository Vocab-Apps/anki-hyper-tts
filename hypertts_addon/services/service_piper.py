import os
import tempfile
import requests
import cachetools
import aqt.sound

from hypertts_addon import voice
from hypertts_addon import service
from hypertts_addon import errors
from hypertts_addon import constants
from hypertts_addon import languages
from hypertts_addon import options
from hypertts_addon import logging_utils
logger = logging_utils.get_child_logger(__name__)

DEFAULT_LENGTH_SCALE = 1.0
DEFAULT_NOISE_SCALE = 0.667
DEFAULT_NOISE_W_SCALE = 0.8

VOICE_OPTIONS = {
    'length_scale': {
        'type': options.ParameterType.number.name,
        'min': 0.1,
        'max': 3.0,
        'default': DEFAULT_LENGTH_SCALE
    },
    'noise_scale': {
        'type': options.ParameterType.number.name,
        'min': 0.0,
        'max': 1.0,
        'default': DEFAULT_NOISE_SCALE
    },
    'noise_w_scale': {
        'type': options.ParameterType.number.name,
        'min': 0.0,
        'max': 1.0,
        'default': DEFAULT_NOISE_W_SCALE
    },
}


class Piper(service.ServiceBase):
    CONFIG_BASE_URL = 'base_url'
    DEFAULT_BASE_URL = 'http://localhost:5100'

    def __init__(self):
        service.ServiceBase.__init__(self)

    def cloudlanguagetools_enabled(self):
        return False

    @property
    def service_type(self) -> constants.ServiceType:
        return constants.ServiceType.tts

    @property
    def service_fee(self) -> constants.ServiceFee:
        return constants.ServiceFee.free

    def enabled_by_default(self):
        return False

    def configuration_options(self):
        return {
            self.CONFIG_BASE_URL: str
        }

    def configure(self, config):
        self._config = config
        self.base_url = self.get_configuration_value_optional(
            self.CONFIG_BASE_URL, self.DEFAULT_BASE_URL
        ).rstrip('/')

    def get_base_url(self):
        if hasattr(self, 'base_url'):
            return self.base_url
        return self.DEFAULT_BASE_URL

    def get_audio_language(self, language_code):
        """Map piper language code (e.g. 'en_US') to AudioLanguage enum."""
        try:
            return languages.AudioLanguage[language_code]
        except KeyError:
            pass

        # try with AudioLanguageDefaults for the base language
        lang_parts = language_code.split('_')
        lang_family = lang_parts[0]
        try:
            language_enum = languages.Language[lang_family]
            if language_enum in languages.AudioLanguageDefaults:
                return languages.AudioLanguageDefaults[language_enum]
        except KeyError:
            pass

        logger.warning(f'could not map piper language code: {language_code}')
        return None

    @cachetools.cached(cache=cachetools.TTLCache(maxsize=1, ttl=300))
    def voice_list_cached(self):
        base_url = self.get_base_url()
        url = f'{base_url}/voices'

        try:
            response = requests.get(url, timeout=constants.RequestTimeout)
            response.raise_for_status()
        except requests.exceptions.ConnectionError:
            logger.warning(f'Piper: could not connect to {url}')
            return []
        except requests.exceptions.Timeout:
            logger.warning(f'Piper: timeout connecting to {url}')
            return []

        voices_data = response.json()
        result = []

        for model_id, voice_config in voices_data.items():
            try:
                language_info = voice_config.get('language', {})
                language_code = language_info.get('code', '')
                audio_language = self.get_audio_language(language_code)

                if audio_language is None:
                    logger.warning(f'Piper: skipping voice {model_id}, unrecognized language: {language_code}')
                    continue

                num_speakers = voice_config.get('num_speakers', 1)
                speaker_id_map = voice_config.get('speaker_id_map', {})

                if num_speakers <= 1 or not speaker_id_map:
                    # single speaker voice
                    voice_key = {
                        'model_id': model_id,
                    }
                    result.append(voice.TtsVoice_v3(
                        name=model_id,
                        gender=constants.Gender.Any,
                        audio_languages=[audio_language],
                        service=self.name,
                        voice_key=voice_key,
                        options=VOICE_OPTIONS,
                        service_fee=self.service_fee
                    ))
                else:
                    # multi-speaker voice: create one entry per speaker
                    for speaker_name, speaker_id in speaker_id_map.items():
                        voice_key = {
                            'model_id': model_id,
                            'speaker_id': speaker_id,
                            'speaker_name': speaker_name,
                        }
                        display_name = f'{model_id} ({speaker_name})'
                        result.append(voice.TtsVoice_v3(
                            name=display_name,
                            gender=constants.Gender.Any,
                            audio_languages=[audio_language],
                            service=self.name,
                            voice_key=voice_key,
                            options=VOICE_OPTIONS,
                            service_fee=self.service_fee
                        ))

            except Exception as e:
                logger.error(f'Piper: error processing voice {model_id}: {e}')
                logger.error(e, exc_info=True)

        return result

    def voice_list(self):
        return self.voice_list_cached()

    def get_tts_audio(self, source_text, voice: voice.TtsVoice_v3, voice_options):
        base_url = self.get_base_url()

        data = {
            'text': source_text,
            'voice': voice.voice_key['model_id'],
        }

        # add speaker_id for multi-speaker voices
        if 'speaker_id' in voice.voice_key:
            data['speaker_id'] = voice.voice_key['speaker_id']

        # apply voice options
        length_scale = voice_options.get('length_scale', VOICE_OPTIONS['length_scale']['default'])
        noise_scale = voice_options.get('noise_scale', VOICE_OPTIONS['noise_scale']['default'])
        noise_w_scale = voice_options.get('noise_w_scale', VOICE_OPTIONS['noise_w_scale']['default'])

        data['length_scale'] = float(length_scale)
        data['noise_scale'] = float(noise_scale)
        data['noise_w_scale'] = float(noise_w_scale)

        try:
            response = requests.post(base_url, json=data, timeout=constants.RequestTimeout)
        except requests.exceptions.ConnectionError as e:
            raise errors.RequestError(
                source_text, voice,
                f'Piper: could not connect to {base_url}: {e}'
            )
        except requests.exceptions.Timeout as e:
            raise errors.RequestError(
                source_text, voice,
                f'Piper: request timed out: {e}'
            )

        if response.status_code != 200:
            error_message = f'Piper: error {response.status_code}: {response.text}'
            logger.error(error_message)
            raise errors.RequestError(source_text, voice, error_message)

        # piper returns WAV audio — convert to MP3 via Anki's encoder
        wav_audio = response.content

        fh_wav, wav_temp_file = tempfile.mkstemp(prefix='hypertts_piper_', suffix='.wav')
        fh_mp3, mp3_temp_file = tempfile.mkstemp(prefix='hypertts_piper_', suffix='.mp3')

        try:
            os.write(fh_wav, wav_audio)
            os.close(fh_wav)
            os.close(fh_mp3)

            aqt.sound._encode_mp3(wav_temp_file, mp3_temp_file)

            with open(mp3_temp_file, 'rb') as f:
                mp3_audio = f.read()

            return mp3_audio
        finally:
            if os.path.exists(wav_temp_file):
                os.remove(wav_temp_file)
            if os.path.exists(mp3_temp_file):
                os.remove(mp3_temp_file)
