import sys
import os
import re
import subprocess
import hashlib
import platform
import tempfile
import aqt.sound

voice = __import__('voice', globals(), locals(), [], sys._addon_import_level_services)
service = __import__('service', globals(), locals(), [], sys._addon_import_level_services)
errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_services)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_services)
languages = __import__('languages', globals(), locals(), [], sys._addon_import_level_services)
logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_services)
logger = logging_utils.get_child_logger(__name__)

class MacOS(service.ServiceBase):
    DEFAULT_SPEECH_RATE=175

    def __init__(self):
        # don't enable service by default, let the user choose
        service.ServiceBase.__init__(self)        

    @property
    def service_type(self) -> constants.ServiceType:
        return constants.ServiceType.tts

    @property
    def service_fee(self) -> constants.ServiceFee:
        return constants.ServiceFee.Free

    def voice_list(self):
        if platform.system() != "Darwin":
            logger.info(f'running on os {os.name}, disabling {self.name} service')
            return []
        
        try:
            raw_say_output=subprocess.check_output(["say", "-v", "?"])
            voice_list_from_say = raw_say_output.decode('utf-8')
            result = self.parse_voices(voice_list_from_say)
            logger.debug(f'MacOS voice list = {result}')
        except subprocess.CalledProcessError as cpe:
            logger.error(f'could not get macos voicelist: {cpe}', exc_info=True)
            result = []

        return result


    def parse_voices(self, voice_list):
        # Voices come in these forms:
        #   name       language_code   # example sentence
        #   name with spaces      language_code       # example sentence
        #   name (language name (country)) language_code   # example sentence
        #
        # No current examples of this but, theoretically, there could items in this form:
        #   name with spaces (language name (country)) language_code # example sentence
        #
        # The voices with the parenthetical detail are less refined and less natural
        # sounding. The following generator expression filters them out intentionally.


        regex = re.compile(r'^([\w ]+)\s\(*([\w() ]+)\)*\s(\w\w_\w+)')
        return [
            # Possible enhancement: add gender inference from names
            voice.Voice(name, constants.Gender.Any, languages.AudioLanguage[lang_id], self, name, {})
            for name, lang_id in sorted(
                (match.group(1).strip(), match.group(3))
                for match in [regex.match(line)
                    for line in voice_list.split('\n')]
                if match and match.group(2) == " "
            )
        ]

    def get_tts_audio(self, source_text, voice: voice.VoiceBase, options):
        logger.info(f'getting audio with voice {voice}')

        rate = options.get('rate', self.DEFAULT_SPEECH_RATE)

        try:
            temp_audio_file = tempfile.NamedTemporaryFile(suffix='.aiff', prefix='hypertts_macos', delete=False)
            arg_list = ['say', '-v', voice.name, '-r', str(rate), '-o', temp_audio_file.name, '--', source_text]
            logger.debug(f"calling 'say' with {arg_list}")
            subprocess.check_call(arg_list)

            mp3_temp_audio_file = tempfile.NamedTemporaryFile(suffix='.aiff', prefix='hypertts_macos')
            aqt.sound._encode_mp3(temp_audio_file.name, mp3_temp_audio_file.name)

            logger.debug(f'opening {mp3_temp_audio_file.name} to read in contents')
            with open(mp3_temp_audio_file.name, 'rb') as audio_file:
                audio = audio_file.read()
                return audio
        except:
            logger.exception(f'could not generate audio with service {self.name}')
            raise
