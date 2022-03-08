import sys
import io
import pyttsx3
import re
import os
import tempfile
import pprint
import hashlib
import logging

voice = __import__('voice', globals(), locals(), [], sys._addon_import_level_services)
service = __import__('service', globals(), locals(), [], sys._addon_import_level_services)
errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_services)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_services)
languages = __import__('languages', globals(), locals(), [], sys._addon_import_level_services)
logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_services)
logger = logging_utils.get_child_logger(__name__)

LANGUAGE_MAP_OVERRIDE = {
    'an': languages.AudioLanguage.af_ZA,
    'zh-yue': languages.AudioLanguage.zh_HK,
    'zh': languages.AudioLanguage.zh_CN,
    'en-uk-north': languages.AudioLanguage.en_GB
}

class LocalSystem(service.ServiceBase):

    def __init__(self):
        service.ServiceBase.__init__(self)
        # reduce logging coming from comtypes
        logging.getLogger("comtypes").setLevel(logging.WARNING)

    @property
    def service_type(self) -> constants.ServiceType:
        return constants.ServiceType.tts

    @property
    def service_fee(self) -> constants.ServiceFee:
        return constants.ServiceFee.Free

    def get_audio_language(self, language_id) -> languages.AudioLanguage:
        language_str = language_id.decode('utf-8')
        language_str = re.sub(r'[^a-zA-Z\_\-]+', '', language_str)
        logger.info(f'language_str: {language_str}')

        if language_str in LANGUAGE_MAP_OVERRIDE:
            return LANGUAGE_MAP_OVERRIDE[language_str]

        m = re.match('([a-z]+)\-([a-z]+)', language_str)
        if m != None:
            language_component = m.groups()[0]
            country_component = m.groups()[1]
            locale = f'{language_component.lower()}_{country_component.upper()}'
            logger.info(f'locale: {locale}')
            if locale not in languages.AudioLanguage.__members__:
                logging.warn(f'language_id not found: {language_str}')
                return None
            return languages.AudioLanguage[locale]

        if language_str in languages.Language.__members__:
            language_enum = languages.Language[language_str]
            if language_enum in languages.LanguageCountryDefaults:
                return languages.LanguageCountryDefaults[language_enum]
        
        return None

    def get_audio_language_from_voice_id(self, voice_id):
        # TTS_MS_EN-US
        m = re.match(r'.*TTS_MS_([A-Z]+)-([A-Z]+).*', voice_id)
        if m != None:
            language_component = m.groups()[0]
            country_component = m.groups()[1]            
            locale = f'{language_component.lower()}_{country_component.upper()}'
            if locale in languages.AudioLanguage.__members__:
                return languages.AudioLanguage[locale]
        return None
    

    def voice_list(self):
        try:
            result = []
            engine = pyttsx3.init()
            voices = engine.getProperty('voices')
            logger.info(f'found {len(voices)} voices')
            for pyttsx_voice in voices:
                logger.info(f'processing voice: {pyttsx_voice}')
                # pprint.pprint(voice)
                if len(pyttsx_voice.languages) == 0:
                    # SAPI5 voices don't have language, has to be infered from the voice id
                    language = self.get_audio_language_from_voice_id(pyttsx_voice.id)
                    if language != None:
                        result.append(voice.Voice(pyttsx_voice.name, constants.Gender.Any, language, self, pyttsx_voice.id, {
                                'rate': {'default': 200, 'type': 'number_int', 'min': 50, 'max': 400},
                                'volume': {'default': 1.0, 'type': 'number', 'min': 0.0, 'max': 1.0}
                            }))
                    else:
                        logger.error(f'could not find language for voice {pyttsx_voice}')
                else:
                    for language_id in pyttsx_voice.languages:
                        logger.info(f'voice name: {pyttsx_voice.name} gender: {pyttsx_voice.gender} language_id: {language_id}')
                        language = self.get_audio_language(language_id)
                        if pyttsx_voice.gender == None:
                            gender = constants.Gender.Any
                        else:
                            gender = constants.Gender[pyttsx_voice.gender.capitalize()]
                        if language != None:
                            result.append(voice.Voice(pyttsx_voice.name, gender, language, self, pyttsx_voice.id, {
                                'rate': {'default': 200, 'type': 'number_int', 'min': 50, 'max': 400},
                                'volume': {'default': 1.0, 'type': 'number', 'min': 0.0, 'max': 1.0}
                            }))
                        else:
                            logging.warn(f'could not find language enum for {language_id}')
            return result

        except Exception as e:
            logger.error(f'could not get voicelist with pyttsx3: {e}', exc_info=True)

        return []


    def get_tts_audio(self, source_text, voice: voice.VoiceBase, options):
        logger.info(f'getting audio with voice {voice}')
        engine = pyttsx3.init()
        
        # for some reason only filename is accepted by sapi
        combined_data = {
            'source_text': source_text,
            'voice_key': voice.voice_key,
            'options': options
        }
        file_hash = hashlib.sha224(str(combined_data).encode('utf-8')).hexdigest()        
        filename = f'hypertts_{file_hash}.mp3'

        engine.setProperty('voice', voice.voice_key)
        
        logger.info(f'writing to file {filename}')
        engine.save_to_file(source_text , filename)
        engine.runAndWait()

        f = open(filename, mode='rb')
        content = f.read()
        f.close()
            
        # delete temp file
        os.remove(filename)
        
        return content

