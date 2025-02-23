import requests
import time
import datetime
import uuid
import urllib
import hmac
import base64

from hypertts_addon import voice
from hypertts_addon import service
from hypertts_addon import errors
from hypertts_addon import constants
from hypertts_addon import logging_utils
logger = logging_utils.get_child_logger(__name__)


class Alibaba(service.ServiceBase):
    CONFIG_ACCESS_KEY_ID = 'access_key_id'
    CONFIG_ACCESS_KEY_SECRET = 'access_key_secret'
    CONFIG_APP_KEY = 'app_key'
 
    access_token = None

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
            self.CONFIG_ACCESS_KEY_ID: str,
            self.CONFIG_ACCESS_KEY_SECRET: str,
            self.CONFIG_APP_KEY: str,
        }
    
    # this process is described by https://www.alibabacloud.com/help/en/isi/getting-started/use-http-or-https-to-obtain-an-access-token?spm=a2c63.p38356.0.i1#topic-2572194
    def refresh_token(self):
        logger.info(f"refreshing token")
        params = {
            "AccessKeyId": self.get_configuration_value_mandatory(self.CONFIG_ACCESS_KEY_ID),
            "Action": "CreateToken",
            "Version": "2019-07-17",
            "Format": "JSON",
            "RegionId": "ap-southeast-1",
            "Timestamp": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "SignatureMethod": "HMAC-SHA1",
            "SignatureVersion": "1.0",
            "SignatureNonce": str(uuid.uuid4())
        }
        # sort by keys alphabetically
        params = dict(sorted(params.items()))
        # timestamp needs to be double-quoted by the end for some reason
        params["Timestamp"] = urllib.parse.quote(params["Timestamp"], safe='')

        # do urlencode with noop lambda for no quoting - we will quote later
        params_str = urllib.parse.urlencode(params, quote_via=lambda a, b, c, d: a)

        # this is always /, as we always hit the path / on the API
        url_encoded = urllib.parse.quote("/", safe='')

        str_to_sign = f"GET&{url_encoded}&{urllib.parse.quote(params_str, safe='')}"
        str_to_sign = str_to_sign.encode("utf-8")

        key = self.get_configuration_value_mandatory(self.CONFIG_ACCESS_KEY_SECRET) + "&"
        key = key.encode("utf-8")

        # calculate HMAC-SHA1 digest, and convert to base64 repr
        dig = hmac.new(key, str_to_sign, "sha1").digest()
        dig = base64.standard_b64encode(dig).decode("utf-8")

        # signature also needs to be quoted...
        signature = urllib.parse.quote(dig, safe='')

        params_str = f"Signature={signature}&{params_str}"

        r = requests.get(f"http://nlsmeta.ap-southeast-1.aliyuncs.com/?{params_str}")
        
        # API definition says any error will return non-200 RC
        if r.status_code != 200:
            logger.warning(f"Request to http://nlsmeta.ap-southeast-1.aliyuncs.com/?{params_str} failed:\n {r.text}")
            return
        
        j = r.json()
        self.access_token = j["Token"]
        logger.info(f"Got access token: {self.access_token}")

    def voice_list(self):
        return self.basic_voice_list()

    def get_tts_audio(self, source_text, voice: voice.VoiceBase, voice_options):
        if not self.access_token or self.access_token["ExpireTime"] <= int(time.time()):
            self.refresh_token()

        app_key = self.get_configuration_value_mandatory(self.CONFIG_APP_KEY)
        speed = int(voice_options.get('speed', voice.options['speed']['default']))
        pitch = int(voice_options.get('pitch', voice.options['pitch']['default']))
        voice_name = voice.voice_key['name']

        params = {
            "format": "mp3",
            "appkey": app_key,
            "speech_rate": speed,
            "pitch_rate": pitch,
            "text": source_text,
            "token": self.access_token["Id"],
            "voice": voice_name
        }

        response = requests.get(
            "https://nls-gateway-ap-southeast-1.aliyuncs.com/stream/v1/tts",
            params=params,
            timeout=constants.RequestTimeout
        )
        
        if response.status_code != 200:
            data = response.json()
            error_message = data.get('message', str(data))
            logger.warning(error_message)
            raise errors.RequestError(source_text, voice, error_message)
        
        if response.headers['Content-Type'] != 'audio/mpeg':
            logger.warning(f'Unexpected response type. Response as text: {response.text}')
            raise errors.RequestError(
                source_text, voice,
                f'Got bad content type in response: {response.headers["Content-Type"]}'
            )
        
        # mp3 result is returned raw
        return response.content