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
    'Aasing (Enhanced)': constants.Gender.Male,
    'Agnes': constants.Gender.Female,
    'Albert': constants.Gender.Male,
    'Alex': constants.Gender.Male,
    'Alice': constants.Gender.Female,
    'Alice (Enhanced)': constants.Gender.Female,
    'Allison': constants.Gender.Female,
    'Allison (Enhanced)': constants.Gender.Female,
    'Soumya': constants.Gender.Female,
    'Soumya (Enhanced)': constants.Gender.Female,
    'Alva': constants.Gender.Female,
    'Alva (Enhanced)': constants.Gender.Female,
    'Alva (Premium)': constants.Gender.Female,
    'Amélie': constants.Gender.Female,
    'Amélie (Enhanced)': constants.Gender.Female,
    'Amélie (Premium)': constants.Gender.Female,
    'Amira': constants.Gender.Female,
    'Amira (Enhanced)': constants.Gender.Female,
    'Ananya': constants.Gender.Female,
    'Ananya (Enhanced)': constants.Gender.Female,
    'Angélica (Enhanced)': constants.Gender.Female,
    'Anna': constants.Gender.Female,
    'Anna (Enhanced)': constants.Gender.Female,
    'Anna (Premium)': constants.Gender.Female,
    'Aude': constants.Gender.Female,
    'Aude (Enhanced)': constants.Gender.Female,
    'Audrey': constants.Gender.Female,
    'Audrey (Enhanced)': constants.Gender.Female,
    'Audrey (Premium)': constants.Gender.Female,
    'Aurélie': constants.Gender.Female,
    'Aurélie (Enhanced)': constants.Gender.Female,
    'Ava': constants.Gender.Female,
    'Ava (Enhanced)': constants.Gender.Female,
    'Ava (Premium)': constants.Gender.Female,
    'Bad News': constants.Gender.Male,
    'Bahh': constants.Gender.Male,
    'Bells': constants.Gender.Female,
    'Binbin': constants.Gender.Male,
    'Binbin (Enhanced)': constants.Gender.Male,
    'Bobo (Enhanced)': constants.Gender.Male,
    'Boing': constants.Gender.Male,
    'Bruce': constants.Gender.Male,
    'Bubbles': constants.Gender.Female,
    'Carlos': constants.Gender.Male,
    'Carlos (Enhanced)': constants.Gender.Male,
    'Carmela': constants.Gender.Female,
    'Carmela (Enhanced)': constants.Gender.Female,
    'Carmit': constants.Gender.Female,
    'Carmit (Enhanced)': constants.Gender.Female,
    'Catarina': constants.Gender.Female,
    'Catarina (Enhanced)': constants.Gender.Female,
    'Cellos': constants.Gender.Male,
    'Cem': constants.Gender.Male,
    'Cem (Enhanced)': constants.Gender.Male,
    'Chantal': constants.Gender.Female,
    'Chantal (Enhanced)': constants.Gender.Female,
    'Claire': constants.Gender.Female,
    'Claire (Enhanced)': constants.Gender.Female,
    'Damayanti': constants.Gender.Female,
    'Damayanti (Enhanced)': constants.Gender.Female,
    'Daniel': constants.Gender.Male,
    'Daniel (Enhanced)': constants.Gender.Male,
    'Daria': constants.Gender.Female,
    'Daria (Enhanced)': constants.Gender.Female,
    'Dariush': constants.Gender.Male,
    'Dariush (Enhanced)': constants.Gender.Male,
    'Wobble': constants.Gender.Male,
    'Diego': constants.Gender.Male,
    'Diego (Enhanced)': constants.Gender.Male,
    'Dongmei (Enhanced)': constants.Gender.Female,
    'Eddy (German (Germany))': constants.Gender.Male,
    'Eddy (English (UK))': constants.Gender.Male,
    'Eddy (English (US))': constants.Gender.Male,
    'Eddy (Spanish (Spain))': constants.Gender.Male,
    'Eddy (Spanish (Mexico))': constants.Gender.Male,
    'Eddy (Finnish (Finland))': constants.Gender.Male,
    'Eddy (French (Canada))': constants.Gender.Male,
    'Eddy (French (France))': constants.Gender.Male,
    'Eddy (Italian (Italy))': constants.Gender.Male,
    'Eddy (Portuguese (Brazil))': constants.Gender.Male,
    'Ellen': constants.Gender.Female,
    'Ellen (Enhanced)': constants.Gender.Female,
    'Emma': constants.Gender.Female,
    'Emma (Enhanced)': constants.Gender.Female,
    'Emma (Premium)': constants.Gender.Female,
    'Pau': constants.Gender.Male,
    'Pau (Enhanced)': constants.Gender.Male,
    'Evan': constants.Gender.Male,
    'Evan (Enhanced)': constants.Gender.Male,
    'Ewa': constants.Gender.Female,
    'Ewa (Enhanced)': constants.Gender.Female,
    'Ewa (Premium)': constants.Gender.Female,
    'Panpan': constants.Gender.Male,
    'Panpan (Premium)': constants.Gender.Male,
    'Federica': constants.Gender.Female,
    'Federica (Enhanced)': constants.Gender.Female,
    'Federica (Premium)': constants.Gender.Female,
    'Felipe': constants.Gender.Male,
    'Felipe (Enhanced)': constants.Gender.Male,
    'Fernanda': constants.Gender.Female,
    'Fernanda (Enhanced)': constants.Gender.Female,
    'Fiona': constants.Gender.Female,
    'Fiona (Enhanced)': constants.Gender.Female,
    'Flo (German (Germany))': constants.Gender.Male,
    'Flo (English (UK))': constants.Gender.Male,
    'Flo (English (US))': constants.Gender.Male,
    'Flo (Spanish (Spain))': constants.Gender.Male,
    'Flo (Spanish (Mexico))': constants.Gender.Male,
    'Flo (Finnish (Finland))': constants.Gender.Male,
    'Flo (French (Canada))': constants.Gender.Male,
    'Flo (French (France))': constants.Gender.Male,
    'Flo (Italian (Italy))': constants.Gender.Male,
    'Flo (Portuguese (Brazil))': constants.Gender.Male,
    'Francisca': constants.Gender.Female,
    'Francisca (Enhanced)': constants.Gender.Female,
    'Fred': constants.Gender.Male,
    'Geeta': constants.Gender.Female,
    'Geeta (Enhanced)': constants.Gender.Female,
    'Good News': constants.Gender.Male,
    'Grandma (German (Germany))': constants.Gender.Female,
    'Grandma (English (UK))': constants.Gender.Female,
    'Grandma (English (US))': constants.Gender.Female,
    'Grandma (Spanish (Spain))': constants.Gender.Female,
    'Grandma (Spanish (Mexico))': constants.Gender.Female,
    'Grandma (Finnish (Finland))': constants.Gender.Female,
    'Grandma (French (Canada))': constants.Gender.Female,
    'Grandma (French (France))': constants.Gender.Female,
    'Grandma (Italian (Italy))': constants.Gender.Female,
    'Grandma (Portuguese (Brazil))': constants.Gender.Female,
    'Grandpa (German (Germany))': constants.Gender.Male,
    'Grandpa (English (UK))': constants.Gender.Male,
    'Grandpa (English (US))': constants.Gender.Male,
    'Grandpa (Spanish (Spain))': constants.Gender.Male,
    'Grandpa (Spanish (Mexico))': constants.Gender.Male,
    'Grandpa (Finnish (Finland))': constants.Gender.Male,
    'Grandpa (French (Canada))': constants.Gender.Male,
    'Grandpa (French (France))': constants.Gender.Male,
    'Grandpa (Italian (Italy))': constants.Gender.Male,
    'Grandpa (Portuguese (Brazil))': constants.Gender.Male,
    'Han (Enhanced)': constants.Gender.Male,
    'Han (Premium)': constants.Gender.Male,
    'Haohao (Enhanced)': constants.Gender.Female,
    'Henrik': constants.Gender.Male,
    'Henrik (Enhanced)': constants.Gender.Male,
    'Jester': constants.Gender.Male,
    'Ioana': constants.Gender.Female,
    'Ioana (Enhanced)': constants.Gender.Female,
    'Isabela': constants.Gender.Female,
    'Isabela (Enhanced)': constants.Gender.Female,
    'Isha': constants.Gender.Female,
    'Isha (Enhanced)': constants.Gender.Female,
    'Isha (Premium)': constants.Gender.Female,
    'Iveta': constants.Gender.Female,
    'Iveta (Enhanced)': constants.Gender.Female,
    'Jacques': constants.Gender.Male,
    'Jaya': constants.Gender.Female,
    'Jaya (Enhanced)': constants.Gender.Female,
    'Jian (Enhanced)': constants.Gender.Female,
    'Jian (Premium)': constants.Gender.Female,
    'Joana': constants.Gender.Female,
    'Joana (Enhanced)': constants.Gender.Female,
    'Joaquim': constants.Gender.Male,
    'Joaquim (Enhanced)': constants.Gender.Male,
    'Joelle (Enhanced)': constants.Gender.Female,
    'Jordi': constants.Gender.Male,
    'Jordi (Enhanced)': constants.Gender.Male,
    'Jorge': constants.Gender.Male,
    'Jorge (Enhanced)': constants.Gender.Male,
    'Juan': constants.Gender.Male,
    'Juan (Enhanced)': constants.Gender.Male,
    'Junior': constants.Gender.Male,
    'Kanya': constants.Gender.Female,
    'Kanya (Enhanced)': constants.Gender.Female,
    'Karen': constants.Gender.Female,
    'Karen (Enhanced)': constants.Gender.Female,
    'Karen (Premium)': constants.Gender.Female,
    'Kate': constants.Gender.Female,
    'Kate (Enhanced)': constants.Gender.Female,
    'Kathy': constants.Gender.Female,
    'Katya': constants.Gender.Female,
    'Katya (Enhanced)': constants.Gender.Female,
    'Kiyara': constants.Gender.Female,
    'Kiyara (Enhanced)': constants.Gender.Female,
    'Kiyara (Premium)': constants.Gender.Female,
    'Klara': constants.Gender.Female,
    'Klara (Enhanced)': constants.Gender.Female,
    'Krzysztof': constants.Gender.Male,
    'Krzysztof (Enhanced)': constants.Gender.Male,
    'Kyoko': constants.Gender.Female,
    'Kyoko (Enhanced)': constants.Gender.Female,
    'Laila': constants.Gender.Female,
    'Laila (Enhanced)': constants.Gender.Female,
    'Lana': constants.Gender.Female,
    'Lana (Enhanced)': constants.Gender.Female,
    'Lanlan (Enhanced)': constants.Gender.Female,
    'Laura': constants.Gender.Female,
    'Laura (Enhanced)': constants.Gender.Female,
    'Lee': constants.Gender.Male,
    'Lee (Enhanced)': constants.Gender.Male,
    'Lee (Premium)': constants.Gender.Male,
    'Lekha': constants.Gender.Female,
    'Lekha (Enhanced)': constants.Gender.Female,
    'Lesya': constants.Gender.Female,
    'Lesya (Enhanced)': constants.Gender.Female,
    'Lili': constants.Gender.Female,
    'Lili (Enhanced)': constants.Gender.Female,
    'Lili (Premium)': constants.Gender.Female,
    'Lilian (Enhanced)': constants.Gender.Female,
    'Lilian (Premium)': constants.Gender.Female,
    'Linh': constants.Gender.Female,
    'Linh (Enhanced)': constants.Gender.Female,
    'Lisheng (Enhanced)': constants.Gender.Male,
    'Luca': constants.Gender.Male,
    'Luca (Enhanced)': constants.Gender.Male,
    'Luciana': constants.Gender.Female,
    'Luciana (Enhanced)': constants.Gender.Female,
    'Nannan (Enhanced)': constants.Gender.Female,
    'Majed': constants.Gender.Male,
    'Majed (Enhanced)': constants.Gender.Male,
    'Majed (Premium)': constants.Gender.Male,
    'Magnus': constants.Gender.Male,
    'Magnus (Enhanced)': constants.Gender.Male,
    'Jamie': constants.Gender.Female,
    'Jamie (Enhanced)': constants.Gender.Female,
    'Jamie (Premium)': constants.Gender.Female,
    'Mariam': constants.Gender.Female,
    'Mariam (Enhanced)': constants.Gender.Female,
    'Tünde': constants.Gender.Female,
    'Tünde (Enhanced)': constants.Gender.Female,
    'Tünde (Premium)': constants.Gender.Female,
    'Marisol': constants.Gender.Female,
    'Marisol (Enhanced)': constants.Gender.Female,
    'Markus': constants.Gender.Male,
    'Markus (Enhanced)': constants.Gender.Male,
    'Matilda': constants.Gender.Female,
    'Matilda (Enhanced)': constants.Gender.Female,
    'Matilda (Premium)': constants.Gender.Female,
    'Meijia': constants.Gender.Female,
    'Meijia (Premium)': constants.Gender.Female,
    'Melina': constants.Gender.Female,
    'Melina (Enhanced)': constants.Gender.Female,
    'Milena': constants.Gender.Female,
    'Milena (Enhanced)': constants.Gender.Female,
    'Minsu': constants.Gender.Male,
    'Minsu (Enhanced)': constants.Gender.Male,
    'Miren': constants.Gender.Female,
    'Miren (Enhanced)': constants.Gender.Female,
    'Moira': constants.Gender.Female,
    'Moira (Enhanced)': constants.Gender.Female,
    'Mónica': constants.Gender.Female,
    'Mónica (Enhanced)': constants.Gender.Female,
    'Montse': constants.Gender.Female, 
    'Montse (Enhanced)': constants.Gender.Female,
    'Narisa (Enhanced)': constants.Gender.Female,
    'Nathan': constants.Gender.Male,
    'Nathan (Enhanced)': constants.Gender.Male,
    'Neel': constants.Gender.Male,
    'Neel (Enhanced)': constants.Gender.Male,
    'Nicolas': constants.Gender.Male,
    'Nicolas (Enhanced)': constants.Gender.Male,
    'Nikos': constants.Gender.Male,
    'Nikos (Enhanced)': constants.Gender.Male,
    'Noelle (Enhanced)': constants.Gender.Female,
    'Nora': constants.Gender.Female,
    'Nora (Enhanced)': constants.Gender.Female,
    'Suhyun': constants.Gender.Female,
    'Suhyun (Enhanced)': constants.Gender.Female,
    'Oliver': constants.Gender.Male,
    'Oliver (Enhanced)': constants.Gender.Male,
    'Onni': constants.Gender.Male,
    'Onni (Enhanced)': constants.Gender.Male,
    'Organ': constants.Gender.Male,
    'Oskar': constants.Gender.Male,
    'Oskar (Enhanced)': constants.Gender.Male,
    'Otoya': constants.Gender.Male,
    'Otoya (Enhanced)': constants.Gender.Male,
    'Paola': constants.Gender.Female,
    'Paola (Enhanced)': constants.Gender.Female,
    'Paulina': constants.Gender.Female,
    'Paulina (Enhanced)': constants.Gender.Female,
    'Piya': constants.Gender.Female,
    'Piya (Enhanced)': constants.Gender.Female,
    'Petra': constants.Gender.Female,
    'Petra (Enhanced)': constants.Gender.Female,
    'Petra (Premium)': constants.Gender.Female,
    'Superstar': constants.Gender.Male,
    'Ralph': constants.Gender.Male,
    'Reed (German (Germany))': constants.Gender.Male,
    'Reed (English (UK))': constants.Gender.Male,
    'Reed (English (US))': constants.Gender.Male,
    'Reed (Spanish (Spain))': constants.Gender.Male,
    'Reed (Spanish (Mexico))': constants.Gender.Male,
    'Reed (Finnish (Finland))': constants.Gender.Male,
    'Reed (French (Canada))': constants.Gender.Male,
    'Reed (Italian (Italy))': constants.Gender.Male,
    'Reed (Portuguese (Brazil))': constants.Gender.Male,
    'Rishi': constants.Gender.Male,
    'Rishi (Enhanced)': constants.Gender.Male,
    'Rocko (German (Germany))': constants.Gender.Male,
    'Rocko (English (UK))': constants.Gender.Male,
    'Rocko (English (US))': constants.Gender.Male,
    'Rocko (Spanish (Spain))': constants.Gender.Male,
    'Rocko (Spanish (Mexico))': constants.Gender.Male,
    'Rocko (Finnish (Finland))': constants.Gender.Male,
    'Rocko (French (Canada))': constants.Gender.Male,
    'Rocko (French (France))': constants.Gender.Male,
    'Rocko (Italian (Italy))': constants.Gender.Male,
    'Rocko (Portuguese (Brazil))': constants.Gender.Male,
    'Samantha': constants.Gender.Female,
    'Samantha (Enhanced)': constants.Gender.Female,
    'Sandy (German (Germany))': constants.Gender.Female,
    'Sandy (English (UK))': constants.Gender.Female,
    'Sandy (English (US))': constants.Gender.Female,
    'Sandy (Spanish (Spain))': constants.Gender.Female,
    'Sandy (Spanish (Mexico))': constants.Gender.Female,
    'Sandy (Finnish (Finland))': constants.Gender.Female,
    'Sandy (French (France))': constants.Gender.Female,
    'Sandy (Italian (Italy))': constants.Gender.Female,
    'Sandy (Portuguese (Brazil))': constants.Gender.Female,
    'Sangeeta': constants.Gender.Female,
    'Sangeeta (Enhanced)': constants.Gender.Female,
    'Sara': constants.Gender.Female,
    'Sara (Enhanced)': constants.Gender.Female,
    'Satu': constants.Gender.Female,
    'Satu (Enhanced)': constants.Gender.Female,
    'Serena': constants.Gender.Female,
    'Serena (Enhanced)': constants.Gender.Female,
    'Serena (Premium)': constants.Gender.Female,
    'Shanshan (Enhanced)': constants.Gender.Female,
    'Shasha (Enhanced)': constants.Gender.Female,
    'Shelley (German (Germany))': constants.Gender.Female,
    'Shelley (English (UK))': constants.Gender.Female,
    'Shelley (English (US))': constants.Gender.Female,
    'Shelley (Spanish (Spain))': constants.Gender.Female,
    'Shelley (Spanish (Mexico))': constants.Gender.Female,
    'Shelley (Finnish (Finland))': constants.Gender.Female,
    'Shelley (French (Canada))': constants.Gender.Female,
    'Shelley (French (France))': constants.Gender.Female,
    'Shelley (Italian (Italy))': constants.Gender.Female,
    'Shelley (Portuguese (Brazil))': constants.Gender.Female,
    'Sinji': constants.Gender.Female,
    'Sinji (Enhanced)': constants.Gender.Female,
    'Sinji (Premium)': constants.Gender.Female,
    'Soledad': constants.Gender.Female,
    'Soledad (Enhanced)': constants.Gender.Female,
    'Sora': constants.Gender.Female,
    'Sora (Enhanced)': constants.Gender.Female,
    'Stephanie': constants.Gender.Female,
    'Stephanie (Enhanced)': constants.Gender.Female,
    'Susan': constants.Gender.Female,
    'Susan (Enhanced)': constants.Gender.Female,
    'Taotao (Enhanced)': constants.Gender.Female,
    'Tarik': constants.Gender.Male,
    'Tarik (Enhanced)': constants.Gender.Male,
    'Tessa': constants.Gender.Female,
    'Tessa (Enhanced)': constants.Gender.Female,
    'Thomas': constants.Gender.Male,
    'Thomas (Enhanced)': constants.Gender.Male,
    'Tiantian': constants.Gender.Female,
    'Tiantian (Enhanced)': constants.Gender.Female,
    'Tina': constants.Gender.Female,
    'Tina (Enhanced)': constants.Gender.Female,
    'Tingting': constants.Gender.Female,
    'Tingting (Enhanced)': constants.Gender.Female,
    'Tom': constants.Gender.Male,
    'Tom (Enhanced)': constants.Gender.Male,
    'Trinoids': constants.Gender.Male,
    'Vani': constants.Gender.Female,
    'Vani (Enhanced)': constants.Gender.Female,
    'Veena': constants.Gender.Female,
    'Veena (Enhanced)': constants.Gender.Female,
    'Vicki': constants.Gender.Female,
    'Victoria': constants.Gender.Female,
    'Viktor': constants.Gender.Male,
    'Viktor (Enhanced)': constants.Gender.Male,
    'Whisper': constants.Gender.Male,
    'Xander': constants.Gender.Male,
    'Xander (Enhanced)': constants.Gender.Male,
    'Jimena': constants.Gender.Female,
    'Jimena (Enhanced)': constants.Gender.Female,
    'Yannick': constants.Gender.Male,
    'Yannick (Enhanced)': constants.Gender.Male,
    'Yelda': constants.Gender.Female,
    'Yelda (Enhanced)': constants.Gender.Female,
    'Yue (Premium)': constants.Gender.Female,
    'Yuna': constants.Gender.Female,
    'Yuna (Enhanced)': constants.Gender.Female,
    'Yuna (Premium)': constants.Gender.Female,
    'Yuri': constants.Gender.Male,
    'Yuri (Enhanced)': constants.Gender.Male,
    'Zarvox': constants.Gender.Male,
    'Zoe': constants.Gender.Female,
    'Zoe (Enhanced)': constants.Gender.Female,
    'Zoe (Premium)': constants.Gender.Female,
    'Zosia': constants.Gender.Female,
    'Zosia (Enhanced)': constants.Gender.Female,
    'Zuzana': constants.Gender.Female,
    'Zuzana (Enhanced)': constants.Gender.Female,
    'Zuzana (Premium)': constants.Gender.Female,
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

        # build a map of all audio locales, we may want to remove those from short voice names
        audio_locales_map = {audio_language.audio_lang_name for audio_language in languages.AudioLanguage}

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

                # is the second part an audio locale ? 
                voice_name_parts = voice_name.split(' ')
                last_part = ' '.join(voice_name_parts[1:])
                without_parentheses = last_part[1:len(last_part)-1]
                if without_parentheses in audio_locales_map:
                    short_voice_name = voice_name_parts[0]
                else:
                    short_voice_name = voice_name

                audio_language = self.get_audio_language(lang_id)
                gender = self.get_gender_from_name(voice_name)
                voice_key = {
                    'name': voice_name,
                }
                parsed_voice = voice.Voice(short_voice_name, gender, audio_language, self, voice_key, self.VOICE_OPTIONS)
                logger.debug(f'parsed voice: {parsed_voice}')
                result.append(parsed_voice)
            except:
                logger.error(f'could not parse line: [{line}]', exc_info=True)

        return result

    def get_tts_audio(self, source_text, voice: voice.VoiceBase, options):
        logger.info(f'getting audio with voice {voice}')

        rate = options.get('rate', self.DEFAULT_SPEECH_RATE)

        try:
            voice_name = voice.voice_key['name']
            temp_audio_file = tempfile.NamedTemporaryFile(suffix='.aiff', prefix='hypertts_macos', delete=False)
            arg_list = ['say', '-v', voice_name, '-r', str(rate), '-o', temp_audio_file.name, '--', source_text]
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
