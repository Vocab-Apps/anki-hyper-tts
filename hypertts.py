
# python imports
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

    def __init__(self, anki_utils):
        self.anki_utils = anki_utils
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
                    sound_tag = self.generate_sound_tag(batch_config['voice'], source_text)
                    note[target_field] = sound_tag
                note.flush()
                    

    def generate_sound_tag(self, voice, source_text):
        return f'[sound:yoyo.mp3]'

    def get_hash_for_audio_request(self, source_text, voice):
        combined_data = {
            'source_text': source_text,
            'voice': voice
        }
        return hashlib.sha224(str(combined_data).encode('utf-8')).hexdigest()

