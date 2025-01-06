import aqt.qt
from . import component_voiceselection
from . import config_models
from . import constants
from . import logging_utils

logger = logging_utils.get_child_logger(__name__)

class VoiceSelectionEasy(component_voiceselection.VoiceSelection):
    def __init__(self, hypertts, dialog, model_change_callback):
        self.model = config_models.VoiceSelectionSingle()
        super().__init__(hypertts, dialog, model_change_callback)
        self.enable_model_change_callback = True

    def draw(self):
        vlayout = aqt.qt.QVBoxLayout()
        
        # Get voice list and populate combo boxes
        self.get_voices()
        
        # Language filter
        hlayout = aqt.qt.QHBoxLayout()
        hlayout.addWidget(aqt.qt.QLabel('Language:'))
        hlayout.addWidget(self.languages_combobox)
        vlayout.addLayout(hlayout)

        # Service filter
        hlayout = aqt.qt.QHBoxLayout()
        hlayout.addWidget(aqt.qt.QLabel('Service:'))
        hlayout.addWidget(self.services_combobox)
        vlayout.addLayout(hlayout)

        # Voice selection combo box
        hlayout = aqt.qt.QHBoxLayout()
        hlayout.addWidget(aqt.qt.QLabel('Voice:'))
        hlayout.addWidget(self.voices_combobox)
        vlayout.addLayout(hlayout)

        self.populate_combobox(self.audio_languages_combobox, [audio_lang.audio_lang_name for audio_lang in self.audio_languages])
        self.populate_combobox(self.languages_combobox, [language.lang_name for language in self.languages])
        self.populate_combobox(self.services_combobox, self.services)
        self.populate_combobox(self.genders_combobox, [gender.name for gender in self.genders])

        # Wire up events
        self.languages_combobox.currentIndexChanged.connect(self.filter_and_draw_voices)
        self.services_combobox.currentIndexChanged.connect(self.filter_and_draw_voices)
        self.voices_combobox.currentIndexChanged.connect(self.voice_selected)

        widget = aqt.qt.QWidget()
        widget.setLayout(vlayout)
        
        # Initialize voice list
        self.filter_and_draw_voices(0)
        
        return widget

    def voice_selected(self, current_index):
        voice = self.filtered_voice_list[current_index]
        logger.info(f'voice_selected: {voice} options: {voice.options}')
        self.voice_selection_model.set_voice(config_models.VoiceWithOptions(voice.voice_id, {}))
        self.notify_model_update()        


    def load_model(self, model):
        # don't report changes back to parent dialog as we adjust widgets
        self.enable_model_change_callback = False
        logger.info(f'load_model, model: {model}')

        # here we need to select the correct voice, based on what the user has saved in their preset (single voice)
        # we have access to the voice_id, but we need to locate the proper voice
        voice_id = model.voice.voice_id
        voice = self.hypertts.service_manager.locate_voice(voice_id)
        voice_index = self.voice_list.index(voice)
        self.voices_combobox.setCurrentIndex(voice_index)

        # OK to report changes after this
        self.enable_model_change_callback = True