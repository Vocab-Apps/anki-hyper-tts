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
import magic
import azure.cognitiveservices.speech
import azure.cognitiveservices.speech.audio

# add external modules to sys.path
addon_dir = os.path.dirname(os.path.realpath(__file__))
external_dir = os.path.join(addon_dir, 'external')
if sys.path[0] != external_dir:
    sys.path.insert(0, external_dir)

import constants
import context
import voice
import servicemanager
import errors
import languages

logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_base)
options = __import__('options', globals(), locals(), [], sys._addon_import_level_base)
config_models = __import__('config_models', globals(), locals(), [], sys._addon_import_level_base)
logger = logging_utils.get_test_child_logger(__name__)

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
        # elevenlabs
        self.manager.get_service('ElevenLabs').enabled = True
        self.manager.get_service('ElevenLabs').configure({
            'api_key': os.environ['ELEVENLABS_API_KEY']
        })                                
        # elevenlabs custom
        self.manager.get_service('ElevenLabsCustom').enabled = True
        self.manager.get_service('ElevenLabsCustom').configure({
            'api_key': os.environ['ELEVENLABS_API_KEY']
        })                                
        # openai
        self.manager.get_service('OpenAI').enabled = True
        self.manager.get_service('OpenAI').configure({
            'api_key': os.environ['OPENAI_API_KEY']
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
        # voicen
        self.manager.get_service('Voicen').enabled = True
        self.manager.get_service('Voicen').configure({
            'api_key': os.environ['VOICEN_API_KEY'],
        })        
        # free services 
        # =============
        # google translate
        self.manager.get_service('GoogleTranslate').enabled = True
        self.manager.get_service('Collins').enabled = True
        self.manager.get_service('Oxford').enabled = True
        self.manager.get_service('Lexico').enabled = True
        self.manager.get_service('DigitalesWorterbuchDeutschenSprache').enabled = True
        self.manager.get_service('Duden').enabled = True
        self.manager.get_service('Cambridge').enabled = True
        self.manager.get_service('SpanishDict').enabled = True
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

    def verify_audio_output(self, voice, source_text, expected_text_override=None, voice_options={}):
        audio_data = self.manager.get_tts_audio(source_text, voice, voice_options, 
            context.AudioRequestContext(constants.AudioRequestReason.batch))
        assert len(audio_data) > 0

        audio_format = options.AudioFormat.mp3
        if options.AUDIO_FORMAT_PARAMETER in voice_options:
            audio_format = options.AudioFormat[voice_options[options.AUDIO_FORMAT_PARAMETER]]
        extension_map = {
            options.AudioFormat.mp3: 'mp3',
            options.AudioFormat.ogg_vorbis: 'ogg',
            options.AudioFormat.ogg_opus: 'ogg',
        }

        output_temp_filename = f'generated_audio.{extension_map[audio_format]}'
        # cannot use tempfiles because windows is weird
        out = open(output_temp_filename, "wb")
        out.write(audio_data)
        out.close()
        file_type = magic.from_file(output_temp_filename)

        speech_config = azure.cognitiveservices.speech.SpeechConfig(subscription=os.environ['AZURE_SERVICES_KEY'], region='eastus')


        if audio_format == options.AudioFormat.mp3:
            self.assertIn('MPEG ADTS, layer III', file_type)
            sound = pydub.AudioSegment.from_mp3(output_temp_filename)
        elif audio_format == options.AudioFormat.ogg_opus:
            self.assertIn('Ogg data, Opus audio', file_type)
            sound = pydub.AudioSegment.from_ogg(output_temp_filename)
        elif audio_format == options.AudioFormat.ogg_vorbis:
            self.assertIn('Ogg data, Vorbis audio', file_type)
            sound = pydub.AudioSegment.from_ogg(output_temp_filename)
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
            languages.AudioLanguage.tr_TR: 'tr-TR',
            languages.AudioLanguage.ru_RU: 'ru-RU',
            languages.AudioLanguage.th_TH: 'th-TH',
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
            assert expected_text == recognized_text, f'expected and actual text not matching (voice: {str(voice)}): expected: [{expected_text}] actual: [{recognized_text}]'
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
        service_name = 'Google'

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
        self.verify_audio_output(selected_voice, 'Je ne suis pas disponible.')

        # test ogg format
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.en_US)
        self.verify_audio_output(selected_voice, 'This is the first sentence', voice_options={'format': 'ogg_opus'})

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
        self.verify_audio_output(selected_voice, 'Je ne suis pas disponible.')

        # test ogg format
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.en_US)
        self.verify_audio_output(selected_voice, 'This is the first sentence', voice_options={'format': 'ogg_opus'})

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

        # test ogg format
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.en_US)
        self.verify_audio_output(selected_voice, 'This is the first sentence', voice_options={'format': 'ogg_vorbis'})

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

    def test_elevenlabs_english(self):
        # pytest test_tts_services.py  -k 'TTSTests and test_elevenlabs_english'
        service_name = 'ElevenLabs'

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service.name == service_name]
        assert len(service_voices) > 5

        # pick a random en_US voice
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.en_US)
        self.verify_audio_output(selected_voice, 'This is the first sentence')        

    def test_elevenlabs_english_all_voices_charlotte(self):
        # pytest test_tts_services.py  -k 'TTSTests and test_elevenlabs_english_all_voices_charlotte'
        service_name = 'ElevenLabs'

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service.name == service_name and voice.language == languages.AudioLanguage.en_US]
        charlotte_voices = [voice for voice in service_voices if 'Charlotte' in voice.name]
        # basically we are testing that all the ElevenLabs models are working, there should be 4 or them
        self.assertGreaterEqual(len(charlotte_voices), 4)
        self.assertLessEqual(len(charlotte_voices), 10)
        for voice in charlotte_voices:
            self.verify_audio_output(voice, 'This is the first sentence')

    def test_elevenlabs_french(self):
        service_name = 'ElevenLabs'
        voice_list = self.manager.full_voice_list()
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.fr_FR)
        self.verify_audio_output(selected_voice, 'Il va pleuvoir demain.')

    def test_elevenlabs_japanese(self):
        service_name = 'ElevenLabs'
        voice_list = self.manager.full_voice_list()
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.ja_JP)
        self.verify_audio_output(selected_voice, 'おはようございます')

    def test_elevenlabs_chinese(self):
        service_name = 'ElevenLabs'
        voice_list = self.manager.full_voice_list()
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.zh_CN)
        self.verify_audio_output(selected_voice, '赚钱')

    def test_elevenlabs_custom(self):
        # pytest --log-cli-level=DEBUG test_tts_services.py  -k 'TTSTests and test_elevenlabs_custom'

        service_name = 'ElevenLabsCustom'
        if self.manager.get_service(service_name).enabled == False:
            logger.warning(f'service {service_name} not enabled, skipping')
            raise unittest.SkipTest(f'service {service_name} not enabled, skipping')

        voice_list = self.manager.full_voice_list()

        # pick a random en_US voice
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.en_US)
        self.verify_audio_output(selected_voice, 'This is the first sentence')

    def test_openai_english(self):
        # pytest test_tts_services.py  -k 'TTSTests and test_openai_english'
        service_name = 'OpenAI'

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service.name == service_name]
        assert len(service_voices) > 5

        # pick a random en_US voice
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.en_US)
        self.verify_audio_output(selected_voice, 'This is the first sentence')        

        # test ogg format
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.en_US)
        self.verify_audio_output(selected_voice, 'This is the first sentence', voice_options={'format': 'ogg_opus'})

    def test_openai_french(self):
        service_name = 'OpenAI'
        voice_list = self.manager.full_voice_list()
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.fr_FR)
        self.verify_audio_output(selected_voice, 'Il va pleuvoir demain.')

    def test_fptai(self):
        # pytest test_tts_services.py  -k 'TTSTests and test_fptai'
        service_name = 'FptAi'

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service.name == service_name]
        assert len(service_voices) > 5

        # pick a random en_US voice
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.vi_VN)
        self.verify_audio_output(selected_voice, 'Tôi bị mất cái ví.')

    @pytest.mark.skip(reason="voicen decommissioned")
    def test_voicen(self):
        # pytest test_tts_services.py  -k 'TTSTests and test_voicen'
        service_name = 'Voicen'

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service.name == service_name]
        assert len(service_voices) > 5

        # test turkish
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.tr_TR)
        self.verify_audio_output(selected_voice, 'kahvaltı')

        # test russian
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.ru_RU)
        self.verify_audio_output(selected_voice, 'улица') 

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
        self.verify_audio_output(selected_voice, 'Je ne suis pas disponible.')

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
        assert len(service_voices) >= 2

        # pick a random en_US voice
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.en_US)
        self.verify_audio_output(selected_voice, 'this is the first sentence')
        
        # pick a random en_US voice with modified rate
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.en_US)
        self.verify_audio_output(selected_voice, 'this is the first sentence', voice_options={'rate': -1})

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

        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.th_TH)
        self.verify_audio_output(selected_voice, 'สวัสดีค่ะ')


    @pytest.mark.skip(reason="stopped working, getting 403 / enable javascript and cookies")
    def test_collins(self):
        # pytest --log-cli-level=DEBUG test_tts_services.py  -k 'TTSTests and test_collins'
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


    def test_oxford(self):
        service_name = 'Oxford'
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

        # pick a random en_GB voice
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.en_US)
        self.verify_audio_output(selected_voice, 'successful')        


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


    @pytest.mark.skip(reason="lexico has shutdown")
    def test_lexico(self):
        service_name = 'Lexico'
        if self.manager.get_service(service_name).enabled == False:
            logger.warning(f'service {service_name} not enabled, skipping')
            raise unittest.SkipTest(f'service {service_name} not enabled, skipping')

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service.name == service_name]
        
        logger.info(f'found {len(service_voices)} voices for {service_name} services')
        assert len(service_voices) >= 1

        # pick a random en_GB voice
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.en_GB)
        self.verify_audio_output(selected_voice, 'vehicle')

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

        # saw this issue on sentry
        self.assertRaises(errors.AudioNotFoundError, 
                          self.manager.get_tts_audio,
                          "to be at one's wits' end", # non-existent word
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

    def test_macos(self):
        # pytest test_tts_services.py -k test_macos
        service_name = 'MacOS'
        if self.manager.get_service(service_name).enabled == False:
            logger.warning(f'service {service_name} not enabled, skipping')
            raise unittest.SkipTest(f'service {service_name} not enabled, skipping')

        voice_list = self.manager.full_voice_list(service_name)
        service_voices = [voice for voice in voice_list if voice.service.name == service_name]

        logger.info(f'found {len(service_voices)} voices for {service_name} services')
        assert len(service_voices) >= 64

        # pick a random en_US voice
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.en_US)
        self.verify_audio_output(selected_voice, 'this is the first sentence')

        # pick a random en_US voice with modified rate
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.en_US)
        self.verify_audio_output(selected_voice, 'this is the first sentence', voice_options={'rate': 170})


    def test_spanishdict(self):
        service_name = 'SpanishDict'
        if self.manager.get_service(service_name).enabled == False:
            logger.warning(f'service {service_name} not enabled, skipping')
            raise unittest.SkipTest(f'service {service_name} not enabled, skipping')

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service.name == service_name]
        
        logger.info(f'found {len(service_voices)} voices for {service_name} services')
        assert len(service_voices) >= 2 # spanish and english

        # test spanish voice
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.es_ES)
        self.verify_audio_output(selected_voice, 'furgoneta')
        # test english voice
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.en_US)
        self.verify_audio_output(selected_voice, 'vehicle')


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
        services_configuration = config_models.Configuration(
            hypertts_pro_api_key = os.environ['ANKI_LANGUAGE_TOOLS_API_KEY'],
            use_vocabai_api = os.environ.get('ANKI_LANGUAGE_TOOLS_VOCABAI_API', 'false').lower() == 'true'
        )
        self.manager.configure(services_configuration)

    # pytest test_tts_services.py  -k 'TTSTestsCloudLanguageTools and test_google'
    # pytest test_tts_services.py  -k 'TTSTestsCloudLanguageTools and test_all_services_mandarin'
