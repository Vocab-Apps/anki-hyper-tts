import PyQt5
import logging
import copy 

import constants
import voice
import config_models

class SelectedVoiceOptionBase():
    def __init__(self, voice_with_options, remove_callback):
        self.voice_with_options = voice_with_options
        self.remove_button = PyQt5.QtWidgets.QPushButton('Remove')
        self.remove_callback = remove_callback
    
class SelectedVoiceOptionRandom(SelectedVoiceOptionBase):
    def __init__(self, voice_with_options, remove_callback):
        SelectedVoiceOptionBase.__init__(self, voice_with_options, remove_callback)
        self.random_weight_widget = PyQt5.QtWidgets.QSpinBox()
        self.random_weight = 1
        self.random_weight_widget.setValue(self.random_weight)

    def set_weight(self, value):
        logging.info(f'set_weight: {value}')
        self.random_weight = value

    def draw(self, grid_layout, row):
        grid_layout.addWidget(PyQt5.QtWidgets.QLabel(str(self.voice_with_options)), row, 0, 1, 1)
        # weight
        grid_layout.addWidget(self.random_weight_widget, row, 1, 1, 1)
        # add handler for changing weight
        self.random_weight_widget.valueChanged.connect(self.set_weight)
        # remove button
        grid_layout.addWidget(self.remove_button, row, 2, 1, 1)
        self.remove_button.pressed.connect(self.remove)

    def remove(self):
        self.remove_callback(self)

class SelectedVoiceOptionPriority(SelectedVoiceOptionBase):
    def __init__(self, voice_with_options, remove_callback):
        SelectedVoiceOptionBase.__init__(self, voice_with_options, remove_callback)

    def draw(self, grid_layout, row):
        grid_layout.addWidget(PyQt5.QtWidgets.QLabel(str(self.voice_with_options)), row, 0, 1, 1)


class ComponentVoiceListBase():
    def __init__(self):
        self.widget = PyQt5.QtWidgets.QWidget()
        self.layout = PyQt5.QtWidgets.QVBoxLayout(self.widget)
        self.selected_voice_list = []

    def draw(self, layout):
        self.voice_list_grid_layout = PyQt5.QtWidgets.QGridLayout()
        self.layout.addLayout(self.voice_list_grid_layout)

        # add ourselves to the parent
        layout.addWidget(self.widget)
        self.widget.setVisible(False)

    def clear_voices(self):
        logging.info('clear_voices')
        # remove everything from layout self.voice_mode_random_voice_list
        self.clear_voices_widget()
        self.selected_voice_list = []

    def clear_voices_widget(self):
        for i in reversed(range(self.voice_list_grid_layout.count())): 
            self.voice_list_grid_layout.itemAt(i).widget().setParent(None)

    def redraw_voices(self):
        for row in range(len(self.selected_voice_list)):
            self.selected_voice_list[row].draw(self.voice_list_grid_layout, row)

    def setVisible(self, visible):
        self.widget.setVisible(visible)

    def remove_voice(self, obj):
        self.clear_voices_widget()
        self.selected_voice_list.remove(obj) # locate by pointer
        self.redraw_voices()


class ComponentRandomVoiceList(ComponentVoiceListBase):
    def __init__(self):
        ComponentVoiceListBase.__init__(self)
        self.layout.addWidget(PyQt5.QtWidgets.QLabel('Voice List (Random)'))

    def add_voice_with_options(self, voice_with_options):
        logging.info('add_voice_with_options')
        row = len(self.selected_voice_list)
        self.selected_voice_list.append(SelectedVoiceOptionRandom(voice_with_options, self.remove_voice))
        self.selected_voice_list[-1].draw(self.voice_list_grid_layout, row)


class ComponentPriorityVoiceList(ComponentVoiceListBase):
    def __init__(self):
        ComponentVoiceListBase.__init__(self)
        self.layout.addWidget(PyQt5.QtWidgets.QLabel('Voice List (Priority)'))

    def add_voice_with_options(self, voice_with_options):
        logging.info('add_voice_with_options')
        row = len(self.voice_with_option_list)
        self.voice_with_option_list.append(voice_with_options)
        self.voice_list_grid_layout.addWidget(PyQt5.QtWidgets.QLabel(str(voice_with_options)), row, 0, 1, 1)


class VoiceSelection():
    def __init__(self, hypertts):
        self.hypertts = hypertts

    def get_voices(self):
        self.voice_list = self.hypertts.service_manager.full_voice_list()

        languages = set()
        audio_languages = set()
        services = set()
        genders = set()

        for voice in self.voice_list:
            audio_languages.add(voice.language)
            languages.add(voice.language.lang)
            services.add(voice.service.name)
            genders.add(voice.gender)

        self.audio_languages = list(audio_languages)
        self.languages = list(languages)
        self.services = list(services)
        self.genders = list(genders)

        self.set_default_selection_model()


    def set_default_selection_model(self):
        self.voice_selection_model = config_models.VoiceSelectionSingle() # default
        # pick first voice
        self.voice_selection_model.set_voice(config_models.VoiceWithOptions(self.voice_list[0], {}))

    def populate_combobox(self, combobox, items):
        combobox.addItem(constants.LABEL_FILTER_ALL)
        combobox.insertSeparator(1)
        combobox.addItems(items)

    def draw(self, layout):
        # filters:
        # - language
        # - locale
        # - service
        # - gender

        # 1. get full voice list
        # 2. iterate over the list, gather attributes
        # 3. populate filters
        # 4. draw all voices


        self.get_voices()

        self.voices_layout = PyQt5.QtWidgets.QVBoxLayout()
        layout.addLayout(self.voices_layout)

        self.audio_languages_combobox = PyQt5.QtWidgets.QComboBox()
        self.languages_combobox = PyQt5.QtWidgets.QComboBox()
        self.services_combobox = PyQt5.QtWidgets.QComboBox()
        self.genders_combobox = PyQt5.QtWidgets.QComboBox()
        self.voices_combobox = PyQt5.QtWidgets.QComboBox()

        self.reset_filters_button = PyQt5.QtWidgets.QPushButton('Reset Filters')

        self.populate_combobox(self.audio_languages_combobox, [audio_lang.audio_lang_name for audio_lang in self.audio_languages])
        self.populate_combobox(self.languages_combobox, [language.lang_name for language in self.languages])
        self.populate_combobox(self.services_combobox, self.services)
        self.populate_combobox(self.genders_combobox, [gender.name for gender in self.genders])

        self.voices_layout.addWidget(self.audio_languages_combobox)
        self.voices_layout.addWidget(self.languages_combobox)
        self.voices_layout.addWidget(self.services_combobox)
        self.voices_layout.addWidget(self.genders_combobox)
        self.voices_layout.addWidget(self.reset_filters_button)
        self.voices_layout.addWidget(self.voices_combobox)

        self.voice_options_layout = PyQt5.QtWidgets.QVBoxLayout()
        self.voices_layout.addLayout(self.voice_options_layout)


        # voice selection mode
        # ====================
        mode_group = PyQt5.QtWidgets.QButtonGroup()
        self.radio_button_single = PyQt5.QtWidgets.QRadioButton('Single')
        self.radio_button_random = PyQt5.QtWidgets.QRadioButton('Random')
        self.radio_button_priority = PyQt5.QtWidgets.QRadioButton('Priority')
        mode_group.addButton(self.radio_button_single)
        mode_group.addButton(self.radio_button_random)
        mode_group.addButton(self.radio_button_priority)
        #self.voices_layout.addWidget(mode_group)
        self.voices_layout.addWidget(self.radio_button_single)
        self.voices_layout.addWidget(self.radio_button_random)
        self.voices_layout.addWidget(self.radio_button_priority)


        # buttons
        # =======

        self.add_voice_button = PyQt5.QtWidgets.QPushButton('Add Voice')
        self.clear_voices_button = PyQt5.QtWidgets.QPushButton('Remove all Voices')

        self.voices_layout.addWidget(self.add_voice_button)
        self.voices_layout.addWidget(self.clear_voices_button)

        # hide buttons by default
        self.add_voice_button.setVisible(False)
        self.clear_voices_button.setVisible(False)

        # additional layouts screens for the various modes
        # ================================================

        self.voice_list_grid_layout = PyQt5.QtWidgets.QGridLayout()
        self.voices_layout.addLayout(self.voice_list_grid_layout)

        # set some defaults
        # =================
        self.radio_button_single.setChecked(True)

        # wire all events
        # ===============

        self.audio_languages_combobox.currentIndexChanged.connect(self.filter_and_draw_voices)
        self.languages_combobox.currentIndexChanged.connect(self.filter_and_draw_voices)
        self.services_combobox.currentIndexChanged.connect(self.filter_and_draw_voices)
        self.genders_combobox.currentIndexChanged.connect(self.filter_and_draw_voices)

        self.voices_combobox.currentIndexChanged.connect(self.voice_selected)

        self.reset_filters_button.pressed.connect(self.reset_filters)

        self.radio_button_single.toggled.connect(self.voice_selection_mode_change)
        self.radio_button_random.toggled.connect(self.voice_selection_mode_change)
        self.radio_button_priority.toggled.connect(self.voice_selection_mode_change)

        self.add_voice_button.pressed.connect(self.add_voice)
        self.clear_voices_button.pressed.connect(self.clear_voices)

        self.filter_and_draw_voices(0)

    def voice_selection_mode_change(self):
        if self.radio_button_single.isChecked():
            self.add_voice_button.setVisible(False)
            self.clear_voices_button.setVisible(False)
            self.voice_selection_model = config_models.VoiceSelectionSingle()
        elif self.radio_button_random.isChecked():
            self.add_voice_button.setVisible(True)
            self.clear_voices_button.setVisible(True)
            self.voice_selection_model = config_models.VoiceSelectionRandom()
        elif self.radio_button_priority.isChecked():
            self.add_voice_button.setVisible(True)
            self.clear_voices_button.setVisible(True)
            self.voice_selection_model = config_models.VoiceSelectionPriority()
        self.redraw_selected_voices()

    def reset_filters(self):
        self.audio_languages_combobox.setCurrentIndex(0)
        self.languages_combobox.setCurrentIndex(0)
        self.services_combobox.setCurrentIndex(0)
        self.genders_combobox.setCurrentIndex(0)


    def add_voice(self):
        selected_voice = self.filtered_voice_list[self.voices_combobox.currentIndex()]
        options = copy.copy(self.current_voice_options)

        if self.radio_button_random.isChecked():
            self.voice_selection_model.add_voice(config_models.VoiceWithOptionsRandom(selected_voice, options))
        elif self.radio_button_priority.isChecked():
            self.voice_selection_model.add_voice(config_models.VoiceWithOptionsPriority(selected_voice, options))

        self.redraw_selected_voices()


    def clear_voices(self):
        if self.radio_button_random.isChecked():
            self.component_random_voice_list.clear_voices()
        elif self.radio_button_priority.isChecked():
            self.component_priority_voice_list.clear_voices()

    def voice_selected(self, current_index):
        voice = self.filtered_voice_list[current_index]
        logging.info(f'voice_selected: {voice} options: {voice.options}')

        # clear the options layout
        for i in reversed(range(self.voice_options_layout.count())): 
            self.voice_options_layout.itemAt(i).widget().setParent(None)

        # clear the current voice options
        self.current_voice_options = {}

        def get_set_option_lambda(voice, key):
            def set_value(value):
                self.current_voice_options[key] = value
                logging.info(f'set option {key} to {value}')
                if self.voice_selection_model.selection_mode == constants.VoiceSelectionMode.single:
                    self.voice_selection_model.set_voice(config_models.VoiceWithOptions(voice, self.current_voice_options))
            return set_value

        # populate voice options layout
        for key, value in voice.options.items():
            widget_name = f'voice_option_{key}'
            option_type = constants.VoiceOptionTypes[value['type']]
            if option_type == constants.VoiceOptionTypes.number:
                # create a spinner
                widget = PyQt5.QtWidgets.QDoubleSpinBox()
                widget.setObjectName(widget_name)
                widget.setRange(value['min'], value['max'])
                widget.setValue(value['default'])
                widget.valueChanged.connect(get_set_option_lambda(voice, key))
                self.voice_options_layout.addWidget(widget)
            else:
                raise Exception(f"voice option type not supported: {value['type']}")

        # if we are in the single voice mode, set the mode on the voice selection model
        if self.voice_selection_model.selection_mode == constants.VoiceSelectionMode.single:
            self.voice_selection_model.set_voice(config_models.VoiceWithOptions(voice, {}))

    def filter_and_draw_voices(self, current_index):
        logging.info('filter_and_draw_voices')
        voice_list = self.voice_list
        # check filtering by audio language
        if self.audio_languages_combobox.currentIndex() != 0:
            audio_language = self.audio_languages[self.audio_languages_combobox.currentIndex() - 2]
            voice_list = [voice for voice in voice_list if voice.language == audio_language]
        # check filtering by language
        if self.languages_combobox.currentIndex() != 0:
            language = self.languages[self.languages_combobox.currentIndex() - 2]
            voice_list = [voice for voice in voice_list if voice.language.lang == language]
        # check filtering by service
        if self.services_combobox.currentIndex() != 0:
            service = self.services[self.services_combobox.currentIndex() - 2]
            voice_list = [voice for voice in voice_list if voice.service.name == service] 
        # check filtering by gender
        if self.genders_combobox.currentIndex() != 0:
            gender = self.genders[self.genders_combobox.currentIndex() - 2]
            voice_list = [voice for voice in voice_list if voice.gender == gender]
        self.filtered_voice_list = voice_list
        self.draw_all_voices(self.filtered_voice_list)

    def draw_all_voices(self, voice_list):
        self.voices_combobox.clear()
        self.voices_combobox.addItems([str(voice) for voice in voice_list])

    def redraw_selected_voices(self):
        if isinstance(self.voice_selection_model, config_models.VoiceSelectionSingle):
            # don't draw if used chose single voice
            return

        def get_remove_lambda(selection_model, voice_with_options_random, redraw_fn):
            def remove():
                # remove this entry (locate by equality)
                selection_model.voice_list.remove(voice_with_options_random)
                redraw_fn()
            return remove

        def get_move_up_lambda(selection_model, voice_with_options_priority, redraw_fn):
            def up():
                selection_model.move_up_voice(voice_with_options_priority)
                redraw_fn()
            return up

        def get_move_down_lambda(selection_model, voice_with_options_priority, redraw_fn):
            def down():
                selection_model.move_down_voice(voice_with_options_priority)
                redraw_fn()
            return down

        
        # clear all voices first
        for i in reversed(range(self.voice_list_grid_layout.count())): 
            self.voice_list_grid_layout.itemAt(i).widget().setParent(None)
        # draw all voices
        row = 0
        for voice_entry in self.voice_selection_model.voice_list:
            column_index = 0
            self.voice_list_grid_layout.addWidget(PyQt5.QtWidgets.QLabel(str(voice_entry)), row, column_index, 1, 1)
            column_index += 1
            if isinstance(self.voice_selection_model, config_models.VoiceSelectionRandom):
                # add weight widget
                weight_widget = PyQt5.QtWidgets.QSpinBox()
                weight_widget.setValue(voice_entry.random_weight)
                weight_widget.valueChanged.connect(voice_entry.set_random_weight)
                self.voice_list_grid_layout.addWidget(weight_widget, row, column_index, 1, 1)
                column_index += 1
            # add remove button
            remove_button = PyQt5.QtWidgets.QPushButton('Remove')
            self.voice_list_grid_layout.addWidget(remove_button, row, column_index, 1, 1)
            column_index += 1
            remove_button.pressed.connect(get_remove_lambda(self.voice_selection_model, voice_entry, self.redraw_selected_voices))
            # add up/down buttons
            if isinstance(self.voice_selection_model, config_models.VoiceSelectionPriority):
                # add weight widget
                up_button = PyQt5.QtWidgets.QPushButton('Up')
                down_button = PyQt5.QtWidgets.QPushButton('Down')
                up_button.pressed.connect(get_move_up_lambda(self.voice_selection_model, voice_entry, self.redraw_selected_voices))
                down_button.pressed.connect(get_move_down_lambda(self.voice_selection_model, voice_entry, self.redraw_selected_voices))

                self.voice_list_grid_layout.addWidget(up_button, row, column_index, 1, 1)
                column_index += 1
                self.voice_list_grid_layout.addWidget(down_button, row, column_index, 1, 1)
                column_index += 1

            row += 1

    def serialize(self):
        return self.voice_selection_model.serialize()
