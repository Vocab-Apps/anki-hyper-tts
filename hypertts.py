
# python imports
import os
import sys
import re
import hashlib
import logging
import random
import copy
import json
from typing import List, Dict

# anki imports
import aqt
import aqt.progress
import aqt.addcards
import anki.notes
import anki.cards

constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_base)
errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_base)
text_utils = __import__('text_utils', globals(), locals(), [], sys._addon_import_level_base)
config_models = __import__('config_models', globals(), locals(), [], sys._addon_import_level_base)


class HyperTTS():
    """
    should have awareness of:
    - anki concepts such as notes, editor
    - understand how user has configured their presets
    should not have awareness of:
    - services (route through servicemanager)
    """

    def __init__(self, anki_utils, service_manager):
        self.anki_utils = anki_utils
        self.service_manager = service_manager
        self.error_manager = errors.ErrorManager(self.anki_utils)
        self.config = self.anki_utils.get_config()
        self.error_manager = errors.ErrorManager(self.anki_utils)


    def process_batch_audio(self, note_id_list, batch, batch_status):
        # for each note, generate audio
        with batch_status.get_batch_running_action_context():
            undo_id = self.anki_utils.undo_start()
            for note_id in note_id_list:
                with batch_status.get_note_action_context(note_id, False) as note_action_context:
                    note = self.anki_utils.get_note_by_id(note_id)
                    # process note
                    source_text, processed_text, sound_file, full_filename = self.process_note_audio(batch, note, False)
                    # update note action context
                    note_action_context.set_source_text(source_text)
                    note_action_context.set_processed_text(processed_text)
                    note_action_context.set_sound(sound_file)
                    note_action_context.set_status(constants.BatchNoteStatus.Done)                    
                if batch_status.must_continue == False:
                    logging.info('batch_status execution interrupted')
                    break
            self.anki_utils.undo_end(undo_id)

    def process_note_audio(self, batch, note, add_mode):
        target_field = batch.target.target_field
        source_text = self.get_source_text(note, batch.source)
        processed_text = self.process_text(source_text, batch.text_processing)

        full_filename, audio_filename = self.get_audio_file(processed_text, batch.voice_selection)
        sound_tag, sound_file = self.get_collection_sound_tag(full_filename, audio_filename)

        target_field_content = note[target_field]
        
        # do we need to remove existing sound tags ?
        if batch.target.remove_sound_tag == True:
                target_field_content = self.strip_sound_tag(target_field_content)
        
        # does the user want text and sound together?
        if batch.target.text_and_sound_tag == True:
            target_field_content = f'{target_field_content} {sound_tag}'
        else:
            target_field_content = f'{sound_tag}'

        note[target_field] = target_field_content
        if not add_mode:
            self.anki_utils.update_note(note)

        return source_text, processed_text, sound_file, full_filename

    def get_note_audio(self, batch, note):
        source_text = self.get_source_text(note, batch.source)
        processed_text = text_utils.process_text(source_text, batch.text_processing)
        return self.get_audio_file(processed_text, batch.voice_selection)        

    def get_audio_file(self, processed_text, voice_selection):
        # sanity checks
        if voice_selection.selection_mode in [constants.VoiceSelectionMode.priority, constants.VoiceSelectionMode.random]:
            if len(voice_selection.voice_list) == 0:
                raise errors.NoVoicesAdded()

        # this voice_list copy is only used for priority mode
        voice_list = None
        priority_mode = voice_selection.selection_mode == constants.VoiceSelectionMode.priority
        if priority_mode:
            voice_list = copy.copy(voice_selection.voice_list)
        sound_found = False
        # loop while we haven't found the sound. this will be used for priority mode
        loop_condition = True
        while loop_condition:
            try:
                voice_with_options = self.choose_voice(voice_selection, voice_list)
                full_filename, audio_filename = self.generate_audio_write_file(processed_text, voice_with_options.voice, voice_with_options.options)
                return full_filename, audio_filename
            except errors.AudioNotFoundError as exc:
                # try the next voice, as long as one is available
                if not priority_mode:
                    # re-raise the exception
                    raise exc
            loop_condition = priority_mode and sound_found == False and len(voice_list) > 0
        raise errors.AudioNotFoundAnyVoiceError(processed_text)

    def choose_voice(self, voice_selection, voice_list) -> config_models.VoiceWithOptions:
        if voice_selection.selection_mode == constants.VoiceSelectionMode.single:
            return voice_selection.voice
        elif voice_selection.selection_mode == constants.VoiceSelectionMode.random:
            logging.info(f'choosing from {len(voice_selection.voice_list)} voices')
            choice = random.choices(voice_selection.voice_list, weights=[x.random_weight for x in voice_selection.voice_list])
            return choice[0]
        elif voice_selection.selection_mode == constants.VoiceSelectionMode.priority:
            # remove that voice from possible list
            voice = voice_list.pop(0)
            return voice

    def editor_note_add_audio(self, batch, editor, note, add_mode):
        undo_id = self.anki_utils.undo_start()
        source_text, processed_text, sound_file, full_filename = self.process_note_audio(batch, note, add_mode)
        editor.set_note(note)
        self.anki_utils.undo_end(undo_id)
        self.anki_utils.play_sound(full_filename)

    # text processing
    # ===============

    def get_source_text(self, note, batch_source):
        if batch_source.mode == constants.BatchMode.simple:
            source_text = note[batch_source.source_field]
        elif batch_source.mode == constants.BatchMode.template:
            source_text = self.expand_simple_template(note, batch_source.source_template)
        elif batch_source.mode == constants.BatchMode.advanced_template:
            source_text = self.expand_advanced_template(note, batch_source.source_template)
        return source_text

    def expand_simple_template(self, note, source_template):
        field_values = self.get_field_values(note)
        # logging.info(f'field_values: {field_values}')
        return source_template.format_map(field_values)

    def expand_advanced_template(self, note, source_template):
        local_variables = {
            'template_fields': self.get_field_values(note)
        }
        expanded_template = exec(source_template, {}, local_variables)
        if 'result' not in local_variables:
            raise errors.NoResultVar()
        result = local_variables['result']
        return result

    def get_field_values(self, note):
        field_values = {}
        for field_name in list(note.keys()):
            field_values[field_name] = note[field_name]
        return field_values

    def process_text(self, source_text, batch_text_processing):
        processed_text = text_utils.process_text(source_text, batch_text_processing)
        # logging.info(f'before text processing: [{source_text}], after text processing: [{processed_text}]')
        if len(processed_text) == 0:
            raise errors.SourceTextEmpty()
        return processed_text

    # sound generation
    # ================

    def preview_note_audio(self, batch, note):
        full_filename, audio_filename = self.get_note_audio(batch, note)
        self.anki_utils.play_sound(full_filename)

    def play_sound(self, source_text, voice, options):
        logging.info(f'playing audio for {source_text}')
        full_filename, audio_filename = self.generate_audio_write_file(source_text, voice, options)
        self.anki_utils.play_sound(full_filename)

    # processing of sound tags / collection stuff
    # ===========================================

    def generate_audio_write_file(self, source_text, voice, options):
        # write to user files directory
        hash_str = self.get_hash_for_audio_request(source_text, voice, options)
        audio_filename = self.get_audio_filename(hash_str)
        full_filename = self.get_full_audio_file_name(hash_str)
        with open(full_filename, 'wb') as f:
            f.write(self.service_manager.get_tts_audio(source_text, voice, options))
        return full_filename, audio_filename

    def get_collection_sound_tag(self, full_filename, audio_filename):
        self.anki_utils.media_add_file(full_filename)
        return f'[sound:{audio_filename}]', audio_filename

    def get_full_audio_file_name(self, hash_str):
        # return the absolute path of the audio file in the user_files directory
        user_files_dir = self.anki_utils.get_user_files_dir()
        filename = self.get_audio_filename(hash_str)
        return os.path.join(user_files_dir, filename)
    
    def get_audio_filename(self, hash_str):
        filename = f'hypertts-{hash_str}.mp3'
        return filename

    def get_hash_for_audio_request(self, source_text, voice, options):
        combined_data = {
            'source_text': source_text,
            'voice_key': voice.voice_key,
            'options': options
        }
        return hashlib.sha224(str(combined_data).encode('utf-8')).hexdigest()

    def strip_sound_tag(self, field_value):
        field_value = re.sub('\[sound:[^\]]+\]', '', field_value)
        return field_value.strip()

    # functions related to getting data from notes
    # ============================================

    def get_all_fields_from_notes(self, note_id_list):
        field_name_set = {}
        for note_id in note_id_list:
            note = self.anki_utils.get_note_by_id(note_id)
            for field in list(note.keys()):
                field_name_set[field] = True
        return sorted(field_name_set.keys())

    def populate_batch_status_processed_text(self, note_id_list, batch_source, text_processing, batch_status):
        with batch_status.get_batch_running_action_context():
            for note_id in note_id_list:
                with batch_status.get_note_action_context(note_id, True) as note_action_context:
                    note = self.anki_utils.get_note_by_id(note_id)
                    source_text, processed_text = self.get_source_processed_text(note, batch_source, text_processing)
                    note_action_context.set_source_text(source_text)
                    note_action_context.set_processed_text(processed_text)
                    note_action_context.set_status(constants.BatchNoteStatus.OK)
                if batch_status.must_continue == False:
                    logging.info('batch_status execution interrupted')
                    break

    def get_source_processed_text(self, note, batch_source, text_processing):
        source_text = self.get_source_text(note, batch_source)
        processed_text = text_utils.process_text(source_text, text_processing)
        return source_text, processed_text

    # functions related to addon config
    # =================================

    def save_batch_config(self, batch_name, batch):
        if constants.CONFIG_BATCH_CONFIG not in self.config:
            self.config[constants.CONFIG_BATCH_CONFIG] = {}
        self.config[constants.CONFIG_BATCH_CONFIG][batch_name] = batch.serialize()
        self.anki_utils.write_config(self.config)
        logging.info(f'saved batch config [{batch_name}]')

    def load_batch_config(self, batch_name):
        logging.info(f'loading batch config [{batch_name}]')
        return self.deserialize_batch_config(self.config[constants.CONFIG_BATCH_CONFIG][batch_name])

    def get_batch_config_list(self):
        if constants.CONFIG_BATCH_CONFIG not in self.config:
            return []
        return list(self.config[constants.CONFIG_BATCH_CONFIG].keys())

    def get_batch_config_list_editor(self):
        return [constants.BATCH_CONFIG_NEW] + self.get_batch_config_list()

    def get_next_batch_name(self):
        existing_batch_names = self.get_batch_config_list()
        i = 1
        batch_name = f'Preset {i}'
        while batch_name in existing_batch_names:
            i += 1
            batch_name = f'Preset {i}'
        return batch_name

    def save_configuration(self, configuration_model):
        self.config[constants.CONFIG_CONFIGURATION] = configuration_model.serialize()
        self.anki_utils.write_config(self.config)

    def get_configuration(self):
        return self.deserialize_configuration(self.config[constants.CONFIG_CONFIGURATION])

    # deserialization routines for loading from config
    # ================================================

    def deserialize_batch_config(self, batch_config):
        batch = config_models.BatchConfig()
        batch_mode = constants.BatchMode[batch_config['source']['mode']]
        if batch_mode == constants.BatchMode.simple:
            source = config_models.BatchSourceSimple(batch_config['source']['source_field'])
        else:
            source = config_models.BatchSourceTemplate(batch_mode, batch_config['source']['source_template'],
                constants.TemplateFormatVersion[batch_config['source']['template_format_version']])
        target = config_models.BatchTarget(batch_config['target']['target_field'], False, False)
        voice_selection = self.deserialize_voice_selection(batch_config['voice_selection'])

        text_processing_config = batch_config.get('text_processing', {})
        text_processing = self.deserialize_text_processing(text_processing_config)

        batch.set_source(source)
        batch.set_target(target)
        batch.set_voice_selection(voice_selection)
        batch.text_processing = text_processing
        
        return batch

    def deserialize_voice_selection(self, voice_selection_config):
        voice_selection_mode = constants.VoiceSelectionMode[voice_selection_config['voice_selection_mode']]
        if voice_selection_mode == constants.VoiceSelectionMode.single:
            single = config_models.VoiceSelectionSingle()
            voice = self.service_manager.deserialize_voice(voice_selection_config['voice']['voice'])
            single.set_voice(config_models.VoiceWithOptions(voice, voice_selection_config['voice']['options']))
            return single
        elif voice_selection_mode == constants.VoiceSelectionMode.random:
            random = config_models.VoiceSelectionRandom()
            for voice_data in voice_selection_config['voice_list']:
                voice = self.service_manager.deserialize_voice(voice_data['voice'])
                random.add_voice(config_models.VoiceWithOptionsRandom(voice, voice_data['options'], voice_data['weight']))
            return random
        elif voice_selection_mode == constants.VoiceSelectionMode.priority:
            priority = config_models.VoiceSelectionPriority()
            for voice_data in voice_selection_config['voice_list']:
                voice = self.service_manager.deserialize_voice(voice_data['voice'])
                priority.add_voice(config_models.VoiceWithOptionsPriority(voice, voice_data['options']))
            return priority

    def deserialize_text_processing(self, text_processing_config):
        text_processing = config_models.TextProcessing()
        text_processing.html_to_text_line = text_processing_config.get('html_to_text_line', constants.TEXT_PROCESSING_DEFAULT_HTMLTOTEXTLINE)
        text_processing.ssml_convert_characters = text_processing_config.get('ssml_convert_characters', constants.TEXT_PROCESSING_DEFAULT_SSML_CHARACTERS)
        text_processing.run_replace_rules_after = text_processing_config.get('run_replace_rules_after', constants.TEXT_PROCESSING_DEFAULT_REPLACE_AFTER)
        rules = text_processing_config.get('text_replacement_rules', [])
        for rule in rules:
            rule_obj = config_models.TextReplacementRule(constants.TextReplacementRuleType[rule['rule_type']])
            rule_obj.source = rule['source']
            rule_obj.target = rule['target']
            text_processing.add_text_replacement_rule(rule_obj)
        return text_processing

    def deserialize_configuration(self, configuration_config):
        configuration = config_models.Configuration()
        configuration.hypertts_pro_api_key = configuration_config.get('hypertts_pro_api_key', None)
        configuration.set_service_config(configuration_config.get('service_config', {}))
        return configuration