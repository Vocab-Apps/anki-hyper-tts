import aqt.qt
from . import component_voiceselection
from . import config_models
from . import constants
from . import errors
from . import constants_events
from .constants_events import Event, EventMode
from . import stats
from . import logging_utils
from . import voice as voice_module

logger = logging_utils.get_child_logger(__name__)

sc = stats.StatsContext(constants_events.EventContext.voice_selection)

class VoiceSelectionEasy(component_voiceselection.VoiceSelection):
    def __init__(self, hypertts, dialog, model_change_callback):
        self.model = config_models.VoiceSelectionSingle()
        super().__init__(hypertts, dialog, model_change_callback)
        self.enable_model_change_callback = True

    def draw(self):
        grid_layout = aqt.qt.QGridLayout()
        
        # Get voice list and populate combo boxes
        self.get_voices()
        
        # Language filter
        grid_layout.addWidget(aqt.qt.QLabel('Language:'), 0, 0)
        grid_layout.addWidget(self.languages_combobox, 0, 1)

        # Service filter
        grid_layout.addWidget(aqt.qt.QLabel('Service:'), 1, 0)
        grid_layout.addWidget(self.services_combobox, 1, 1)

        # Voice selection combo box
        grid_layout.addWidget(aqt.qt.QLabel('Voice:'), 2, 0)
        grid_layout.addWidget(self.voices_combobox, 2, 1)

        self.populate_combobox(self.audio_languages_combobox, [audio_lang.audio_lang_name for audio_lang in self.audio_languages])
        self.populate_combobox(self.languages_combobox, [language.lang_name for language in self.languages])
        self.populate_combobox(self.services_combobox, self.services)
        self.populate_combobox(self.genders_combobox, [gender.name for gender in self.genders])

        # Wire up events
        self.languages_combobox.currentIndexChanged.connect(self.filter_and_draw_voices)
        self.services_combobox.currentIndexChanged.connect(self.filter_and_draw_voices)
        self.voices_combobox.currentIndexChanged.connect(self.voice_selected)

        widget = aqt.qt.QWidget()
        widget.setLayout(grid_layout)
        
        # Initialize voice list
        self.filter_and_draw_voices(0)
        
        return widget

    def voice_selected(self, current_index):
        logger.debug(f'voice_selected, current_index: {current_index}')
        if current_index >= len(self.filtered_voice_list) or current_index < 0:
            logger.warning(f'voice_selected: current_index out of range: {current_index}, len(self.filtered_voice_list): {len(self.filtered_voice_list)}')
            return
        voice = self.filtered_voice_list[current_index]
        logger.info(f'voice_selected: {voice} options: {voice.options}')
        self.voice_selection_model.set_voice(config_models.VoiceWithOptions(voice.voice_id, {}))
        self.notify_model_update()        


    def load_model(self, model):
        # don't report changes back to parent dialog as we adjust widgets
        self.enable_model_change_callback = False
        logger.info(f'load_model, model: {model}')

        # Check if the model is a VoiceSelectionSingle
        if not isinstance(model, config_models.VoiceSelectionSingle):
            # Handle VoiceSelectionPriority or VoiceSelectionRandom by using the first voice
            if isinstance(model, (config_models.VoiceSelectionPriority, config_models.VoiceSelectionRandom)):
                if len(model.voice_list) > 0:
                    # Use the first voice from the list
                    first_voice = model.voice_list[0]
                    voice_id = first_voice.voice_id
                    logger.warning(f'VoiceSelectionEasy received {type(model).__name__} model, using first voice: {voice_id}')
                else:
                    logger.error(f'VoiceSelectionEasy received {type(model).__name__} model with empty voice list')
                    self.enable_model_change_callback = True
                    return
            else:
                logger.error(f'VoiceSelectionEasy cannot handle model type: {type(model).__name__}')
                self.enable_model_change_callback = True
                return
        else:
            # here we need to select the correct voice, based on what the user has saved in their preset (single voice)
            # we have access to the voice_id, but we need to locate the proper voice
            voice_id = model.voice.voice_id
        try:
            voice = self.hypertts.service_manager.locate_voice(voice_id)
            voice_index = self.voice_list.index(voice)
            self.voices_combobox.setCurrentIndex(voice_index)
        except ValueError as e:
            logger.warning(f'Voice not found: {voice_id}: {e}')
            logger.error(f'while loading model: voice not found')
        except errors.VoiceIdNotFound as e:
            logger.warning(f'VoiceId not found: {model.voice}: {e}')
            logger.error(f'while loading model: voice_id not found')

        # OK to report changes after this
        self.enable_model_change_callback = True

    def pick_default_voice(self):
        # no preset loaded, pick a reasonable default voice which should work for most users
        # otherwise the voice will default to Forvo which is confusing for many people
        logger.info('pick_default_voice called, setting default voice to JennyMultilingualNeural')
        voice_id = voice_module.TtsVoiceId_v3(
            voice_key={'name': 'Microsoft Server Speech Text to Speech Voice (en-US, JennyMultilingualNeural)'}, 
            service='Azure')
        try:
            voice = self.hypertts.service_manager.locate_voice(voice_id)
            voice_index = self.voice_list.index(voice)
            self.voices_combobox.setCurrentIndex(voice_index)
        except ValueError as e:
            logger.warning(f'Voice not found: {voice_id}: {e}')
        except errors.VoiceIdNotFound as e:
            logger.warning(f'VoiceId not found: {voice_id}: {e}')