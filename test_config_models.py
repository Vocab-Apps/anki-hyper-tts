import pprint
import logging
import unittest

import constants
import servicemanager
import testing_utils
import config_models
import hypertts

def get_service_manager():
    manager = servicemanager.ServiceManager(testing_utils.get_test_services_dir(), 'test_services', True)
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
        single.set_voice(config_models.VoiceWithOptions(voice_a_1, {'speed': 42}))

        expected_output = {
            'voice_selection_mode': 'single',
            'voice': {
                'voice': {
                    'gender': 'Male', 
                    'language': 'fr_FR', 
                    'name': 'voice_a_1', 
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
        random.add_voice(config_models.VoiceWithOptionsRandom(voice_a_1, {'speed': 43}))
        random.add_voice(config_models.VoiceWithOptionsRandom(voice_jane, {}))

        expected_output = {
            'voice_selection_mode': 'random',
            'voice_list': [
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
                    'weight': 1
                },
                {
                    'voice': {
                        'gender': 'Male', 
                        'language': 'ja_JP', 
                        'name': 'jane', 
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
        priority.add_voice(config_models.VoiceWithOptionsPriority(voice_a_1, {'speed': 43}))
        priority.add_voice(config_models.VoiceWithOptionsPriority(voice_a_1, {'speed': 84}))
        priority.add_voice(config_models.VoiceWithOptionsPriority(voice_jane, {}))

        expected_output = {
            'voice_selection_mode': 'priority',
            'voice_list': [
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
                {
                    'voice': {
                        'gender': 'Male', 
                        'language': 'fr_FR', 
                        'name': 'voice_a_1', 
                        'service': 'ServiceA',
                        'voice_key': {'name': 'voice_1'}
                    },
                    'options': {
                        'speed': 84
                    },
                },            
                {
                    'voice': {
                        'gender': 'Male', 
                        'language': 'ja_JP', 
                        'name': 'jane', 
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
                {
                    'voice': {
                        'gender': 'Male', 
                        'language': 'ja_JP', 
                        'name': 'jane', 
                        'service': 'ServiceB',
                        'voice_key': {'voice_id': 'jane'}
                    },
                    'options': {
                    },
                },
                {
                    'voice': {
                        'gender': 'Male', 
                        'language': 'fr_FR', 
                        'name': 'voice_a_1', 
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
                    'voice': {
                        'gender': 'Male', 
                        'language': 'ja_JP', 
                        'name': 'jane', 
                        'service': 'ServiceB',
                        'voice_key': {'voice_id': 'jane'}
                    },
                    'options': {
                    },
                },
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
                {
                    'voice': {
                        'gender': 'Male', 
                        'language': 'fr_FR', 
                        'name': 'voice_a_1', 
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

    def test_batch_config(self):
        hypertts_instance = get_hypertts_instance()
        voice_list = hypertts_instance.service_manager.full_voice_list()

        voice_a_1 = [x for x in voice_list if x.name == 'voice_a_1'][0]
        voice_selection = config_models.VoiceSelectionSingle()
        voice_selection.set_voice(config_models.VoiceWithOptions(voice_a_1, {'speed': 43}))

        batch_config = config_models.BatchConfig()
        source = config_models.BatchSourceSimple('Chinese')
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
                'run_replace_rules_after': True,
                'ssml_convert_characters': True,            
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

        assert str(batch_config) == """<b>Source:</b> Chinese
<b>Target:</b> Sound
<b>Voice Selection:</b> Single
"""

    def test_batch_config_target(self):
        # serialize tests for Target
        hypertts_instance = get_hypertts_instance()
        voice_list = hypertts_instance.service_manager.full_voice_list()

        voice_a_1 = [x for x in voice_list if x.name == 'voice_a_1'][0]
        voice_selection = config_models.VoiceSelectionSingle()
        voice_selection.set_voice(config_models.VoiceWithOptions(voice_a_1, {'speed': 43}))
        batch_config = config_models.BatchConfig()
        source = config_models.BatchSourceSimple('Chinese')
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
                    'remove_sound_tag': remove_sound_tag
                }
                assert batch_config.serialize()['target'] == expected_output

                # try deserializing
                deserialized_batch_config = hypertts_instance.deserialize_batch_config(batch_config.serialize())
                assert deserialized_batch_config.serialize()['target'] == expected_output


    def test_text_processing(self):
        
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
            'run_replace_rules_after': True,
            'ssml_convert_characters': True,
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
            'run_replace_rules_after': True,
            'ssml_convert_characters': True,        
            'text_replacement_rules': [
                {
                    'rule_type': 'Regex',
                    'source': 'c',
                    'target': 'd'
                },            
            ]
        }
        assert text_processing.serialize() == expected_output

    def test_configuration(self):
        hypertts_instance = get_hypertts_instance()

        configuration = config_models.Configuration()
        configuration.hypertts_pro_api_key = '123456'
        configuration.set_service_enabled('ServiceA', True)
        configuration.set_service_enabled('ServiceB', False)
        configuration.set_service_configuration_key('ServiceA', 'region', 'europe')

        expected_output = {
            'hypertts_pro_api_key': '123456',
            'service_enabled': {
                'ServiceA': True,
                'ServiceB': False
            },
            'service_config': {
                'ServiceA': {
                    'region': 'europe'
                },
            }
        }

        assert configuration.serialize() == expected_output

        deserialized_configuration = hypertts_instance.deserialize_configuration(configuration.serialize())
        assert deserialized_configuration.get_service_configuration_key('ServiceA', 'region') == 'europe'
        assert deserialized_configuration.get_service_enabled('ServiceA') == True
        assert deserialized_configuration.get_service_enabled('ServiceB') == False

        assert configuration.serialize() == deserialized_configuration.serialize()


        # some services' enabled flag not defined
        configuration = config_models.Configuration()
        configuration.hypertts_pro_api_key = '123456'
        configuration.set_service_enabled('ServiceA', True)

        assert configuration.get_service_enabled('ServiceA') == True
        assert configuration.get_service_enabled('ServiceB') == None

        deserialized_configuration = hypertts_instance.deserialize_configuration(configuration.serialize())

        assert deserialized_configuration.get_service_enabled('ServiceA') == True
        assert deserialized_configuration.get_service_enabled('ServiceB') == None

        assert deserialized_configuration.get_service_configuration_key('ServiceA', 'region') == None


    def test_batch_config_advanced_template(self):
        hypertts_instance = get_hypertts_instance()
        voice_list = hypertts_instance.service_manager.full_voice_list()

        voice_a_1 = [x for x in voice_list if x.name == 'voice_a_1'][0]
        voice_selection = config_models.VoiceSelectionSingle()
        voice_selection.set_voice(config_models.VoiceWithOptions(voice_a_1, {'speed': 43}))

        source_template = """result = 'yoyo'"""

        batch_config = config_models.BatchConfig()
        source = config_models.BatchSourceTemplate(constants.BatchMode.advanced_template, 
            source_template, constants.TemplateFormatVersion.v1)
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
            'source': {
                'mode': 'advanced_template',
                'template_format_version': 'v1',
                'source_template': """result = 'yoyo'""",
            },
            'target': {
                'target_field': 'Audio',
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
                'run_replace_rules_after': True,
                'ssml_convert_characters': True,            
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
        voice_selection.set_voice(config_models.VoiceWithOptions(voice_a_1, {'speed': 43}))

        batch_config = config_models.BatchConfig()
        source = config_models.BatchSourceSimple('')
        target = config_models.BatchTarget('Sound', False, False)
        text_processing = config_models.TextProcessing()

        batch_config.set_source(source)
        batch_config.set_target(target)
        batch_config.set_voice_selection(voice_selection)
        batch_config.text_processing = text_processing

        # assert False