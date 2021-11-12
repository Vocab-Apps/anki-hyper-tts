
# python imports
import sys
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
        pass