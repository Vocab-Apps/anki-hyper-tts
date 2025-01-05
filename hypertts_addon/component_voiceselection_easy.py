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
        self.populate_combobox(self.languages_combobox, [language.lang_name for language in self.languages])
        hlayout.addWidget(self.languages_combobox)
        vlayout.addLayout(hlayout)

        # Service filter
        hlayout = aqt.qt.QHBoxLayout()
        hlayout.addWidget(aqt.qt.QLabel('Service:'))
        self.populate_combobox(self.services_combobox, self.services)
        hlayout.addWidget(self.services_combobox)
        vlayout.addLayout(hlayout)

        # Voice selection combo box
        hlayout = aqt.qt.QHBoxLayout()
        hlayout.addWidget(aqt.qt.QLabel('Voice:'))
        self.voice_combobox = aqt.qt.QComboBox()
        self.voice_combobox.currentIndexChanged.connect(self.voice_selected)
        hlayout.addWidget(self.voice_combobox)
        vlayout.addLayout(hlayout)

        # Wire up events
        self.languages_combobox.currentIndexChanged.connect(self.language_changed)
        self.services_combobox.currentIndexChanged.connect(self.service_changed)

        widget = aqt.qt.QWidget()
        widget.setLayout(vlayout)
        
        # Initialize voice list
        self.update_voice_list()
        
        return widget

    def voice_selected(self, index):
        if index >= 0 and self.enable_model_change_callback:
            voice = self.filtered_voice_list[index]
            self.model.voice_list = [voice]
            self.notify_model_update()

    def update_voice_list(self):
        self.filtered_voice_list = self.get_filtered_voice_list()
        voice_display_list = [f'{voice.name} ({voice.service.name})' for voice in self.filtered_voice_list]
        self.voice_combobox.clear()
        self.populate_combobox(self.voice_combobox, voice_display_list)

    def language_changed(self, index):
        if index >= 0 and self.enable_model_change_callback:
            self.update_voice_list()
            if len(self.filtered_voice_list) > 0:
                self.model.voice_list = [self.filtered_voice_list[0]]
                self.notify_model_update()

    def service_changed(self, index):
        if index >= 0 and self.enable_model_change_callback:
            self.update_voice_list()
            if len(self.filtered_voice_list) > 0:
                self.model.voice_list = [self.filtered_voice_list[0]]
                self.notify_model_update()

    def load_model(self, model):
        self.enable_model_change_callback = False
        super().load_model(model)
        # Update voice combobox
        self.update_voice_list()
        if len(model.voice_list) > 0:
            voice = model.voice_list[0]
            index = self.filtered_voice_list.index(voice)
            self.voice_combobox.setCurrentIndex(index)
        self.enable_model_change_callback = True
