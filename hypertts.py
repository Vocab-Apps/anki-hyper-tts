
# python imports
import os
import sys
import re
import hashlib
import logging
import random
from typing import List, Dict

# anki imports
import aqt
import aqt.progress
import aqt.addcards
import anki.notes
import anki.cards

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


    def process_batch_audio(self, note_id_list, batch_config, progress_fn):
        batch_error_manager = self.error_manager.get_batch_error_manager('adding audio to notes')
        # for each note, generate audio
        for note_id in note_id_list:
            with batch_error_manager.get_batch_action_context():
                note = self.anki_utils.get_note_by_id(note_id)
                target_field = batch_config['target_field']
                source_text = self.get_source_text(note, batch_config)
                processed_text = self.process_text(source_text)
                voice = self.choose_voice(batch_config['voices'])
                sound_tag = self.generate_sound_tag_add_collection(source_text, voice)
                if batch_config[constants.CONFIG_BATCH_TEXT_AND_SOUND_TAG] == True:
                    # remove existing sound tag
                    current_target_field_content = note[target_field]
                    field_content = self.strip_sound_tag(current_target_field_content)
                    note[target_field] = f'{field_content} {sound_tag}'
                else:
                    note[target_field] = sound_tag
                note.flush()
            progress_fn(batch_error_manager.iteration_count)
        return batch_error_manager

    def choose_voice(self, voices):
        logging.info(f'choosing from {len(voices)} voices')
        voice_list = []
        weights = []
        for voice in voices:
            voice_list.append(voice)
            weight = voice.get('weight', 1)
            weights.append(weight)
        choice = random.choices(voice_list, weights=weights)
        return choice[0]

    # text processing
    # ===============

    def get_source_text(self, note, batch_config):
        if batch_config['mode'] == constants.BatchMode.simple.name:
            source_text = note[batch_config['source_field']]
        elif batch_config['mode'] == constants.BatchMode.template.name:
            source_text = self.expand_template(note, batch_config['source_template'])
        return source_text

    def expand_template(self, note, source_template):
        field_values = {}
        for field in note.fields:
            field_values[field] = note[field]
        local_variables = {
            'template_fields': field_values
        }
        expanded_template = exec(source_template, {}, local_variables)
        result = local_variables['result']
        return result

    def process_text(self, source_text):
        processed_text = self.text_utils.process(source_text)
        logging.info(f'before text processing: [{source_text}], after text processing: [{processed_text}]')
        if self.text_utils.is_empty(processed_text):
            raise errors.SourceTextEmpty()
        return processed_text

    # processing of sound tags / collection stuff
    # ===========================================

    def generate_sound_tag_add_collection(self, source_text, voice):
        # write to user files directory
        hash_str = self.get_hash_for_audio_request(voice, source_text)
        audio_filename = self.get_audio_filename(hash_str)
        full_filename = self.get_full_audio_file_name(hash_str)
        with open(full_filename, 'wb') as f:
            f.write(self.service_manager.get_tts_audio(source_text, voice))
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


    # functions related to addon config
    # =================================

    def get_text_processing_settings(self):
        return self.config.get(constants.CONFIG_TEXT_PROCESSING, {})

    def store_text_processing_settings(self, settings):
        self.config[constants.CONFIG_TEXT_PROCESSING] = settings
        self.anki_utils.write_config(self.config)
        self.text_utils = text_utils.TextUtils(settings)