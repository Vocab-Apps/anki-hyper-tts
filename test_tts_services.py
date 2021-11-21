import os
import logging
import constants
import servicemanager

import random
import tempfile


import pydub
import azure.cognitiveservices.speech
import azure.cognitiveservices.speech.audio

def services_dir():
    current_script_path = os.path.realpath(__file__)
    current_script_dir = os.path.dirname(current_script_path)    
    return os.path.join(current_script_dir, 'services')

def verify_audio_output(manager, voice, source_text):
    audio_data = manager.get_tts_audio(source_text, voice)
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
        constants.AudioLanguage.en_US: 'en-US'
    }

    recognition_language = recognition_language_map[voice.language]

    audio_input = azure.cognitiveservices.speech.audio.AudioConfig(filename=wav_filepath)
    speech_recognizer = azure.cognitiveservices.speech.SpeechRecognizer(speech_config=speech_config, audio_config=audio_input, language=recognition_language)
    result = speech_recognizer.recognize_once()

    # Checks result.
    if result.reason == azure.cognitiveservices.speech.ResultReason.RecognizedSpeech:
        recognized_text =  result.text
        assert source_text == recognized_text
    elif result.reason == azure.cognitiveservices.speech.ResultReason.NoMatch:
        error_message = "No speech could be recognized: {}".format(result.no_match_details)
        raise Exception(error_message)
    elif result.reason == azure.cognitiveservices.speech.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        error_message = "Speech Recognition canceled: {}".format(cancellation_details)
        raise Exception(error_message)

    raise "unknown error"


def test_google():
    manager = servicemanager.ServiceManager(services_dir(), 'services')
    manager.init_services()
    manager.get_service('Google').configure({'api_key': os.environ['GOOGLE_SERVICES_KEY']})

    voice_list = manager.full_voice_list()
    google_voices = [voice for voice in voice_list if voice.service.name == 'Google']
    # print(voice_list)
    logging.info(f'found {len(google_voices)}')
    assert len(google_voices) > 300

    # pick a random en_US voice
    us_voices = [voice for voice in google_voices if voice.language == constants.AudioLanguage.en_US]
    random_us_voice = random.choice(us_voices)

    # audio_data = manager.get_tts_audio('This is the first sentence.', random_us_voice)
    verify_audio_output(manager, random_us_voice, 'This is the first sentence')


