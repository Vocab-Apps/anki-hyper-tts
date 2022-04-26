
import unittest

import errors
import testing_utils
import config_models
import constants

class HyperTTSTests(unittest.TestCase):

    def test_expand_advanced_template(self):

        field_dict = {
            'French': 'Bonjour',
            'English': 'Hello'
        }
        field_array = ['French', 'English']
        note = testing_utils.MockNote(42, 43, field_dict, field_array, None)

        source_template = """
french = template_fields['French']
english = template_fields['English']
result = f"{french} {english}"
"""
        config_gen = testing_utils.TestConfigGenerator()
        hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

        self.assertEqual(hypertts_instance.expand_advanced_template(note, source_template), 'Bonjour Hello')

        # test missing result variable
        # ============================

        source_template = """
french = template_fields['French']
english = template_fields['English']
"""
        self.assertRaises(errors.NoResultVar, hypertts_instance.expand_advanced_template, note, source_template)

        # test syntax error
        # =================

        source_template = """
yoyo
"""
        self.assertRaises(errors.TemplateExpansionError, hypertts_instance.expand_advanced_template, note, source_template)


    def test_expand_simple_template(self):
        field_dict = {
            'French': 'Bonjour',
            'English': 'Hello'
        }
        field_array = ['French', 'English']
        note = testing_utils.MockNote(42, 43, field_dict, field_array, None)

        config_gen = testing_utils.TestConfigGenerator()
        hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

        source_template = """{French}"""
        self.assertEqual(hypertts_instance.expand_simple_template(note, source_template), 'Bonjour')
        source_template = """{French} {English}"""
        self.assertEqual(hypertts_instance.expand_simple_template(note, source_template), 'Bonjour Hello')

        source_template = """{French} {English"""
        self.assertRaises(errors.TemplateExpansionError, hypertts_instance.expand_simple_template, note, source_template)



    def test_get_audio_file_errors(self):
        # error situations

        # random mode with no voices
        # ==========================
        config_gen = testing_utils.TestConfigGenerator()
        hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

        random = config_models.VoiceSelectionRandom()        
        self.assertRaises(errors.NoVoicesAdded, hypertts_instance.get_audio_file, 'yoyo', random, None)

        # priority mode with no voices
        # ============================
        config_gen = testing_utils.TestConfigGenerator()
        hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

        priority = config_models.VoiceSelectionPriority()
        self.assertRaises(errors.NoVoicesAdded, hypertts_instance.get_audio_file, 'yoyo', priority, None)

    def test_process_hypertts_tag(self):
        config_gen = testing_utils.TestConfigGenerator()
        hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

        extra_args_array = [f'{constants.TTS_TAG_HYPERTTS_PRESET}=yoyo42']

        self.assertEqual(hypertts_instance.extract_hypertts_preset(extra_args_array), 'yoyo42')

        extra_args_array = []
        self.assertRaises(errors.TTSTagProcessingError, hypertts_instance.extract_hypertts_preset, extra_args_array)

        extra_args_array = ['bla', 'yo']
        self.assertRaises(errors.TTSTagProcessingError, hypertts_instance.extract_hypertts_preset, extra_args_array)


    def test_keep_only_sound_tags(self):
        config_gen = testing_utils.TestConfigGenerator()
        hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

        field_value = 'hello [sound:yoyo1.mp3] [sound:test2.mp3] yoyo'
        output = hypertts_instance.keep_only_sound_tags(field_value)
        self.assertEqual(output, '[sound:yoyo1.mp3] [sound:test2.mp3]')

    def test_get_editor_default_batch_name(self):
        config_gen = testing_utils.TestConfigGenerator()
        hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

        # by default, it's none
        self.assertEqual(hypertts_instance.get_editor_default_batch_name(), constants.BATCH_CONFIG_NEW)

        # save a batch config
        hypertts_instance.latest_saved_batch_name = 'new_batch_1'
        self.assertEqual(hypertts_instance.get_editor_default_batch_name(), 'new_batch_1')

        # now, use a batch config from the editor
        hypertts_instance.set_editor_last_used_batch_name('used_batch_2')
        self.assertEqual(hypertts_instance.get_editor_default_batch_name(), 'used_batch_2')

        # save a batch config
        hypertts_instance.latest_saved_batch_name = 'new_batch_3'
        self.assertEqual(hypertts_instance.get_editor_default_batch_name(), 'new_batch_3')

        # now, use a batch config from the editor
        hypertts_instance.set_editor_last_used_batch_name('used_batch_4')
        self.assertEqual(hypertts_instance.get_editor_default_batch_name(), 'used_batch_4')        

    def test_save_configuration(self):
        config_gen = testing_utils.TestConfigGenerator()
        hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

        # save a Configuration config model
        config_model = config_models.Configuration()
        config_model.set_service_enabled('ServiceA', True)
        config_model.set_service_enabled('ServiceB', False)
        config_model.set_service_enabled('ServiceNonExistent', False)
        config_model.set_service_configuration_key('ServiceA', 'api_key', 'mykey')
        config_model.set_service_configuration_key('ServiceNonExistent', 'api_key', 'nonexistent_key')

        hypertts_instance.save_configuration(config_model)


        expected_saved_config = {
            'hypertts_pro_api_key': None,
            'service_config': {
                'ServiceA': {'api_key': 'mykey'}
            },
            'service_enabled': {
                'ServiceA': True,
                'ServiceB': False
            }
        }

        self.assertEqual(hypertts_instance.anki_utils.written_config['configuration'], expected_saved_config)

    def test_play_sound_empty(self):
        config_gen = testing_utils.TestConfigGenerator()
        hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')        

        source_text = ''
        self.assertRaises(errors.SourceTextEmpty, hypertts_instance.play_sound, source_text, None, None)
        source_text = None
        self.assertRaises(errors.SourceTextEmpty, hypertts_instance.play_sound, source_text, None, None)


