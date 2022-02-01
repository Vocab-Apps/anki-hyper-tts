import sys
import requests
import datetime
import logging

voice = __import__('voice', globals(), locals(), [], sys._addon_import_level_services)
service = __import__('service', globals(), locals(), [], sys._addon_import_level_services)
errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_services)

class Azure(service.ServiceBase):
    CONFIG_REGION = 'region'
    CONFIG_API_KEY = 'api_key'

    def __init__(self):
        service.ServiceBase.__init__(self)
        self.access_token = None

    def cloudlanguagetools_enabled(self):
        return True

    def configuration_options(self):
        return {
            self.CONFIG_REGION: [
                'centralus',
                'eastus',
                'eastus2',
                'northcentralus',
                'southcentralus',
                'westcentralus',
                'westus',
                'westus2',
                'canadacentral',
                'brazilsouth',
                'eastasia',
                'southeastasia',
                'australiaeast',
                'centralindia',
                'japaneast',
                'japanwest',
                'koreacentral',
                'northeurope',
                'westeurope',
                'francecentral',
                'switzerlandnorth',
                'uksouth',                
            ],
            self.CONFIG_API_KEY: str
        }

    def get_token(self, subscription_key, region):
        if len(subscription_key) == 0:
            raise ValueError("subscription key required")

        fetch_token_url = f"https://{region}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
        headers = {
            'Ocp-Apim-Subscription-Key': subscription_key
        }
        response = requests.post(fetch_token_url, headers=headers)
        self.access_token = str(response.text)
        self.access_token_timestamp = datetime.datetime.now()
        logging.debug(f'requested access_token')

    def token_refresh_required(self):
        if self.access_token == None:
            logging.debug(f'no token, must request')
            return True
        time_diff = datetime.datetime.now() - self.access_token_timestamp
        if time_diff.total_seconds() > 300:
            logging.debug(f'time_diff: {time_diff}, requesting token')
            return True
        return False

    def voice_list(self):
        return self.basic_voice_list()

    def get_tts_audio(self, source_text, voice: voice.VoiceBase, options):

        region = self.get_configuration_value_mandatory(self.CONFIG_REGION)
        subscription_key = self.get_configuration_value_mandatory(self.CONFIG_API_KEY)
        
        if self.token_refresh_required():
            self.get_token(subscription_key, region)

        voice_name = voice.voice_key['name']

        rate = voice.options['rate']['default']
        pitch = voice.options['pitch']['default']

        base_url = f'https://{region}.tts.speech.microsoft.com/'
        url_path = 'cognitiveservices/v1'
        constructed_url = base_url + url_path
        headers = {
            'Authorization': 'Bearer ' + self.access_token,
            'Content-Type': 'application/ssml+xml',
            'X-Microsoft-OutputFormat': 'audio-24khz-96kbitrate-mono-mp3',
            'User-Agent': 'anki-hyper-tts'
        }

        ssml_str = f"""<speak version="1.0" xmlns="https://www.w3.org/2001/10/synthesis" xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="en-US">
<voice name="{voice_name}"><prosody rate="{rate:0.1f}" pitch="{pitch:+.0f}Hz" >{source_text}</prosody></voice>
</speak>""".replace('\n', '')
        
        body = ssml_str.encode(encoding='utf-8')

        response = requests.post(constructed_url, headers=headers, data=body)
        if response.status_code != 200:
            error_message = f'status code {response.status_code}: {response.reason}'
            logging.error(error_message)
            raise errors.RequestError(source_text, voice, error_message)

        return response.content
