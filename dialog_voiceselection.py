import sys
import PyQt5

if hasattr(sys, '_pytest_mode'):
    import constants
    import deck_utils
    import gui_utils
    import errors
    from languagetools import LanguageTools
else:
    from . import constants
    from . import deck_utils
    from . import gui_utils
    from . import errors
    from .languagetools import LanguageTools

class VoiceSelectionDialog(PyQt5.QtWidgets.QDialog):
    def __init__(self, languagetools: LanguageTools, voice_list):
        super(PyQt5.QtWidgets.QDialog, self).__init__()
        self.languagetools = languagetools
        
        # get list of languages
        self.voice_list = voice_list
        wanted_language_arrays = languagetools.get_wanted_language_arrays()
        self.language_name_list = wanted_language_arrays['language_name_list']
        self.language_code_list = wanted_language_arrays['language_code_list']

        self.sample_size = 10

        self.voice_selection_settings = self.languagetools.get_voice_selection_settings()

        self.voice_mapping_changes = {} # indexed by language code

        self.voice_select_callback_enabled = True

    def setupUi(self):
        self.setWindowTitle(constants.ADDON_NAME)
        self.resize(700, 500)

        vlayout = PyQt5.QtWidgets.QVBoxLayout(self)

        vlayout.addWidget(gui_utils.get_header_label('Audio Voice Selection'))

        # setup grid
        # ==========

        gridlayout = PyQt5.QtWidgets.QGridLayout()

        label_font_size = 13
        font1 = PyQt5.QtGui.QFont()
        font1.setBold(True)
        font1.setPointSize(label_font_size)

        # language

        language_label = PyQt5.QtWidgets.QLabel()
        language_label.setText('Language:')
        language_label.setFont(font1)
        gridlayout.addWidget(language_label, 0, 0, 1, 1)

        language_combobox = PyQt5.QtWidgets.QComboBox()
        language_combobox.addItems(self.language_name_list)
        language_combobox.setObjectName('languages_combobox')
        gridlayout.addWidget(language_combobox, 0, 1, 1, 1)

        # voices

        voice_label = PyQt5.QtWidgets.QLabel()
        voice_label.setText('Voice:')
        voice_label.setFont(font1)
        gridlayout.addWidget(voice_label, 1, 0, 1, 1)

        self.voice_combobox = PyQt5.QtWidgets.QComboBox()
        self.voice_combobox.setMaxVisibleItems(15)
        self.voice_combobox.setStyleSheet("combobox-popup: 0;")        
        self.voice_combobox.setObjectName('voices_combobox')
        gridlayout.addWidget(self.voice_combobox, 1, 1, 1, 1)

        # button to refresh samples
        samples_label = PyQt5.QtWidgets.QLabel()
        samples_label.setText('Random Samples:')
        samples_label.setFont(font1)
        gridlayout.addWidget(samples_label, 2, 0, 1, 1)

        samples_reload_button = PyQt5.QtWidgets.QPushButton()
        samples_reload_button.setText('Reload Random Samples')
        gridlayout.addWidget(samples_reload_button, 2, 1, 1, 1)

        gridlayout.setContentsMargins(10, 20, 10, 0)
        vlayout.addLayout(gridlayout)

        # samples, 
        self.samples_gridlayout = PyQt5.QtWidgets.QGridLayout()
        self.sample_labels = []
        self.sample_play_buttons = []
        for i in range(self.sample_size):
            sample_label = PyQt5.QtWidgets.QLabel()
            sample_label.setText('sample')
            self.sample_labels.append(sample_label)
            sample_button = PyQt5.QtWidgets.QPushButton()
            sample_button.setText('Play Audio')
            sample_button.setObjectName(f'play_sample_{i}')
            def get_play_lambda(i):
                def play():
                    self.play_sample(i)
                return play
            sample_button.pressed.connect(get_play_lambda(i))
            self.sample_play_buttons.append(sample_button)
            self.samples_gridlayout.addWidget(sample_label, i, 0, 1, 1)
            self.samples_gridlayout.addWidget(sample_button, i, 1, 1, 1)
        self.samples_gridlayout.setColumnStretch(0, 70)
        self.samples_gridlayout.setColumnStretch(1, 30)
        self.samples_gridlayout.setContentsMargins(20, 20, 20, 20)
        vlayout.addLayout(self.samples_gridlayout)

        vlayout.addStretch()

        # buttom buttons
        buttonBox = PyQt5.QtWidgets.QDialogButtonBox()
        self.applyButton = buttonBox.addButton("Save Voice Selection", PyQt5.QtWidgets.QDialogButtonBox.AcceptRole)
        self.applyButton.setObjectName('apply')
        self.applyButton.setEnabled(False)
        self.cancelButton = buttonBox.addButton("Cancel", PyQt5.QtWidgets.QDialogButtonBox.RejectRole)
        self.cancelButton.setObjectName('cancel')
        self.cancelButton.setStyleSheet(self.languagetools.anki_utils.get_red_stylesheet())
        vlayout.addWidget(buttonBox)

        # wire events
        # ===========

        language_combobox.currentIndexChanged.connect(self.language_index_changed)
        # run once
        self.language_index_changed(0)
        self.voice_combobox.currentIndexChanged.connect(self.voice_index_changed)

        samples_reload_button.pressed.connect(self.load_field_samples)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

    def language_index_changed(self, current_index):
        self.voice_select_callback_enabled = False
        self.language_code = self.language_code_list[current_index]
        self.language_name = self.language_name_list[current_index]
        # filter voices that match this language
        available_voices = [x for x in self.voice_list if x['language_code'] == self.language_code]
        self.available_voices = sorted(available_voices, key=lambda x: x['voice_description'])
        available_voice_mappings = self.available_voices
        available_voice_names = [x['voice_description'] for x in self.available_voices]
        self.voice_combobox.clear()
        self.voice_combobox.addItems(available_voice_names)
        # do we have a required change for this language already ?
        voice_index = 0
        if self.language_code in self.voice_mapping_changes:
            try:
                voice_index = available_voice_mappings.index(self.voice_mapping_changes[self.language_code])
            except ValueError:
                pass
            # print(f'found language_code {self.language_code} in voice_mapping_changes: {voice_index}')
        elif self.language_code in self.voice_selection_settings:
            try:
                voice_index = available_voice_mappings.index(self.voice_selection_settings[self.language_code])
            except ValueError:
                pass                
            # print(f'found language_code {self.language_code} in voice_selection_settings: {voice_index}')
        self.voice_combobox.setCurrentIndex(voice_index)

        self.load_field_samples()

        self.voice_select_callback_enabled = True

    def voice_index_changed(self, current_index):
        if self.voice_select_callback_enabled:
            voice = self.available_voices[current_index]
            change_required = False
            if self.language_code not in self.voice_selection_settings:
                change_required = True
            elif self.voice_selection_settings[self.language_code] != voice:
                change_required = True

            if change_required:
                self.voice_mapping_changes[self.language_code] = voice
                # print(f'voice_mapping_changes: {self.voice_mapping_changes}')
                self.applyButton.setEnabled(True)
                self.applyButton.setStyleSheet(self.languagetools.anki_utils.get_green_stylesheet())

    def load_field_samples(self):
        # get sample
        self.field_samples = self.languagetools.get_field_samples_for_language(self.language_code, self.sample_size)
        # print(self.field_samples)
        for i in range(self.sample_size):
            if i < len(self.field_samples):
                # populate label
                self.sample_labels[i].setText(self.field_samples[i])
            else:
                self.sample_labels[i].setText('empty')

    def play_sample(self, i):
        if i < len(self.field_samples):
            source_text = self.field_samples[i]
            if len(self.available_voices) == 0:
                # no voice available
                self.languagetools.anki_utils.critical_message(f'No voice available for {self.language_name}', self)
                return
            # get index of voice
            voice_index = self.voice_combobox.currentIndex()
            voice = self.available_voices[voice_index]

            self.sample_play_buttons[i].setText('Loading...')
            self.sample_play_buttons[i].setDisabled(True)
            self.languagetools.anki_utils.run_in_background(lambda: self.play_audio(source_text, voice), lambda x: self.play_audio_done(x, i))


    def play_audio(self, source_text, voice):
        self.play_audio_error = None
        voice_key = voice['voice_key']
        service = voice['service']
        language_code = voice['language_code']

        try:
            self.languagetools.play_tts_audio(source_text, service, language_code, voice_key, {})
        except errors.LanguageToolsRequestError as err:
            self.play_audio_error = str(err)

    def play_audio_done(self, future_result, i):
        self.sample_play_buttons[i].setText('Play Audio')
        self.sample_play_buttons[i].setDisabled(False)

        if self.play_audio_error != None:
            self.languagetools.anki_utils.critical_message(f'Could not play audio: {self.play_audio_error}', self)

    def accept(self):
        for language_code, voice_mapping in self.voice_mapping_changes.items():
            self.languagetools.store_voice_selection(language_code, voice_mapping)
        self.close()


def prepare_voice_selection_dialog(languagetools, voice_list):
    voice_selection_dialog = VoiceSelectionDialog(languagetools, voice_list)
    voice_selection_dialog.setupUi()
    return voice_selection_dialog

def voice_selection_dialog(languagetools, parent_window):
    # did the user perform language mapping ? 
    if not languagetools.language_detection_done():
        languagetools.anki_utils.info_message('Please setup Language Mappings, from the Anki main screen: Tools -> Language Tools: Language Mapping', parent_window)
        return

    voice_selection_dialog = prepare_voice_selection_dialog(languagetools, languagetools.voice_list)
    voice_selection_dialog.exec_()            
