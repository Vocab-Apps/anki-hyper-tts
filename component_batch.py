import PyQt5
import logging

import component_common
import component_source
import component_target
import component_voiceselection
import component_batch_preview
import config_models


class ComponentBatch(component_common.ConfigComponentBase):
    def __init__(self, hypertts, note_id_list):
        self.hypertts = hypertts
        self.note_id_list = note_id_list

        self.source = component_source.BatchSource(self.hypertts, self.note_id_list, self.source_model_updated)
        self.target = component_target.BatchTarget(self.hypertts, self.note_id_list, self.target_model_updated)
        self.voice_selection = component_voiceselection.VoiceSelection(self.hypertts, self.voice_selection_model_updated)
        self.voice_selection.configure(['yo', 'yo'])
        self.preview = component_batch_preview.BatchPreview(self.hypertts, self.note_id_list)

        self.batch_model = config_models.BatchConfig()

    def load_model(self, model):
        pass

    def get_model(self):
        return None

    def source_model_updated(self, model):
        logging.info(f'source_model_updated: {model}')
        self.batch_model.set_source(model)

    def target_model_updated(self, model):
        logging.info('target_model_updated')
        self.batch_model.set_target(model)

    def voice_selection_model_updated(self, model):
        logging.info('voice_selection_model_updated')
        self.batch_model.set_voice_selection(model)

    def draw(self, layout):
        self.tabs = PyQt5.QtWidgets.QTabWidget()
        self.tab_source = PyQt5.QtWidgets.QWidget()
        self.tab_target = PyQt5.QtWidgets.QWidget()
        self.tab_voice_selection = PyQt5.QtWidgets.QWidget()
        self.tab_preview = PyQt5.QtWidgets.QWidget()

        self.tab_source.setLayout(self.source.draw())
        self.tab_target.setLayout(self.target.draw())
        self.tab_voice_selection.setLayout(self.voice_selection.draw())
        self.tab_preview.setLayout(self.preview.draw())

        self.tabs.addTab(self.tab_source, 'Source')
        self.tabs.addTab(self.tab_target, 'Target')
        self.tabs.addTab(self.tab_voice_selection, 'Voice Selection')
        self.tabs.addTab(self.tab_preview, 'Preview')

        # return self.tabs
        layout.addWidget(self.tabs)

