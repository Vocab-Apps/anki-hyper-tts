import sys
import logging
from typing import List, Dict
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

class LanguageMappingDeckWidgets(object):
    def __init__(self):
        pass

class LanguageMappingNoteTypeWidgets(object):
    def __init__(self):
        pass

class LanguageMappingFieldWidgets(object):
    def __init__(self):
        pass


class LanguageMappingDialog_UI(object):
    def __init__(self, languagetools: LanguageTools, dialog):
        self.languagetools: LanguageTools = languagetools
        self.dialog = dialog
        
        # do some processing on languages
        data = languagetools.get_all_language_arrays()
        self.language_name_list = data['language_name_list']
        self.language_code_list = data['language_code_list']
        self.language_name_list.append('Not Set')

        self.language_mapping_changes = {}

        self.deckWidgetMap = {}
        self.deckNoteTypeWidgetMap = {}
        self.fieldWidgetMap = {}

        self.dntfComboxBoxMap = {}

        self.autodetect_in_progress = False
        self.interrupt_autodetect = False

    def setupUi(self, Dialog, deck_map: Dict[str, deck_utils.Deck]):
        Dialog.setObjectName("Dialog")
        Dialog.resize(700, 800)

        self.Dialog = Dialog

        self.topLevel = PyQt5.QtWidgets.QVBoxLayout(Dialog)

        self.scrollArea = PyQt5.QtWidgets.QScrollArea()
        
        self.scrollArea.setVerticalScrollBarPolicy(PyQt5.QtCore.Qt.ScrollBarAlwaysOn)
        self.scrollArea.setHorizontalScrollBarPolicy(PyQt5.QtCore.Qt.ScrollBarAlwaysOff)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName("scrollArea")

        self.layoutWidget = PyQt5.QtWidgets.QWidget()
        self.layoutWidget.setObjectName("layoutWidget")

        all_decks = PyQt5.QtWidgets.QVBoxLayout(self.layoutWidget)
        all_decks.setContentsMargins(20, 20, 20, 20)
        all_decks.setObjectName("all_decks")

        # add header
        self.topLevel.addWidget(gui_utils.get_header_label('Language Mapping'))

        # add auto-detection widgets
        hlayout_global = PyQt5.QtWidgets.QHBoxLayout()
        vlayout_left_side = PyQt5.QtWidgets.QVBoxLayout()
        self.autodetect_progressbar = PyQt5.QtWidgets.QProgressBar()
        vlayout_left_side.addWidget(self.autodetect_progressbar)
        hlayout_global.addLayout(vlayout_left_side)

        font2 = PyQt5.QtGui.QFont()
        font2.setPointSize(14)
        self.autodetect_button = PyQt5.QtWidgets.QPushButton()
        self.autodetect_button.setText('Run Auto Detection\n(all decks)')
        self.autodetect_button.setObjectName('run_autodetect')
        self.autodetect_button.setFont(font2)
        self.autodetect_button.setStyleSheet(self.languagetools.anki_utils.get_green_stylesheet())
        self.autodetect_button.pressed.connect(self.runLanguageDetection)
        hlayout_global.addWidget(self.autodetect_button)

        # add filter bar
        hlayout = PyQt5.QtWidgets.QHBoxLayout()
        filter_label = PyQt5.QtWidgets.QLabel('Filter Decks:')
        hlayout.addWidget(filter_label)
        self.filter_text = None
        self.filter_text_input = PyQt5.QtWidgets.QLineEdit()
        self.filter_text_input.textChanged.connect(self.filterTextChanged)
        hlayout.addWidget(self.filter_text_input)
        self.filter_result_label = PyQt5.QtWidgets.QLabel(self.getFilterResultText(len(deck_map), len(deck_map)))
        hlayout.addWidget(self.filter_result_label)
        
        vlayout_left_side.addLayout(hlayout)

        self.topLevel.addLayout(hlayout_global)

        self.deck_name_widget_map = {}
        for deck_name, deck in deck_map.items():
            deck_layout = self.layoutDecks(deck_name, deck)
            frame = PyQt5.QtWidgets.QFrame()
            frame.setObjectName(f'frame_{deck_name}')
            frame.setLayout(deck_layout)
            self.deck_name_widget_map[deck_name] = frame
            all_decks.addWidget(frame)


        self.scrollArea.setWidget(self.layoutWidget)
        self.topLevel.addWidget(self.scrollArea)

        self.buttonBox = PyQt5.QtWidgets.QDialogButtonBox()
        self.applyButton = self.buttonBox.addButton("Apply", PyQt5.QtWidgets.QDialogButtonBox.AcceptRole)
        self.applyButton.setObjectName('apply')
        self.disableApplyButton()
        cancelButton = self.buttonBox.addButton("Cancel", PyQt5.QtWidgets.QDialogButtonBox.RejectRole)
        cancelButton.setObjectName('cancel')
        cancelButton.setStyleSheet(self.languagetools.anki_utils.get_red_stylesheet())
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.topLevel.addWidget(self.buttonBox)


    def layoutDecks(self, deck_name, deck: deck_utils.Deck):
        layout = PyQt5.QtWidgets.QVBoxLayout()

        deckWidgets = LanguageMappingDeckWidgets()
        self.deckWidgetMap[deck_name] = deckWidgets
        self.deckNoteTypeWidgetMap[deck_name] = {}
        self.fieldWidgetMap[deck_name] = {}

        deckWidgets.deck_info = PyQt5.QtWidgets.QHBoxLayout()
        deckWidgets.deck_info.setObjectName("deck_info")
        
        fontSize = 14

        deckWidgets.deck_label = PyQt5.QtWidgets.QLabel(self.layoutWidget)
        font1 = PyQt5.QtGui.QFont()
        font1.setBold(True)
        font1.setPointSize(fontSize)
        deckWidgets.deck_label.setFont(font1)
        deckWidgets.deck_label.setObjectName("deck_label")
        deckWidgets.deck_label.setText('Deck:')
        deckWidgets.deck_info.addWidget(deckWidgets.deck_label)

        font2 = PyQt5.QtGui.QFont()
        font2.setPointSize(fontSize)
        deckWidgets.deck_name = PyQt5.QtWidgets.QLabel(self.layoutWidget)
        deckWidgets.deck_name.setObjectName(f'deck_name_{deck_name}')
        deckWidgets.deck_name.setText(deck_name)
        deckWidgets.deck_name.setFont(font2)
        deckWidgets.deck_info.addWidget(deckWidgets.deck_name)

        deckWidgets.deck_info.addStretch(1)

        layout.addLayout(deckWidgets.deck_info)
        
        # iterate over note types 
        for note_type_name, dntf_list in deck.note_type_map.items():
            self.layoutNoteTypes(layout, deck_name, note_type_name, dntf_list)

        # add spacing at the end
        layout.addSpacing(30)

        layout.addStretch(1)

        return layout
                        

    def layoutNoteTypes(self, layout, deck_name, note_type_name, dntf_list: List[deck_utils.DeckNoteTypeField]):
        noteTypeWidgets = LanguageMappingNoteTypeWidgets()
        self.deckNoteTypeWidgetMap[deck_name][note_type_name] = noteTypeWidgets
        self.fieldWidgetMap[deck_name][note_type_name] = {}

        noteTypeWidgets.note_type_info = PyQt5.QtWidgets.QHBoxLayout()
        noteTypeWidgets.note_type_info.setObjectName("note_type_info")

        fontSize = 12

        font1 = PyQt5.QtGui.QFont()
        font1.setBold(True)
        font1.setPointSize(fontSize)

        noteTypeWidgets.note_type_label = PyQt5.QtWidgets.QLabel(self.layoutWidget)
        noteTypeWidgets.note_type_label.setObjectName("note_type_label")
        noteTypeWidgets.note_type_label.setText('Note Type:')
        noteTypeWidgets.note_type_label.setFont(font1)
        noteTypeWidgets.note_type_info.addWidget(noteTypeWidgets.note_type_label)

        font2 = PyQt5.QtGui.QFont()
        font2.setPointSize(fontSize)
        noteTypeWidgets.note_type_name = PyQt5.QtWidgets.QLabel(self.layoutWidget)
        noteTypeWidgets.note_type_name.setObjectName(f"note_type_name_{deck_name}_{note_type_name}")
        noteTypeWidgets.note_type_name.setText(note_type_name)
        noteTypeWidgets.note_type_name.setFont(font2)
        noteTypeWidgets.note_type_info.addWidget(noteTypeWidgets.note_type_name)

        noteTypeWidgets.note_type_info.addStretch(1)

        layout.addLayout(noteTypeWidgets.note_type_info)

        noteTypeWidgets.field_info = PyQt5.QtWidgets.QGridLayout()
        noteTypeWidgets.field_info.setContentsMargins(20, 0, 0, 0)
        # set stretch factors
        noteTypeWidgets.field_info.setColumnStretch(0, 50)
        noteTypeWidgets.field_info.setColumnStretch(1, 50)
        noteTypeWidgets.field_info.setColumnStretch(2, 0)
        noteTypeWidgets.field_info.setObjectName("field_info")

        row = 0
        for deck_note_type_field in dntf_list:
            self.layoutField(row, deck_note_type_field, noteTypeWidgets.field_info)
            row += 1

        layout.addLayout(noteTypeWidgets.field_info)


    def layoutField(self, row:int, deck_note_type_field: deck_utils.DeckNoteTypeField, gridLayout: PyQt5.QtWidgets.QGridLayout):

        fieldWidgets = LanguageMappingFieldWidgets()
        self.fieldWidgetMap[deck_note_type_field.deck_note_type.deck_name][deck_note_type_field.deck_note_type.model_name][deck_note_type_field.field_name] = fieldWidgets

        language_set = self.languagetools.get_language(deck_note_type_field)

        fieldWidgets.field_label = PyQt5.QtWidgets.QLabel(self.layoutWidget)
        field_label_obj_name = f'field_label_{str(deck_note_type_field)}'
        fieldWidgets.field_label.setObjectName(field_label_obj_name)
        fieldWidgets.field_label.setText(deck_note_type_field.field_name)
        gridLayout.addWidget(fieldWidgets.field_label, row, 0, 1, 1)

        fieldWidgets.field_language = PyQt5.QtWidgets.QComboBox(self.layoutWidget)
        field_language_obj_name = f'field_language_{str(deck_note_type_field)}'
        fieldWidgets.field_language.setObjectName(field_language_obj_name)
        fieldWidgets.field_language.addItems(self.language_name_list)
        fieldWidgets.field_language.setMaxVisibleItems(15)
        fieldWidgets.field_language.setStyleSheet("combobox-popup: 0;")
        self.setFieldLanguageIndex(fieldWidgets.field_language, language_set)

        # listen to events
        def get_currentIndexChangedLambda(comboBox, deck_note_type_field: deck_utils.DeckNoteTypeField):
            def callback(currentIndex):
                self.fieldLanguageIndexChanged(comboBox, deck_note_type_field, currentIndex)
            return callback
        fieldWidgets.field_language.currentIndexChanged.connect(get_currentIndexChangedLambda(fieldWidgets.field_language, deck_note_type_field)) 

        self.dntfComboxBoxMap[deck_note_type_field] = fieldWidgets.field_language

        gridLayout.addWidget(fieldWidgets.field_language, row, 1, 1, 1)

        fieldWidgets.field_samples_button = PyQt5.QtWidgets.QPushButton(self.layoutWidget)
        field_samples_button_obj_name = f'field_samples_{str(deck_note_type_field)}'
        fieldWidgets.field_samples_button.setObjectName(field_samples_button_obj_name)
        fieldWidgets.field_samples_button.setText('Show Samples')

        def getShowFieldSamplesLambda(deck_note_type_field: deck_utils.DeckNoteTypeField):
            def callback():
                self.showFieldSamples(deck_note_type_field)
            return callback
        fieldWidgets.field_samples_button.pressed.connect(getShowFieldSamplesLambda(deck_note_type_field))

        gridLayout.addWidget(fieldWidgets.field_samples_button, row, 2, 1, 1)

    def setFieldLanguageIndex(self, comboBox, language):
        if language != None:
            # locate index of language
            current_index = self.language_code_list.index(language)
            comboBox.setCurrentIndex(current_index)
        else:
            # not set
            comboBox.setCurrentIndex(len(self.language_name_list) - 1)

    def fieldLanguageIndexChanged(self, comboBox, deck_note_type_field: deck_utils.DeckNoteTypeField, currentIndex):
        # print(f'fieldLanguageIndexChanged: {deck_note_type_field}')
        language_code = None
        if currentIndex < len(self.language_code_list):
            language_code = self.language_code_list[currentIndex]
        self.language_mapping_changes[deck_note_type_field] = language_code
        # change stylesheet of combobox
        comboBox.setStyleSheet(self.languagetools.anki_utils.get_green_stylesheet() + "combobox-popup: 0;")
        # enable apply button
        if not self.autodetect_in_progress:
            self.enableApplyButton()

    def showFieldSamples(self, deck_note_type_field: deck_utils.DeckNoteTypeField):
        field_samples = self.languagetools.get_field_samples(deck_note_type_field, 20)
        if len(field_samples) == 0:
            self.languagetools.anki_utils.info_message('No usable field data found', self.dialog)
        else:
            joined_text = ', '.join(field_samples)
            text = f'<b>Samples</b>: {joined_text}'
            self.languagetools.anki_utils.info_message(text, self.dialog)

    def accept(self):
        self.saveLanguageMappingChanges()
        self.Dialog.close()

    def reject(self):
        self.interrupt_autodetect = True
        self.Dialog.close()

    def filterEmpty(self, filter_text):
        if filter_text == None:
            return True
        if len(filter_text) == 0:
            return True
        return False

    def matchFilter(self, filter_text, deck_name):
        if self.filterEmpty(filter_text):
            return True
        return filter_text.lower() in deck_name.lower()

    def getFilterResultText(self, displayed_count, total_count):
        filter_result = f'{displayed_count} / {total_count} decks'
        return filter_result

    def filterTextChanged(self, new_filter_text):
        self.filter_text = new_filter_text
        total_count = len(self.deck_name_widget_map)
        displayed_count = 0
        for deck_name, frame in self.deck_name_widget_map.items():
            if self.matchFilter(new_filter_text, deck_name):
                frame.setVisible(True)
                displayed_count += 1
            else:
                frame.setVisible(False)
        filter_result = self.getFilterResultText(displayed_count, total_count)
        self.filter_result_label.setText(filter_result)

        if displayed_count != total_count:
            self.autodetect_button.setText('Run Auto Detection\n(Selected)')
        else:
            self.autodetect_button.setText('Run Auto Detection\n(All Decks)')


    def saveLanguageMappingChanges(self):
        for key, value in self.language_mapping_changes.items():
            self.languagetools.store_language_detection_result(key, value)

    def runLanguageDetection(self):
        if self.languagetools.ensure_api_key_checked() == False:
            return

        self.languagetools.anki_utils.run_in_background(self.runLanguageDetectionBackground, self.runLanguageDetectionDone)

    def runLanguageDetectionBackground(self):
        try:
            self.autodetect_in_progress = True
            self.autodetect_button.setEnabled(False)
            self.disableApplyButton()

            dtnf_list: List[deck_utils.DeckNoteTypeField] = self.languagetools.get_populated_dntf()
            progress_max = 0
            for dntf in dtnf_list:
                deck_name = dntf.deck_note_type.deck_name
                if self.matchFilter(self.filter_text, deck_name):
                    progress_max += 1
            self.setProgressBarMax(progress_max)

            progress = 0
            for dntf in dtnf_list:
                if self.interrupt_autodetect == True:
                    return

                deck_name = dntf.deck_note_type.deck_name
                if self.matchFilter(self.filter_text, deck_name):
                    language = self.languagetools.perform_language_detection_deck_note_type_field(dntf)
                    #self.language_mapping_changes[deck_note_type_field] = language
                    # need to set combo box correctly.
                    comboBox = self.dntfComboxBoxMap[dntf]
                    self.setFieldLanguageIndex(comboBox, language)

                    # progress bar
                    self.setProgressValue(progress)
                    progress += 1
            
            self.setProgressValue(progress_max)
        except:
            logging.exception('could not run language detection')
            error_message = str(sys.exc_info())
            self.displayErrorMessage(error_message)


    def setProgressBarMax(self, progress_max):
        self.languagetools.anki_utils.run_on_main(lambda: self.autodetect_progressbar.setMaximum(progress_max))

    def setProgressValue(self, progress):
        self.languagetools.anki_utils.run_on_main(lambda: self.autodetect_progressbar.setValue(progress))

    def displayErrorMessage(self, message):
        self.languagetools.anki_utils.run_on_main(lambda: self.languagetools.anki_utils.critical_message(message, self.dialog))

    def runLanguageDetectionDone(self, future_result):
        self.autodetect_in_progress = False
        self.autodetect_button.setEnabled(True)
        self.enableApplyButton()


    def disableApplyButton(self):
        self.applyButton.setStyleSheet(None)
        self.applyButton.setDisabled(True)

    def enableApplyButton(self):
        self.applyButton.setStyleSheet(self.languagetools.anki_utils.get_green_stylesheet())
        self.applyButton.setDisabled(False)

def prepare_language_mapping_dialogue(languagetools):
    deck_map: Dict[str, Deck] = languagetools.get_populated_decks()

    mapping_dialog = PyQt5.QtWidgets.QDialog()
    mapping_dialog.ui = LanguageMappingDialog_UI(languagetools, mapping_dialog)
    mapping_dialog.ui.setupUi(mapping_dialog, deck_map)
    return mapping_dialog