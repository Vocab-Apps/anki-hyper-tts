
# python imports
import os
import sys
import hashlib
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

# anki imports
import aqt

class HyperTTS():

    def __init__(self, anki_utils, service_manager):
        self.anki_utils = anki_utils
        self.service_manager = service_manager
        self.error_manager = errors.ErrorManager(self.anki_utils)
        self.config = self.anki_utils.get_config()
        #self.text_utils = text_utils.TextUtils(self.get_text_processing_settings())
        self.error_manager = errors.ErrorManager(self.anki_utils)


    def process_batch_audio(self, note_id_list, batch_config):
        batch_error_manager = self.error_manager.get_batch_error_manager('adding audio to notes')
        # for each note, generate audio
        for note_id in note_id_list:
            with batch_error_manager.get_batch_action_context(f'adding audio to note {note_id}'):
                note = self.anki_utils.get_note_by_id(note_id)
                target_field = batch_config['target_field']
                if batch_config['mode'] == 'simple':
                    source_text = note[batch_config['source_field']]
                    sound_tag = self.generate_sound_tag_add_collection(source_text, batch_config['voice'])
                    note[target_field] = sound_tag
                note.flush()
                    

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