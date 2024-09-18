import sys
import os
import json
import unittest

from test_utils import testing_utils

from hypertts import config_models
from hypertts import constants
from hypertts import languages
from hypertts import servicemanager
from hypertts import voice
from hypertts import errors


class ServiceManagerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manager = servicemanager.ServiceManager(testing_utils.get_test_services_dir(), 'hypertts.test_services', True, testing_utils.MockCloudLanguageTools())

    @classmethod
    def tearDownClass(cls):
        pass

    def test_discover(self):
        # discover available services
        actual_module_names = self.manager.discover_services()
        expected_module_names = ['service_a', 'service_c', 'service_b'] 
        actual_module_names.sort()
        expected_module_names.sort()
        self.assertEqual(expected_module_names, actual_module_names)

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
        assert self.manager.get_service('ServiceA')._config['api_key'] == 'yoyo'
        assert self.manager.get_service('ServiceA')._config['region'] == 'europe'

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
        assert self.manager.cloudlanguagetools.config.hypertts_pro_api_key == '123456'
        assert self.manager.cloudlanguagetools_enabled == True

        # remove pro api key
        configuration = config_models.Configuration()
        configuration.hypertts_pro_api_key = ''
        self.manager.configure(configuration)
        assert self.manager.cloudlanguagetools_enabled == False

    def test_services_partial_configuration(self):
        # try to partially configure a service

        self.manager.init_services()
        assert self.manager.get_service('ServiceA').enabled == False
        assert self.manager.get_service('ServiceB').enabled == False

        configuration = config_models.Configuration()
        configuration.set_service_enabled('ServiceA', True)
        configuration.set_service_configuration_key('ServiceA', 'region', 'europe')
        # should throw an error, we don't have api_key set
        self.assertRaises(errors.MissingServiceConfiguration, self.manager.configure, configuration)

        # same thing, but service is not enabled, we should not throw an error
        configuration = config_models.Configuration()
        configuration.set_service_enabled('ServiceA', False)
        configuration.set_service_configuration_key('ServiceA', 'region', 'europe')
        # should throw an error, we don't have api_key set
        self.manager.configure(configuration)

    def test_services_pro_mode_configure(self):
        # ensure that configuring services and pro mode don't conflict with each other

        self.manager.init_services()
        assert self.manager.get_service('ServiceA').enabled == False
        assert self.manager.get_service('ServiceB').enabled == False
        assert self.manager.get_service('ServiceC').enabled == False

        service_name = 'ServiceC'

        # missing password
        self.manager.init_services()
        self.assertEqual(self.manager.get_service(service_name).enabled, False)
        configuration = config_models.Configuration()
        self.assertFalse(configuration.hypertts_pro_api_key_set())
        configuration.set_service_enabled(service_name, True)
        configuration.set_service_configuration_key(service_name, 'user', 'user1')
        # should throw an error, we don't have password set
        self.assertRaises(errors.MissingServiceConfiguration, self.manager.configure, configuration)
        self.assertEqual(self.manager.get_service(service_name).password, None)
        self.assertEqual(self.manager.get_service(service_name).enabled, True)
        self.assertFalse(self.manager.cloudlanguagetools_enabled)

        # missing user
        self.manager.init_services()
        self.assertEqual(self.manager.get_service(service_name).enabled, False)        
        configuration = config_models.Configuration()
        self.assertFalse(configuration.hypertts_pro_api_key_set())
        configuration.set_service_enabled(service_name, True)
        configuration.set_service_configuration_key(service_name, 'password', 'pw1')
        self.assertRaises(errors.MissingServiceConfiguration, self.manager.configure, configuration)
        self.assertEqual(self.manager.get_service(service_name).user, None)
        self.assertEqual(self.manager.get_service(service_name).enabled, True)
        self.assertFalse(self.manager.cloudlanguagetools_enabled)        

        # complete configuration
        self.manager.init_services()
        self.assertEqual(self.manager.get_service(service_name).enabled, False)        
        configuration = config_models.Configuration()
        self.assertFalse(configuration.hypertts_pro_api_key_set())
        configuration.set_service_enabled(service_name, True)
        configuration.set_service_configuration_key(service_name, 'user', 'user1')
        configuration.set_service_configuration_key(service_name, 'password', 'pw1')
        self.manager.configure(configuration)
        self.assertEqual(self.manager.get_service(service_name).user, 'user1')
        self.assertEqual(self.manager.get_service(service_name).password, 'pw1')
        self.assertEqual(self.manager.get_service(service_name).enabled, True)
        self.assertFalse(self.manager.cloudlanguagetools_enabled)

        # now, set hypertts pro key
        self.manager.init_services()
        self.assertEqual(self.manager.get_service(service_name).enabled, False)        
        configuration = config_models.Configuration()
        configuration.set_hypertts_pro_api_key('key42')
        self.assertTrue(configuration.hypertts_pro_api_key_set())
        configuration.set_service_enabled(service_name, False)
        self.manager.configure(configuration)
        self.assertEqual(self.manager.get_service(service_name).enabled, True) # enabled any way, because of clt
        self.assertEqual(self.manager.get_service(service_name).user, None)
        self.assertEqual(self.manager.get_service(service_name).password, None)
        self.assertTrue(self.manager.cloudlanguagetools_enabled)

        # now, set hypertts pro key, partial service config
        self.manager.init_services()
        self.assertEqual(self.manager.get_service(service_name).enabled, False)        
        configuration = config_models.Configuration()
        configuration.set_hypertts_pro_api_key('key42')
        self.assertTrue(configuration.hypertts_pro_api_key_set())
        configuration.set_service_enabled(service_name, True)
        configuration.set_service_configuration_key(service_name, 'password', 'pw1')
        self.manager.configure(configuration)
        self.assertEqual(self.manager.get_service(service_name).enabled, True) # enabled any way, because of clt
        self.assertEqual(self.manager.get_service(service_name).user, None)
        self.assertEqual(self.manager.get_service(service_name).password, None)
        self.assertTrue(self.manager.cloudlanguagetools_enabled)


        


        


    def test_full_voice_list(self):
        self.manager.init_services()
        self.manager.get_service('ServiceA').enabled = True
        self.manager.get_service('ServiceB').enabled = True
        voice_list = self.manager.full_voice_list()

        # find ServiceA's voice_1
        subset = [voice for voice in voice_list if voice.service == 'ServiceA' and voice.gender == constants.Gender.Male]
        assert len(subset) == 1
        servicea_voice_1 = subset[0]
        assert servicea_voice_1.name == 'voice_a_1'
        assert servicea_voice_1.audio_languages == [languages.AudioLanguage.fr_FR]

        subset = [voice for voice in voice_list if voice.service == 'ServiceB' and voice.name == 'jane']
        assert len(subset) == 1
        servicea_voice_1 = subset[0]
        assert servicea_voice_1.name == 'jane'
        assert servicea_voice_1.audio_languages == [languages.AudioLanguage.ja_JP]


    def test_voice_serialization(self):
        self.manager.init_services()
        self.manager.get_service('ServiceA').enabled = True
        self.manager.get_service('ServiceB').enabled = True
        voice_list = self.manager.full_voice_list()

        subset = [voice for voice in voice_list if voice.name == 'voice_a_1']
        assert len(subset) == 1
        selected_voice = subset[0]

        # we don't serialize voices anymore, only voice ids

        voice_id_data = voice.serialize_voice_id_v3(selected_voice.voice_id)
        expected_voice_data = {
            'service': 'ServiceA',
            'voice_key': {'name': 'voice_1'}
        }
        assert voice_id_data == expected_voice_data

        assert str(selected_voice) == 'French (France), Male, voice_a_1 (ServiceA)'

        # test VoiceWithOptions
        # =====================

        voice_with_options = config_models.VoiceWithOptions(selected_voice.voice_id, {'pitch': 1.0, 'speaking_rate': 2.0})

        expected_voice_with_option_data = {
            'voice_id': voice_id_data,
            'options': {
                'pitch': 1.0,
                'speaking_rate': 2.0
            }
        }

        assert voice_with_options.serialize() == expected_voice_with_option_data
        expected_output = 'French (France), Male, voice_a_1 (ServiceA) (pitch: 1.0, speaking_rate: 2.0)'
        assert voice.generate_voice_with_options_str(selected_voice, voice_with_options.options) == expected_output

        # test deserializing of voice_id
        # ==============================

        deserialized_voice_id = voice.deserialize_voice_id_v3(voice_id_data)
        assert deserialized_voice_id.voice_key == {'name': 'voice_1'}
        assert deserialized_voice_id.service == 'ServiceA'


    def test_get_tts_audio(self):
        self.manager.init_services()
        self.manager.get_service('ServiceA').enabled = True
        self.manager.get_service('ServiceB').enabled = True
        voice_list = self.manager.full_voice_list()

        # find ServiceA's voice_1
        subset = [voice for voice in voice_list if voice.service == 'ServiceA' and voice.gender == constants.Gender.Male]
        assert len(subset) == 1
        servicea_voice_1 = subset[0]

        audio_result = self.manager.get_tts_audio('test sentence 123', servicea_voice_1, {}, None)

        audio_result_dict = json.loads(audio_result)

        assert audio_result_dict['source_text'] == 'test sentence 123'
        assert audio_result_dict['voice']['voice_key'] == {'name': 'voice_1'}

    def test_services_configuration(self):
        self.manager.init_services()    

        service_a_options = self.manager.service_configuration_options('ServiceA')
        assert service_a_options == {'api_key': str, 'region': ['us', 'europe'], 'delay': int, 'demo_key': bool}

        for key, value in service_a_options.items():
            if value == str:
                print(f'{key} is a string')
            elif value == int:
                print(f'{key} is integer')
            elif isinstance(value, list):
                print(f'{key} is list')
