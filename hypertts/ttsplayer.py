"""
Register HyperTTS voices with the Anki {{tts}} tag.
code modeled after 
https://ankiweb.net/shared/info/391644525 
https://github.com/ankitects/anki-addons/blob/master/code/gtts_player/__init__.py
"""

import sys
from concurrent.futures import Future
from dataclasses import dataclass
from typing import List, cast

# import aqt
import aqt.tts
import anki
import anki.utils

constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_base)
languages = __import__('languages', globals(), locals(), [], sys._addon_import_level_base)
logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_base)
logger = logging_utils.get_child_logger(__name__)


class AnkiHyperTTSPlayer(aqt.tts.TTSProcessPlayer):
    def __init__(self, taskman: aqt.taskman.TaskManager, hypertts) -> None:
        super(aqt.tts.TTSProcessPlayer, self).__init__(taskman)
        self.hypertts = hypertts
        logger.info('created AnkiHyperTTSPlayer')

    # this is called the first time Anki tries to play a TTS file
    def get_available_voices(self) -> List[aqt.tts.TTSVoice]:

        # register a voice for every possible language HyperTTS supports. This avoids forcing the user to do a restart when
        # they configure a new TTS tag
        
        voices = []
        for audio_language in languages.AudioLanguage:
            language_name = audio_language.name
            if anki.utils.point_version() == 58: # this regression only concerns Anki 2.1.58
                voices.append(aqt.tts.TTSVoice(name=constants.TTS_TAG_VOICE, lang=language_name, available=True))
            else:
                voices.append(aqt.tts.TTSVoice(name=constants.TTS_TAG_VOICE, lang=language_name))

        return voices  # type: ignore

    # this is called on a background thread, and will not block the UI
    def _play(self, tag: anki.sound.AVTag):
        self.audio_file_path = None
        self.playback_error = False
        self.playback_error_message = None

        assert isinstance(tag, anki.sound.TTSTag)

        if constants.TTS_TAG_VOICE not in tag.voices:
            logger.warning(f'HyperTTS voice not found in tag {tag}, skipping')
            return None

        logger.info(f'playing TTS sound for {tag}, voices: {tag.voices}')

        audio_filename = self.hypertts.get_audio_filename_tts_tag(tag)
        return audio_filename

    # this is called on the main thread, after _play finishes
    def _on_done(self, ret: Future, cb: aqt.sound.OnDoneCallback) -> None:
        with self.hypertts.get_tts_player_action_context():
            audio_filename = ret.result()
            if audio_filename != None:
                logger.info(f'got audio_filename: {audio_filename}')
                aqt.sound.av_player.insert_file(audio_filename)
            else:
                logger.warning(f'no audio filename, not playing any audio')
        cb()

