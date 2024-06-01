import sys
import requests
import base64
import time
import uuid
import hmac
import hashlib
import datetime

voice = __import__('voice', globals(), locals(), [], sys._addon_import_level_services)
service = __import__('service', globals(), locals(), [], sys._addon_import_level_services)
errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_services)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_services)
languages = __import__('languages', globals(), locals(), [], sys._addon_import_level_services)
logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_services)
logger = logging_utils.get_child_logger(__name__)



class NaverPapago(service.ServiceBase):
    CONFIG_THROTTLE_SECONDS = 'throttle_seconds'

    TRANSLATE_ENDPOINT = 'https://papago.naver.com/apis/tts/'
    TRANSLATE_MKID = TRANSLATE_ENDPOINT + 'makeID'    
    HMAC_KEY = 'v1.8.1_b443f57e55'
    UUID = str(uuid.uuid4())

    def __init__(self):
        service.ServiceBase.__init__(self)

    def configuration_options(self):
        return {
            self.CONFIG_THROTTLE_SECONDS: float
        }

    @property
    def service_type(self) -> constants.ServiceType:
        return constants.ServiceType.tts

    @property
    def service_fee(self) -> constants.ServiceFee:
        return constants.ServiceFee.Free

    def build_voice(self, audio_language, gender, speaker_name):
        return voice.Voice(speaker_name, gender, audio_language, self, speaker_name, {})

    def voice_list(self):
        return [
            self.build_voice(languages.AudioLanguage.ko_KR, constants.Gender.Female, 'kyuri'),
            self.build_voice(languages.AudioLanguage.ja_JP, constants.Gender.Female, 'yuri'),
            self.build_voice(languages.AudioLanguage.en_US, constants.Gender.Female, 'clara'),
            self.build_voice(languages.AudioLanguage.zh_CN, constants.Gender.Female, 'meimei'),
            self.build_voice(languages.AudioLanguage.zh_TW, constants.Gender.Female, 'chiahua'),
            self.build_voice(languages.AudioLanguage.es_ES, constants.Gender.Female, 'carmen'),
            self.build_voice(languages.AudioLanguage.fr_FR, constants.Gender.Female, 'roxane'),
            self.build_voice(languages.AudioLanguage.de_DE, constants.Gender.Female, 'lena'),
            self.build_voice(languages.AudioLanguage.ru_RU, constants.Gender.Female, 'vera'),
            self.build_voice(languages.AudioLanguage.th_TH, constants.Gender.Female, 'somsi'),
        ]

    # This function implements function I(a,t) found at
    # https://papago.naver.com/main.87cbe57a9fc46d3db5c1.chunk.js
    # 2021/05/27 update:
    # HMAC_KEY has changed, and the timestamp is now in milliseconds
    # use this tool: https://lelinhtinh.github.io/de4js/
    #  var b = function (e, a) {
    #     var t = Object(E.a)(),
    #         n = (new Date).getTime() + a - d;
    #     return {
    #         Authorization: "PPG " + t + ":" + p.a.HmacMD5(t + "\n" + e.split("?")[0] + "\n" + n, "v1.8.1_b443f57e55").toString(p.a.enc.Base64),
    #         Timestamp: n
    #     }
    # },

    def compute_token(self, timestamp, uuid_str):
        msg = uuid_str + '\n' + self.TRANSLATE_MKID + '\n' + timestamp
        signature = hmac.new(bytes(self.HMAC_KEY, 'ascii'), bytes(msg, 'ascii'),
                            hashlib.md5).digest()
        signature = base64.b64encode(signature).decode()
        auth = 'PPG ' + uuid_str + ':' + signature
        return auth

    def generate_headers(self):
        timestamp_seconds_float = datetime.datetime.now().timestamp()
        timestamp_milliseconds = timestamp_seconds_float * 1000.0
        timestamp_str = str(int(timestamp_milliseconds))
        auth = self.compute_token(timestamp_str, self.UUID)

        return {'authorization': auth, 
                'timestamp': timestamp_str,
                'Content-Type': 'application/x-www-form-urlencoded',
                'Host': 'papago.naver.com',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:88.0) Gecko/20100101 Firefox/88.0',
                'Accept': 'application/json',
                'Accept-Language': 'en-US',
                'Accept-Encoding': 'gzip, deflate, br',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Content-Length': '64',
                'Origin': 'https://papago.naver.com',
                'Referer': 'https://papago.naver.com/',
                'Connection': 'keep-alive',
                'Pragma': 'no-cache',
                'Cache-Control': 'no-cache',
                'TE': 'Trailers'
        }

    def get_tts_audio(self, source_text, voice: voice.VoiceBase, options):
        # configuration options
        throttle_seconds = self.get_configuration_value_optional(self.CONFIG_THROTTLE_SECONDS, 0)
        if throttle_seconds > 0:
            time.sleep(throttle_seconds)

        url = self.TRANSLATE_MKID
        params = {
            'alpha': 0,
            'pitch': 0,
            'speaker': voice.voice_key,
            'speed': 0,
            'text': source_text,
        }
        headers = self.generate_headers()
        logger.info(f'executing POST request on {url} with headers={headers}, data={params}')
        response = requests.post(url, headers=headers, data=params)
        if response.status_code != 200:
            raise errors.RequestError(source_text, voice, f'got status_code {response.status_code} from {url}: {response.content}')

        response_data = response.json()
        sound_id = response_data['id']
        logger.info(f'retrieved sound_id successfully: {sound_id}')

        # actually retrieve sound file
        # ============================

        final_url = self.TRANSLATE_ENDPOINT + sound_id
        logger.info(f'final_url: {final_url}')

        response = requests.get(final_url)
        if response.status_code != 200:
            raise errors.RequestError(source_text, voice, f'got status_code {response.status_code} from {final_url}: {response.content}')
        return response.content
