import sys
import requests
import datetime
import time
import boto3
import botocore
import contextlib


voice = __import__('voice', globals(), locals(), [], sys._addon_import_level_services)
service = __import__('service', globals(), locals(), [], sys._addon_import_level_services)
errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_services)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_services)
options = __import__('options', globals(), locals(), [], sys._addon_import_level_services)
logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_services)
logger = logging_utils.get_child_logger(__name__)

class Amazon(service.ServiceBase):
    CONFIG_ACCESS_KEY_ID = 'aws_access_key_id'
    CONFIG_SECRET_ACCESS_KEY = 'aws_secret_access_key'
    CONFIG_REGION = 'aws_region'
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
            self.CONFIG_ACCESS_KEY_ID: str,
            self.CONFIG_SECRET_ACCESS_KEY: str,
            self.CONFIG_REGION: [
                'us-east-1',
                'us-west-1',
                'us-west-2',
                'af-south-1',
                'ap-east-1',
                'ap-southeast-3',
                'ap-south-1',
                'ap-northeast-3',
                'ap-northeast-2',
                'ap-southeast-1',
                'ap-southeast-2',
                'ap-northeast-1',
                'ca-central-1',
                'eu-central-1',
                'eu-west-1',
                'eu-west-2',
                'eu-south-1',
                'eu-west-3',
                'eu-north-1',
                'me-south-1',
                'sa-east-1',
                'us-gov-east-1',
                'us-gov-west-1',                
            ],
            self.CONFIG_THROTTLE_SECONDS: float
        }

    def configure(self, config):
        self._config = config
        self.polly_client = boto3.client("polly",
            aws_access_key_id=self.get_configuration_value_mandatory(self.CONFIG_ACCESS_KEY_ID),
            aws_secret_access_key=self.get_configuration_value_mandatory(self.CONFIG_SECRET_ACCESS_KEY),
            region_name=self.get_configuration_value_optional(self.CONFIG_REGION, 'us-east-1'),
            config=botocore.config.Config(connect_timeout=constants.RequestTimeout, read_timeout=constants.RequestTimeout))        


    def voice_list(self):
        return self.basic_voice_list()

    def get_tts_audio(self, source_text, voice: voice.VoiceBase, voice_options):
        # try to get mandatory configuration items to ensure configuration has been done
        aws_access_key_id=self.get_configuration_value_mandatory(self.CONFIG_ACCESS_KEY_ID)
        aws_secret_access_key=self.get_configuration_value_mandatory(self.CONFIG_SECRET_ACCESS_KEY)

        throttle_seconds = self.get_configuration_value_optional(self.CONFIG_THROTTLE_SECONDS, 0)
        if throttle_seconds > 0:
            time.sleep(throttle_seconds)        

        pitch = voice_options.get('pitch', voice.options['pitch']['default'])
        pitch_str = f'{pitch:+.0f}%'
        rate = voice_options.get('rate', voice.options['rate']['default'])
        rate_str = f'{rate:0.0f}%'

        audio_format_str = voice_options.get(options.AUDIO_FORMAT_PARAMETER, options.AudioFormat.mp3.name)
        audio_format = options.AudioFormat[audio_format_str]
        audio_format_map = {
            options.AudioFormat.mp3: 'mp3',
            options.AudioFormat.ogg_vorbis: 'ogg_vorbis'
        }

        prosody_tags = f'pitch="{pitch_str}" rate="{rate_str}"'
        if voice.voice_key['engine'] == 'neural':
            # pitch not supported on neural voices
            prosody_tags = f'rate="{rate_str}"'


        ssml_str = f"""<speak>
    <prosody {prosody_tags} >
        {source_text}
    </prosody>
</speak>"""

        try:
            response = self.polly_client.synthesize_speech(Text=ssml_str, TextType="ssml", OutputFormat=audio_format_map[audio_format], VoiceId=voice.voice_key['voice_id'], Engine=voice.voice_key['engine'])
        except (botocore.exceptions.BotoCoreError, botocore.exceptions.ClientError) as error:
            raise errors.RequestError(source_text, voice, str(error))

        if "AudioStream" in response:
            with contextlib.closing(response["AudioStream"]) as stream:
                return stream.read()

        raise errors.RequestError(source_text, voice, 'no audio stream')