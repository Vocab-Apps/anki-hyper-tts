import sys
import sys
import os
import pprint
import unittest

# add external modules to sys.path
addon_dir = os.path.dirname(os.path.realpath(__file__))
external_dir = os.path.join(addon_dir, 'external')
sys.path.insert(0, external_dir)

import hypertts
import constants
import servicemanager
import testing_utils
import config_models
import errors

logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_base)
logger = logging_utils.get_test_child_logger(__name__)

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

        self.assertEquals(batch_config_deserialized.source.source_field, 'Chinese')
        self.assertEquals(batch_config_deserialized.source.mode, constants.BatchMode.simple)   


    def test_batch_config_target(self):
        # serialize tests for Target
        hypertts_instance = get_hypertts_instance()
        voice_list = hypertts_instance.service_manager.full_voice_list()

        voice_a_1 = [x for x in voice_list if x.name == 'voice_a_1'][0]
        voice_selection = config_models.VoiceSelectionSingle()
        voice_selection.set_voice(config_models.VoiceWithOptions(voice_a_1, {'speed': 43}))
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
                    'remove_sound_tag': remove_sound_tag
                }
                assert batch_config.serialize()['target'] == expected_output

                # try deserializing
                deserialized_batch_config = hypertts_instance.deserialize_batch_config(batch_config.serialize())
                assert deserialized_batch_config.serialize()['target'] == expected_output


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
        voice_selection.set_voice(config_models.VoiceWithOptions(voice_a_1, {'speed': 43}))

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
        voice_selection.set_voice(config_models.VoiceWithOptions(voice_a_1, {'speed': 43}))

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
                'realtime_tts_errors_dialog_type': 'Dialog'
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
                'realtime_tts_errors_dialog_type': 'Dialog'
            }                           
        })

        preferences_config = {
            'keyboard_shortcuts': {
                'shortcut_editor_add_audio': 'Ctrl+T',
                'shortcut_editor_preview_audio': None
            }
        }
        preferences = hypertts_instance.deserialize_preferences(preferences_config)
        self.assertEquals(preferences.keyboard_shortcuts.shortcut_editor_add_audio, 'Ctrl+T')
        self.assertEquals(preferences.keyboard_shortcuts.shortcut_editor_preview_audio, None)
        self.assertEqual(preferences.error_handling.realtime_tts_errors_dialog_type, constants.ErrorDialogType.Dialog)
        self.assertEqual(config_models.serialize_preferences(preferences), 
        {
            'keyboard_shortcuts': {
                'shortcut_editor_add_audio': 'Ctrl+T',
                'shortcut_editor_preview_audio': None
            },
            'error_handling': {
                'realtime_tts_errors_dialog_type': 'Dialog'
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
                    'automatic': False
                }
            ]
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
                    'automatic': False
                }
            ]
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
                    'automatic': False
                }
            ]
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
        self.assertEqual(updated_config['config_schema'], 2)


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
        self.assertEqual(updated_config['config_schema'], 2)
        expected_preset_1_uuid = 'uuid_0'
        self.assertIn(expected_preset_1_uuid, updated_config['presets'])
        self.assertEqual(updated_config['presets'][expected_preset_1_uuid]['name'], 'preset_1')
        self.assertEqual(updated_config['presets'][expected_preset_1_uuid]['uuid'], expected_preset_1_uuid)

        # try to run migration again, nothing should happen
        updated_config = config_models.migrate_configuration(anki_utils, updated_config)
        self.assertIn(expected_preset_1_uuid, updated_config['presets'])
        self.assertEqual(updated_config['presets'][expected_preset_1_uuid]['name'], 'preset_1')
        self.assertEqual(updated_config['presets'][expected_preset_1_uuid]['uuid'], expected_preset_1_uuid)        


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