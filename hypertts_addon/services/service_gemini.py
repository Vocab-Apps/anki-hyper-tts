import base64
import binascii
import shutil
import subprocess
import time

import requests

from hypertts_addon import constants
from hypertts_addon import errors
from hypertts_addon import languages
from hypertts_addon import options
from hypertts_addon import service
from hypertts_addon import voice

MODEL_OPTIONS = [
    'gemini-2.5-flash-tts',
    'gemini-2.5-pro-tts',
]

VOICE_OPTIONS = {
    'instructions': {
        'type': options.ParameterType.text.name,
        'default': ''
    },
    'model': {
        'type': options.ParameterType.list.name,
        'values': MODEL_OPTIONS,
        'default': MODEL_OPTIONS[0]
    },
    options.AUDIO_FORMAT_PARAMETER: {
        'type': options.ParameterType.list.name,
        'values': [options.AudioFormat.mp3.name],
        'default': options.AudioFormat.mp3.name
    }
}

VOICE_NAMES = [
    'Zephyr',
    'Puck',
    'Charon',
    'Kore',
    'Fenrir',
    'Leda',
    'Orus',
    'Aoede',
    'Callirrhoe',
    'Autonoe',
    'Enceladus',
    'Iapetus',
    'Umbriel',
    'Algieba',
    'Despina',
    'Erinome',
    'Algenib',
    'Rasalgethi',
    'Laomedeia',
    'Achernar',
    'Alnilam',
    'Schedar',
    'Gacrux',
    'Pulcherrima',
    'Achird',
    'Zubenelgenubi',
    'Vindemiatrix',
    'Sadachbia',
    'Sadaltager',
    'Sulafat',
]

# Locale list kept deliberately focused to the set already exposed by HyperTTS,
# while matching Cloud Gemini-TTS locale codes.
SUPPORTED_VOICE_LOCALES = [
    (languages.AudioLanguage.en_US, 'en-us'),
    (languages.AudioLanguage.en_IN, 'en-in'),
    (languages.AudioLanguage.ar_XA, 'ar-xa'),
    (languages.AudioLanguage.bn_BD, 'bn-bd'),
    (languages.AudioLanguage.de_DE, 'de-de'),
    (languages.AudioLanguage.es_ES, 'es-es'),
    (languages.AudioLanguage.fr_FR, 'fr-fr'),
    (languages.AudioLanguage.hi_IN, 'hi-in'),
    (languages.AudioLanguage.id_ID, 'id-id'),
    (languages.AudioLanguage.it_IT, 'it-it'),
    (languages.AudioLanguage.ja_JP, 'ja-jp'),
    (languages.AudioLanguage.ko_KR, 'ko-kr'),
    (languages.AudioLanguage.mr_IN, 'mr-in'),
    (languages.AudioLanguage.nl_NL, 'nl-nl'),
    (languages.AudioLanguage.pl_PL, 'pl-pl'),
    (languages.AudioLanguage.pt_BR, 'pt-br'),
    (languages.AudioLanguage.ro_RO, 'ro-ro'),
    (languages.AudioLanguage.ru_RU, 'ru-ru'),
    (languages.AudioLanguage.ta_IN, 'ta-in'),
    (languages.AudioLanguage.te_IN, 'te-in'),
    (languages.AudioLanguage.th_TH, 'th-th'),
    (languages.AudioLanguage.tr_TR, 'tr-tr'),
    (languages.AudioLanguage.uk_UA, 'uk-ua'),
    (languages.AudioLanguage.vi_VN, 'vi-vn'),
    (languages.AudioLanguage.zh_CN, 'cmn-cn'),
    (languages.AudioLanguage.zh_TW, 'cmn-tw'),
]

GCLOUD_ACCESS_TOKEN_COMMANDS = [
    ['gcloud', 'auth', 'application-default', 'print-access-token'],
    ['gcloud', 'auth', 'print-access-token'],
]


class Gemini(service.ServiceBase):
    CONFIG_PROJECT_ID = 'project_id'
    CONFIG_THROTTLE_SECONDS = 'throttle_seconds'
    CONFIG_MAX_RETRIES = 'max_retries'
    CONFIG_RETRY_DELAY_SECONDS = 'retry_delay_seconds'
    DEFAULT_THROTTLE_SECONDS = 0.0
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RETRY_DELAY_SECONDS = 5.0
    ACCESS_TOKEN_TTL_SECONDS = 45 * 60

    def __init__(self):
        service.ServiceBase.__init__(self)
        self._voice_list = None
        self._cached_access_token = None
        self._cached_access_token_expires_at = 0.0

    @property
    def service_type(self) -> constants.ServiceType:
        return constants.ServiceType.tts

    @property
    def service_fee(self) -> constants.ServiceFee:
        return constants.ServiceFee.paid

    def configuration_options(self):
        return {
            self.CONFIG_PROJECT_ID: str,
        }

    def configuration_display_name(self):
        return 'Gemini (Cloud TTS)'

    def configuration_description(self):
        return (
            'paid, text-to-speech. Google Cloud Text-to-Speech Gemini-TTS with explicit locale selection. '
            'Requires a Google Cloud project and gcloud authentication.'
        )

    def configure(self, config):
        self._config = config

    def normalize_language_code(self, language_code):
        if language_code is None:
            return None
        return str(language_code).replace('_', '-').lower()

    def normalize_voice_key(self, voice_key):
        if not isinstance(voice_key, dict):
            return voice_key

        normalized_voice_key = dict(voice_key)
        if 'name' in normalized_voice_key and 'voice_name' not in normalized_voice_key:
            normalized_voice_key['voice_name'] = normalized_voice_key.pop('name')
        if 'language_code' in normalized_voice_key:
            normalized_voice_key['language_code'] = self.normalize_language_code(normalized_voice_key['language_code'])
        return normalized_voice_key

    def matches_voice_key(self, requested_voice_key, candidate_voice_key):
        normalized_requested_voice_key = self.normalize_voice_key(requested_voice_key)
        normalized_candidate_voice_key = self.normalize_voice_key(candidate_voice_key)

        if normalized_requested_voice_key == normalized_candidate_voice_key:
            return True

        if not isinstance(normalized_requested_voice_key, dict) or not isinstance(normalized_candidate_voice_key, dict):
            return False

        if normalized_requested_voice_key.get('voice_name') != normalized_candidate_voice_key.get('voice_name'):
            return False

        requested_language_code = normalized_requested_voice_key.get('language_code')
        if requested_language_code is None:
            return True

        return requested_language_code == normalized_candidate_voice_key.get('language_code')

    def voice_list(self):
        if self._voice_list is None:
            voices = []
            for voice_name in VOICE_NAMES:
                for audio_language, language_code in SUPPORTED_VOICE_LOCALES:
                    voices.append(voice.TtsVoice_v3(
                        name=voice_name,
                        gender=constants.Gender.Any,
                        audio_languages=[audio_language],
                        service=self.name,
                        voice_key={
                            'voice_name': voice_name,
                            'language_code': language_code,
                        },
                        options=VOICE_OPTIONS,
                        service_fee=self.service_fee
                    ))
            self._voice_list = voices
        return self._voice_list

    def build_payload(self, source_text, voice_entry: voice.TtsVoice_v3, voice_options):
        model = voice_options.get('model', voice_entry.options['model']['default'])
        instructions = voice_options.get('instructions', voice_entry.options['instructions']['default']).strip()
        synthesis_input = {
            'text': source_text,
        }
        if instructions:
            synthesis_input['prompt'] = instructions

        payload = {
            'input': synthesis_input,
            'voice': {
                'languageCode': voice_entry.voice_key['language_code'],
                'name': voice_entry.voice_key['voice_name'],
                'modelName': model,
            },
            'audioConfig': {
                'audioEncoding': 'MP3',
            }
        }
        return model, payload

    def clear_access_token_cache(self):
        self._cached_access_token = None
        self._cached_access_token_expires_at = 0.0

    def get_access_token(self, source_text, voice_entry, force_refresh=False):
        now = time.monotonic()
        if not force_refresh and self._cached_access_token and now < self._cached_access_token_expires_at:
            return self._cached_access_token

        if shutil.which('gcloud') is None:
            raise errors.RequestError(
                source_text,
                voice_entry,
                'gcloud CLI not found. Install Google Cloud SDK and run `gcloud auth application-default login`.',
            )

        command_errors = []
        for command in GCLOUD_ACCESS_TOKEN_COMMANDS:
            try:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=constants.RequestTimeout,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                command_errors.append(f'{" ".join(command)} timed out')
                continue
            except OSError as exc:
                command_errors.append(f'{" ".join(command)} failed: {exc}')
                continue

            token = result.stdout.strip()
            if result.returncode == 0 and token:
                self._cached_access_token = token
                self._cached_access_token_expires_at = time.monotonic() + self.ACCESS_TOKEN_TTL_SECONDS
                return token

            stderr_output = (result.stderr or result.stdout or '').strip()
            if stderr_output:
                command_errors.append(f'{" ".join(command)}: {stderr_output}')

        detail = ' | '.join(command_errors) if command_errors else 'no output from gcloud'
        raise errors.RequestError(
            source_text,
            voice_entry,
            'could not acquire Google Cloud access token. '
            'Run `gcloud auth application-default login` and ensure your project has Cloud TTS enabled. '
            f'Details: {detail}',
        )

    def build_request_headers(self, source_text, voice_entry, force_refresh=False):
        project_id = self.get_configuration_value_optional(self.CONFIG_PROJECT_ID, None)
        if project_id is None or len(project_id) == 0:
            raise errors.MissingServiceConfiguration(self.name, self.CONFIG_PROJECT_ID)
        access_token = self.get_access_token(source_text, voice_entry, force_refresh=force_refresh)
        return {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json; charset=utf-8',
            'x-goog-user-project': project_id,
        }

    def parse_error_message(self, response):
        try:
            data = response.json()
        except ValueError:
            return response.text
        return data.get('error', {}).get('message', response.text)

    def get_retry_delay(self, response, retry_delay_seconds, attempt):
        retry_after = response.headers.get('Retry-After')
        if retry_after:
            try:
                return max(float(retry_after), retry_delay_seconds)
            except ValueError:
                pass
        return retry_delay_seconds * (attempt + 1)

    def post_with_retry(self, url, payload, source_text, voice_entry):
        max_retries = self.get_configuration_value_optional(self.CONFIG_MAX_RETRIES, self.DEFAULT_MAX_RETRIES)
        retry_delay_seconds = self.get_configuration_value_optional(
            self.CONFIG_RETRY_DELAY_SECONDS,
            self.DEFAULT_RETRY_DELAY_SECONDS,
        )
        refreshed_credentials = False

        for attempt in range(max_retries + 1):
            force_refresh = False

            try:
                while True:
                    response = requests.post(
                        url,
                        json=payload,
                        headers=self.build_request_headers(
                            source_text,
                            voice_entry,
                            force_refresh=force_refresh,
                        ),
                        timeout=constants.RequestTimeout,
                    )

                    if response.status_code == 401 and not refreshed_credentials:
                        refreshed_credentials = True
                        self.clear_access_token_cache()
                        force_refresh = True
                        continue

                    break
            except requests.exceptions.RequestException as exc:
                if attempt < max_retries:
                    time.sleep(retry_delay_seconds * (attempt + 1))
                    continue
                raise errors.RequestError(source_text, voice_entry, f'network error contacting Google Cloud TTS: {exc}')

            if response.status_code == 200:
                return response

            if response.status_code in (429, 500, 502, 503, 504) and attempt < max_retries:
                time.sleep(self.get_retry_delay(response, retry_delay_seconds, attempt))
                continue

            error_message = self.parse_error_message(response)
            raise errors.RequestError(source_text, voice_entry, error_message)

        raise errors.RequestError(source_text, voice_entry, 'exhausted retry attempts contacting Google Cloud TTS')

    def get_tts_audio(self, source_text, voice_entry: voice.TtsVoice_v3, voice_options):
        throttle_seconds = self.get_configuration_value_optional(self.CONFIG_THROTTLE_SECONDS, self.DEFAULT_THROTTLE_SECONDS)
        if throttle_seconds > 0:
            time.sleep(throttle_seconds)

        _, payload = self.build_payload(source_text, voice_entry, voice_options)
        response = self.post_with_retry(
            'https://texttospeech.googleapis.com/v1/text:synthesize',
            payload,
            source_text,
            voice_entry,
        )

        try:
            data = response.json()
        except ValueError:
            raise errors.RequestError(source_text, voice_entry, 'invalid JSON response from Gemini Cloud TTS')

        encoded_audio_content = data.get('audioContent')
        if not encoded_audio_content:
            raise errors.RequestError(source_text, voice_entry, 'audio payload missing from Gemini Cloud TTS response')

        try:
            return base64.b64decode(encoded_audio_content)
        except (ValueError, binascii.Error):
            raise errors.RequestError(source_text, voice_entry, 'invalid base64 audio payload from Gemini Cloud TTS')
