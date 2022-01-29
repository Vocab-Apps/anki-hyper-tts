
import os
import json
import unittest

import config_models
import constants
import servicemanager
import voice
import testing_utils


class ServiceManagerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manager = servicemanager.ServiceManager(testing_utils.get_test_services_dir(), 'test_services', True, testing_utils.MockCloudLanguageTools())

    @classmethod
    def tearDownClass(cls):
        pass

    def test_discover(self):
        # discover available services
        module_names = self.manager.discover_services()
        assert module_names == ['service_a', 'service_b']

    def test_import(self):
        self.manager.init_services()

    def test_services_enabled(self):
        # test service enabled / disabled logic

        self.manager.init_services()
        assert self.manager.get_service('ServiceA').enabled == False
        assert self.manager.get_service('ServiceB').enabled == False

        configuration = config_models.Configuration()
        configuration.set_service_enabled('ServiceA', True)
        configuration.set_service_configuration_key('ServiceA', 'api_key', 'yoyo')
        configuration.set_service_configuration_key('ServiceA', 'region', 'europe')
        self.manager.configure(configuration)

        assert self.manager.get_service('ServiceA').enabled == True
        assert self.manager.get_service('ServiceB').enabled == False
        assert self.manager.get_service('ServiceA').config['api_key'] == 'yoyo'
        assert self.manager.get_service('ServiceA').config['region'] == 'europe'

        configuration = config_models.Configuration()
        configuration.set_service_enabled('ServiceA', False)
        self.manager.configure(configuration)
        assert self.manager.get_service('ServiceA').enabled == False

        # disable all services, they will get re-enabled when we enable cloudlanguagetools for some of them
        configuration = config_models.Configuration()
        configuration.hypertts_pro_api_key = '123456'
        configuration.set_service_enabled('ServiceA', False)
        configuration.set_service_enabled('ServiceB', False)
        self.manager.configure(configuration)

        assert self.manager.get_service('ServiceA').enabled == False
        assert self.manager.get_service('ServiceB').enabled == True # enabled by default for clt
        assert self.manager.cloudlanguagetools.api_key == '123456'
        assert self.manager.cloudlanguagetools_enabled == True

        # remove pro api key
        configuration = config_models.Configuration()
        configuration.hypertts_pro_api_key = ''
        self.manager.configure(configuration)
        assert self.manager.cloudlanguagetools_enabled == False




    def test_full_voice_list(self):
        self.manager.init_services()
        self.manager.get_service('ServiceA').enabled = True
        self.manager.get_service('ServiceB').enabled = True
        voice_list = self.manager.full_voice_list()

        # find ServiceA's voice_1
        subset = [voice for voice in voice_list if voice.service.name == 'ServiceA' and voice.gender == constants.Gender.Male]
        assert len(subset) == 1
        servicea_voice_1 = subset[0]
        assert servicea_voice_1.name == 'voice_a_1'
        assert servicea_voice_1.language == constants.AudioLanguage.fr_FR

        subset = [voice for voice in voice_list if voice.service.name == 'ServiceB' and voice.name == 'jane']
        assert len(subset) == 1
        servicea_voice_1 = subset[0]
        assert servicea_voice_1.name == 'jane'
        assert servicea_voice_1.language == constants.AudioLanguage.ja_JP


    def test_voice_serialization(self):
        self.manager.init_services()
        self.manager.get_service('ServiceA').enabled = True
        self.manager.get_service('ServiceB').enabled = True
        voice_list = self.manager.full_voice_list()

        subset = [voice for voice in voice_list if voice.name == 'voice_a_1']
        assert len(subset) == 1
        selected_voice = subset[0]

        voice_data = selected_voice.serialize()
        expected_voice_data = {
            'name': 'voice_a_1',
            'gender': 'Male',
            'language': 'fr_FR',
            'service': 'ServiceA',
            'voice_key': {'name': 'voice_1'}
        }
        assert voice_data == expected_voice_data

        assert str(selected_voice) == 'ServiceA, French (France), Male, voice_a_1'

        # test VoiceWithOptions
        # =====================

        voice_with_options = config_models.VoiceWithOptions(selected_voice, {'pitch': 1.0, 'speaking_rate': 2.0})

        expected_voice_with_option_data = {
            'voice': voice_data,
            'options': {
                'pitch': 1.0,
                'speaking_rate': 2.0
            }
        }

        assert voice_with_options.serialize() == expected_voice_with_option_data
        assert str(voice_with_options) == "ServiceA, French (France), Male, voice_a_1 (pitch: 1.0, speaking_rate: 2.0)"

        # test deserializing of voice
        # ===========================

        deserialized_voice = self.manager.deserialize_voice(voice_data)
        assert deserialized_voice.voice_key == {'name': 'voice_1'}
        assert deserialized_voice.name == 'voice_a_1'
        assert deserialized_voice.service.name == 'ServiceA'


    def test_get_tts_audio(self):
        self.manager.init_services()
        self.manager.get_service('ServiceA').enabled = True
        self.manager.get_service('ServiceB').enabled = True
        voice_list = self.manager.full_voice_list()

        # find ServiceA's voice_1
        subset = [voice for voice in voice_list if voice.service.name == 'ServiceA' and voice.gender == constants.Gender.Male]
        assert len(subset) == 1
        servicea_voice_1 = subset[0]

        audio_result = self.manager.get_tts_audio('test sentence 123', servicea_voice_1, {})

        audio_result_dict = json.loads(audio_result)

        assert audio_result_dict['source_text'] == 'test sentence 123'
        assert audio_result_dict['voice']['voice_key'] == {'name': 'voice_1'}

    def test_services_configuration(self):
        self.manager.init_services()    

        service_a_options = self.manager.service_configuration_options('ServiceA')
        assert service_a_options == {'api_key': str, 'region': ['us', 'europe'], 'delay': int}

        for key, value in service_a_options.items():
            if value == str:
                print(f'{key} is a string')
            elif value == int:
                print(f'{key} is integer')
            elif isinstance(value, list):
                print(f'{key} is list')
