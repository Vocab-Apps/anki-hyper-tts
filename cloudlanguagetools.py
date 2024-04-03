import sys
import os
import requests
import json

errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_base)
version = __import__('version', globals(), locals(), [], sys._addon_import_level_base)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_base)
config_models = __import__('config_models', globals(), locals(), [], sys._addon_import_level_base)
logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_base)
logger = logging_utils.get_child_logger(__name__)

if hasattr(sys, '_sentry_crash_reporting'):
    import sentry_sdk

class CloudLanguageTools():
    def __init__(self):
        self.clt_api_base_url = os.environ.get('ANKI_LANGUAGE_TOOLS_BASE_URL', constants.CLOUDLANGUAGETOOLS_API_BASE_URL)
        self.vocabai_api_base_url = os.environ.get('ANKI_LANGUAGE_TOOLS_VOCABAI_BASE_URL', constants.VOCABAI_API_BASE_URL)

    def configure(self, config: config_models.Configuration):
        self.config = config

    def get_request_headers(self):
        if self.config.use_vocabai_api:
            return {
                'Authorization': f'Api-Key {self.config.hypertts_pro_api_key}',
                'User-Agent': f'anki-hyper-tts/{version.ANKI_HYPER_TTS_VERSION}'}
        else:
            return {
                'api_key': self.config.hypertts_pro_api_key, 
                'client': 'hypertts', 
                'client_version': version.ANKI_HYPER_TTS_VERSION,
                'User-Agent': f'anki-hyper-tts/{version.ANKI_HYPER_TTS_VERSION}'}

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
        else:
            url_path = '/audio_v2'
        full_url = self.get_base_url() + url_path
        data = {
            'text': source_text,
            'service': voice.service.name,
            'request_mode': audio_request_context.get_request_mode().name,
            'language_code': voice.language.lang.name,
            'voice_key': voice.voice_key,
            'options': options
        }
        logger.info(f'request url: {full_url}, data: {data}')
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


    def request_trial_key(self, email):
        logger.info(f'requesting trial key for email {email}')
        response = requests.post(self.clt_api_base_url + '/request_trial_key', json={'email': email})
        data = json.loads(response.content)
        logger.info(f'retrieved {data}')
        return data        