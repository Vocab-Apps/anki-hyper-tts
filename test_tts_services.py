from calendar import c
import sys
import os
import re
import random
import tempfile
import copy
import pytest
import pprint
import unittest
import pydub
import azure.cognitiveservices.speech
import azure.cognitiveservices.speech.audio

import constants
import context
import voice
import servicemanager
import errors
import languages

logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_base)
logger = logging_utils.get_test_child_logger(__name__)

# add external dir to sys.path
addon_dir = os.path.dirname(os.path.realpath(__file__))
external_dir = os.path.join(addon_dir, 'external')
sys.path.append(external_dir)


def services_dir():
    current_script_path = os.path.realpath(__file__)
    current_script_dir = os.path.dirname(current_script_path)    
    return os.path.join(current_script_dir, 'services')

class TTSTests(unittest.TestCase):
    RANDOM_VOICE_COUNT = 1
    
    @classmethod
    def setUpClass(cls):
        cls.configure_service_manager(cls)

    def configure_service_manager(self):
        # use individual service keys
        self.manager = servicemanager.ServiceManager(services_dir(), 'services', False)
        self.manager.init_services()

        # premium services
        # ================
        # google
        self.manager.get_service('Google').enabled = True
        self.manager.get_service('Google').configure({'api_key': os.environ['GOOGLE_SERVICES_KEY']})
        # azure
        self.manager.get_service('Azure').enabled = True
        self.manager.get_service('Azure').configure({
            'api_key': os.environ['AZURE_SERVICES_KEY'],
            'region': os.environ['AZURE_SERVICES_REGION']
        })        
        # amazon
        self.manager.get_service('Amazon').enabled = True
        self.manager.get_service('Amazon').configure({
            'aws_access_key_id': os.environ['AWS_ACCESS_KEY_ID'],
            'aws_secret_access_key': os.environ['AWS_SECRET_ACCESS_KEY'],
            'aws_region': os.environ['AWS_DEFAULT_REGION']
        })
        # vocalware
        self.manager.get_service('VocalWare').enabled = True
        self.manager.get_service('VocalWare').configure({
            'secret_phrase': os.environ['VOCALWARE_SECRET_PHRASE'],
            'account_id': os.environ['VOCALWARE_ACCOUNT_ID'],
            'api_id': os.environ['VOCALWARE_API_ID'],
        })        
        # watson
        self.manager.get_service('Watson').enabled = True
        self.manager.get_service('Watson').configure({
            'speech_key': os.environ['WATSON_SERVICES_KEY'],
            'speech_url': os.environ['WATSON_SERVICES_URL'],
        })                
        # naver
        self.manager.get_service('Naver').enabled = True
        self.manager.get_service('Naver').configure({
            'client_id': os.environ['NAVER_CLIENT_ID'],
            'client_secret': os.environ['NAVER_CLIENT_SECRET'],
        })                        
        # forvo
        self.manager.get_service('Forvo').enabled = True
        self.manager.get_service('Forvo').configure({
            'api_key': os.environ['FORVO_SERVICES_KEY'],
            'api_url': os.environ['FORVO_SERVICES_URL'],
        })        
        # cereproc
        self.manager.get_service('CereProc').enabled = True
        self.manager.get_service('CereProc').configure({
            'username': os.environ['CEREPROC_USERNAME'],
            'password': os.environ['CEREPROC_PASSWORD'],
        })                
        # fptai
        self.manager.get_service('FptAi').enabled = True
        self.manager.get_service('FptAi').configure({
            'api_key': os.environ['FPTAPI_SERVICES_KEY'],
        })
        # free services 
        # =============
        # google translate
        self.manager.get_service('GoogleTranslate').enabled = True
        self.manager.get_service('Collins').enabled = True
        self.manager.get_service('DigitalesWorterbuchDeutschenSprache').enabled = True
        self.manager.get_service('Duden').enabled = True
        self.manager.get_service('Cambridge').enabled = True
        self.manager.get_service('NaverPapago').enabled = True
        if os.name == 'nt':
            logger.info('running on windows, enabling Windows service')
            self.manager.get_service('Windows').enabled = True
        if sys.platform == 'linux':
            logger.info('running on Linux, enabling espeakng service')
            self.manager.get_service('ESpeakNg').enabled = True            


    def sanitize_recognized_text(self, recognized_text):
        recognized_text = re.sub('<[^<]+?>', '', recognized_text)
        result_text = recognized_text.replace('.', '').\
            replace('。', '').\
            replace('?', '').\
            replace('？', '').\
            replace('您', '你').\
            replace(':', '').lower()
        return result_text

    def verify_audio_output(self, voice, source_text, expected_text_override=None):
        audio_data = self.manager.get_tts_audio(source_text, voice, {}, 
            context.AudioRequestContext(constants.AudioRequestReason.batch))
        assert len(audio_data) > 0

        output_temp_filename = "generated_audio.mp3"
        # cannot use tempfiles because windows is weird
        out = open(output_temp_filename, "wb")
        out.write(audio_data)
        out.close()

        speech_config = azure.cognitiveservices.speech.SpeechConfig(subscription=os.environ['AZURE_SERVICES_KEY'], region='eastus')

        sound = pydub.AudioSegment.from_mp3(output_temp_filename)
        # cannot use tempfiles because windows is weird
        wav_filepath = "converted_wav.wav"
        out_filehandle = sound.export(wav_filepath, format="wav")
        out_filehandle.close()

        recognition_language_map = {
            languages.AudioLanguage.en_US: 'en-US',
            languages.AudioLanguage.en_GB: 'en-GB',
            languages.AudioLanguage.fr_FR: 'fr-FR',
            languages.AudioLanguage.zh_CN: 'zh-CN',
            languages.AudioLanguage.ja_JP: 'ja-JP',
            languages.AudioLanguage.de_DE: 'de-DE',
            languages.AudioLanguage.es_ES: 'es-ES',
            languages.AudioLanguage.it_IT: 'it-IT',
            languages.AudioLanguage.ko_KR: 'ko-KR',
            languages.AudioLanguage.vi_VN: 'vi-VN',
            languages.AudioLanguage.he_IL: 'he-IL',
        }

        recognition_language = recognition_language_map[voice.language]

        audio_input = azure.cognitiveservices.speech.audio.AudioConfig(filename=wav_filepath)
        speech_recognizer = azure.cognitiveservices.speech.SpeechRecognizer(speech_config=speech_config, audio_config=audio_input, language=recognition_language)
        result = speech_recognizer.recognize_once()

        # Checks result.
        if result.reason == azure.cognitiveservices.speech.ResultReason.RecognizedSpeech:
            recognized_text =  self.sanitize_recognized_text(result.text)
            expected_text = self.sanitize_recognized_text(source_text)
            if expected_text_override != None:
                expected_text = self.sanitize_recognized_text(expected_text_override)    
            assert expected_text == recognized_text, f'expected and actual text not matching (voice: {str(voice)})'
            logger.info(f'actual and expected text match [{recognized_text}]')
        elif result.reason == azure.cognitiveservices.speech.ResultReason.NoMatch:
            error_message = "No speech could be recognized: {}".format(result.no_match_details)
            raise Exception(error_message)
        elif result.reason == azure.cognitiveservices.speech.ResultReason.Canceled:
            cancellation_details = result.cancellation_details
            error_message = "Speech Recognition canceled: {}".format(cancellation_details)
            raise Exception(error_message)

    def pick_random_voice(self, voice_list, service_name, language):
        voice_subset = [voice for voice in voice_list if voice.service.name == service_name and voice.language == language]
        if len(voice_subset) == 0:
            logger.error(f'found no voices for service {service_name}, language {language}')
        random_voice = random.choice(voice_subset)
        return random_voice

    def pick_random_voices_sample(self, voice_list, service_name, language, count):
        voice_subset = [voice for voice in voice_list if voice.service.name == service_name and voice.language == language]
        if len(voice_subset) > count:
            return random.sample(voice_subset, count)
        return []



    def test_google(self):
        voice_list = self.manager.full_voice_list()
        google_voices = [voice for voice in voice_list if voice.service.name == 'Google']
        # print(voice_list)
        logger.info(f'found {len(google_voices)} voices for Google services')
        assert len(google_voices) > 300

        # pick a random en_US voice
        selected_voice = self.pick_random_voice(voice_list, 'Google', languages.AudioLanguage.en_US)
        self.verify_audio_output(selected_voice, 'This is the first sentence')

        # french
        selected_voice = self.pick_random_voice(voice_list, 'Google', languages.AudioLanguage.fr_FR)
        self.verify_audio_output(selected_voice, 'Je ne suis pas intéressé.')

        # error checking
        # try a voice which doesn't exist
        selected_voice = self.pick_random_voice(voice_list, 'Google', languages.AudioLanguage.en_US)
        selected_voice = copy.copy(selected_voice)
        voice_key = copy.copy(selected_voice.voice_key)
        voice_key['name'] = 'non existent'
        altered_voice = voice.Voice('non existent', 
                                    selected_voice.gender, 
                                    selected_voice.language, 
                                    selected_voice.service, 
                                    voice_key,
                                    selected_voice.options)

        exception_caught = False
        try:
            audio_data = self.manager.get_tts_audio('This is the second sentence', altered_voice, {}, 
                context.AudioRequestContext(constants.AudioRequestReason.batch))
        except errors.RequestError as e:
            assert 'Could not request audio for' in str(e)
            assert e.source_text == 'This is the second sentence'
            assert e.voice.service.name == 'Google'
            exception_caught = True
        assert exception_caught


    def test_azure(self):
        service_name = 'Azure'

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service.name == service_name]
        assert len(service_voices) > 300

        # pick a random en_US voice
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.en_US)
        self.verify_audio_output(selected_voice, 'This is the first sentence')

        # french
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.fr_FR)
        self.verify_audio_output(selected_voice, 'Je ne suis pas intéressé.')

        # error checking
        # try a voice which doesn't exist
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.en_US)
        selected_voice = copy.copy(selected_voice)
        voice_key = copy.copy(selected_voice.voice_key)
        voice_key['name'] = 'non existent'
        altered_voice = voice.Voice('non existent', 
                                    selected_voice.gender, 
                                    selected_voice.language, 
                                    selected_voice.service, 
                                    voice_key,
                                    selected_voice.options)

        exception_caught = False
        try:
            audio_data = self.manager.get_tts_audio('This is the second sentence', altered_voice, {}, 
                context.AudioRequestContext(constants.AudioRequestReason.batch))
        except errors.RequestError as e:
            assert 'Could not request audio for' in str(e)
            assert e.source_text == 'This is the second sentence'
            assert e.voice.service.name == service_name
            exception_caught = True
        assert exception_caught

    def test_amazon(self):
        # pytest test_tts_services.py  -k 'TTSTests and test_amazon'
        service_name = 'Amazon'

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service.name == service_name]
        assert len(service_voices) > 50

        # pick a random en_US voice
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.en_US)
        self.verify_audio_output(selected_voice, 'This is the first sentence')

    def test_vocalware(self):
        # pytest test_tts_services.py  -k 'TTSTests and test_vocalware'
        service_name = 'VocalWare'

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service.name == service_name]
        assert len(service_voices) > 50

        # pick a random en_US voice
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.en_US)
        self.verify_audio_output(selected_voice, 'This is the first sentence')

    def test_watson(self):
        # pytest test_tts_services.py  -k 'TTSTests and test_watson'
        service_name = 'Watson'

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service.name == service_name]
        assert len(service_voices) > 50

        # pick a random en_US voice
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.en_US)
        self.verify_audio_output(selected_voice, 'This is the first sentence')

    def test_cereproc(self):
        # pytest test_tts_services.py  -k 'TTSTests and test_cereproc'
        service_name = 'CereProc'

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service.name == service_name]
        assert len(service_voices) > 50

        # pick a random en_US voice
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.en_GB)
        self.verify_audio_output(selected_voice, 'This is the first sentence')

    def test_fptai(self):
        # pytest test_tts_services.py  -k 'TTSTests and test_fptai'
        service_name = 'FptAi'

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service.name == service_name]
        assert len(service_voices) > 5

        # pick a random en_US voice
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.vi_VN)
        self.verify_audio_output(selected_voice, 'Tôi bị mất cái ví.')

    def test_naver(self):
        # pytest test_tts_services.py  -k 'TTSTests and test_naver'
        service_name = 'Naver'

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service.name == service_name]
        assert len(service_voices) > 30

        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.ko_KR)
        self.verify_audio_output(selected_voice, '여보세요')
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.ja_JP)
        self.verify_audio_output(selected_voice, 'おはようございます')


    def test_forvo(self):
        # pytest test_tts_services.py  -k 'TTSTests and test_forvo'
        service_name = 'Forvo'

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service.name == service_name]
        assert len(service_voices) > 50

        # pick a random en_US voice
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.en_US)
        self.verify_audio_output(selected_voice, 'Camera')
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.fr_FR)
        self.verify_audio_output(selected_voice, 'ordinateur')




    def test_googletranslate(self):
        # pytest test_tts_services.py  -k 'TTSTests and test_googletranslate'
        service_name = 'GoogleTranslate'
        if self.manager.get_service(service_name).enabled == False:
            logger.warning(f'service {service_name} not enabled, skipping')
            raise unittest.SkipTest(f'service {service_name} not enabled, skipping')

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service.name == service_name]
        
        logger.info(f'found {len(service_voices)} voices for {service_name} services')
        assert len(service_voices) >= 2
        pprint.pprint(service_voices)

        # pick a random en_US voice
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.en_US)
        self.verify_audio_output(selected_voice, 'This is the first sentence')

        # french
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.fr_FR)
        self.verify_audio_output(selected_voice, 'Je ne suis pas intéressé.')

        # hebrew
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.he_IL)
        self.verify_audio_output(selected_voice, '.בבקשה')

    def test_windows(self):
        # pytest test_tts_services.py  -k test_windows
        service_name = 'Windows'
        if self.manager.get_service(service_name).enabled == False:
            logger.warning(f'service {service_name} not enabled, skipping')
            raise unittest.SkipTest(f'service {service_name} not enabled, skipping')

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service.name == service_name]
        
        logger.info(f'found {len(service_voices)} voices for {service_name} services')
        assert len(service_voices) >= 5

        # pick a random en_US voice
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.en_US)
        self.verify_audio_output(selected_voice, 'this is the first sentence')

    def test_espeakng(self):
        service_name = 'ESpeakNg'
        if self.manager.get_service(service_name).enabled == False:
            logger.warning(f'service {service_name} not enabled, skipping')
            raise unittest.SkipTest(f'service {service_name} not enabled, skipping')

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service.name == service_name]
        
        logger.info(f'found {len(service_voices)} voices for {service_name} service')
        assert len(service_voices) >= 5

        # pick a random en_US voice
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.en_US)
        self.verify_audio_output(selected_voice, 'welcome home')


    def test_naverpapago(self):
        service_name = 'NaverPapago'
        if self.manager.get_service(service_name).enabled == False:
            logger.warning(f'service {service_name} not enabled, skipping')
            raise unittest.SkipTest(f'service {service_name} not enabled, skipping')

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service.name == service_name]
        
        logger.info(f'found {len(service_voices)} voices for {service_name} services')
        assert len(service_voices) >= 2

        # pick a random ko_KR voice
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.ko_KR)
        self.verify_audio_output(selected_voice, '여보세요')
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.ja_JP)
        self.verify_audio_output(selected_voice, 'おはようございます')


    def test_collins(self):
        service_name = 'Collins'
        if self.manager.get_service(service_name).enabled == False:
            logger.warning(f'service {service_name} not enabled, skipping')
            raise unittest.SkipTest(f'service {service_name} not enabled, skipping')

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service.name == service_name]
        
        logger.info(f'found {len(service_voices)} voices for {service_name} services')
        assert len(service_voices) >= 2

        # pick a random en_GB voice
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.en_GB)
        self.verify_audio_output(selected_voice, 'successful')

        # test other languages
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.fr_FR)
        self.verify_audio_output(selected_voice, 'bienvenue')
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.de_DE)
        self.verify_audio_output(selected_voice, 'Hallo')
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.es_ES)
        self.verify_audio_output(selected_voice, 'furgoneta')
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.it_IT)
        self.verify_audio_output(selected_voice, 'attenzione')


        # error handling
        # ==============

        # ensure that a non-existent word raises AudioNotFoundError
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.en_GB)
        self.assertRaises(errors.AudioNotFoundError, 
                          self.manager.get_tts_audio,
                          'xxoanetuhsoae', # non-existent word
                          selected_voice,
                          {},
                          context.AudioRequestContext(constants.AudioRequestReason.batch))

        # german word not found
        german_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.de_DE)
        self.assertRaises(errors.AudioNotFoundError, 
                          self.manager.get_tts_audio,
                          'Fahrkarte', # no pronounciation
                          selected_voice,
                          {},
                          context.AudioRequestContext(constants.AudioRequestReason.batch))        

        self.assertRaises(errors.AudioNotFoundError, 
                          self.manager.get_tts_audio,
                          'Entschuldigung', # no pronounciation
                          selected_voice,
                          {},
                          context.AudioRequestContext(constants.AudioRequestReason.batch))                                  


    def test_dwds(self):
        # pytest test_tts_services.py -k test_dwds
        service_name = 'DigitalesWorterbuchDeutschenSprache'
        if self.manager.get_service(service_name).enabled == False:
            logger.warning(f'service {service_name} not enabled, skipping')
            raise unittest.SkipTest(f'service {service_name} not enabled, skipping')

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service.name == service_name]
        
        logger.info(f'found {len(service_voices)} voices for {service_name} services')
        assert len(service_voices) >= 1

        # test german voice
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.de_DE)
        self.verify_audio_output(selected_voice, 'Gesundheit', 'die Gesundheit')
        self.verify_audio_output(selected_voice, 'Entschuldigung', 'die Entschuldigung')

        # test error handling
        self.assertRaises(errors.AudioNotFoundError, 
                          self.manager.get_tts_audio,
                          'xxoanetuhsoae', # non-existent word
                          selected_voice,
                          {},
                          context.AudioRequestContext(constants.AudioRequestReason.batch))


    def test_duden(self):
        # pytest test_tts_services.py -k test_duden
        service_name = 'Duden'
        if self.manager.get_service(service_name).enabled == False:
            logger.warning(f'service {service_name} not enabled, skipping')
            raise unittest.SkipTest(f'service {service_name} not enabled, skipping')

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service.name == service_name]
        
        logger.info(f'found {len(service_voices)} voices for {service_name} services')
        assert len(service_voices) >= 1

        # test german voice
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.de_DE)
        self.verify_audio_output(selected_voice, 'Gesundheit')
        self.verify_audio_output(selected_voice, 'Entschuldigung')

        # test error handling
        self.assertRaises(errors.AudioNotFoundError, 
                          self.manager.get_tts_audio,
                          'xxoanetuhsoae', # non-existent word
                          selected_voice,
                          {},
                          context.AudioRequestContext(constants.AudioRequestReason.batch))

    def test_cambridge(self):
        service_name = 'Cambridge'
        if self.manager.get_service(service_name).enabled == False:
            logger.warning(f'service {service_name} not enabled, skipping')
            raise unittest.SkipTest(f'service {service_name} not enabled, skipping')

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service.name == service_name]
        
        logger.info(f'found {len(service_voices)} voices for {service_name} services')
        assert len(service_voices) >= 2 # british and american

        # test british voice
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.en_GB)
        self.verify_audio_output(selected_voice, 'vehicle')
        # test american voice
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.en_US)
        self.verify_audio_output(selected_voice, 'vehicle')

        # test error handling
        self.assertRaises(errors.AudioNotFoundError, 
                          self.manager.get_tts_audio,
                          'xxoanetuhsoae', # non-existent word
                          selected_voice,
                          {},
                          context.AudioRequestContext(constants.AudioRequestReason.batch))

    def verify_all_services_language(self, service_type: constants.ServiceType, language, source_text):
        voice_list = self.manager.full_voice_list()
        service_name_list = [service.name for service in self.manager.get_all_services()]

        for service_name in service_name_list:
            service = self.manager.get_service(service_name)
            if service.enabled and service.service_type == service_type:
                logger.info(f'testing language {language.name}, service {service_name}')
                random_voices = self.pick_random_voices_sample(voice_list, service_name, language, self.RANDOM_VOICE_COUNT)
                for voice in random_voices:
                    self.verify_audio_output(voice, source_text)    

    def test_all_services_english(self):
        self.verify_all_services_language(constants.ServiceType.tts, languages.AudioLanguage.en_US, 'The weather is good today.')
        self.verify_all_services_language(constants.ServiceType.dictionary, languages.AudioLanguage.en_GB, 'camera')

    def test_all_services_french(self):
        self.verify_all_services_language(constants.ServiceType.tts, languages.AudioLanguage.fr_FR, 'Il va pleuvoir demain.')

    def test_all_services_mandarin(self):
        self.verify_all_services_language(constants.ServiceType.tts, languages.AudioLanguage.zh_CN, '赚钱')

    def test_all_services_japanese(self):
        self.verify_all_services_language(constants.ServiceType.tts, languages.AudioLanguage.ja_JP, 'おはようございます')


class TTSTestsCloudLanguageTools(TTSTests):
    def configure_service_manager(self):
        # configure using cloud language tools
        self.manager = servicemanager.ServiceManager(services_dir(), 'services', False)
        self.manager.init_services()
        self.manager.configure_cloudlanguagetools(os.environ['ANKI_LANGUAGE_TOOLS_API_KEY'])

    # pytest test_tts_services.py  -k 'TTSTestsCloudLanguageTools and test_google'
    # pytest test_tts_services.py  -k 'TTSTestsCloudLanguageTools and test_all_services_mandarin'