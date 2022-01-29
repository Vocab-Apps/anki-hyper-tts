import sys
import os
import logging
import requests
import json

errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_base)
version = __import__('version', globals(), locals(), [], sys._addon_import_level_base)

class CloudLanguageTools():
    def __init__(self):
        self.base_url = os.environ.get('ANKI_LANGUAGE_TOOLS_BASE_URL', 'https://cloud-language-tools-tts-prod.anki.study')

    def configure(self, api_key):
        self.api_key = api_key

    def get_tts_audio(self, source_text, voice, options):
        # query cloud language tools API
        url_path = '/audio_v2'
        full_url = self.cloudlanguagetools_base_url + url_path
        data = {
            'text': source_text,
            'service': voice.service.name,
            'request_mode': 'batch',
            'language_code': voice.language.lang.name,
            'voice_key': voice.voice_key,
            'options': options
        }
        logging.info(f'request url: {full_url}, data: {data}')
        response = requests.post(full_url, json=data, headers={
            'api_key': self.cloudlanguagetools_api_key, 
            'client': 'hypertts', 
            'client_version': version.ANKI_HYPER_TTS_VERSION})

        if response.status_code == 200:
            return response.content
        else:
            error_message = f"Status code: {response.status_code} ({response.content})"
            raise errors.RequestError(source_text, voice, error_message)    

    def account_info(self, api_key):
        response = requests.get(self.base_url + '/account', headers={'api_key': api_key})
        data = json.loads(response.content)
        return data