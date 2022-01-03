
# python imports
import os
import sys
import re
import hashlib
import logging
import random
import copy
from typing import List, Dict

# anki imports
import aqt
import aqt.progress
import aqt.addcards
import anki.notes
import anki.cards

import config_models

if hasattr(sys, '_pytest_mode'):
    import constants
    import version
    import errors
    import text_utils
else:
    from . import constants
    from . import version
    from . import errors
    from . import text_utils



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
        self.text_utils = text_utils.TextUtils(self.get_text_processing_settings())
        self.error_manager = errors.ErrorManager(self.anki_utils)


    def process_batch_audio(self, note_id_list, batch, progress_fn):
        batch_error_manager = self.error_manager.get_batch_error_manager('adding audio to notes')
        # for each note, generate audio
        for note_id in note_id_list:
            with batch_error_manager.get_batch_action_context():
                note = self.anki_utils.get_note_by_id(note_id)
                target_field = batch.target.target_field
                source_text = self.get_source_text(note, batch.source)
                processed_text = self.process_text(source_text)
                # this voice_list copy is only used for priority mode
                voice_list = None
                if batch.voice_selection.selection_mode == constants.VoiceSelectionMode.priority:
                    voice_list = copy.copy(batch.voice_selection.voice_list)
                sound_found = False
                # loop while we haven't found the sound. this will be used for priority mode
                loop_condition = True
                while loop_condition:
                    try:
                        voice_with_options = self.choose_voice(batch.voice_selection, voice_list)
                        sound_tag = self.generate_sound_tag_add_collection(source_text, voice_with_options.voice, voice_with_options.options)
                        if batch.target.remove_sound_tag == True:
                            # remove existing sound tag
                            current_target_field_content = note[target_field]
                            field_content = self.strip_sound_tag(current_target_field_content)
                            note[target_field] = f'{field_content} {sound_tag}'
                        else:
                            note[target_field] = sound_tag
                        note.flush()
                        sound_found = True
                    except errors.AudioNotFoundError as exc:
                        # try the next voice, as long as one is available
                        pass
                    loop_condition = sound_found == False and len(voice_list) > 0
                if sound_found == False:
                    raise errors.AudioNotFoundAnyVoiceError(source_text)
            progress_fn(batch_error_manager.iteration_count)
        return batch_error_manager

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
        return source_template.format_map(field_values)

    def expand_advanced_template(self, note, source_template):
        local_variables = {
            'template_fields': self.get_field_values(note)
        }
        expanded_template = exec(source_template, {}, local_variables)
        result = local_variables['result']
        return result

    def get_field_values(self, note):
        field_values = {}
        for field in note.fields:
            field_values[field] = note[field]
        return field_values

    def process_text(self, source_text):
        processed_text = self.text_utils.process(source_text)
        logging.info(f'before text processing: [{source_text}], after text processing: [{processed_text}]')
        if self.text_utils.is_empty(processed_text):
            raise errors.SourceTextEmpty()
        return processed_text

    # sound generation
    # ================

    def play_sound(self, source_text, voice, options):
        full_filename, audio_filename = self.generate_audio_write_file(source_text, voice, options)
        self.anki_utils.play_sound(full_filename)

    # processing of sound tags / collection stuff
    # ===========================================

    def generate_audio_write_file(self, source_text, voice, options):
        # write to user files directory
        hash_str = self.get_hash_for_audio_request(voice, source_text)
        audio_filename = self.get_audio_filename(hash_str)
        full_filename = self.get_full_audio_file_name(hash_str)
        with open(full_filename, 'wb') as f:
            f.write(self.service_manager.get_tts_audio(source_text, voice, options))
        return full_filename, audio_filename

    def generate_sound_tag_add_collection(self, source_text, voice, options):
        full_filename, audio_filename = self.generate_audio_write_file(source_text, voice, options)
        # add to collection
        self.anki_utils.media_add_file(full_filename)
        return f'[sound:{audio_filename}]'

    def get_full_audio_file_name(self, hash_str):
        # return the absolute path of the audio file in the user_files directory
        user_files_dir = self.anki_utils.get_user_files_dir()
        filename = self.get_audio_filename(hash_str)
        return os.path.join(user_files_dir, filename)
    
    def get_audio_filename(self, hash_str):
        filename = f'hypertts-{hash_str}.mp3'
        return filename

    def get_hash_for_audio_request(self, source_text, voice):
        combined_data = {
            'source_text': source_text,
            'voice': voice
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
            for field in note.fields:
                field_name_set[field] = True
        return sorted(field_name_set.keys())

    def get_field_values_array(self, note_id_list, field_name):
        result = []
        for note_id in note_id_list:
            note = self.anki_utils.get_note_by_id(note_id)
            result.append([note_id, note[field_name]])
        return result

    def get_source_text_array(self, note_id_list, batch_source):
        result = []
        for note_id in note_id_list:
            note = self.anki_utils.get_note_by_id(note_id)
            source_text = self.get_source_text(note, batch_source)
            result.append([note_id, source_text])
        return result


    # functions related to addon config
    # =================================

    def get_text_processing_settings(self):
        return self.config.get(constants.CONFIG_TEXT_PROCESSING, {})

    def store_text_processing_settings(self, settings):
        self.config[constants.CONFIG_TEXT_PROCESSING] = settings
        self.anki_utils.write_config(self.config)
        self.text_utils = text_utils.TextUtils(settings)

    # deserialization routines for loading from config
    # ================================================

    def deserialize_batch_config(self, batch_config):
        batch = config_models.BatchConfig()
        batch_mode = constants.BatchMode[batch_config['source']['mode']]
        if batch_mode == constants.BatchMode.simple:
            source = config_models.BatchSourceSimple(batch_config['source']['source_field'])
        else:
            source = config_models.BatchSourceTemplate(batch_config['source']['source_template'],
                constants.TemplateFormatVersion[batch_config['source']['batch_template_version']])
        target = config_models.BatchTarget('Sound', False, False)
        voice_selection = self.deserialize_voice_selection(batch_config['voice_selection'])

        batch.set_source(source)
        batch.set_target(target)
        batch.set_voice_selection(voice_selection)
        
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