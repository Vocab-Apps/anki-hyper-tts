import sys
import PyQt5
import logging

component_common = __import__('component_common', globals(), locals(), [], sys._addon_import_level_base)
component_source = __import__('component_source', globals(), locals(), [], sys._addon_import_level_base)
component_target = __import__('component_target', globals(), locals(), [], sys._addon_import_level_base)
component_voiceselection = __import__('component_voiceselection', globals(), locals(), [], sys._addon_import_level_base)
component_batch_preview = __import__('component_batch_preview', globals(), locals(), [], sys._addon_import_level_base)
component_label_preview = __import__('component_label_preview', globals(), locals(), [], sys._addon_import_level_base)
config_models = __import__('config_models', globals(), locals(), [], sys._addon_import_level_base)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_base)


class ComponentBatch(component_common.ConfigComponentBase):
    def __init__(self, hypertts, dialog):
        self.hypertts = hypertts
        self.dialog = dialog
        self.batch_model = config_models.BatchConfig()

    def configure_browser(self, note_id_list):
        self.note_id_list = note_id_list
        field_list = self.hypertts.get_all_fields_from_notes(note_id_list)
        self.source = component_source.BatchSource(self.hypertts, field_list, self.source_model_updated)
        self.target = component_target.BatchTarget(self.hypertts, field_list, self.target_model_updated)
        self.voice_selection = component_voiceselection.VoiceSelection(self.hypertts, self.voice_selection_model_updated)        
        self.preview = component_batch_preview.BatchPreview(self.hypertts, self.note_id_list, self.sample_selected)
        self.editor_mode = False

    def configure_editor(self, note, add_mode):
        self.note = note
        self.add_mode = add_mode
        field_list = list(self.note.keys())
        self.source = component_source.BatchSource(self.hypertts, field_list, self.source_model_updated)
        self.target = component_target.BatchTarget(self.hypertts, field_list, self.target_model_updated)
        self.voice_selection = component_voiceselection.VoiceSelection(self.hypertts, self.voice_selection_model_updated)        
        self.preview = component_label_preview.LabelPreview(self.hypertts, note)
        self.editor_mode = True

    def load_batch(self, batch_name):
        batch = self.hypertts.load_batch_config(batch_name)
        self.load_model(batch)
        self.profile_name_combobox.setCurrentText(batch_name)

    def load_model(self, model):
        self.batch_model = model
        # disseminate to all components
        self.source.load_model(model.source)
        self.target.load_model(model.target)
        self.voice_selection.load_model(model.voice_selection)
        self.preview.load_model(self.batch_model)

    def get_model(self):
        return self.batch_model

    def source_model_updated(self, model):
        logging.info(f'source_model_updated: {model}')
        self.batch_model.set_source(model)
        self.preview.load_model(self.batch_model)

    def target_model_updated(self, model):
        logging.info('target_model_updated')
        self.batch_model.set_target(model)
        self.preview.load_model(self.batch_model)

    def voice_selection_model_updated(self, model):
        logging.info('voice_selection_model_updated')
        self.batch_model.set_voice_selection(model)
        self.preview.load_model(self.batch_model)

    def sample_selected(self, text):
        self.voice_selection.sample_text_selected(text)

    def draw(self, layout):
        self.vlayout = PyQt5.QtWidgets.QVBoxLayout()

        hlayout = PyQt5.QtWidgets.QHBoxLayout()
        self.profile_name_combobox = PyQt5.QtWidgets.QComboBox()
        self.profile_name_combobox.setEditable(True)
        # populate with existing profile names
        profile_name_list = [self.hypertts.get_next_batch_name()] + self.hypertts.get_batch_config_list()
        self.profile_name_combobox.addItems(profile_name_list)

        hlayout.addWidget(self.profile_name_combobox)
        self.profile_load_button = PyQt5.QtWidgets.QPushButton('Load')
        hlayout.addWidget(self.profile_load_button)
        self.profile_save_button = PyQt5.QtWidgets.QPushButton('Save')
        hlayout.addWidget(self.profile_save_button)
        self.vlayout.addLayout(hlayout)

        self.profile_load_button.pressed.connect(self.load_profile_button_pressed)
        self.profile_save_button.pressed.connect(self.save_profile_button_pressed)

        self.tabs = PyQt5.QtWidgets.QTabWidget()
        self.tab_source = PyQt5.QtWidgets.QWidget()
        self.tab_target = PyQt5.QtWidgets.QWidget()
        self.tab_voice_selection = PyQt5.QtWidgets.QWidget()

        self.tab_source.setLayout(self.source.draw())
        self.tab_target.setLayout(self.target.draw())
        self.tab_voice_selection.setLayout(self.voice_selection.draw())

        self.tabs.addTab(self.tab_source, 'Source')
        self.tabs.addTab(self.tab_target, 'Target')
        self.tabs.addTab(self.tab_voice_selection, 'Voice Selection')


        if self.editor_mode == False:
            self.splitter = PyQt5.QtWidgets.QSplitter(PyQt5.QtCore.Qt.Horizontal)
            self.splitter.addWidget(self.tabs)

            self.preview_widget = PyQt5.QtWidgets.QWidget()
            self.preview_widget.setLayout(self.preview.draw())
            self.splitter.addWidget(self.preview_widget)
            self.vlayout.addWidget(self.splitter)
        else:
            self.vlayout.addWidget(self.tabs)
            self.preview_widget = PyQt5.QtWidgets.QWidget()
            self.preview_widget.setLayout(self.preview.draw())            
            self.vlayout.addWidget(self.preview_widget)

        # return self.tabs

        # setup bottom buttons
        hlayout = PyQt5.QtWidgets.QHBoxLayout()
        hlayout.addStretch()
        self.preview_sound_button = PyQt5.QtWidgets.QPushButton('Preview Sound')
        hlayout.addWidget(self.preview_sound_button)
        apply_label_text = 'Apply To Notes'
        if self.editor_mode:
            apply_label_text = 'Apply To Note'
        self.apply_button = PyQt5.QtWidgets.QPushButton(apply_label_text)
        self.apply_button.setStyleSheet(self.hypertts.anki_utils.get_green_stylesheet())
        hlayout.addWidget(self.apply_button)
        self.cancel_button = PyQt5.QtWidgets.QPushButton('Cancel')
        self.cancel_button.setStyleSheet(self.hypertts.anki_utils.get_red_stylesheet())
        hlayout.addWidget(self.cancel_button)
        self.vlayout.addLayout(hlayout)

        self.preview_sound_button.pressed.connect(self.sound_preview_button_pressed)
        self.apply_button.pressed.connect(self.apply_button_pressed)
        self.cancel_button.pressed.connect(self.cancel_button_pressed)

        layout.addLayout(self.vlayout)

    def load_profile_button_pressed(self):
        profile_name = self.profile_name_combobox.currentText()
        self.load_model(self.hypertts.load_batch_config(profile_name))

    def save_profile_button_pressed(self):
        profile_name = self.profile_name_combobox.currentText()
        self.hypertts.save_batch_config(profile_name, self.get_model())

    def sound_preview_button_pressed(self):
        if self.editor_mode:
            self.hypertts.preview_note_audio(self.batch_model, self.note)
        else:
            pass

    def apply_button_pressed(self):
        logging.info('apply_button_pressed')
        if self.editor_mode:
            self.apply_button.setEnabled(False)
            self.cancel_button.setEnabled(False)
            self.apply_button.setText('Loading...')
            self.hypertts.editor_note_add_audio(self.batch_model, self.note, self.add_mode)
            self.dialog.close()
        else:
            pass

    def cancel_button_pressed(self):
        pass