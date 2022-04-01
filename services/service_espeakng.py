import sys
import os
import hashlib
import aqt.sound
import tempfile
import espeakng

voice = __import__('voice', globals(), locals(), [], sys._addon_import_level_services)
service = __import__('service', globals(), locals(), [], sys._addon_import_level_services)
errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_services)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_services)
languages = __import__('languages', globals(), locals(), [], sys._addon_import_level_services)
logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_services)
logger = logging_utils.get_child_logger(__name__)

AUDIO_LANGUAGE_OVERRIDE_MAP = {
    'as': languages.AudioLanguage.as_IN,
    'cmn': languages.AudioLanguage.zh_CN,
    'en-us': languages.AudioLanguage.en_US,
    'en-gb': languages.AudioLanguage.en_GB,
    'en-gb-scotland': languages.AudioLanguage.en_GB,
    'en-gb-x-gbclan': languages.AudioLanguage.en_GB,
    'en-gb-x-gbcwmd': languages.AudioLanguage.en_GB,
    'en-gb-x-rp': languages.AudioLanguage.en_GB,
    'en-029': languages.AudioLanguage.en_CB,
    'en-029': languages.AudioLanguage.en_CB,
    'es-419': languages.AudioLanguage.es_LA,
    'fr-be': languages.AudioLanguage.fr_BE,
    'fr-ch': languages.AudioLanguage.fr_CH,
    'fr-fr': languages.AudioLanguage.fr_FR,

    'pt': languages.AudioLanguage.pt_PT,
    'pt-br': languages.AudioLanguage.pt_BR,

    
    'vi-vn-x-south': languages.AudioLanguage.vi_VN,
    'vi-vn-x-central': languages.AudioLanguage.vi_VN,
}


class ESpeakNg(service.ServiceBase):

    def __init__(self):
        service.ServiceBase.__init__(self)

    @property
    def service_type(self) -> constants.ServiceType:
        return constants.ServiceType.tts

    @property
    def service_fee(self) -> constants.ServiceFee:
        return constants.ServiceFee.Free

    def get_audio_language(self, espeakng_language):
        if espeakng_language in AUDIO_LANGUAGE_OVERRIDE_MAP:
            return AUDIO_LANGUAGE_OVERRIDE_MAP[espeakng_language]
        if espeakng_language in languages.Language.__members__:
            language = languages.Language[espeakng_language]
            if language in languages.AudioLanguageDefaults:
                return languages.AudioLanguageDefaults[language]
            else:
                logger.warning(f'no default audio language for: {language}')
        return None

    def voice_list(self):
        gender_map = {
            'M': constants.Gender.Male,
            'F': constants.Gender.Female
        }

        try:
            result = []
            esng = espeakng.ESpeakNG()
            for espeakng_voice in esng.voices:
                # logger.debug(espeakng_voice)
                voice_name = espeakng_voice['voice_name']
                gender = gender_map[espeakng_voice['gender']]
                espeakng_language = espeakng_voice['language']
                audio_language = self.get_audio_language(espeakng_language)
                if audio_language != None:
                    result.append(voice.Voice(voice_name, gender, audio_language, self, espeakng_language, {}))                    
                else:
                    logger.warning(f'language not recognized: {espeakng_language}, {espeakng_voice}')
            return result

        except Exception as e:
            logger.warning(f'could not get voicelist: {e}', exc_info=True)

        return []

    def get_tts_audio(self, source_text, voice: voice.VoiceBase, options):

        esng = espeakng.ESpeakNG()
        esng.voice = voice.voice_key
        wavs = esng.synth_wav(source_text)

        fh, wav_temp_file_name = tempfile.mkstemp(prefix='hyper_tts_espeakng', suffix='.wav')
        f = open(wav_temp_file_name, 'wb')
        f.write(wavs)
        f.close()

        fh, mp3_temp_file_name = tempfile.mkstemp(prefix='hyper_tts_espeakng', suffix='.mp3') 
        aqt.sound._encode_mp3(wav_temp_file_name, mp3_temp_file_name)

        # read final mp3 file
        f = open(mp3_temp_file_name, 'rb')
        content = f.read()
        f.close()        

        # remove temporary files (wav sound already removed)
        os.remove(mp3_temp_file_name)

        return content