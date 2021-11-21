import os
import logging
import constants
import servicemanager

import random


def services_dir():
    current_script_path = os.path.realpath(__file__)
    current_script_dir = os.path.dirname(current_script_path)    
    return os.path.join(current_script_dir, 'services')

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

    audio_data = manager.get_tts_audio('This is the first sentence.', random_us_voice)

    
