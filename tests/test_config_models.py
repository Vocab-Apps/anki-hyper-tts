import sys
import sys
import pprint
import unittest
import json
import pprint
import copy

from test_utils import testing_utils

from hypertts_addon import hypertts
from hypertts_addon import constants
from hypertts_addon import servicemanager
from hypertts_addon import config_models
from hypertts_addon import errors
from hypertts_addon import voice
from hypertts_addon import languages
from hypertts_addon import logging_utils

logger = logging_utils.get_test_child_logger(__name__)

def get_service_manager():
    manager = servicemanager.ServiceManager(testing_utils.get_test_services_dir(), f'{constants.DIR_HYPERTTS_ADDON}.test_services', True)
    manager.init_services()
    manager.get_service('ServiceA').enabled = True
    manager.get_service('ServiceB').enabled = True
    return manager    

def get_hypertts_instance():
    manager = get_service_manager()
    voice_list = manager.full_voice_list()    

    anki_utils = testing_utils.MockAnkiUtils({})
    hypertts_instance = hypertts.HyperTTS(anki_utils, manager)

    return hypertts_instance    

class ConfigModelsTests(unittest.TestCase):

    def test_voice_selection(self):
        # test the models around voice selection
        # =======================================

        manager = get_service_manager()
        voice_list = manager.full_voice_list()    

        anki_utils = testing_utils.MockAnkiUtils({})
        hypertts_instance = hypertts.HyperTTS(anki_utils, manager)

        voice_a_1 = [x for x in voice_list if x.name == 'voice_a_1'][0]
        voice_jane = [x for x in voice_list if x.name == 'jane'][0]

        # single voice mode
        # =================

        single = config_models.VoiceSelectionSingle()
        single.set_voice(config_models.VoiceWithOptions(voice_a_1.voice_id, {'speed': 42}))

        expected_output = {
            'voice_selection_mode': 'single',
            'voice': {
                'voice_id': {
                    'service': 'ServiceA',
                    'voice_key': {'name': 'voice_1'}
                },
                'options': {
                    'speed': 42
                }
            }
        }
        assert single.serialize() == expected_output

        # test deserialization
        single_deserialized = hypertts_instance.deserialize_voice_selection(single.serialize())

        # check that it gives the same output
        assert single_deserialized.serialize() == expected_output


        # random voice mode
        # =================

        random = config_models.VoiceSelectionRandom()
        random.add_voice(config_models.VoiceWithOptionsRandom(voice_a_1.voice_id, {'speed': 43}))
        random.add_voice(config_models.VoiceWithOptionsRandom(voice_jane.voice_id, {}))

        expected_output = {
            'voice_selection_mode': 'random',
            'voice_list': [
                {
                    'voice_id': {
                        'service': 'ServiceA',
                        'voice_key': {'name': 'voice_1'}
                    },
                    'options': {
                        'speed': 43
                    },
                    'weight': 1
                },
                {
                    'voice_id': {
                        'service': 'ServiceB',
                        'voice_key': {'voice_id': 'jane'}
                    },
                    'options': {
                    },
                    'weight': 1
                },            
            ]
        }
        assert random.serialize() == expected_output

        random.set_random_weight(1, 3)
        expected_output['voice_list'][1]['weight'] = 3

        assert random.serialize() == expected_output

        # test deserialization
        random_deserialized = hypertts_instance.deserialize_voice_selection(random.serialize())

        # check that it gives the same output
        assert random_deserialized.serialize() == expected_output

        random.remove_voice(random.voice_list[1])
        del expected_output['voice_list'][1]

        assert random.serialize() == expected_output

        # priority voice mode
        # ===================

        priority = config_models.VoiceSelectionPriority()
        priority.add_voice(config_models.VoiceWithOptionsPriority(voice_a_1.voice_id, {'speed': 43}))
        priority.add_voice(config_models.VoiceWithOptionsPriority(voice_a_1.voice_id, {'speed': 84}))
        priority.add_voice(config_models.VoiceWithOptionsPriority(voice_jane.voice_id, {}))

        expected_output = {
            'voice_selection_mode': 'priority',
            'voice_list': [
                {
                    'voice_id': {
                        'service': 'ServiceA',
                        'voice_key': {'name': 'voice_1'}
                    },
                    'options': {
                        'speed': 43
                    },
                },
                {
                    'voice_id': {
                        'service': 'ServiceA',
                        'voice_key': {'name': 'voice_1'}
                    },
                    'options': {
                        'speed': 84
                    },
                },            
                {
                    'voice_id': {
                        'service': 'ServiceB',
                        'voice_key': {'voice_id': 'jane'}
                    },
                    'options': {
                    },
                },            
            ]
        }
        assert priority.serialize() == expected_output

        priority.move_up_voice(priority.voice_list[2])

        expected_output = {
            'voice_selection_mode': 'priority',
            'voice_list': [
                {
                    'voice_id': {
                        'service': 'ServiceA',
                        'voice_key': {'name': 'voice_1'}
                    },
                    'options': {
                        'speed': 43
                    },
                },
                {
                    'voice_id': {
                        'service': 'ServiceB',
                        'voice_key': {'voice_id': 'jane'}
                    },
                    'options': {
                    },
                },
                {
                    'voice_id': {
                        'service': 'ServiceA',
                        'voice_key': {'name': 'voice_1'}
                    },
                    'options': {
                        'speed': 84
                    },
                },            
            ]
        }
        assert priority.serialize() == expected_output    


        priority.move_down_voice(priority.voice_list[0])

        expected_output = {
            'voice_selection_mode': 'priority',
            'voice_list': [
                {
                    'voice_id': {
                        'service': 'ServiceB',
                        'voice_key': {'voice_id': 'jane'}
                    },
                    'options': {
                    },
                },
                {
                    'voice_id': {
                        'service': 'ServiceA',
                        'voice_key': {'name': 'voice_1'}
                    },
                    'options': {
                        'speed': 43
                    },
                },
                {
                    'voice_id': {
                        'service': 'ServiceA',
                        'voice_key': {'name': 'voice_1'}
                    },
                    'options': {
                        'speed': 84
                    },
                },            
            ]
        }
        assert priority.serialize() == expected_output

        # test deserialization
        priority_deserialized = hypertts_instance.deserialize_voice_selection(priority.serialize())

        # check that it gives the same output
        assert priority_deserialized.serialize() == expected_output

    def test_missing_voice_random(self):
        manager = get_service_manager()
        voice_list = manager.full_voice_list()    

        anki_utils = testing_utils.MockAnkiUtils({})
        hypertts_instance = hypertts.HyperTTS(anki_utils, manager)

        # the first voice is non-existent
        random_serialized_config = {
            'voice_selection_mode': 'random',
            'voice_list': [
                {
                    'voice_id': {
                        'service': 'ServiceA',
                        'voice_key': {'name': 'voice_4'}
                    },
                    'options': {
                        'speed': 43
                    },
                    'weight': 1
                },
                {
                    'voice_id': {
                        'service': 'ServiceA',
                        'voice_key': {'name': 'voice_1'}
                    },
                    'options': {
                        'speed': 43
                    },
                    'weight': 1
                },
                {
                    'voice_id': {
                        'service': 'ServiceB',
                        'voice_key': {'voice_id': 'jane'}
                    },
                    'options': {
                    },
                    'weight': 1
                },            
            ]
        }
        random_deserialized = hypertts_instance.deserialize_voice_selection(random_serialized_config)
        self.assertEqual(len(random_deserialized.voice_list), 2) # the first voice is missing
        self.assertEqual(random_deserialized.voice_list[0].voice_id.voice_key, {'name': 'voice_1'})
        self.assertEqual(random_deserialized.voice_list[1].voice_id.voice_key, {'voice_id': 'jane'})

    def test_missing_voice_priority(self):
        manager = get_service_manager()
        voice_list = manager.full_voice_list()    

        anki_utils = testing_utils.MockAnkiUtils({})
        hypertts_instance = hypertts.HyperTTS(anki_utils, manager)

        # the first voice is non-existent
        priority_serialized_config = {
            'voice_selection_mode': 'priority',
            'voice_list': [
                {
                    'voice_id': {
                        'service': 'ServiceA',
                        'voice_key': {'name': 'voice_4'}
                    },
                    'options': {
                        'speed': 43
                    },
                },                
                {
                    'voice_id': {
                        'service': 'ServiceA',
                        'voice_key': {'name': 'voice_1'}
                    },
                    'options': {
                        'speed': 43
                    },
                },
                {
                    'voice_id': {
                        'service': 'ServiceA',
                        'voice_key': {'name': 'voice_1'}
                    },
                    'options': {
                        'speed': 84
                    },
                },            
                {
                    'voice_id': {
                        'service': 'ServiceB',
                        'voice_key': {'voice_id': 'jane'}
                    },
                    'options': {
                    },
                },            
            ]
        }

        priority_deserialized = hypertts_instance.deserialize_voice_selection(priority_serialized_config)
        self.assertEqual(len(priority_deserialized.voice_list), 3) # the first voice is missing
        self.assertEqual(priority_deserialized.voice_list[0].voice_id.voice_key, {'name': 'voice_1'})
        self.assertEqual(priority_deserialized.voice_list[1].voice_id.voice_key, {'name': 'voice_1'})
        self.assertEqual(priority_deserialized.voice_list[2].voice_id.voice_key, {'voice_id': 'jane'})
        

    def test_batch_config(self):
        hypertts_instance = get_hypertts_instance()
        voice_list = hypertts_instance.service_manager.full_voice_list()

        voice_a_1 = [x for x in voice_list if x.name == 'voice_a_1'][0]
        voice_selection = config_models.VoiceSelectionSingle()
        voice_selection.set_voice(config_models.VoiceWithOptions(voice_a_1.voice_id, {'speed': 43}))

        batch_config = config_models.BatchConfig(hypertts_instance.anki_utils)
        batch_config.name = 'preset_1'
        source = config_models.BatchSource(mode=constants.BatchMode.simple, source_field='Chinese')
        target = config_models.BatchTarget('Sound', False, False)
        text_processing = config_models.TextProcessing()
        rule = config_models.TextReplacementRule(constants.TextReplacementRuleType.Simple)
        rule.source = 'a'
        rule.target = 'b'
        text_processing.add_text_replacement_rule(rule)

        batch_config.set_source(source)
        batch_config.set_target(target)
        batch_config.set_voice_selection(voice_selection)
        batch_config.text_processing = text_processing

        expected_output = {
            'name': 'preset_1',
            'uuid': 'uuid_0',
            'source': {
                'mode': 'simple',            
                'source_field': 'Chinese',
                'source_template': None,
                'template_format_version': 'v1',
                'use_selection': False
            },
            'target': {
                'target_field': 'Sound',
                'text_and_sound_tag': False,
                'remove_sound_tag': False,
                'insert_location': 'AFTER',
                'same_field': False
            },
            'voice_selection': {
                'voice_selection_mode': 'single',
                'voice': 
                    {
                        'voice_id': {
                            'service': 'ServiceA',
                            'voice_key': {'name': 'voice_1'}
                        },
                        'options': {
                            'speed': 43
                        },
                    },        
            },
            'text_processing': {
                'html_to_text_line': True,
                'strip_brackets': False,
                'strip_cloze': False,
                'run_replace_rules_after': True,
                'ssml_convert_characters': True,
                'ignore_case': False,
                'text_replacement_rules': [
                    {
                        'rule_type': 'Simple',
                        'source': 'a',
                        'target': 'b'
                    }]
            }
        }
        assert batch_config.serialize() == expected_output

        batch_config_deserialized = hypertts_instance.deserialize_batch_config(batch_config.serialize())

        assert batch_config_deserialized.serialize() == batch_config.serialize()

        self.assertEqual(batch_config_deserialized.source.source_field, 'Chinese')
        self.assertEqual(batch_config_deserialized.source.mode, constants.BatchMode.simple)   


    def test_batch_config_target_serialize(self):
        # serialize tests for Target
        hypertts_instance = get_hypertts_instance()
        voice_list = hypertts_instance.service_manager.full_voice_list()

        voice_a_1 = [x for x in voice_list if x.name == 'voice_a_1'][0]
        voice_selection = config_models.VoiceSelectionSingle()
        voice_selection.set_voice(config_models.VoiceWithOptions(voice_a_1.voice_id, {'speed': 43}))
        batch_config = config_models.BatchConfig(hypertts_instance.anki_utils)
        source = config_models.BatchSource(mode=constants.BatchMode.simple, source_field='Chinese')
        text_processing = config_models.TextProcessing()
        batch_config.set_source(source)
        batch_config.set_voice_selection(voice_selection)
        batch_config.text_processing = text_processing


        for text_and_sound_tag in [True, False]:
            for remove_sound_tag in [True, False]:

                target = config_models.BatchTarget('Sound', text_and_sound_tag, remove_sound_tag)
                batch_config.set_target(target)

                expected_output = {
                    'target_field': 'Sound',
                    'text_and_sound_tag': text_and_sound_tag,
                    'remove_sound_tag': remove_sound_tag,
                    'insert_location': 'AFTER',
                    'same_field': False
                }
                assert batch_config.serialize()['target'] == expected_output

                # try deserializing
                deserialized_batch_config = hypertts_instance.deserialize_batch_config(batch_config.serialize())
                assert deserialized_batch_config.serialize()['target'] == expected_output

    def test_batch_config_target_deserialize_schema_v3(self):
        config = {
            'target_field': 'Sound',
            'text_and_sound_tag': False,
            'remove_sound_tag': True
        }

        batch_target = config_models.deserialize_batch_target(config)
        self.assertEqual(batch_target.target_field, 'Sound')
        self.assertEqual(batch_target.text_and_sound_tag, False)
        self.assertEqual(batch_target.remove_sound_tag, True)
        self.assertEqual(batch_target.insert_location, config_models.InsertLocation.AFTER)
        self.assertEqual(batch_target.same_field, False)


    def test_batch_config_target_deserialize_schema_v4(self):
        config = {
            'target_field': 'Chinese',
            'text_and_sound_tag': False,
            'remove_sound_tag': True,
            'insert_location': 'CURSOR_LOCATION',
            'same_field': True
        }

        batch_target = config_models.deserialize_batch_target(config)
        self.assertEqual(batch_target.target_field, 'Chinese')
        self.assertEqual(batch_target.text_and_sound_tag, False)
        self.assertEqual(batch_target.remove_sound_tag, True)
        self.assertEqual(batch_target.insert_location, config_models.InsertLocation.CURSOR_LOCATION)
        self.assertEqual(batch_target.same_field, True)


    def test_text_processing(self):
        hypertts_instance = get_hypertts_instance()
        
        text_processing = config_models.TextProcessing()
        rule = config_models.TextReplacementRule(constants.TextReplacementRuleType.Simple)
        rule.source = 'a'
        rule.target = 'b'
        text_processing.add_text_replacement_rule(rule)
        rule = config_models.TextReplacementRule(constants.TextReplacementRuleType.Regex)
        rule.source = 'c'
        rule.target = 'd'    
        text_processing.add_text_replacement_rule(rule)

        expected_output = {
            'html_to_text_line': True,
            'strip_brackets': False,
            'strip_cloze': False,
            'run_replace_rules_after': True,
            'ssml_convert_characters': True,
            'ignore_case': False,
            'text_replacement_rules': [
                {
                    'rule_type': 'Simple',
                    'source': 'a',
                    'target': 'b'
                },
                {
                    'rule_type': 'Regex',
                    'source': 'c',
                    'target': 'd'
                },            
            ]
        }
        assert text_processing.serialize() == expected_output

        # remove first rule
        text_processing.remove_text_replacement_rule(0)

        expected_output = {
            'html_to_text_line': True,
            'strip_brackets': False,
            'strip_cloze': False,
            'run_replace_rules_after': True,
            'ssml_convert_characters': True,
            'ignore_case': False,
            'text_replacement_rules': [
                {
                    'rule_type': 'Regex',
                    'source': 'c',
                    'target': 'd'
                },            
            ]
        }
        assert text_processing.serialize() == expected_output

        # set strip brackets to true
        text_processing.strip_brackets = True
        expected_output = {
            'html_to_text_line': True,
            'strip_brackets': True,
            'strip_cloze': False,
            'run_replace_rules_after': True,
            'ssml_convert_characters': True,        
            'ignore_case': False,
            'text_replacement_rules': [
                {
                    'rule_type': 'Regex',
                    'source': 'c',
                    'target': 'd'
                },            
            ]
        }
        assert hypertts_instance.deserialize_text_processing(text_processing.serialize()).serialize() == expected_output

    def test_deserialize_text_processing_missing_strip_cloze(self):
        """Test deserializing text processing without strip_cloze field - should default to False"""
        hypertts_instance = get_hypertts_instance()
        
        # Create input data without strip_cloze field
        input_data = {
            'html_to_text_line': True,
            'strip_brackets': False,
            'run_replace_rules_after': True,
            'ssml_convert_characters': True,
            'ignore_case': False,
            'text_replacement_rules': []
        }
        
        # Deserialize and check that strip_cloze defaults to False
        deserialized = hypertts_instance.deserialize_text_processing(input_data)
        assert deserialized.strip_cloze == False

    def test_deserialize_text_processing_strip_cloze_true(self):
        """Test deserializing text processing with strip_cloze = True"""
        hypertts_instance = get_hypertts_instance()
        
        # Create input data with strip_cloze = True
        input_data = {
            'html_to_text_line': True,
            'strip_brackets': False,
            'strip_cloze': True,
            'run_replace_rules_after': True,
            'ssml_convert_characters': True,
            'ignore_case': False,
            'text_replacement_rules': []
        }
        
        # Deserialize and check that strip_cloze is True
        deserialized = hypertts_instance.deserialize_text_processing(input_data)
        assert deserialized.strip_cloze == True

    def test_deserialize_text_processing_strip_cloze_false(self):
        """Test deserializing text processing with strip_cloze = False"""
        hypertts_instance = get_hypertts_instance()
        
        # Create input data with strip_cloze = False
        input_data = {
            'html_to_text_line': True,
            'strip_brackets': False,
            'strip_cloze': False,
            'run_replace_rules_after': True,
            'ssml_convert_characters': True,
            'ignore_case': False,
            'text_replacement_rules': []
        }
        
        # Deserialize and check that strip_cloze is False
        deserialized = hypertts_instance.deserialize_text_processing(input_data)
        assert deserialized.strip_cloze == False


    def test_configuration(self):
        # exclude these from comparison
        keys_to_remove = ['install_time', 'display_introduction_message', 'trial_registration_step']

        hypertts_instance = get_hypertts_instance()

        configuration = config_models.Configuration()
        configuration.hypertts_pro_api_key = '123456'
        configuration.set_service_enabled('ServiceA', True)
        configuration.set_service_enabled('ServiceB', False)
        configuration.set_service_configuration_key('ServiceA', 'region', 'europe')

        expected_output = {
            'hypertts_pro_api_key': '123456',
            'use_vocabai_api': False, 
            'vocabai_api_url_override': None,
            'service_enabled': {
                'ServiceA': True,
                'ServiceB': False
            },
            'service_config': {
                'ServiceA': {
                    'region': 'europe'
                },
            },
            'user_uuid': None,
            'user_choice_easy_advanced': False
        }

        actual_output = config_models.serialize_configuration(configuration)
        for key in keys_to_remove:
            del actual_output[key]
        assert actual_output == expected_output

        deserialized_configuration = hypertts_instance.deserialize_configuration(config_models.serialize_configuration(configuration))
        assert deserialized_configuration.get_service_configuration_key('ServiceA', 'region') == 'europe'
        assert deserialized_configuration.get_service_enabled('ServiceA') == True
        assert deserialized_configuration.get_service_enabled('ServiceB') == False

        assert config_models.serialize_configuration(configuration) == config_models.serialize_configuration(deserialized_configuration)

        # hypertts pro key
        configuration = config_models.Configuration()
        configuration.hypertts_pro_api_key = None
        self.assertFalse(configuration.hypertts_pro_api_key_set())
        configuration = config_models.Configuration()
        configuration.hypertts_pro_api_key = ''
        self.assertFalse(configuration.hypertts_pro_api_key_set())
        configuration = config_models.Configuration()
        configuration.hypertts_pro_api_key = 'yoyo'
        self.assertTrue(configuration.hypertts_pro_api_key_set())

        # some services' enabled flag not defined
        configuration = config_models.Configuration()
        configuration.hypertts_pro_api_key = '123456'
        configuration.set_service_enabled('ServiceA', True)

        assert configuration.get_service_enabled('ServiceA') == True
        assert configuration.get_service_enabled('ServiceB') == None

        deserialized_configuration = hypertts_instance.deserialize_configuration(config_models.serialize_configuration(configuration))

        assert deserialized_configuration.get_service_enabled('ServiceA') == True
        assert deserialized_configuration.get_service_enabled('ServiceB') == None

        assert deserialized_configuration.get_service_configuration_key('ServiceA', 'region') == None

        # try to serialize float
        configuration = config_models.Configuration()
        configuration.hypertts_pro_api_key = '123456'
        configuration.set_service_enabled('ServiceA', True)
        configuration.set_service_configuration_key('ServiceA', 'speed', 1.42)

        expected_output = {
            'hypertts_pro_api_key': '123456',
            'use_vocabai_api': False, 
            'vocabai_api_url_override': None,
            'service_enabled': {
                'ServiceA': True,
            },
            'service_config': {
                'ServiceA': {
                    'speed': 1.42
                },
            },
            'user_uuid': None,
            'user_choice_easy_advanced': False
        }

        actual_output = config_models.serialize_configuration(configuration)
        for key in keys_to_remove:
            del actual_output[key]
        assert actual_output == expected_output

        # now try to deserialize float
        deserialized_configuration = config_models.deserialize_configuration(expected_output)
        self.assertEqual(type(deserialized_configuration.service_config['ServiceA']['speed']), float)
        self.assertEqual(deserialized_configuration.get_service_configuration_key('ServiceA', 'speed'), 1.42)


    def test_batch_config_advanced_template(self):
        hypertts_instance = get_hypertts_instance()
        voice_list = hypertts_instance.service_manager.full_voice_list()

        voice_a_1 = [x for x in voice_list if x.name == 'voice_a_1'][0]
        voice_selection = config_models.VoiceSelectionSingle()
        voice_selection.set_voice(config_models.VoiceWithOptions(voice_a_1.voice_id, {'speed': 43}))

        source_template = """result = 'yoyo'"""

        batch_config = config_models.BatchConfig(hypertts_instance.anki_utils)
        batch_config.name = 'preset_2'
        source = config_models.BatchSource(mode=constants.BatchMode.advanced_template, 
            source_template=source_template, template_format_version=constants.TemplateFormatVersion.v1)
        target = config_models.BatchTarget('Audio', False, False)
        text_processing = config_models.TextProcessing()
        rule = config_models.TextReplacementRule(constants.TextReplacementRuleType.Simple)
        rule.source = 'a'
        rule.target = 'b'
        text_processing.add_text_replacement_rule(rule)

        batch_config.set_source(source)
        batch_config.set_target(target)
        batch_config.set_voice_selection(voice_selection)
        batch_config.text_processing = text_processing

        expected_output = {
            'name': 'preset_2',
            'uuid': 'uuid_0',
            'source': {
                'mode': 'advanced_template',
                'source_field': None,
                'template_format_version': 'v1',
                'source_template': """result = 'yoyo'""",
                'use_selection': False
            },
            'target': {
                'target_field': 'Audio',
                'text_and_sound_tag': False,
                'remove_sound_tag': False,
                'insert_location': 'AFTER',
                'same_field': False
            },
            'voice_selection': {
                'voice_selection_mode': 'single',
                'voice': 
                    {
                        'voice_id': {
                            'service': 'ServiceA',
                            'voice_key': {'name': 'voice_1'}
                        },
                        'options': {
                            'speed': 43
                        },
                    },        
            },
            'text_processing': {
                'html_to_text_line': True,
                'strip_brackets': False,
                'strip_cloze': False,
                'run_replace_rules_after': True,
                'ssml_convert_characters': True,
                'ignore_case': False,
                'text_replacement_rules': [
                    {
                        'rule_type': 'Simple',
                        'source': 'a',
                        'target': 'b'
                    }]
            }
        }
        pprint.pprint(batch_config.serialize())

        assert batch_config.serialize() == expected_output

        batch_config_deserialized = hypertts_instance.deserialize_batch_config(batch_config.serialize())

        assert batch_config_deserialized.serialize() == batch_config.serialize()


    def test_batch_config_validation(self):
        hypertts_instance = get_hypertts_instance()
        voice_list = hypertts_instance.service_manager.full_voice_list()

        voice_a_1 = [x for x in voice_list if x.name == 'voice_a_1'][0]
        voice_selection = config_models.VoiceSelectionSingle()
        voice_selection.set_voice(config_models.VoiceWithOptions(voice_a_1.voice_id, {'speed': 43}))

        # missing source field
        # ====================

        batch_config = config_models.BatchConfig(hypertts_instance.anki_utils)
        batch_config.name = 'preset_3'
        source = config_models.BatchSource(mode=constants.BatchMode.simple, source_field='')
        target = config_models.BatchTarget('Sound', False, False)
        text_processing = config_models.TextProcessing()

        batch_config.set_source(source)
        batch_config.set_target(target)
        batch_config.set_voice_selection(voice_selection)
        batch_config.text_processing = text_processing

        self.assertRaises(errors.SourceFieldNotSet, batch_config.validate)

        # missing target field
        # ====================

        source = config_models.BatchSource(mode=constants.BatchMode.simple, source_field='Chinese')
        target = config_models.BatchTarget(None, False, False)

        batch_config.set_source(source)
        batch_config.set_target(target)        

        self.assertRaises(errors.TargetFieldNotSet, batch_config.validate)

        # single voice, voice not set
        # ===========================

        source = config_models.BatchSource(mode=constants.BatchMode.simple, source_field='Chinese')
        target = config_models.BatchTarget('Sound', False, False)
        voice_selection = config_models.VoiceSelectionSingle()

        batch_config.set_source(source)
        batch_config.set_target(target)
        batch_config.set_voice_selection(voice_selection)

        self.assertRaises(errors.NoVoiceSet, batch_config.validate)

        
        # priority mode, no voice set
        # ===========================

        voice_selection = config_models.VoiceSelectionPriority()
        batch_config.set_voice_selection(voice_selection)

        self.assertRaises(errors.NoVoiceSet, batch_config.validate)


        # random mode, no voice set
        # ===========================

        voice_selection = config_models.VoiceSelectionRandom()
        batch_config.set_voice_selection(voice_selection)

        self.assertRaises(errors.NoVoiceSet, batch_config.validate)


    def test_realtime_config(self):
        self.maxDiff = None
        hypertts_instance = get_hypertts_instance()
        voice_list = hypertts_instance.service_manager.full_voice_list()

        voice_a_1 = [x for x in voice_list if x.name == 'voice_a_1'][0]
        voice_selection = config_models.VoiceSelectionSingle()
        voice_selection.set_voice(config_models.VoiceWithOptions(voice_a_1.voice_id, {'speed': 43}))

        realtime_config = config_models.RealtimeConfig()
        front = config_models.RealtimeConfigSide()
        front.side_enabled = True

        source = config_models.RealtimeSourceAnkiTTS()
        source.field_name = 'Chinese'
        source.field_type = constants.AnkiTTSFieldType.Regular
        text_processing = config_models.TextProcessing()
        front.source = source
        front.text_processing = text_processing
        front.voice_selection = voice_selection

        back = config_models.RealtimeConfigSide()

        realtime_config.front = front
        realtime_config.back = back

        realtime_config.validate()

        expected_output = {
            'front': {
                'side_enabled': True,
                'source': {
                    'mode': 'AnkiTTSTag',
                    'field_name': 'Chinese',
                    'field_type': 'Regular'
                },
                'voice_selection': {
                    'voice_selection_mode': 'single',
                    'voice': 
                        {
                            'voice_id': {
                                'service': 'ServiceA',
                                'voice_key': {'name': 'voice_1'}
                            },
                            'options': {
                                'speed': 43
                            },
                        },        
                },
                'text_processing': {
                    'html_to_text_line': True,
                    'strip_brackets': False,
                    'strip_cloze': False,
                    'run_replace_rules_after': True,
                    'ssml_convert_characters': True,
                    'ignore_case': False,   
                    'text_replacement_rules': []
                }
            },
            'back': {
                'side_enabled': False
            }
        }

        self.assertEqual(realtime_config.serialize(), expected_output)

        deserialized_realtime_config = hypertts_instance.deserialize_realtime_config(realtime_config.serialize())
        self.assertEqual(deserialized_realtime_config.serialize(), realtime_config.serialize())

    def test_preferences_1(self):
        # pytest test_config_models.py -k test_preferences_1
        hypertts_instance = get_hypertts_instance()

        # serialization test
        # ==================

        preferences = config_models.Preferences()
        preferences.keyboard_shortcuts.shortcut_editor_add_audio = 'Ctrl+A'
        preferences.keyboard_shortcuts.shortcut_editor_preview_audio = 'Ctrl+P'

        expected_output = {
            'keyboard_shortcuts': {
                'shortcut_editor_add_audio': 'Ctrl+A',
                'shortcut_editor_preview_audio': 'Ctrl+P'
            },
            'error_handling': {
                'realtime_tts_errors_dialog_type': 'Dialog',
                'error_stats_reporting': True
            }
        }
        self.assertEqual(config_models.serialize_preferences(preferences), expected_output)


        # deserialization test
        # ====================
        preferences_config = {
        }
        preferences_1 = hypertts_instance.deserialize_preferences(preferences_config)
        self.assertEqual(preferences_1.error_handling.realtime_tts_errors_dialog_type, constants.ErrorDialogType.Dialog)
        self.assertEqual(preferences_1.keyboard_shortcuts.shortcut_editor_add_audio, None)
        self.assertEqual(preferences_1.keyboard_shortcuts.shortcut_editor_preview_audio, None)
        self.assertEqual(config_models.serialize_preferences(preferences_1), 
        {
            'keyboard_shortcuts': {
                'shortcut_editor_add_audio': None,
                'shortcut_editor_preview_audio': None
            },
            'error_handling': {
                'realtime_tts_errors_dialog_type': 'Dialog',
                'error_stats_reporting': True
            }                           
        })

        preferences_config = {
            'keyboard_shortcuts': {
                'shortcut_editor_add_audio': 'Ctrl+T',
                'shortcut_editor_preview_audio': None
            }
        }
        preferences = hypertts_instance.deserialize_preferences(preferences_config)
        self.assertEqual(preferences.keyboard_shortcuts.shortcut_editor_add_audio, 'Ctrl+T')
        self.assertEqual(preferences.keyboard_shortcuts.shortcut_editor_preview_audio, None)
        self.assertEqual(preferences.error_handling.realtime_tts_errors_dialog_type, constants.ErrorDialogType.Dialog)
        self.assertEqual(config_models.serialize_preferences(preferences), 
        {
            'keyboard_shortcuts': {
                'shortcut_editor_add_audio': 'Ctrl+T',
                'shortcut_editor_preview_audio': None
            },
            'error_handling': {
                'realtime_tts_errors_dialog_type': 'Dialog',
                'error_stats_reporting': True
            }                           
        })        

    def test_preset_mapping_rules(self):
        # pytest test_config_models.py -k test_preset_mapping_rules
        hypertts_instance = get_hypertts_instance()

        # serialization test
        # ==================

        mapping_rules = config_models.PresetMappingRules()
        rule_1 = config_models.MappingRule(preset_id='preset_1', 
            rule_type=constants.MappingRuleType.DeckNoteType, 
            model_id=42,
            deck_id=52,
            enabled=True, 
            automatic=False)
        mapping_rules.rules.append(rule_1)

        expected_output = {
            'rules': [
                {
                    'preset_id': 'preset_1',
                    'rule_type': 'DeckNoteType',
                    'model_id': 42,
                    'deck_id': 52,
                    'enabled': True,
                    'automatic': False,
                    'is_default': False
                }
            ],
            'use_easy_mode': False
        }
        self.assertEqual(config_models.serialize_preset_mapping_rules(mapping_rules), expected_output)


        # deserialization test
        # ==================

        preset_mapping_rule_data = {
            'rules': [
                {
                    'preset_id': 'preset_2',
                    'rule_type': 'NoteType',
                    'model_id': 43,
                    'deck_id': 53,
                    'enabled': False,
                    'automatic': False,
                    'is_default': False
                }
            ],
            'use_easy_mode': False
        }

        mapping_rules = config_models.deserialize_preset_mapping_rules(preset_mapping_rule_data)

        self.assertEqual(mapping_rules.rules[0].preset_id, 'preset_2')
        self.assertEqual(mapping_rules.rules[0].rule_type, constants.MappingRuleType.NoteType)
        self.assertEqual(mapping_rules.rules[0].model_id, 43)
        self.assertEqual(mapping_rules.rules[0].deck_id, 53)
        self.assertEqual(mapping_rules.rules[0].enabled, False)
        self.assertEqual(mapping_rules.rules[0].automatic, False)

        preset_mapping_rule_data = {
            'rules': [
                {
                    'preset_id': 'preset_2',
                    'rule_type': 'NoteType',
                    'model_id': 42,
                    'deck_id': None,
                    'enabled': False,
                    'automatic': False,
                    'is_default': False
                }
            ],
            'use_easy_mode': False
        }

        mapping_rules = config_models.deserialize_preset_mapping_rules(preset_mapping_rule_data)

        self.assertEqual(mapping_rules.rules[0].preset_id, 'preset_2')
        self.assertEqual(mapping_rules.rules[0].rule_type, constants.MappingRuleType.NoteType)
        self.assertEqual(mapping_rules.rules[0].model_id, 42)
        self.assertEqual(mapping_rules.rules[0].deck_id, None)
        self.assertEqual(mapping_rules.rules[0].enabled, False)
        self.assertEqual(mapping_rules.rules[0].automatic, False)        


    def test_migration_0_to_2_empty(self):
        anki_utils = testing_utils.MockAnkiUtils({})
        # config revision 0
        config = {}
        updated_config = config_models.migrate_configuration(anki_utils, config)
        self.assertEqual(updated_config['config_schema'], 4)


    def test_migration_0_to_2(self):
        anki_utils = testing_utils.MockAnkiUtils({})
        # config revision 0
        config = {
            'batch_config': {
                'preset_1': {
                    'source': {
                        'mode': 'simple',            
                        'source_field': 'Chinese'
                    },
                    'target': {
                        'target_field': 'Sound',
                        'text_and_sound_tag': False,
                        'remove_sound_tag': False
                    },
                    'voice_selection': {
                        'voice_selection_mode': 'single',
                        'voice': 
                            {
                                'voice': {
                                    'gender': 'Male', 
                                    'language': 'fr_FR', 
                                    'name': 'voice_a_1', 
                                    'service': 'ServiceA',
                                    'voice_key': {'name': 'voice_1'}
                                },
                                'options': {
                                    'speed': 43
                                },
                            },        
                    },
                    'text_processing': {
                        'html_to_text_line': True,
                        'strip_brackets': False,
                        'strip_cloze': False,
                        'run_replace_rules_after': True,
                        'ssml_convert_characters': True,
                        'ignore_case': False,
                        'text_replacement_rules': [
                            {
                                'rule_type': 'Simple',
                                'source': 'a',
                                'target': 'b'
                            }]
                    }
                }
            }
        }

        updated_config = config_models.migrate_configuration(anki_utils, config)
        self.assertEqual(updated_config['config_schema'], 4)
        expected_preset_1_uuid = 'uuid_0'
        self.assertIn(expected_preset_1_uuid, updated_config['presets'])
        self.assertEqual(updated_config['presets'][expected_preset_1_uuid]['name'], 'preset_1')
        self.assertEqual(updated_config['presets'][expected_preset_1_uuid]['uuid'], expected_preset_1_uuid)

        # try to run migration again, nothing should happen
        updated_config = config_models.migrate_configuration(anki_utils, updated_config)
        self.assertIn(expected_preset_1_uuid, updated_config['presets'])
        self.assertEqual(updated_config['presets'][expected_preset_1_uuid]['name'], 'preset_1')
        self.assertEqual(updated_config['presets'][expected_preset_1_uuid]['uuid'], expected_preset_1_uuid)        


    def test_migration_2_to_3_a(self):
        anki_utils = testing_utils.MockAnkiUtils({})
        config_rev_2_json_str = """
{
    "batch_config": {},
    "config_schema": 2,
    "configuration": {
        "hypertts_pro_api_key": "api_key_1",
        "service_config": {},
        "service_enabled": {},
        "use_vocabai_api": true,
        "vocabai_api_url_override": null
    },
    "preferences": {},
    "presets": {
        "1f8ae532-c1e0-4467-8220-9394f523ff17": {
            "name": "Chinese Single Voice",
            "source": {
                "mode": "simple",
                "source_field": "Chinese",
                "source_template": null,
                "template_format_version": "v1",
                "use_selection": false
            },
            "target": {
                "remove_sound_tag": true,
                "target_field": "Chinese",
                "text_and_sound_tag": false
            },
            "text_processing": {
                "html_to_text_line": true,
                "ignore_case": false,
                "run_replace_rules_after": true,
                "ssml_convert_characters": true,
                "strip_brackets": false,
                "strip_cloze": false,
                "text_replacement_rules": []
            },
            "uuid": "1f8ae532-c1e0-4467-8220-9394f523ff17",
            "voice_selection": {
                "voice": {
                    "options": {},
                    "voice": {
                        "gender": "Female",
                        "language": "zh_CN",
                        "name": "Xiaoyou 晓悠 (Neural)",
                        "service": "Azure",
                        "voice_key": {
                            "name": "Microsoft Server Speech Text to Speech Voice (zh-CN, XiaoyouNeural)"
                        }
                    }
                },
                "voice_selection_mode": "single"
            }
        },
        "79b2715e-9871-4b4f-9a5b-8bd5ac89d689": {
            "name": "Chinese Priority",
            "source": {
                "mode": "simple",
                "source_field": "Chinese",
                "source_template": null,
                "template_format_version": "v1",
                "use_selection": false
            },
            "target": {
                "remove_sound_tag": true,
                "target_field": "Chinese",
                "text_and_sound_tag": false
            },
            "text_processing": {
                "html_to_text_line": true,
                "ignore_case": false,
                "run_replace_rules_after": true,
                "ssml_convert_characters": true,
                "strip_brackets": false,
                "strip_cloze": false,
                "text_replacement_rules": []
            },
            "uuid": "79b2715e-9871-4b4f-9a5b-8bd5ac89d689",
            "voice_selection": {
                "voice_list": [
                    {
                        "options": {},
                        "voice": {
                            "gender": "Female",
                            "language": "zh_CN",
                            "name": null,
                            "service": "Forvo",
                            "voice_key": {
                                "country_code": "CHN",
                                "gender": "f",
                                "language_code": "zh"
                            }
                        }
                    },
                    {
                        "options": {},
                        "voice": {
                            "gender": "Female",
                            "language": "zh_CN",
                            "name": "Charlotte (Multilingual v2)",
                            "service": "ElevenLabs",
                            "voice_key": {
                                "language": "zh_CN",
                                "model_id": "eleven_multilingual_v2",
                                "voice_id": "XB0fDUnXU5powFXDhCwa"
                            }
                        }
                    }
                ],
                "voice_selection_mode": "priority"
            }
        },
        "a82dec0d-f140-42f1-b635-89ff1dad4262": {
            "name": "Chinese Random",
            "source": {
                "mode": "simple",
                "source_field": "Chinese",
                "source_template": null,
                "template_format_version": "v1",
                "use_selection": false
            },
            "target": {
                "remove_sound_tag": true,
                "target_field": "Chinese",
                "text_and_sound_tag": false
            },
            "text_processing": {
                "html_to_text_line": true,
                "ignore_case": false,
                "run_replace_rules_after": true,
                "ssml_convert_characters": true,
                "strip_brackets": false,
                "strip_cloze": false,
                "text_replacement_rules": []
            },
            "uuid": "a82dec0d-f140-42f1-b635-89ff1dad4262",
            "voice_selection": {
                "voice_list": [
                    {
                        "options": {},
                        "voice": {
                            "gender": "Female",
                            "language": "zh_CN",
                            "name": "Xiaochen 晓辰 (Neural)",
                            "service": "Azure",
                            "voice_key": {
                                "name": "Microsoft Server Speech Text to Speech Voice (zh-CN, XiaochenNeural)"
                            }
                        },
                        "weight": 1
                    },
                    {
                        "options": {},
                        "voice": {
                            "gender": "Male",
                            "language": "zh_CN",
                            "name": "Yunye 云野 (Neural)",
                            "service": "Azure",
                            "voice_key": {
                                "name": "Microsoft Server Speech Text to Speech Voice (zh-CN, YunyeNeural)"
                            }
                        },
                        "weight": 1
                    }
                ],
                "voice_selection_mode": "random"
            }
        }
    },
    "realtime_config": {
        "realtime_0": {
            "back": {
                "side_enabled": true,
                "source": {
                    "field_name": "English",
                    "field_type": "Regular",
                    "mode": "AnkiTTSTag"
                },
                "text_processing": {
                    "html_to_text_line": true,
                    "ignore_case": false,
                    "run_replace_rules_after": true,
                    "ssml_convert_characters": true,
                    "strip_brackets": false,
                    "strip_cloze": false,
                    "text_replacement_rules": []
                },
                "voice_selection": {
                    "voice": {
                        "options": {},
                        "voice": {
                            "gender": "Female",
                            "language": "en_AU",
                            "name": "en-AU-Neural2-A",
                            "service": "Google",
                            "voice_key": {
                                "language_code": "en-AU",
                                "name": "en-AU-Neural2-A",
                                "ssml_gender": "FEMALE"
                            }
                        }
                    },
                    "voice_selection_mode": "single"
                }
            },
            "front": {
                "side_enabled": false
            }
        }
    },
    "unique_id": "uuid:7a544af5402f"
}
"""
        config_rev_2 = json.loads(config_rev_2_json_str)



        config_rev_3_json_str = """
{
    "batch_config": {},
    "config_schema": 4,
    "configuration": {
        "hypertts_pro_api_key": "api_key_1",
        "service_config": {},
        "service_enabled": {},
        "use_vocabai_api": true,
        "vocabai_api_url_override": null
    },
    "preferences": {},
    "presets": {
        "1f8ae532-c1e0-4467-8220-9394f523ff17": {
            "name": "Chinese Single Voice",
            "source": {
                "mode": "simple",
                "source_field": "Chinese",
                "source_template": null,
                "template_format_version": "v1",
                "use_selection": false
            },
            "target": {
                "remove_sound_tag": true,
                "target_field": "Chinese",
                "text_and_sound_tag": false
            },
            "text_processing": {
                "html_to_text_line": true,
                "ignore_case": false,
                "run_replace_rules_after": true,
                "ssml_convert_characters": true,
                "strip_brackets": false,
                "strip_cloze": false,
                "text_replacement_rules": []
            },
            "uuid": "1f8ae532-c1e0-4467-8220-9394f523ff17",
            "voice_selection": {
                "voice": {
                    "options": {},
                    "voice_id": {
                        "service": "Azure",
                        "voice_key": {
                            "name": "Microsoft Server Speech Text to Speech Voice (zh-CN, XiaoyouNeural)"
                        }
                    }
                },
                "voice_selection_mode": "single"
            }
        },
        "79b2715e-9871-4b4f-9a5b-8bd5ac89d689": {
            "name": "Chinese Priority",
            "source": {
                "mode": "simple",
                "source_field": "Chinese",
                "source_template": null,
                "template_format_version": "v1",
                "use_selection": false
            },
            "target": {
                "remove_sound_tag": true,
                "target_field": "Chinese",
                "text_and_sound_tag": false
            },
            "text_processing": {
                "html_to_text_line": true,
                "ignore_case": false,
                "run_replace_rules_after": true,
                "ssml_convert_characters": true,
                "strip_brackets": false,
                "strip_cloze": false,
                "text_replacement_rules": []
            },
            "uuid": "79b2715e-9871-4b4f-9a5b-8bd5ac89d689",
            "voice_selection": {
                "voice_list": [
                    {
                        "options": {},
                        "voice_id": {
                            "service": "Forvo",
                            "voice_key": {
                                "country_code": "CHN",
                                "gender": "f",
                                "language_code": "zh"
                            }
                        }
                    },
                    {
                        "options": {},
                        "voice_id": {
                            "service": "ElevenLabs",
                            "voice_key": {
                                "model_id": "eleven_multilingual_v2",
                                "voice_id": "XB0fDUnXU5powFXDhCwa"
                            }
                        }
                    }
                ],
                "voice_selection_mode": "priority"
            }
        },
        "a82dec0d-f140-42f1-b635-89ff1dad4262": {
            "name": "Chinese Random",
            "source": {
                "mode": "simple",
                "source_field": "Chinese",
                "source_template": null,
                "template_format_version": "v1",
                "use_selection": false
            },
            "target": {
                "remove_sound_tag": true,
                "target_field": "Chinese",
                "text_and_sound_tag": false
            },
            "text_processing": {
                "html_to_text_line": true,
                "ignore_case": false,
                "run_replace_rules_after": true,
                "ssml_convert_characters": true,
                "strip_brackets": false,
                "strip_cloze": false,
                "text_replacement_rules": []
            },
            "uuid": "a82dec0d-f140-42f1-b635-89ff1dad4262",
            "voice_selection": {
                "voice_list": [
                    {
                        "options": {},
                        "voice_id": {
                            "service": "Azure",
                            "voice_key": {
                                "name": "Microsoft Server Speech Text to Speech Voice (zh-CN, XiaochenNeural)"
                            }
                        },
                        "weight": 1
                    },
                    {
                        "options": {},
                        "voice_id": {
                            "service": "Azure",
                            "voice_key": {
                                "name": "Microsoft Server Speech Text to Speech Voice (zh-CN, YunyeNeural)"
                            }
                        },
                        "weight": 1
                    }
                ],
                "voice_selection_mode": "random"
            }
        }
    },
    "realtime_config": {
        "realtime_0": {
            "back": {
                "side_enabled": true,
                "source": {
                    "field_name": "English",
                    "field_type": "Regular",
                    "mode": "AnkiTTSTag"
                },
                "text_processing": {
                    "html_to_text_line": true,
                    "ignore_case": false,
                    "run_replace_rules_after": true,
                    "ssml_convert_characters": true,
                    "strip_brackets": false,
                    "strip_cloze": false,
                    "text_replacement_rules": []
                },
                "voice_selection": {
                    "voice": {
                        "options": {},
                        "voice_id": {
                            "service": "Google",
                            "voice_key": {
                                "language_code": "en-AU",
                                "name": "en-AU-Neural2-A",
                                "ssml_gender": "FEMALE"
                            }
                        }
                    },
                    "voice_selection_mode": "single"
                }
            },
            "front": {
                "side_enabled": false
            }
        }
    }
}
"""
        expected_config_rev_3 = json.loads(config_rev_3_json_str)
        # pprint.pprint(expected_config_rev_3)

        self.maxDiff = None
        updated_config = config_models.migrate_configuration(anki_utils, config_rev_2)
        self.assertEqual(updated_config['config_schema'], 4)
        self.assertEqual(expected_config_rev_3, updated_config)

    def test_migration_2_to_3_b(self):
        anki_utils = testing_utils.MockAnkiUtils({})
        config_rev_2_json_str = """
{
    "batch_config": {},
    "config_schema": 2,
    "configuration": {
        "hypertts_pro_api_key": "api_key_1",
        "service_config": {},
        "service_enabled": {},
        "use_vocabai_api": false,
        "vocabai_api_url_override": null
    },
    "preferences": {},
    "presets": {},
    "realtime_config": {
        "realtime_0": {
            "back": {
                "side_enabled": true,
                "source": {
                    "field_name": "English",
                    "field_type": "Regular",
                    "mode": "AnkiTTSTag"
                },
                "text_processing": {
                    "html_to_text_line": true,
                    "ignore_case": false,
                    "run_replace_rules_after": true,
                    "ssml_convert_characters": true,
                    "strip_brackets": false,
                    "strip_cloze": false,
                    "text_replacement_rules": []
                },
                "voice_selection": {
                    "voice_list": [
                        {
                            "options": {},
                            "voice": {
                                "gender": "Female",
                                "language": "en_US",
                                "name": "Grace (Turbo v2)",
                                "service": "ElevenLabs",
                                "voice_key": {
                                    "language": "en_US",
                                    "model_id": "eleven_turbo_v2",
                                    "voice_id": "oWAxZDx7w5VEj9dCyTzz"
                                }
                            }
                        },
                        {
                            "options": {},
                            "voice": {
                                "gender": "Female",
                                "language": "en_US",
                                "name": "Matilda (Multilingual v2)",
                                "service": "ElevenLabs",
                                "voice_key": {
                                    "language": "en_US",
                                    "model_id": "eleven_multilingual_v2",
                                    "voice_id": "XrExE9yKIg1WjnnlVkGX"
                                }
                            }
                        }
                    ],
                    "voice_selection_mode": "priority"
                }
            },
            "front": {
                "side_enabled": true,
                "source": {
                    "field_name": "English",
                    "field_type": "Regular",
                    "mode": "AnkiTTSTag"
                },
                "text_processing": {
                    "html_to_text_line": true,
                    "ignore_case": false,
                    "run_replace_rules_after": true,
                    "ssml_convert_characters": true,
                    "strip_brackets": false,
                    "strip_cloze": false,
                    "text_replacement_rules": []
                },
                "voice_selection": {
                    "voice_list": [
                        {
                            "options": {},
                            "voice": {
                                "gender": "Female",
                                "language": "en_AU",
                                "name": "Natasha (Neural)",
                                "service": "Azure",
                                "voice_key": {
                                    "name": "Microsoft Server Speech Text to Speech Voice (en-AU, NatashaNeural)"
                                }
                            },
                            "weight": 1
                        },
                        {
                            "options": {},
                            "voice": {
                                "gender": "Female",
                                "language": "en_AU",
                                "name": "Tina (Neural)",
                                "service": "Azure",
                                "voice_key": {
                                    "name": "Microsoft Server Speech Text to Speech Voice (en-AU, TinaNeural)"
                                }
                            },
                            "weight": 1
                        }
                    ],
                    "voice_selection_mode": "random"
                }
            }
        }
    },
    "unique_id": "uuid:089db83fbb66"
}
"""
        config_rev_2 = json.loads(config_rev_2_json_str)



        config_rev_3_json_str = """
{
    "batch_config": {},
    "config_schema": 4,
    "configuration": {
        "hypertts_pro_api_key": "api_key_1",
        "service_config": {},
        "service_enabled": {},
        "use_vocabai_api": false,
        "vocabai_api_url_override": null
    },
    "preferences": {},
    "presets": {},
    "realtime_config": {
        "realtime_0": {
            "back": {
                "side_enabled": true,
                "source": {
                    "field_name": "English",
                    "field_type": "Regular",
                    "mode": "AnkiTTSTag"
                },
                "text_processing": {
                    "html_to_text_line": true,
                    "ignore_case": false,
                    "run_replace_rules_after": true,
                    "ssml_convert_characters": true,
                    "strip_brackets": false,
                    "strip_cloze": false,
                    "text_replacement_rules": []
                },
                "voice_selection": {
                    "voice_list": [
                        {
                            "options": {},
                            "voice_id": {
                                "service": "ElevenLabs",
                                "voice_key": {
                                    "model_id": "eleven_turbo_v2",
                                    "voice_id": "oWAxZDx7w5VEj9dCyTzz"
                                }
                            }
                        },
                        {
                            "options": {},
                            "voice_id": {
                                "service": "ElevenLabs",
                                "voice_key": {
                                    "model_id": "eleven_multilingual_v2",
                                    "voice_id": "XrExE9yKIg1WjnnlVkGX"
                                }
                            }
                        }
                    ],
                    "voice_selection_mode": "priority"
                }
            },
            "front": {
                "side_enabled": true,
                "source": {
                    "field_name": "English",
                    "field_type": "Regular",
                    "mode": "AnkiTTSTag"
                },
                "text_processing": {
                    "html_to_text_line": true,
                    "ignore_case": false,
                    "run_replace_rules_after": true,
                    "ssml_convert_characters": true,
                    "strip_brackets": false,
                    "strip_cloze": false,
                    "text_replacement_rules": []
                },
                "voice_selection": {
                    "voice_list": [
                        {
                            "options": {},
                            "voice_id": {
                                "service": "Azure",
                                "voice_key": {
                                    "name": "Microsoft Server Speech Text to Speech Voice (en-AU, NatashaNeural)"
                                }
                            },
                            "weight": 1
                        },
                        {
                            "options": {},
                            "voice_id": {
                                "service": "Azure",
                                "voice_key": {
                                    "name": "Microsoft Server Speech Text to Speech Voice (en-AU, TinaNeural)"
                                }
                            },
                            "weight": 1
                        }
                    ],
                    "voice_selection_mode": "random"
                }
            }
        }
    }
}
"""
        expected_config_rev_3 = json.loads(config_rev_3_json_str)
        # pprint.pprint(expected_config_rev_3)

        self.maxDiff = None
        updated_config = config_models.migrate_configuration(anki_utils, config_rev_2)
        self.assertEqual(updated_config['config_schema'], 4)
        self.assertEqual(expected_config_rev_3, updated_config)

    def test_rule_applies(self):
        rule = config_models.MappingRule(preset_id='preset_1', 
            rule_type=constants.MappingRuleType.DeckNoteType, 
            model_id=42,
            deck_id=52,
            enabled=True, 
            automatic=True)
        # different note
        deck_note_type = config_models.DeckNoteType(model_id=142, deck_id=52)
        self.assertFalse(rule.rule_applies(deck_note_type, True))

        # different deck
        deck_note_type = config_models.DeckNoteType(model_id=42, deck_id=53)
        self.assertFalse(rule.rule_applies(deck_note_type, True))

        # same deck, same note
        deck_note_type = config_models.DeckNoteType(model_id=42, deck_id=52)
        self.assertTrue(rule.rule_applies(deck_note_type, True))

        # rule is not enabled
        rule.enabled = False
        self.assertFalse(rule.rule_applies(deck_note_type, True))

        # rule is not automatic
        rule.enabled = True
        rule.automatic = False
        self.assertFalse(rule.rule_applies(deck_note_type, True))

        # however when we do a manual run, apply the rule
        self.assertTrue(rule.rule_applies(deck_note_type, False))

    def test_iterate_applicable_rules(self):
        mapping_rules = config_models.PresetMappingRules()

        rule_1 = config_models.MappingRule(preset_id='preset_1', 
            rule_type=constants.MappingRuleType.DeckNoteType, 
            model_id=42,
            deck_id=52,
            enabled=True, 
            automatic=True)
        mapping_rules.rules.append(rule_1)

        rule_4 = config_models.MappingRule(preset_id='preset_4', 
            rule_type=constants.MappingRuleType.DeckNoteType, 
            model_id=1042,
            deck_id=1053,
            enabled=True, 
            automatic=True)
        mapping_rules.rules.append(rule_4)

        rule_2 = config_models.MappingRule(preset_id='preset_2', 
            rule_type=constants.MappingRuleType.DeckNoteType, 
            model_id=42,
            deck_id=52,
            enabled=True, 
            automatic=True)
        mapping_rules.rules.append(rule_2)

        deck_note_type = config_models.DeckNoteType(model_id=42, deck_id=52)

        applicable_rules = list(mapping_rules.iterate_applicable_rules(deck_note_type, True))
        pprint.pprint(applicable_rules)
        self.assertEqual(len(applicable_rules), 2)

        assert applicable_rules[0] == (0, 0, rule_1)
        assert applicable_rules[1] == (2, 1, rule_2)


    def test_iterate_related_rules(self):
        mapping_rules = config_models.PresetMappingRules()

        rule_1 = config_models.MappingRule(preset_id='preset_1', 
            rule_type=constants.MappingRuleType.DeckNoteType, 
            model_id=42,
            deck_id=52,
            enabled=False, 
            automatic=True)
        mapping_rules.rules.append(rule_1)

        rule_4 = config_models.MappingRule(preset_id='preset_4', 
            rule_type=constants.MappingRuleType.DeckNoteType, 
            model_id=1042,
            deck_id=1053,
            enabled=True, 
            automatic=True)
        mapping_rules.rules.append(rule_4)

        rule_2 = config_models.MappingRule(preset_id='preset_2', 
            rule_type=constants.MappingRuleType.DeckNoteType, 
            model_id=42,
            deck_id=52,
            enabled=False, 
            automatic=True)
        mapping_rules.rules.append(rule_2)

        rule_5 = config_models.MappingRule(preset_id='preset_5', 
            rule_type=constants.MappingRuleType.NoteType,
            model_id=42,
            deck_id=152,
            enabled=False, 
            automatic=True)
        mapping_rules.rules.append(rule_5)

        # this rule shouldn't be included, because it's DeckNoteType, for another deck
        rule_6 = config_models.MappingRule(preset_id='preset_6', 
            rule_type=constants.MappingRuleType.DeckNoteType,
            model_id=42,
            deck_id=252,
            enabled=False, 
            automatic=True)
        mapping_rules.rules.append(rule_6)

        deck_note_type = config_models.DeckNoteType(model_id=42, deck_id=52)

        applicable_rules = list(mapping_rules.iterate_related_rules(deck_note_type))
        pprint.pprint(applicable_rules)
        self.assertEqual(len(applicable_rules), 3)

        assert applicable_rules[0] == (0, 0, rule_1)
        assert applicable_rules[1] == (2, 1, rule_2)
        assert applicable_rules[2] == (3, 2, rule_5)

    def test_batch_source(self):
        # serialization tests
        # ===================

        source = config_models.BatchSource(
            mode=constants.BatchMode.simple,
            source_field='Chinese')
        self.assertEqual(config_models.serialize_batchsource(source), {
            'mode': 'simple',
            'source_field': 'Chinese',
            'source_template': None,
            'template_format_version': 'v1',
            'use_selection': False
        })

        source = config_models.BatchSource(
            mode=constants.BatchMode.template,
            source_template='{Field1}')
        self.assertEqual(config_models.serialize_batchsource(source), {
            'mode': 'template',
            'source_field': None,
            'source_template': '{Field1}',
            'template_format_version': 'v1',
            'use_selection': False
        })

        # deserialization tests
        # =====================

        source = config_models.deserialize_batchsource({
            'mode': 'simple',
            'source_field': 'Chinese',
        })
        self.assertEqual(source.mode, constants.BatchMode.simple)
        self.assertEqual(source.source_field, 'Chinese')

        source = config_models.deserialize_batchsource({
            'mode': 'template',
            'source_template': '{Field1}',
        })
        self.assertEqual(source.mode, constants.BatchMode.template)
        self.assertEqual(source.source_template, '{Field1}')
        self.assertEqual(source.template_format_version, constants.TemplateFormatVersion.v1)

        # validation
        # ==========
        source = config_models.BatchSource(
            mode=constants.BatchMode.simple,
            source_field='')
        self.assertRaises(errors.SourceFieldNotSet, source.validate)

        source = config_models.BatchSource(
            mode=constants.BatchMode.template,
            source_template='')
        self.assertRaises(errors.SourceTemplateNotSet, source.validate)

    def test_voice_id(self):
        voice_id_1 = voice.TtsVoiceId_v3(voice_key={'voice_id': 'a'}, service='ServiceA')
        voice_id_2 = voice.TtsVoiceId_v3(voice_key={'voice_id': 'a'}, service='ServiceA')

        self.assertEqual(voice_id_1, voice_id_2)
        self.assertEqual(hash(voice_id_1), hash(voice_id_2))

    def test_voice_string(self):
        # single language voice
        voice_1 = voice.TtsVoice_v3(
            name='Peppa',
            voice_key={'id': 'peppa'},
            options={},
            service='ServiceA',
            gender=constants.Gender.Female,
            audio_languages=[languages.AudioLanguage.en_GB],
            service_fee=constants.ServiceFee.paid
        )

        self.assertEqual(str(voice_1), 'English (UK), Female, Peppa (ServiceA)')

        voice_1 = voice.TtsVoice_v3(
            name='Peppa',
            voice_key={'id': 'peppa'},
            options={},
            service='ServiceA',
            gender=constants.Gender.Female,
            audio_languages=[languages.AudioLanguage.en_GB, languages.AudioLanguage.fr_FR],
            service_fee=constants.ServiceFee.paid
        )

        self.assertEqual(str(voice_1), 'Multilingual, Female, Peppa (ServiceA)')

    def test_voice_hash(self):
        # the hash should work whether the voice_key is a dict or str
        voice_id_1 = voice.TtsVoiceId_v3(
            voice_key={'id': 'peppa'},
            service='ServiceA',
        )
        voice_id_2 = voice.TtsVoiceId_v3(
            voice_key='peppa',
            service='ServiceA',
        )
        # should not throw an exception
        hash(voice_id_1)
        hash(voice_id_2)

        # try serializing
        self.assertEqual(voice.serialize_voice_id_v3(voice_id_1), {'service': 'ServiceA', 'voice_key': {'id': 'peppa'}})
        self.assertEqual(voice.serialize_voice_id_v3(voice_id_2), {'service': 'ServiceA', 'voice_key': 'peppa'})

        # try de-serializing
        deserialized_voice_id_1 = voice.deserialize_voice_id_v3({'service': 'ServiceA', 'voice_key': {'id': 'peppa'}})
        deserialized_voice_id_2 = voice.deserialize_voice_id_v3({'service': 'ServiceA', 'voice_key': 'peppa'})

        self.assertEqual(voice_id_1, deserialized_voice_id_1)
        self.assertEqual(voice_id_2, deserialized_voice_id_2)

        self.assertTrue(True)

    def test_default_presets(self):
        hypertts_instance: hypertts.HyperTTS = get_hypertts_instance()

        # build batch config
        # ------------------
        voice_list = hypertts_instance.service_manager.full_voice_list()
        voice_a_1 = [x for x in voice_list if x.name == 'voice_a_1'][0]
        voice_selection = config_models.VoiceSelectionSingle()
        voice_selection.set_voice(config_models.VoiceWithOptions(voice_a_1.voice_id, {}))

        batch_config = config_models.BatchConfig(hypertts_instance.anki_utils)
        batch_config.source = config_models.BatchSource(mode=constants.BatchMode.simple, source_field='Chinese')
        batch_config.target = config_models.BatchTarget('Sound', False, False)
        batch_config.voice_selection = voice_selection
        batch_config.text_processing = config_models.TextProcessing()

        uuid_1 = 'uuid_1'
        uuid_2 = 'uuid_2'
        uuid_3 = 'uuid_3'

        deck_note_type_1 = config_models.DeckNoteType(model_id=42, deck_id=52)
        deck_note_type_2 = config_models.DeckNoteType(model_id=42, deck_id=53)
        deck_note_type_3 = config_models.DeckNoteType(model_id=58, deck_id=54)

        # should be none by default
        self.assertEqual(hypertts_instance.get_default_preset_id(deck_note_type_1), None)
        # we also should have no preset mapping rules
        self.assertEqual(hypertts_instance.load_mapping_rules().rules, [])

        # save default preset
        batch_config.uuid = uuid_1
        batch_config.name = 'default for model_id 42, deck_id 52'
        hypertts_instance.save_default_preset(deck_note_type_1, batch_config)
        # now the default preset_id should be returned
        self.assertEqual(hypertts_instance.get_default_preset_id(deck_note_type_1), uuid_1)
        # we should have one mapping rule set
        mapping_rules: config_models.PresetMappingRules = hypertts_instance.load_mapping_rules()
        self.assertEqual(len(mapping_rules.rules), 1)
        rule: config_models.MappingRule = mapping_rules.rules[0]
        self.assertEqual(rule.preset_id, uuid_1)
        self.assertEqual(rule.model_id, 42)
        self.assertEqual(rule.deck_id, 52)

        # check other deck note types
        self.assertEqual(hypertts_instance.get_default_preset_id(deck_note_type_2), None)
        batch_config_2 = copy.copy(batch_config)
        batch_config_2.uuid = uuid_2
        batch_config_2.name = 'default for model_id 42, deck_id 53'
        hypertts_instance.save_default_preset(deck_note_type_2, batch_config_2)
        self.assertEqual(hypertts_instance.get_default_preset_id(deck_note_type_2), uuid_2)
        # we should have two mapping rules set
        mapping_rules: config_models.PresetMappingRules = hypertts_instance.load_mapping_rules()
        self.assertEqual(len(mapping_rules.rules), 2)

        # overwrite for uuid_1
        hypertts_instance.save_default_preset(deck_note_type_1, batch_config_2)
        self.assertEqual(hypertts_instance.get_default_preset_id(deck_note_type_1), uuid_2)
        # we should still have two mapping rules set
        mapping_rules: config_models.PresetMappingRules = hypertts_instance.load_mapping_rules()
        self.assertEqual(len(mapping_rules.rules), 2)

        # check uuid_3
        self.assertEqual(hypertts_instance.get_default_preset_id(deck_note_type_3), None)
        batch_config_3 = copy.copy(batch_config)
        batch_config_3.uuid = uuid_3
        batch_config_3.name = 'default for model_id 58, deck_id 54'
        hypertts_instance.save_default_preset(deck_note_type_3, batch_config_3)
        self.assertEqual(hypertts_instance.get_default_preset_id(deck_note_type_3), uuid_3)

        # now, we should have three in total
        mapping_rules: config_models.PresetMappingRules = hypertts_instance.load_mapping_rules()
        self.assertEqual(len(mapping_rules.rules), 3)        

        # load the preset
        preset = hypertts_instance.load_preset(hypertts_instance.get_default_preset_id(deck_note_type_3))
        self.assertEqual(preset.name, 'default for model_id 58, deck_id 54')





