import sys
import os
import re
import subprocess
import hashlib
import platform
import tempfile
import aqt.sound
from typing import List

voice = __import__('voice', globals(), locals(), [], sys._addon_import_level_services)
service = __import__('service', globals(), locals(), [], sys._addon_import_level_services)
errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_services)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_services)
languages = __import__('languages', globals(), locals(), [], sys._addon_import_level_services)
logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_services)
logger = logging_utils.get_child_logger(__name__)

class MacOS(service.ServiceBase):
    MIN_SPEECH_RATE=150
    DEFAULT_SPEECH_RATE=175
    MAX_SPEECH_RATE=220

    GENDER_MAP = {
        "Albert": constants.Gender.Male,
        "Alice": constants.Gender.Female,
        "Alva": constants.Gender.Female,
        "Amélie": constants.Gender.Female,
        "Amira": constants.Gender.Female,
        "Anna": constants.Gender.Female,
        "Bad News": constants.Gender.Male,
        "Bahh": constants.Gender.Male,
        "Bells": constants.Gender.Female,
        "Boing": constants.Gender.Male,
        "Bubbles": constants.Gender.Female,
        "Carmit": constants.Gender.Female,
        "Cellos": constants.Gender.Male,
        "Damayanti": constants.Gender.Female,
        "Daniel": constants.Gender.Male,
        "Daria": constants.Gender.Female,
        "Wobble": constants.Gender.Male,
        "Eddy": constants.Gender.Male,  # Multiple languages, assumed all male based on name
        "Ellen": constants.Gender.Female,
        "Flo": constants.Gender.Female,  # Multiple languages, assumed all female based on name
        "Fred": constants.Gender.Male,
        "Good News": constants.Gender.Male,
        "Grandma": constants.Gender.Female,  # Multiple languages, all female
        "Grandpa": constants.Gender.Male,  # Multiple languages, all male
        "Jester": constants.Gender.Male,
        "Ioana": constants.Gender.Female,
        "Jacques": constants.Gender.Male,
        "Joana": constants.Gender.Female,
        "Junior": constants.Gender.Male,
        "Kanya": constants.Gender.Female,
        "Karen": constants.Gender.Female,
        "Kathy": constants.Gender.Female,
        "Kyoko": constants.Gender.Female,
        "Lana": constants.Gender.Female,
        "Laura": constants.Gender.Female,
        "Lekha": constants.Gender.Female,
        "Lesya": constants.Gender.Female,
        "Linh": constants.Gender.Female,
        "Luciana": constants.Gender.Female,
        "Majed": constants.Gender.Male,
        "Tünde": constants.Gender.Female,
        "Meijia": constants.Gender.Female,
        "Melina": constants.Gender.Female,
        "Milena": constants.Gender.Female,
        "Moira": constants.Gender.Female,
        "Mónica": constants.Gender.Female,
        "Montse": constants.Gender.Female,
        "Nora": constants.Gender.Female,
        "Organ": constants.Gender.Male,
        "Paulina": constants.Gender.Female,
        "Superstar": constants.Gender.Male,
        "Ralph": constants.Gender.Male,
        "Reed": constants.Gender.Male,  # Multiple languages, assumed all male based on name
        "Rishi": constants.Gender.Male,
        "Rocko": constants.Gender.Male,  # Multiple languages, all male
        "Samantha": constants.Gender.Female,
        "Sandy": constants.Gender.Female,  # Multiple languages, all female
        "Sara": constants.Gender.Female,
        "Satu": constants.Gender.Female,
        "Shelley": constants.Gender.Female,  # Multiple languages, all female
        "Sinji": constants.Gender.Female,
        "Tessa": constants.Gender.Female,
        "Thomas": constants.Gender.Male,
        "Tingting": constants.Gender.Female,
        "Trinoids": constants.Gender.Male,
        "Whisper": constants.Gender.Male,
        "Xander": constants.Gender.Male,
        "Yelda": constants.Gender.Female,
        "Yuna": constants.Gender.Female,
        "Zarvox": constants.Gender.Male,
        "Zosia": constants.Gender.Female,
        "Zuzana": constants.Gender.Female
    }

    VOICE_OPTIONS = {
            'rate': {'default': DEFAULT_SPEECH_RATE, 'max': MAX_SPEECH_RATE, 'min': MIN_SPEECH_RATE, 'type': 'number_int'}
    }

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

    def get_audio_language(self, lang_id: str) -> languages.AudioLanguage:
        override_map = {
            'ar_001': 'ar_XA'
        }
        lang_id = override_map.get(lang_id, lang_id)
        return languages.AudioLanguage[lang_id]

    def get_gender_from_name(self, name):
        # get gender from name, default to male for new voices
        return self.GENDER_MAP.get(name, constants.Gender.Male)

    def parse_voices(self, voice_list_lines) -> List[voice.Voice]:
        # see test_tts_services / test_macos_parse_voice_list for examples of the input
        result = []

        for line in voice_list_lines.split('\n'):
            if line == '':
                continue
            try:
                logger.debug(f'{self.name}: parsing line: [{line}]')

                # Split the line on the hash symbol
                name_and_lang, example_sentence = line.split('#', 1)
                # remove whitespace
                name_and_lang = name_and_lang.strip()

                # Split the name and language on the last occurrence of two spaces
                voice_name, lang_id = name_and_lang.rsplit(' ', 1)

                # Now you can strip parentheses from the name and trim whitespace
                voice_name = voice_name.strip()
                lang_id = lang_id.strip()

                audio_language = self.get_audio_language(lang_id)
                gender = self.get_gender_from_name(voice_name)
                parsed_voice = voice.Voice(voice_name, gender, audio_language, self, voice_name, self.VOICE_OPTIONS)
                logger.debug(f'parsed voice: {parsed_voice}')
                result.append(parsed_voice)
            except:
                logger.error(f'could not parse line: [{line}]', exc_info=True)

        return result

    def get_tts_audio(self, source_text, voice: voice.VoiceBase, options):
        logger.info(f'getting audio with voice {voice}')

        rate = options.get('rate', self.DEFAULT_SPEECH_RATE)

        try:
            temp_audio_file = tempfile.NamedTemporaryFile(suffix='.aiff', prefix='hypertts_macos', delete=False)
            arg_list = ['say', '-v', voice.name, '-r', str(rate), '-o', temp_audio_file.name, '--', source_text]
            logger.debug(f"calling 'say' with {arg_list}")
            subprocess.check_call(arg_list)

            mp3_temp_audio_file = tempfile.NamedTemporaryFile(suffix='.mp3', prefix='hypertts_macos')
            aqt.sound._encode_mp3(temp_audio_file.name, mp3_temp_audio_file.name)

            logger.debug(f'opening {mp3_temp_audio_file.name} to read in contents')
            with open(mp3_temp_audio_file.name, 'rb') as audio_file:
                audio = audio_file.read()
                return audio
        except:
            logger.exception(f'could not generate audio with service {self.name}')
            raise
