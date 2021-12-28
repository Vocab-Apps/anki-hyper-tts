import os
import logging
import constants
import voice
import servicemanager
import errors

import re
import random
import tempfile
import copy
import pytest

import pydub
import azure.cognitiveservices.speech
import azure.cognitiveservices.speech.audio

def services_dir():
    current_script_path = os.path.realpath(__file__)
    current_script_dir = os.path.dirname(current_script_path)    
    return os.path.join(current_script_dir, 'services')

def sanitize_recognized_text(recognized_text):
    recognized_text = re.sub('<[^<]+?>', '', recognized_text)
    result_text = recognized_text.replace('.', '').\
        replace('。', '').\
        replace('?', '').\
        replace('？', '').\
        replace('您', '你').\
        replace(':', '').lower()
    return result_text

def verify_audio_output(manager, voice, source_text):
    audio_data = manager.get_tts_audio(source_text, voice, {})
    assert len(audio_data) > 0

    output_temp_file = tempfile.NamedTemporaryFile()
    output_temp_filename = output_temp_file.name
    with open(output_temp_filename, "wb") as out:
        out.write(audio_data)

    speech_config = azure.cognitiveservices.speech.SpeechConfig(subscription=os.environ['AZURE_SERVICES_KEY'], region='eastus')

    sound = pydub.AudioSegment.from_mp3(output_temp_filename)
    wav_filepath = tempfile.NamedTemporaryFile(suffix='.wav').name
    sound.export(wav_filepath, format="wav")

    recognition_language_map = {
        constants.AudioLanguage.en_US: 'en-US',
        constants.AudioLanguage.fr_FR: 'fr-FR',
        constants.AudioLanguage.zh_CN: 'zh-CN',
        constants.AudioLanguage.ja_JP: 'ja-JP',
    }

    recognition_language = recognition_language_map[voice.language]

    audio_input = azure.cognitiveservices.speech.audio.AudioConfig(filename=wav_filepath)
    speech_recognizer = azure.cognitiveservices.speech.SpeechRecognizer(speech_config=speech_config, audio_config=audio_input, language=recognition_language)
    result = speech_recognizer.recognize_once()

    # Checks result.
    if result.reason == azure.cognitiveservices.speech.ResultReason.RecognizedSpeech:
        recognized_text =  sanitize_recognized_text(result.text)
        expected_text = sanitize_recognized_text(source_text)
        assert expected_text == recognized_text, f'expected and actual text not matching (voice: {str(voice)})'
        logging.info(f'actual and expected text match [{recognized_text}]')
    elif result.reason == azure.cognitiveservices.speech.ResultReason.NoMatch:
        error_message = "No speech could be recognized: {}".format(result.no_match_details)
        raise Exception(error_message)
    elif result.reason == azure.cognitiveservices.speech.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        error_message = "Speech Recognition canceled: {}".format(cancellation_details)
        raise Exception(error_message)

def pick_random_voice(voice_list, service_name, language):
    voice_subset = [voice for voice in voice_list if voice.service.name == service_name and voice.language == language]
    random_voice = random.choice(voice_subset)
    return random_voice

def pick_random_voices_sample(voice_list, service_name, language, count):
    voice_subset = [voice for voice in voice_list if voice.service.name == service_name and voice.language == language]
    random_voice_sample = random.sample(voice_subset, count)
    return random_voice_sample


def test_google():
    manager = servicemanager.ServiceManager(services_dir(), 'services')
    manager.init_services()
    manager.get_service('Google').set_enabled(True)
    manager.get_service('Google').configure({'api_key': os.environ['GOOGLE_SERVICES_KEY']})

    voice_list = manager.full_voice_list()
    google_voices = [voice for voice in voice_list if voice.service.name == 'Google']
    # print(voice_list)
    logging.info(f'found {len(google_voices)}')
    assert len(google_voices) > 300

    # pick a random en_US voice
    selected_voice = pick_random_voice(voice_list, 'Google', constants.AudioLanguage.en_US)
    verify_audio_output(manager, selected_voice, 'This is the first sentence')

    # french
    selected_voice = pick_random_voice(voice_list, 'Google', constants.AudioLanguage.fr_FR)
    verify_audio_output(manager, selected_voice, 'Je ne suis pas intéressé.')

    # error checking
    # try a voice which doesn't exist
    selected_voice = pick_random_voice(voice_list, 'Google', constants.AudioLanguage.en_US)
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
        audio_data = manager.get_tts_audio('This is the second sentence', altered_voice, {})
    except errors.RequestError as e:
        assert 'Could not request audio for' in str(e)
        assert e.source_text == 'This is the second sentence'
        assert e.voice.service.name == 'Google'
        exception_caught = True
    assert exception_caught


def test_azure():
    service_name = 'Azure'
    manager = servicemanager.ServiceManager(services_dir(), 'services')
    manager.init_services()
    manager.get_service(service_name).set_enabled(True)
    manager.get_service(service_name).configure({
        'api_key': os.environ['AZURE_SERVICES_KEY'],
        'region': os.environ['AZURE_SERVICES_REGION']
    })

    voice_list = manager.full_voice_list()
    service_voices = [voice for voice in voice_list if voice.service.name == service_name]
    assert len(service_voices) > 300

    # pick a random en_US voice
    selected_voice = pick_random_voice(voice_list, service_name, constants.AudioLanguage.en_US)
    verify_audio_output(manager, selected_voice, 'This is the first sentence')

    # french
    selected_voice = pick_random_voice(voice_list, service_name, constants.AudioLanguage.fr_FR)
    verify_audio_output(manager, selected_voice, 'Je ne suis pas intéressé.')

    # error checking
    # try a voice which doesn't exist
    selected_voice = pick_random_voice(voice_list, service_name, constants.AudioLanguage.en_US)
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
        audio_data = manager.get_tts_audio('This is the second sentence', altered_voice, {})
    except errors.RequestError as e:
        assert 'Could not request audio for' in str(e)
        assert e.source_text == 'This is the second sentence'
        assert e.voice.service.name == service_name
        exception_caught = True
    assert exception_caught

def get_configured_servicemanager():
    manager = servicemanager.ServiceManager(services_dir(), 'services')
    manager.init_services()
    manager.get_service('Azure').set_enabled(True)
    manager.get_service('Azure').configure({
        'api_key': os.environ['AZURE_SERVICES_KEY'],
        'region': os.environ['AZURE_SERVICES_REGION']
    })    
    manager.get_service('Google').set_enabled(True)
    manager.get_service('Google').configure({'api_key': os.environ['GOOGLE_SERVICES_KEY']})
    return manager

def verify_all_services_language(language, source_text):
    manager = get_configured_servicemanager()
    voice_list = manager.full_voice_list()
    service_name_list = [service.name for service in manager.get_all_services()]

    for service_name in service_name_list:
        logging.info(f'testing language {language.name}, service {service_name}')
        random_voices = pick_random_voices_sample(voice_list, service_name, language, 3)
        for voice in random_voices:
            verify_audio_output(manager, voice, source_text)    

def test_all_services_english():
    verify_all_services_language(constants.AudioLanguage.en_US, 'The weather is good today.')

def test_all_services_french():
    verify_all_services_language(constants.AudioLanguage.fr_FR, 'Il va pleuvoir demain.')

def test_all_services_mandarin():
    verify_all_services_language(constants.AudioLanguage.zh_CN, '老人家')

def test_all_services_japanese():
    verify_all_services_language(constants.AudioLanguage.ja_JP, 'おはようございます')

@pytest.mark.skip(reason="covered by per-language tests")
def manual_test_all_services():
    # pytest test_tts_services.py -k test_all_services -rPP -s

    input_map = {
        constants.AudioLanguage.en_US: 'The weather is good today.',
        constants.AudioLanguage.fr_FR: 'Il va pleuvoir demain.',
        constants.AudioLanguage.zh_CN: '老人家',
        constants.AudioLanguage.ja_JP: 'おはようございます',
    }

    manager = get_configured_servicemanager()
    voice_list = manager.full_voice_list()
    service_name_list = [service.name for service in manager.get_all_services()]

    for language, source_text in input_map.items():
        for service_name in service_name_list:
            logging.info(f'testing language {language.name}, service {service_name}')
            random_voices = pick_random_voices_sample(voice_list, service_name, language, 3)
            for voice in random_voices:
                verify_audio_output(manager, voice, source_text)
