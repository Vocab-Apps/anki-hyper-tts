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
        logger.info(f'using CLT API base URL: {self.clt_api_base_url}')
        logger.info(f'using VocabAi API base URL: {self.vocabai_api_base_url}')

    def configure(self, config: config_models.Configuration):
        self.config = config

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

    def get_tts_audio(self, source_text, voice, options, audio_request_context):
        if hasattr(sys, '_sentry_crash_reporting'):
            sentry_sdk.set_user({"id": f'api_key:{self.config.hypertts_pro_api_key}'})
            sentry_sdk.set_context("user", {
                "api_key": self.config.hypertts_pro_api_key,
            })

        # query cloud language tools API
        if self.config.use_vocabai_api:
            url_path = '/audio'
            # api V4
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
                'options': options
            }            
        else:
            url_path = '/audio_v2'
            data = {
                'text': source_text,
                'service': voice.service,
                'request_mode': audio_request_context.get_request_mode().name,
                'language_code': voice_module.get_audio_language_for_voice(voice).lang.name,
                'voice_key': voice.voice_key,
                'options': options
            }
        full_url = self.get_base_url() + url_path
        logger.info(f'request url: {full_url}, data: {data}')
        headers = self.get_request_headers()
        logger.debug(f'get_tts_audio: headers: {headers} data: {data}')
        response = requests.post(full_url, json=data, headers=self.get_request_headers(),
            timeout=constants.RequestTimeout)

        if response.status_code == 200:
            return response.content
        elif response.status_code == 404:
            raise errors.AudioNotFoundError(source_text, voice)
        else:
            error_message = f"Status code: {response.status_code} ({response.content})"
            raise errors.RequestError(source_text, voice, error_message)    

    def account_info(self, api_key):
        # try to get account data on vocabai first
        logger.debug(f'verifying API key on vocabai API')
        response = requests.get(self.vocabai_api_base_url + '/account', headers={
                'Authorization': f'Api-Key {api_key}',
                'User-Agent': f'anki-hyper-tts/{version.ANKI_HYPER_TTS_VERSION}'}
        )
        logger.debug(f'vocabai API result: {response.json()}')
        if response.status_code == 200:
            # API key is valid on vocab API
            return config_models.HyperTTSProAccountConfig(
                api_key=api_key,
                api_key_valid=True,
                use_vocabai_api=True,
                account_info=response.json()
            )

        # now try to get account data on CLT API
        logger.debug(f'verifying API key on CLT API')
        response = requests.get(self.clt_api_base_url + '/account', headers={'api_key': api_key})
        logger.debug(f'CLT API result: {response.json()}')
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
        logger.info(f'checking email verification status for email {email}')
        
        response = requests.get(self.vocabai_api_base_url + '/check_email_verification',
                               headers=self.get_request_headers())
        
        if response.status_code != 200:
            error_message = f"Status code: {response.status_code} ({response.content})"
            raise errors.RequestError(email, None, error_message)
        
        data = json.loads(response.content)
        return data['email_verified']

    def request_trial_key(self, email, password, client_uuid) -> config_models.TrialRequestReponse:
        logger.info(f'requesting trial key for email {email}')
        
        data = self.build_trial_key_request_data(email, password, client_uuid)
        response = requests.post(self.vocabai_api_base_url + '/register_trial', 
                                 json=data,
                                 headers=self.get_trial_request_headers())
        data = json.loads(response.content)
        logger.info(f'retrieved {data}, status_code: {response.status_code}')

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
