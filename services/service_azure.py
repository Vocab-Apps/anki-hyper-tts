import sys
import requests
import datetime
import time

voice = __import__('voice', globals(), locals(), [], sys._addon_import_level_services)
service = __import__('service', globals(), locals(), [], sys._addon_import_level_services)
errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_services)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_services)
options = __import__('options', globals(), locals(), [], sys._addon_import_level_services)
logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_services)
logger = logging_utils.get_child_logger(__name__)

class Azure(service.ServiceBase):
    CONFIG_REGION = 'region'
    CONFIG_API_KEY = 'api_key'
    CONFIG_THROTTLE_SECONDS = 'throttle_seconds'

    def __init__(self):
        service.ServiceBase.__init__(self)
        self.access_token = None

    def cloudlanguagetools_enabled(self):
        return True

    @property
    def service_type(self) -> constants.ServiceType:
        return constants.ServiceType.tts

    @property
    def service_fee(self) -> constants.ServiceFee:
        return constants.ServiceFee.Premium

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
                'germanywestcentral'
            ],
            self.CONFIG_API_KEY: str,
            self.CONFIG_THROTTLE_SECONDS: float
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
        logger.debug(f'requested access_token')

    def token_refresh_required(self):
        if self.access_token == None:
            logger.debug(f'no token, must request')
            return True
        time_diff = datetime.datetime.now() - self.access_token_timestamp
        if time_diff.total_seconds() > 300:
            logger.debug(f'time_diff: {time_diff}, requesting token')
            return True
        return False

    def voice_list(self):
        return self.basic_voice_list()

    def get_tts_audio(self, source_text, voice: voice.VoiceBase, voice_options):

        region = self.get_configuration_value_mandatory(self.CONFIG_REGION)
        subscription_key = self.get_configuration_value_mandatory(self.CONFIG_API_KEY)
        throttle_seconds = self.get_configuration_value_optional(self.CONFIG_THROTTLE_SECONDS, 0)

        if throttle_seconds > 0:
            time.sleep(throttle_seconds)
        
        if self.token_refresh_required():
            self.get_token(subscription_key, region)

        voice_name = voice.voice_key['name']

        rate = voice_options.get('rate', voice.options['rate']['default'])
        pitch = voice_options.get('pitch', voice.options['pitch']['default'])

        audio_format_str = voice_options.get(options.AUDIO_FORMAT_PARAMETER, options.AudioFormat.mp3.name)
        audio_format = options.AudioFormat[audio_format_str]
        audio_format_map = {
            options.AudioFormat.mp3: 'audio-24khz-96kbitrate-mono-mp3',
            options.AudioFormat.ogg_opus: 'ogg-48khz-16bit-mono-opus'
        }

        base_url = f'https://{region}.tts.speech.microsoft.com/'
        url_path = 'cognitiveservices/v1'
        constructed_url = base_url + url_path
        headers = {
            'Authorization': 'Bearer ' + self.access_token,
            'Content-Type': 'application/ssml+xml',
            'X-Microsoft-OutputFormat': audio_format_map[audio_format],
            'User-Agent': 'anki-hyper-tts'
        }

        ssml_str = f"""<speak version="1.0" xmlns="https://www.w3.org/2001/10/synthesis" xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="en-US">
<voice name="{voice_name}"><prosody rate="{rate:0.1f}" pitch="{pitch:+.0f}Hz" >{source_text}</prosody></voice>
</speak>""".replace('\n', '')
        
        body = ssml_str.encode(encoding='utf-8')

        response = requests.post(constructed_url, headers=headers, data=body, timeout=constants.RequestTimeout)
        if response.status_code != 200:
            error_message = f'status code {response.status_code}: {response.reason}'
            logger.error(error_message)
            raise errors.RequestError(source_text, voice, error_message)

        return response.content
