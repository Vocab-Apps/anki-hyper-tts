import sys
import os
import unittest
import pytest
import json
import pprint

from test_utils import testing_utils
from test_utils import gui_testing_utils

from hypertts_addon import errors
from hypertts_addon import config_models
from hypertts_addon import constants
from hypertts_addon import cloudlanguagetools

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
            'use_vocabai_api': False, 
            'vocabai_api_url_override': None,            
            'service_config': {
                'ServiceA': {'api_key': 'mykey'}
            },
            'service_enabled': {
                'ServiceA': True,
                'ServiceB': False
            },
            'user_uuid': None,
            'user_choice_easy_advanced': False,
            'display_introduction_message': False
        }

        self.assertEqual(hypertts_instance.anki_utils.written_config['configuration'], expected_saved_config)

    def test_play_sound_empty(self):
        config_gen = testing_utils.TestConfigGenerator()
        hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')        

        source_text = ''
        self.assertRaises(errors.SourceTextEmpty, hypertts_instance.play_sound, source_text, None, None)
        source_text = None
        self.assertRaises(errors.SourceTextEmpty, hypertts_instance.play_sound, source_text, None, None)


    def test_preview_all_mapping_rules_1(self):
        hypertts_instance, deck_note_type, editor_context = gui_testing_utils.get_editor_context()

        # create simple preset
        preset_id_1 = 'uuid_0'
        name = 'my preset 1'
        voice_name_1 = 'voice_a_1'
        testing_utils.create_simple_batch(hypertts_instance, preset_id=preset_id_1, name=name, voice_name=voice_name_1)
        preset_id_2 = 'uuid_1'
        name = 'my preset 2'
        voice_name_2 = 'voice_a_2'
        testing_utils.create_simple_batch(hypertts_instance, preset_id=preset_id_2, name=name, voice_name=voice_name_2)

        # add the preset rules
        preset_mapping_rules = config_models.PresetMappingRules()
        rule_1 = config_models.MappingRule(preset_id=preset_id_1,
                                           rule_type = constants.MappingRuleType.DeckNoteType,
                                           model_id = deck_note_type.model_id,
                                           enabled = True,
                                           automatic = False,
                                           deck_id = deck_note_type.deck_id)
        preset_mapping_rules.rules.append(rule_1)

        rule_2 = config_models.MappingRule(preset_id=preset_id_2,
                                             rule_type = constants.MappingRuleType.NoteType,
                                             model_id = deck_note_type.model_id,
                                             enabled = True,
                                             automatic = False)
        preset_mapping_rules.rules.append(rule_2)

        hypertts_instance.preview_all_mapping_rules(editor_context, preset_mapping_rules)

        # we should have played audio for the two rules
        self.assertEqual(len(hypertts_instance.anki_utils.all_played_sounds), 2)

        # look at the first one
        audio_result_dict = hypertts_instance.anki_utils.all_played_sounds[0]
        self.assertEqual(audio_result_dict['source_text'], '老人家')
        self.assertEqual(audio_result_dict['voice']['name'], voice_name_1)

        # second one
        audio_result_dict = hypertts_instance.anki_utils.all_played_sounds[1]
        self.assertEqual(audio_result_dict['source_text'], '老人家')
        self.assertEqual(audio_result_dict['voice']['name'], voice_name_2)  

    def test_preview_apply_all_mapping_rules_empty(self):
        hypertts_instance, deck_note_type, editor_context = gui_testing_utils.get_editor_context()

        # empty rules
        preset_mapping_rules = config_models.PresetMappingRules()

        self.assertRaises(errors.NoPresetMappingRulesDefined, hypertts_instance.preview_all_mapping_rules, editor_context, preset_mapping_rules)
        self.assertRaises(errors.NoPresetMappingRulesDefined, hypertts_instance.apply_all_mapping_rules, editor_context, preset_mapping_rules)

    def test_apply_all_mapping_rules_1(self):
        hypertts_instance, deck_note_type, editor_context = gui_testing_utils.get_editor_context()

        # create simple preset
        preset_id_1 = 'uuid_0'
        name = 'my preset 1'
        voice_name_1 = 'voice_a_1'
        testing_utils.create_simple_batch(hypertts_instance, preset_id=preset_id_1, name=name, voice_name=voice_name_1)
        preset_id_2 = 'uuid_1'
        name = 'my preset 2'
        voice_name_2 = 'voice_a_2'
        testing_utils.create_simple_batch(hypertts_instance, preset_id=preset_id_2, name=name, voice_name=voice_name_2,
                target_field = 'Sound English')

        # add the preset rules
        preset_mapping_rules = config_models.PresetMappingRules()
        rule_1 = config_models.MappingRule(preset_id=preset_id_1,
                                           rule_type = constants.MappingRuleType.DeckNoteType,
                                           model_id = deck_note_type.model_id,
                                           enabled = True,
                                           automatic = False,
                                           deck_id = deck_note_type.deck_id)
        preset_mapping_rules.rules.append(rule_1)

        rule_2 = config_models.MappingRule(preset_id=preset_id_2,
                                             rule_type = constants.MappingRuleType.NoteType,
                                             model_id = deck_note_type.model_id,
                                             enabled = True,
                                             automatic = False)
        preset_mapping_rules.rules.append(rule_2)

        hypertts_instance.apply_all_mapping_rules(editor_context, preset_mapping_rules)

        # look at the sound field
        sound_tag = editor_context.note.set_values['Sound']
        audio_full_path = hypertts_instance.anki_utils.extract_sound_tag_audio_full_path(sound_tag)
        audio_data = hypertts_instance.anki_utils.extract_mock_tts_audio(audio_full_path)
        assert audio_data['source_text'] == '老人家'
        assert audio_data['voice']['name'] == voice_name_1

        sound_tag = editor_context.note.set_values['Sound English']
        audio_full_path = hypertts_instance.anki_utils.extract_sound_tag_audio_full_path(sound_tag)
        audio_data = hypertts_instance.anki_utils.extract_mock_tts_audio(audio_full_path)
        assert audio_data['source_text'] == '老人家'
        assert audio_data['voice']['name'] == voice_name_2


        # we should have played audio for the two rules
        self.assertEqual(len(hypertts_instance.anki_utils.all_played_sounds), 2)

        # look at the first one
        audio_result_dict = hypertts_instance.anki_utils.all_played_sounds[0]
        self.assertEqual(audio_result_dict['source_text'], '老人家')
        self.assertEqual(audio_result_dict['voice']['name'], voice_name_1)

        # second one
        audio_result_dict = hypertts_instance.anki_utils.all_played_sounds[1]
        self.assertEqual(audio_result_dict['source_text'], '老人家')
        self.assertEqual(audio_result_dict['voice']['name'], voice_name_2)  

        # look at the preset rules status object 
        preset_rules_status = hypertts_instance.anki_utils.preset_rules_status
        self.assertEqual(len(preset_rules_status.rule_action_context_list), 2)
        
        preset_status_1 = preset_rules_status.rule_action_context_list[0]
        self.assertEqual(preset_status_1.rule.preset_id, preset_id_1)
        self.assertEqual(preset_status_1.success, True)

        preset_status_2 = preset_rules_status.rule_action_context_list[1]
        self.assertEqual(preset_status_2.rule.preset_id, preset_id_2)
        self.assertEqual(preset_status_2.success, True)        


    def test_apply_all_mapping_rules_error(self):
        hypertts_instance, deck_note_type, editor_context = gui_testing_utils.get_editor_context()

        # create simple preset
        preset_id_1 = 'uuid_0'
        name = 'my preset 1'
        voice_name_1 = 'notfound' # this voice will throw an error when generating audio
        testing_utils.create_simple_batch(hypertts_instance, preset_id=preset_id_1, name=name, voice_name=voice_name_1)
        preset_id_2 = 'uuid_1'
        name = 'my preset 2'
        voice_name_2 = 'voice_a_2'
        testing_utils.create_simple_batch(hypertts_instance, preset_id=preset_id_2, name=name, voice_name=voice_name_2,
                target_field = 'Sound English')

        # add the preset rules
        preset_mapping_rules = config_models.PresetMappingRules()
        rule_1 = config_models.MappingRule(preset_id=preset_id_1,
                                           rule_type = constants.MappingRuleType.DeckNoteType,
                                           model_id = deck_note_type.model_id,
                                           enabled = True,
                                           automatic = False,
                                           deck_id = deck_note_type.deck_id)
        preset_mapping_rules.rules.append(rule_1)

        rule_2 = config_models.MappingRule(preset_id=preset_id_2,
                                             rule_type = constants.MappingRuleType.NoteType,
                                             model_id = deck_note_type.model_id,
                                             enabled = True,
                                             automatic = False)
        preset_mapping_rules.rules.append(rule_2)

        hypertts_instance.apply_all_mapping_rules(editor_context, preset_mapping_rules)

        # the first preset generated no audio

        # but the second preset should have
        sound_tag = editor_context.note.set_values['Sound English']
        audio_full_path = hypertts_instance.anki_utils.extract_sound_tag_audio_full_path(sound_tag)
        audio_data = hypertts_instance.anki_utils.extract_mock_tts_audio(audio_full_path)
        assert audio_data['source_text'] == '老人家'
        assert audio_data['voice']['name'] == voice_name_2

        # look at the preset rules status object 
        preset_rules_status = hypertts_instance.anki_utils.preset_rules_status
        self.assertEqual(len(preset_rules_status.rule_action_context_list), 2)
        
        preset_status_1 = preset_rules_status.rule_action_context_list[0]
        self.assertEqual(preset_status_1.rule.preset_id, preset_id_1)
        self.assertEqual(preset_status_1.success, False)
        # check that preset_status_1.exception is of type errors.AudioNotFoundError
        self.assertIsInstance(preset_status_1.exception, errors.AudioNotFoundError)

        preset_status_2 = preset_rules_status.rule_action_context_list[1]
        self.assertEqual(preset_status_2.rule.preset_id, preset_id_2)
        self.assertEqual(preset_status_2.success, True)        


    @pytest.mark.skip(reason="previews will not be done with bridge commands anymore")
    def test_process_bridge_cmd(self):
        # initialize hypertts instance
        # ============================
        config_gen = testing_utils.TestConfigGenerator()
        hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

        # configure a batch/preset
        # ========================

        voice_list = hypertts_instance.service_manager.full_voice_list()

        voice_a_1 = [x for x in voice_list if x.name == 'voice_a_1'][0]
        voice_selection = config_models.VoiceSelectionSingle()
        voice_selection.set_voice(config_models.VoiceWithOptions(voice_a_1, {}))

        batch_config = config_models.BatchConfig(hypertts_instance.anki_utils)
        source = config_models.BatchSource(mode=constants.BatchMode.simple, source_field='Chinese')
        target = config_models.BatchTarget('Sound', False, True)
        text_processing = config_models.TextProcessing()

        batch_config.set_source(source)
        batch_config.set_target(target)
        batch_config.set_voice_selection(voice_selection)
        batch_config.set_text_processing(text_processing)
        batch_config.name = 'test_preset_1'

        # save the preset
        # note: this function is deprecated, we may not need to process bridge commands after change is done
        hypertts_instance.save_batch_config('test_preset_1', batch_config)


        # configure mock editor
        # =====================
        mock_editor = config_gen.get_mock_editor_with_note(config_gen.note_id_1)

        # using full field
        # ================

        # previewing audio
        # ----------------

        pycmd_str = 'hypertts:previewaudio:false:test_preset_1'
        hypertts_instance.process_bridge_cmd(pycmd_str, mock_editor, False)        

        self.assertEqual(hypertts_instance.anki_utils.played_sound['source_text'], '老人家')


        # adding audio
        # ------------

        pycmd_str = 'hypertts:addaudio:false:test_preset_1'
        hypertts_instance.process_bridge_cmd(pycmd_str, mock_editor, False)

        # verify that audio was added

        note_1 = mock_editor.note
        assert 'Sound' in note_1.set_values 

        sound_tag = note_1.set_values['Sound']
        audio_full_path = hypertts_instance.anki_utils.extract_sound_tag_audio_full_path(sound_tag)
        audio_data = hypertts_instance.anki_utils.extract_mock_tts_audio(audio_full_path)

        assert audio_data['source_text'] == '老人家'

        # having something selected should have no effect
        mock_editor.web.selected_text = '人'

        pycmd_str = 'hypertts:addaudio:false:test_preset_1'
        hypertts_instance.process_bridge_cmd(pycmd_str, mock_editor, False)

        # verify that audio was added

        note_1 = mock_editor.note
        assert 'Sound' in note_1.set_values 

        sound_tag = note_1.set_values['Sound']
        audio_full_path = hypertts_instance.anki_utils.extract_sound_tag_audio_full_path(sound_tag)
        audio_data = hypertts_instance.anki_utils.extract_mock_tts_audio(audio_full_path)

        assert audio_data['source_text'] == '老人家'        

        # using selected field
        # ====================

        # previewing audio
        # ----------------

        mock_editor.web.selected_text = '人'

        pycmd_str = 'hypertts:previewaudio:true:test_preset_1'
        hypertts_instance.process_bridge_cmd(pycmd_str, mock_editor, False)

        self.assertEqual(hypertts_instance.anki_utils.played_sound['source_text'], '人')        

        # when no text is selected
        mock_editor.web.selected_text = ''

        pycmd_str = 'hypertts:previewaudio:true:test_preset_1'
        hypertts_instance.process_bridge_cmd(pycmd_str, mock_editor, False)

        self.assertEqual(hypertts_instance.anki_utils.played_sound['source_text'], '老人家')

        # adding audio
        # ------------

        mock_editor.web.selected_text = '人'

        pycmd_str = 'hypertts:addaudio:true:test_preset_1'
        hypertts_instance.process_bridge_cmd(pycmd_str, mock_editor, False)

        # verify that audio was added

        note_1 = mock_editor.note
        assert 'Sound' in note_1.set_values 

        sound_tag = note_1.set_values['Sound']
        audio_full_path = hypertts_instance.anki_utils.extract_sound_tag_audio_full_path(sound_tag)
        audio_data = hypertts_instance.anki_utils.extract_mock_tts_audio(audio_full_path)

        assert audio_data['source_text'] == '人'

        # with empty selection, we should get the full field
        mock_editor.web.selected_text = ''

        pycmd_str = 'hypertts:addaudio:true:test_preset_1'
        hypertts_instance.process_bridge_cmd(pycmd_str, mock_editor, False)

        # verify that audio was added

        note_1 = mock_editor.note
        assert 'Sound' in note_1.set_values 

        sound_tag = note_1.set_values['Sound']
        audio_full_path = hypertts_instance.anki_utils.extract_sound_tag_audio_full_path(sound_tag)
        audio_data = hypertts_instance.anki_utils.extract_mock_tts_audio(audio_full_path)

        assert audio_data['source_text'] == '老人家'

    def test_trial_request_payload(self):
        email = 'test@email.com'
        client_uuid = '1234567890'
        password = 'password@01'

        cloudlanguagetools_instance = cloudlanguagetools.CloudLanguageTools()
        data = cloudlanguagetools_instance.build_trial_key_request_data(email, password, client_uuid)
        
        # Verify the data structure
        self.assertEqual(data['email'], email)
        self.assertEqual(data['password'], password)
        self.assertEqual(data['id_1'], client_uuid)
        self.assertTrue('id_2' in data)  # machine ID will be dynamic
        self.assertTrue('id_3' in data)  # HMAC signature will be dynamic

        pprint.pprint(data)

        self.assertEqual(data, {'email': 'test@email.com',
            'id_1': '1234567890',
            'id_2': '5ada07e49da742fbb640595632bd36b8',
            'id_3': '8929e02001664ae9d21f73a61e62f7aa024cd42304bf63b4af4ec11bbcc20d98',
            'password': 'password@01'})
            
    def test_get_editor_context(self):
        config_gen = testing_utils.TestConfigGenerator()
        hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')
        
        # Create a mock editor with note
        mock_editor = config_gen.get_mock_editor_with_note(config_gen.note_id_1)
        
        # Set up test conditions
        mock_editor.currentField = 0  # First field
        mock_editor.web.selected_text = '人'  # Set some selected text
        
        # Get editor context
        editor_context = hypertts_instance.get_editor_context(mock_editor)
        
        # Verify the editor context
        self.assertEqual(editor_context.note.id, config_gen.note_id_1)
        self.assertEqual(editor_context.editor, mock_editor)
        self.assertEqual(editor_context.add_mode, False)
        self.assertEqual(editor_context.selected_text, '人')
        self.assertEqual(editor_context.current_field, 'Chinese')  # First field should be 'Chinese' based on TestConfigGenerator
