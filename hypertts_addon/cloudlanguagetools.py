import sys
import os
import requests
import json
import base64

from . import errors
from . import version
from . import constants
from . import config_models
from . import voice as voice_module
from . import logging_utils
from . import config_models
logger = logging_utils.get_child_logger(__name__)

if hasattr(sys, '_sentry_crash_reporting'):
    import sentry_sdk

class CloudLanguageTools():
    def __init__(self):
        self.clt_api_base_url = os.environ.get('ANKI_LANGUAGE_TOOLS_BASE_URL', constants.CLOUDLANGUAGETOOLS_API_BASE_URL)
        self.vocabai_api_base_url = os.environ.get('ANKI_LANGUAGE_TOOLS_VOCABAI_BASE_URL', constants.VOCABAI_API_BASE_URL)
        self.disable_ssl_verification = False
        logger.info(f'using CLT API base URL: {self.clt_api_base_url}')
        logger.info(f'using VocabAi API base URL: {self.vocabai_api_base_url}')

    def configure(self, config: config_models.Configuration, disable_ssl_verification: bool = False):
        self.config = config
        self.disable_ssl_verification = disable_ssl_verification
        if self.disable_ssl_verification:
            logger.warning('SSL verification is disabled for cloud language tools connections')

    def get_request_headers(self):
        if self.config.use_vocabai_api:
            return {
                'Authorization': f'Api-Key {self.config.hypertts_pro_api_key}',
            }
        else:
            return {
                'api_key': self.config.hypertts_pro_api_key, 
                'client': 'hypertts', 
                'client_version': version.ANKI_HYPER_TTS_VERSION,
                'User-Agent': f'anki-hyper-tts/{version.ANKI_HYPER_TTS_VERSION}'}

    def get_trial_request_headers(self):
        return {
            'User-Agent': f'anki-hyper-tts/{version.ANKI_HYPER_TTS_VERSION}',
            'X-Vocab-Addon-ID': self.config.user_uuid
        }

    def get_base_url(self):
        if self.config.use_vocabai_api:
            if self.config.vocabai_api_url_override != None:
                return self.config.vocabai_api_url_override
            return self.vocabai_api_base_url
        else:
            return self.clt_api_base_url

    def get_vocabai_url(self, path):
        if self.config.vocabai_api_url_override != None:
            base_url = self.config.vocabai_api_url_override
        else:
            base_url = self.vocabai_api_base_url
        return base_url + f'/languagetools-api/v5/{path}'

    def get_verify_ssl(self):
        """Returns the SSL verification setting for requests. Returns True (verify SSL) by default."""
        return not self.disable_ssl_verification

    # Raises only subclasses of:
    #   PermanentError  – non-retryable (400, 403, 404)
    #   TransientError  – retryable (503, 504, timeout, unknown)
    def get_tts_audio(self, source_text, voice, options, audio_request_context):
        if hasattr(sys, '_sentry_crash_reporting'):
            sentry_sdk.set_user({"id": f'api_key:{self.config.hypertts_pro_api_key}'})
            sentry_sdk.set_context("user", {
                "api_key": self.config.hypertts_pro_api_key,
            })

        if self.config.use_vocabai_api:
            return self._get_tts_audio_vocabai(source_text, voice, options, audio_request_context)
        else:
            return self._get_tts_audio_clt(source_text, voice, options, audio_request_context)

    def _get_tts_audio_vocabai(self, source_text, voice, options, audio_request_context):
        # API v5
        full_url = self.get_vocabai_url('audio')
        data = {
            'text': source_text,
            'service': voice.service,
            'request_mode': audio_request_context.get_request_mode().name,
            'client': constants.CLIENT_NAME,
            'client_version': version.ANKI_HYPER_TTS_VERSION,
            'client_uuid': self.config.user_uuid,
            'batch_uuid': audio_request_context.get_batch_uuid_str(),
            'language_code': voice_module.get_audio_language_for_voice(voice).lang.name,
            'voice_key': voice.voice_key,
            'options': options,
            'retry_count': audio_request_context.retry_count,
            'retry_max': audio_request_context.retry_max,
        }
        logger.info(f'_get_tts_audio_vocabai: request url: {full_url}, data: {data}')
        headers = self.get_request_headers()
        logger.debug(f'_get_tts_audio_vocabai: headers: {headers} data: {data}')

        try:
            response = requests.post(full_url, json=data, headers=headers,
                timeout=constants.RequestTimeout, verify=self.get_verify_ssl())
            logger.info(f'_get_tts_audio_vocabai: response status_code: {response.status_code}')

            if response.status_code == 200:
                # success
                return response.content

            if response.status_code == 404:
                # not found (for example on Forvo)
                raise errors.AudioNotFoundError(source_text, voice)

            # extract response JSON
            response_data = response.json()

            if response.status_code == 400:
                if 'error' in response_data:
                    raise errors.PermanentError(source_text, voice, response_data['error'])
                raise errors.PermanentError(source_text, voice, str(response_data))
            elif response.status_code == 403:
                # permission issue
                detail = response_data.get('detail', 'Forbidden')
                raise errors.PermissionError(source_text, voice, detail)
            elif response.status_code == 503:
                # transient error with retry-after in seconds
                retry_after = response_data.get('retry_after', 30)
                error_msg = response_data.get('error', 'rate limited')
                raise errors.RateLimitRetryAfterError(source_text, voice, error_msg, retry_after)
            elif response.status_code == 504:
                # transient error without specific retry-after
                error_msg = response_data.get('error', 'temporary failure')
                raise errors.TransientError(source_text, voice, error_msg)

            # default: log full details and raise
            error_message = f"Status code: {response.status_code} ({response.content})"
            logger.exception(f'Unhandled VocabAI API error: {error_message}')
            raise errors.UnknownServiceError(source_text, voice, error_message)

        except errors.HyperTTSError:
            # we need to let the exceptions created by parsing the payload through, 
            # since they have the correct error type and message
            raise
        except requests.exceptions.Timeout:
            raise errors.TimeoutError(source_text, voice, 'HTTP request timed out')
        except Exception as e:
            # eventually we should not have any exceptions coming through here
            # for now, classify them as unknown service errors, which is a TransientError
            logger.exception(f'Unexpected error during VocabAI HTTP request: {e}')
            raise errors.UnknownServiceError(source_text, voice, str(e))

    def _get_tts_audio_clt(self, source_text, voice, options, audio_request_context):
        full_url = self.get_base_url() + '/audio_v2'
        data = {
            'text': source_text,
            'service': voice.service,
            'request_mode': audio_request_context.get_request_mode().name,
            'language_code': voice_module.get_audio_language_for_voice(voice).lang.name,
            'voice_key': voice.voice_key,
            'options': options
        }
        logger.info(f'_get_tts_audio_clt: request url: {full_url}, data: {data}')
        headers = self.get_request_headers()
        logger.debug(f'_get_tts_audio_clt: headers: {headers} data: {data}')

        try:
            response = requests.post(full_url, json=data, headers=headers,
                timeout=constants.RequestTimeout, verify=self.get_verify_ssl())
            logger.info(f'_get_tts_audio_clt: response status_code: {response.status_code}')
        except requests.exceptions.Timeout:
            raise errors.TimeoutError(source_text, voice, 'HTTP request timed out')

        if response.status_code == 200:
            return response.content
        elif response.status_code == 404:
            raise errors.AudioNotFoundError(source_text, voice)
        else:
            error_message = f"Status code: {response.status_code} ({response.content})"
            raise errors.UnknownServiceError(source_text, voice, error_message)    

    def account_info(self, api_key):
        # try to get account data on vocabai first
        vocabai_url = self.get_vocabai_url('account')
        logger.info(f'account_info: request url: {vocabai_url}, data: None')
        response = requests.get(vocabai_url, headers={
                'Authorization': f'Api-Key {api_key}',
                'User-Agent': f'anki-hyper-tts/{version.ANKI_HYPER_TTS_VERSION}'},
            verify=self.get_verify_ssl()
        )
        logger.info(f'account_info: response status_code: {response.status_code}')
        if response.status_code == 200:
            logger.debug(f'vocabai API result: {response.json()}')
            # API key is valid on vocab API
            return config_models.HyperTTSProAccountConfig(
                api_key=api_key,
                api_key_valid=True,
                use_vocabai_api=True,
                account_info=response.json()
            )

        # now try to get account data on CLT API
        clt_url = self.clt_api_base_url + '/account'
        logger.info(f'account_info: request url: {clt_url}, data: None')
        response = requests.get(clt_url, headers={'api_key': api_key},
            verify=self.get_verify_ssl())
        logger.info(f'account_info: response status_code: {response.status_code}')
        if response.status_code == 200:
            # API key is valid on CLT API
            # check if there are errors
            if 'error' in response.json():
                return config_models.HyperTTSProAccountConfig(
                    api_key=api_key,
                    api_key_valid=False,
                    api_key_error=response.json()['error'])

            # otherwise, it's considered valid
            return config_models.HyperTTSProAccountConfig(
                api_key=api_key,
                api_key_valid=True,
                use_vocabai_api=False,
                account_info=response.json()
            )

        # default case, API key is not valid
        return config_models.HyperTTSProAccountConfig(
            api_key=api_key,
            api_key_valid=False,
            api_key_error='API key not found')


    def build_trial_key_request_data(self, email, password, client_uuid):
        namespace = {}
        exec(base64.b64decode(constants.REQUEST_TRIAL_PAYLOAD).decode('utf-8'), namespace)
        data = namespace['build_trial_request_payload'](email, client_uuid)
        data['email'] = email
        data['password'] = password
        return data

    def check_email_verification_status(self, email) -> bool:
        url = self.get_vocabai_url('check_email_verification')
        logger.info(f'check_email_verification_status: request url: {url}, data: None')

        response = requests.get(url,
                               headers=self.get_request_headers(),
                               verify=self.get_verify_ssl())
        logger.info(f'check_email_verification_status: response status_code: {response.status_code}')

        if response.status_code != 200:
            error_message = f"Status code: {response.status_code} ({response.content})"
            raise errors.RequestError(email, None, error_message)
        
        data = json.loads(response.content)
        return data['email_verified']

    def request_trial_key(self, email, password, client_uuid) -> config_models.TrialRequestReponse:
        url = self.get_vocabai_url('register_trial')
        data = self.build_trial_key_request_data(email, password, client_uuid)
        logger.info(f'request_trial_key: request url: {url}, data: {data}')
        response = requests.post(url,
                                 json=data,
                                 headers=self.get_trial_request_headers(),
                                 verify=self.get_verify_ssl())
        logger.info(f'request_trial_key: response status_code: {response.status_code}')
        data = json.loads(response.content)

        if response.status_code == 201:
            # trial key was successfully created
            return config_models.TrialRequestReponse(
                success=True,
                api_key=data['api_key']
            )
        else:
            error_message = '<b>error:</b> ' + ', '.join([f"{key}: {value}" for key, value in data.items()])
            return config_models.TrialRequestReponse(
                success=False,
                error=error_message
            )
