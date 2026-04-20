import sys
import requests
import datetime
import time

from hypertts_addon import voice
from hypertts_addon import service
from hypertts_addon import errors
from hypertts_addon import constants
from hypertts_addon import options
from hypertts_addon import logging_utils
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
        return constants.ServiceFee.paid

    def configuration_options(self):
        return {
            self.CONFIG_REGION: [
                'australiaeast',
                'brazilsouth',
                'canadacentral',
                'centralindia',
                'centralus',
                'chinaeast2',
                'chinanorth2',
                'chinanorth3',
                'eastasia',
                'eastus',
                'eastus2',
                'francecentral',
                'germanywestcentral',
                'japaneast',
                'japanwest',
                'koreacentral',
                'northcentralus',
                'northeurope',
                'norwayeast',
                'qatarcentral',
                'southafricanorth',
                'southcentralus',
                'southeastasia',
                'swedencentral',
                'switzerlandnorth',
                'switzerlandwest',
                'uaenorth',
                'uksouth',
                'usgovarizona',
                'usgovvirginia',
                'westcentralus',
                'westeurope',
                'westus',
                'westus2',
                'westus3'
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

        # DragonHD parameters
        parameters_attr = ''
        if 'DragonHD' in voice_name:
            dragonhd_defaults = {'temperature': 0.7, 'top_p': 0.7, 'top_k': 22, 'cfg_scale': 1.4}
            param_parts = []
            for param_name, default_val in dragonhd_defaults.items():
                val = voice_options.get(param_name, voice.options.get(param_name, {}).get('default', default_val))
                if val != default_val:
                    param_parts.append(f'{param_name}={val}')
            if param_parts:
                parameters_attr = f' parameters="{";".join(param_parts)}"'

        # Style / role express-as wrapper
        style_val = voice_options.get('style', voice.options.get('style', {}).get('default', ''))
        express_as_open = ''
        express_as_close = ''
        if style_val:
            styledegree_val = voice_options.get('styledegree', voice.options.get('styledegree', {}).get('default', 1.0))
            role_val = voice_options.get('role', voice.options.get('role', {}).get('default', ''))
            express_as_open = f'<mstts:express-as style="{style_val}"'
            if styledegree_val != 1.0:
                express_as_open += f' styledegree="{styledegree_val}"'
            if role_val:
                express_as_open += f' role="{role_val}"'
            express_as_open += '>'
            express_as_close = '</mstts:express-as>'

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
<voice name="{voice_name}"{parameters_attr}>{express_as_open}<prosody rate="{rate:0.1f}" pitch="{pitch:+.0f}Hz" >{source_text}</prosody>{express_as_close}</voice>
</speak>""".replace('\n', '')
        
        body = ssml_str.encode(encoding='utf-8')

        response = requests.post(constructed_url, headers=headers, data=body, timeout=constants.RequestTimeout)
        if response.status_code != 200:
            error_message = f'status code {response.status_code}: {response.reason}, response content: {response.text}'
            logger.warning(error_message)
            if response.status_code == 401:
                raise errors.ServicePermissionError(source_text, voice, error_message)
            raise errors.RequestError(source_text, voice, error_message)

        return response.content
