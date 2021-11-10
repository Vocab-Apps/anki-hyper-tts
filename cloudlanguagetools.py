import os
import requests
import json
import logging

from . import constants
from . import errors
from . import version

class CloudLanguageTools():
    def __init__(self):
        self.base_url = 'https://cloud-language-tools-nlp-prod.anki.study'
        if constants.ENV_VAR_ANKI_LANGUAGE_TOOLS_BASE_URL in os.environ:
            self.base_url = os.environ[constants.ENV_VAR_ANKI_LANGUAGE_TOOLS_BASE_URL]

    def get_language_data(self):
        response = requests.get(self.base_url + '/language_data_v1')
        return json.loads(response.content)

    def api_key_validate_query(self, api_key):
        response = requests.post(self.base_url + '/verify_api_key', json={
            'api_key': api_key
        })
        data = json.loads(response.content)
        return data

    def account_info(self, api_key):
        response = requests.get(self.base_url + '/account', headers={'api_key': api_key})
        data = json.loads(response.content)
        return data

    def language_detection(self, api_key, field_sample):
        response = requests.post(self.base_url + '/detect', json={
                'text_list': field_sample
        }, headers={'api_key': api_key})
        if response.status_code == 200:
            data = json.loads(response.content)
            detected_language = data['detected_language']

            return detected_language
        else:
            # error occured, return none
            logging.error(f'could not perform language detection: (status code {response.status_code}) {response.content}')
            return None        

    def get_tts_voice_list(self, api_key):
        response = requests.get(self.base_url + '/voice_list')
        if response.status_code == 200:
            data = json.loads(response.content)
            return data
        raise errors.VoiceListRequestError(f'Could not retrieve voice list, please try again ({response.content})')

    def get_tts_audio(self, api_key, source_text, service, language_code, voice_key, options):
        url_path = '/audio_v2'
        data = {
            'text': source_text,
            'service': service,
            'voice_key': voice_key,
            'request_mode': 'batch',
            'language_code': language_code,
            'deck_name': 'n/a',
            'options': options
        }
        response = requests.post(self.base_url + url_path, json=data, 
            headers={'api_key': api_key, 'client': constants.CLIENT_NAME, 'client_version': version.ANKI_LANGUAGE_TOOLS_VERSION})

        if response.status_code == 200:
            return response.content
        else:
            response_data = json.loads(response.content)
            error_msg = response_data
            if 'error' in response_data:
                error_msg = 'Error: ' + response_data['error']
            raise errors.AudioLanguageToolsRequestError(f'Status Code: {response.status_code} ({error_msg})')

    def get_translation(self, api_key, source_text, translation_option):
        response = requests.post(self.base_url + '/translate', json={
            'text': source_text,
            'service': translation_option['service'],
            'from_language_key': translation_option['source_language_id'],
            'to_language_key': translation_option['target_language_id']
        }, headers={'api_key': api_key})
        return response

    def get_transliteration(self, api_key, source_text, transliteration_option):
        response = requests.post(self.base_url + '/transliterate', json={
                'text': source_text,
                'service': transliteration_option['service'],
                'transliteration_key': transliteration_option['transliteration_key']
        }, headers={'api_key': api_key})
        return response        

    def get_breakdown(self, api_key, source_text, tokenization_option, translation_option, transliteration_option):
        breakdown_request = {
                'text': source_text,
                'tokenization_option': tokenization_option
        }
        if translation_option != None:
            breakdown_request['translation_option'] = translation_option
        if transliteration_option != None:
            breakdown_request['transliteration_option'] = transliteration_option
        logging.debug(f'sending breakdown request: {breakdown_request}')
        response = requests.post(self.base_url + '/breakdown_v1', json=breakdown_request, headers={'api_key': api_key})
        return response        


    def get_translation_all(self, api_key, source_text, from_language, to_language):
        response = requests.post(self.base_url + '/translate_all', json={
                'text': source_text,
                'from_language': from_language,
                'to_language': to_language
        }, headers={'api_key': api_key})
        data = json.loads(response.content)        
        return data