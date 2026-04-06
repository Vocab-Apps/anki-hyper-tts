import sys
import os
import re
import random
import copy
import unittest
import pydub
import platform
import magic
import azure.cognitiveservices.speech
import azure.cognitiveservices.speech.audio
import requests
import openai
import pytest
import uuid
import shutil
import string
import time


from hypertts_addon import constants
from hypertts_addon import context
from hypertts_addon import servicemanager
from hypertts_addon import errors
from hypertts_addon import languages
from hypertts_addon.languages import AudioLanguage

from hypertts_addon import logging_utils
from hypertts_addon import options
from hypertts_addon import config_models
from hypertts_addon import voice as voice_module

logger = logging_utils.get_test_child_logger(__name__)

def services_dir():
    current_script_path = os.path.realpath(__file__)
    current_script_dir = os.path.dirname(current_script_path)
    root_dir = os.path.join(current_script_dir, '..', '..')
    hypertts_dir = os.path.join(root_dir, constants.DIR_HYPERTTS_ADDON)

    return os.path.join(hypertts_dir, constants.DIR_SERVICES)

class TTSTests(unittest.TestCase):
    RANDOM_VOICE_COUNT = 1
    GENERATED_FILES_DIRECTORY = 'test_audio_files'

    ENGLISH_INPUT_TEXT = 'english language'

    CONFIG_MODE = 'direct'

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(cls.GENERATED_FILES_DIRECTORY):
            os.makedirs(cls.GENERATED_FILES_DIRECTORY)
        if cls.CONFIG_MODE == 'clt':
            cls.configure_service_manager_clt(cls)
        else:
            cls.configure_service_manager(cls)

    @classmethod
    def tearDownClass(cls):
        # Clean up test audio files
        pass
        # import shutil
        # shutil.rmtree('test_audio_files', ignore_errors=True)

    def sanitize_filename(self, filename):
        valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
        return ''.join(c for c in filename if c in valid_chars)

    def create_problem_filename(self, voice_name, extension, language):
        sanitized_name = self.sanitize_filename(voice_name[:100])
        sanitized_name = sanitized_name.replace(' ', '-').replace('(', '-').replace(')', '-')
        return os.path.join(self.GENERATED_FILES_DIRECTORY, f"{uuid.uuid4()}_{sanitized_name}_{language}.{extension}")

    def configure_service_manager(self):
        # use individual service keys
        self.manager = servicemanager.ServiceManager(services_dir(), f'{constants.DIR_HYPERTTS_ADDON}.{constants.DIR_SERVICES}', False)
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
        # alibaba
        self.manager.get_service('Alibaba').enabled = True
        self.manager.get_service('Alibaba').configure({
            'access_key_id': os.environ['ALIBABA_ACCESS_KEY_ID'],
            'access_key_secret': os.environ['ALIBABA_ACCESS_KEY_SECRET'],
            'app_key': os.environ['ALIBABA_APP_KEY'],
        })
        # free services
        # =============
        # google translate
        self.manager.get_service('GoogleTranslate').enabled = True
        self.manager.get_service('Oxford').enabled = True
        self.manager.get_service('DigitalesWorterbuchDeutschenSprache').enabled = True
        self.manager.get_service('Duden').enabled = True
        self.manager.get_service('Cambridge').enabled = True
        self.manager.get_service('SpanishDict').enabled = True
        self.manager.get_service('NaverPapago').enabled = True
        self.manager.get_service('Youdao').enabled = True
        if os.name == 'nt':
            logger.info('running on windows, enabling Windows service')
            self.manager.get_service('Windows').enabled = True
        if sys.platform == 'linux':
            logger.info('running on Linux, enabling espeakng service')
            self.manager.get_service('ESpeakNg').enabled = True
        if platform.system() == "Darwin":
            logger.info('running on MacOS, enabling MacOS service')
            self.manager.get_service('MacOS').enabled = True

    def configure_service_manager_clt(self):
        # configure using cloud language tools
        self.manager = servicemanager.ServiceManager(services_dir(), f'{constants.DIR_HYPERTTS_ADDON}.{constants.DIR_SERVICES}', False)
        self.manager.init_services()
        services_configuration = config_models.Configuration(
            hypertts_pro_api_key = os.environ['ANKI_LANGUAGE_TOOLS_API_KEY'],
            use_vocabai_api = os.environ.get('ANKI_LANGUAGE_TOOLS_VOCABAI_API', 'false').lower() == 'true',
            user_uuid = 'anki-hyper-tts-tests'
        )
        self.manager.configure(services_configuration)

    def sanitize_recognized_text(self, recognized_text):
        recognized_text = re.sub('<[^<]+?>', '', recognized_text)
        result_text = recognized_text.replace('.', '').\
            replace('。', '').\
            replace('?', '').\
            replace('？', '').\
            replace('!', '').\
            replace('您', '你').\
            replace(':', '').lower()
        return result_text

    def verify_audio_output(self, voice, audio_language, source_text, expected_text_override=None, voice_options={}, acceptable_solutions=None):
        max_retries = 3
        retry_delay = 2  # second

        if acceptable_solutions:
            acceptable_solutions = [self.sanitize_recognized_text(solution) for solution in acceptable_solutions]

        for attempt in range(max_retries):
            try:
                audio_data = self.manager.get_tts_audio(source_text, voice, voice_options,
                    context.AudioRequestContext(constants.AudioRequestReason.batch))
                assert len(audio_data) > 0
                break
            except errors.RequestError as request_error:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    # optionally we can add exceptions for unsupported voices here
                    # if voice.service == 'Google' and 'Journey' in voice.name:
                    #     raise unittest.SkipTest(f'skipping voice {voice} which is unsupported for now')
                    raise Exception(f"Failed to get audio data for {voice} and {source_text} after {max_retries} tries: {request_error}")
            except requests.exceptions.ReadTimeout:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    raise Exception(f"Failed to get audio data for {voice} and {source_text} after {max_retries} tries: timeout")

        audio_format = options.AudioFormat.mp3
        if options.AUDIO_FORMAT_PARAMETER in voice_options:
            audio_format = options.AudioFormat[voice_options[options.AUDIO_FORMAT_PARAMETER]]
        extension_map = {
            options.AudioFormat.mp3: 'mp3',
            options.AudioFormat.ogg_vorbis: 'ogg',
            options.AudioFormat.ogg_opus: 'ogg',
        }

        output_temp_filename = os.path.join(self.GENERATED_FILES_DIRECTORY, f'generated_audio_{uuid.uuid4()}.{extension_map[audio_format]}')
        with open(output_temp_filename, "wb") as out:
            out.write(audio_data)
        file_type = magic.from_file(output_temp_filename)

        verify_format_voice_information = f'verifying format {audio_format} for {voice}'
        if audio_format == options.AudioFormat.mp3:
            self.assertIn('MPEG ADTS, layer III', file_type, verify_format_voice_information)
            sound = pydub.AudioSegment.from_mp3(output_temp_filename)
        elif audio_format == options.AudioFormat.ogg_opus:
            self.assertIn('Ogg data, Opus audio', file_type, verify_format_voice_information)
            sound = pydub.AudioSegment.from_ogg(output_temp_filename)
        elif audio_format == options.AudioFormat.ogg_vorbis:
            self.assertIn('Ogg data, Vorbis audio', file_type, verify_format_voice_information)
            sound = pydub.AudioSegment.from_ogg(output_temp_filename)

        wav_filepath = os.path.join(self.GENERATED_FILES_DIRECTORY, f"converted_wav_{uuid.uuid4()}.wav")
        # https://github.com/Azure-Samples/cognitive-services-speech-sdk/issues/756
        # this indicates that converting to 16khz helps avoid this issue:
        # No speech could be recognized: NoMatchDetails(reason=NoMatchReason.InitialSilenceTimeout)
        sound = sound.set_frame_rate(16000)
        sound.export(wav_filepath, format="wav", parameters=["-ar", "16000"])

        # First, try with OpenAI Whisper API
        openai_whisper_result = None
        try:
            client = openai.OpenAI(api_key=os.environ['OPENAI_API_KEY'])
            with open(wav_filepath, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )

            whisper_recognized_text = self.sanitize_recognized_text(transcript.text)
            expected_text = self.sanitize_recognized_text(source_text)
            if expected_text_override is not None:
                expected_text = self.sanitize_recognized_text(expected_text_override)

            if expected_text == whisper_recognized_text or (acceptable_solutions and whisper_recognized_text in acceptable_solutions):
                logger.info(f'OpenAI Whisper: actual text matches expected or acceptable solution [{whisper_recognized_text}]')
                os.remove(wav_filepath)
                os.remove(output_temp_filename)
                return
            else:
                openai_whisper_result = f'OpenAI Whisper: Text mismatch. Expected: [{expected_text}], Actual: [{whisper_recognized_text}], Acceptable: {acceptable_solutions}'
                logger.info(openai_whisper_result)
        except Exception as e:
            openai_whisper_result = f'OpenAI Whisper transcription failed: {str(e)}'
            logger.warning(openai_whisper_result)

        # If Whisper fails or doesn't match, proceed with Azure speech recognition
        speech_config = azure.cognitiveservices.speech.SpeechConfig(subscription=os.environ['AZURE_SERVICES_KEY'], region='eastus')

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

        recognition_language = recognition_language_map[audio_language]

        audio_input = azure.cognitiveservices.speech.audio.AudioConfig(filename=wav_filepath)
        speech_recognizer = azure.cognitiveservices.speech.SpeechRecognizer(speech_config=speech_config, audio_config=audio_input, language=recognition_language)
        result = speech_recognizer.recognize_once()

        # to run problematic tests:
        # COLUMNS=500 pytest tests/test_tts_services/  -k 'test_all_services_mandarin or test_elevenlabs_chinese or test_elevenlabs_english or test_openai_french or test_all_services_french'

        # Checks result.
        if result.reason == azure.cognitiveservices.speech.ResultReason.RecognizedSpeech:
            recognized_text = self.sanitize_recognized_text(result.text)
            expected_text = self.sanitize_recognized_text(source_text)
            if expected_text_override is not None:
                expected_text = self.sanitize_recognized_text(expected_text_override)
            if expected_text == recognized_text or (acceptable_solutions and recognized_text in acceptable_solutions):
                logger.info(f'Azure: actual text matches expected or acceptable solution [{recognized_text}]')
            else:
                problem_file = self.create_problem_filename(voice.name, 'wav', audio_language.name)
                shutil.copy(wav_filepath, problem_file)
                error_message = f'expected and actual text not matching (voice: {str(voice)}): expected: [{expected_text}] actual: [{recognized_text}] acceptable: {acceptable_solutions}. Problematic audio file: {problem_file}. openai_whisper_result: {openai_whisper_result}'
                raise AssertionError(error_message)
        elif result.reason == azure.cognitiveservices.speech.ResultReason.NoMatch:
            error_message = f"No speech could be recognized: {result.no_match_details} voice: {voice} source_text: {source_text}"
            problem_file = self.create_problem_filename(voice.name, 'wav', audio_language.name)
            shutil.copy(wav_filepath, problem_file)
            raise Exception(f"{error_message}. Problematic audio file: {problem_file} openai_whisper_result: {openai_whisper_result}")
        elif result.reason == azure.cognitiveservices.speech.ResultReason.Canceled:
            cancellation_details = result.cancellation_details
            error_message = f"Speech Recognition canceled: {cancellation_details} voice: {voice} source_text: {source_text}"
            problem_file = self.create_problem_filename(voice.name, 'wav', audio_language.name)
            shutil.copy(wav_filepath, problem_file)
            raise Exception(f"{error_message}. Problematic audio file: {problem_file} openai_whisper_result: {openai_whisper_result}")

        # cleanup
        os.remove(wav_filepath)
        os.remove(output_temp_filename)

    def pick_random_voice(self, voice_list, service_name, language):
        voice_subset = [voice for voice in voice_list if voice.service == service_name and language in voice.audio_languages]
        if len(voice_subset) == 0:
            logger.error(f'found no voices for service {service_name}, language {language}')
        random_voice = random.choice(voice_subset)
        return random_voice

    def pick_random_voices_sample(self, voice_list, service_name, language, count):
        voice_subset = [voice for voice in voice_list if voice.service == service_name and language in voice.audio_languages]
        if len(voice_subset) > count:
            return random.sample(voice_subset, count)
        return []

    def random_voice_test(self, service_name, audio_language, source_text, acceptable_solutions=None):
        voice_list = self.manager.full_voice_list()
        selected_voice = self.pick_random_voice(voice_list, service_name, audio_language)
        self.verify_audio_output(selected_voice, audio_language, source_text, acceptable_solutions=acceptable_solutions)

    def verify_all_services_language(self, service_type: constants.ServiceType, language, source_text, acceptable_solutions=None):
        voice_list = self.manager.full_voice_list()
        service_name_list = [service.name for service in self.manager.get_all_services()]

        for service_name in service_name_list:
            service = self.manager.get_service(service_name)
            if service.enabled and service.service_type == service_type:
                logger.info(f'testing language {language.name}, service {service_name}')
                random_voices = self.pick_random_voices_sample(voice_list, service_name, language, self.RANDOM_VOICE_COUNT)
                for voice in random_voices:
                    if (service_name in ['OpenAI', 'ElevenLabs', 'ElevenLabsCustom'] and
                        language != languages.AudioLanguage.en_US):
                        logger.info(f'Skipping {service_name} for non-English language {language.name}')
                        continue
                    self.verify_audio_output(voice, language, source_text, acceptable_solutions=acceptable_solutions)
