import sys
import requests
import urllib
import hashlib
import time

voice = __import__('voice', globals(), locals(), [], sys._addon_import_level_services)
service = __import__('service', globals(), locals(), [], sys._addon_import_level_services)
errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_services)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_services)
logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_services)
logger = logging_utils.get_child_logger(__name__)

class VocalWare(service.ServiceBase):
    CONFIG_SECRET_PHRASE= 'secret_phrase'
    CONFIG_ACCOUNT_ID = 'account_id'
    CONFIG_API_ID = 'api_id'

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
            self.CONFIG_SECRET_PHRASE: str,
            self.CONFIG_ACCOUNT_ID: str,
            self.CONFIG_API_ID: str
        }

    def voice_list(self):
        return self.basic_voice_list()

    def get_tts_audio(self, source_text, voice: voice.VoiceBase, options):

        secret_phrase = self.get_configuration_value_mandatory(self.CONFIG_SECRET_PHRASE)
        account_id = self.get_configuration_value_mandatory(self.CONFIG_ACCOUNT_ID)
        api_id = self.get_configuration_value_mandatory(self.CONFIG_API_ID)

        urlencoded_text = urllib.parse.unquote_plus(source_text)

        # checksum calculation
        # CS = md5 (EID + LID + VID + TXT + EXT + FX_TYPE + FX_LEVEL + ACC + API+ SESSION + HTTP_ERR + SECRET PHRASE)
        checksum_input = f"""{voice.voice_key['engine_id']}{voice.voice_key['language_id']}{voice.voice_key['voice_id']}{source_text}{account_id}{api_id}{secret_phrase}"""
        checksum = hashlib.md5(checksum_input.encode('utf-8')).hexdigest()

        url_parameters = f"""EID={voice.voice_key['engine_id']}&LID={voice.voice_key['language_id']}&VID={voice.voice_key['voice_id']}&TXT={urlencoded_text}&ACC={account_id}&API={api_id}&CS={checksum}"""
        url = f"""http://www.vocalware.com/tts/gen.php?{url_parameters}"""

        retry_count = 3
        while retry_count > 0:
            response = requests.get(url, timeout=constants.RequestTimeout)
            if response.status_code == 200:
                return response.content
            retry_count -= 1
            time.sleep(0.5)

        response_data = response.content
        error_message = f'Status code: {response.status_code}: {response_data}'

        # reformat certain error messages
        if response.status_code == 503:
            error_message = f'VocalWare service temporarily unavailable (503)'

        raise errors.RequestError(source_text, voice, error_message)
