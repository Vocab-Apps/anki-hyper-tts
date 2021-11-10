import sys
from typing import List, Dict
import traceback
import logging
import json
import urllib.parse

import aqt.qt
from PyQt5 import QtCore, QtGui, QtWidgets, Qt

if hasattr(sys, '_pytest_mode'):
    import constants
    import deck_utils
    import gui_utils
    import errors
    import dialog_languagemapping
    import dialog_voiceselection
    import dialog_apikey
    import dialog_batchtransformation
    import dialog_notesettings
    from languagetools import LanguageTools
else:
    from . import constants
    from . import deck_utils
    from . import gui_utils
    from . import errors
    from . import dialog_languagemapping
    from . import dialog_voiceselection
    from . import dialog_apikey
    from . import dialog_batchtransformation
    from . import dialog_notesettings
    from .languagetools import LanguageTools



class AddAudioDialog(aqt.qt.QDialog):
    def __init__(self, languagetools: LanguageTools, deck_note_type: deck_utils.DeckNoteType, note_id_list):
        super(aqt.qt.QDialog, self).__init__()
        self.languagetools = languagetools
        self.deck_note_type = deck_note_type
        self.note_id_list = note_id_list

        # get field list
        field_names = self.languagetools.deck_utils.get_field_names(self.deck_note_type)

        self.voice_selection_settings = languagetools.get_voice_selection_settings()
        self.batch_audio_settings = languagetools.get_batch_audio_settings(self.deck_note_type)

        # logging.debug(f'voice_selection_settings: {self.voice_selection_settings}')
        # logging.debug(f'batch_audio_settings: {self.batch_audio_settings}')

        # these are the available fields
        # build separate lists for to and from
        self.from_field_name_list = []
        self.from_deck_note_type_field_list = []
        self.from_field_language = []

        self.to_field_name_list = []
        self.to_deck_note_type_field_list = []

        # retain fields which have a language set
        for field_name in field_names:
            deck_note_type_field = self.languagetools.deck_utils.build_dntf_from_dnt(deck_note_type, field_name)
            language = self.languagetools.get_language(deck_note_type_field)

            if self.languagetools.language_available_for_translation(language):
                self.from_field_name_list.append(field_name)
                self.from_deck_note_type_field_list.append(deck_note_type_field)
                self.from_field_language.append(language)

            self.to_field_name_list.append(field_name)
            self.to_deck_note_type_field_list.append(deck_note_type_field)
        
        # do we have any language mappings at all ? 
        if len(self.from_field_name_list) == 0:
            error_message = f'Language Mapping not done for {self.deck_note_type}'
            raise errors.LanguageMappingError(error_message)

        
    def setupUi(self):
        self.setWindowTitle(constants.ADDON_NAME)
        self.resize(700, 200)

        vlayout = QtWidgets.QVBoxLayout(self)

        vlayout.addWidget(gui_utils.get_header_label('Add Audio'))

        description_label = aqt.qt.QLabel(f'After adding audio to notes, the setting will be memorized.')
        vlayout.addWidget(description_label)        

        # from/ to field
        gridlayout = QtWidgets.QGridLayout()

        # from
        gridlayout.addWidget(gui_utils.get_medium_label('From Field:'), 0, 0, 1, 1)
        self.from_field_combobox = QtWidgets.QComboBox()
        self.from_field_combobox.addItems(self.from_field_name_list)
        gridlayout.addWidget(self.from_field_combobox, 0, 1, 1, 1)
        # to
        gridlayout.addWidget(gui_utils.get_medium_label('To Field:'), 0, 3, 1, 1)
        self.to_field_combobox = QtWidgets.QComboBox()
        self.to_field_combobox.addItems(self.to_field_name_list)
        gridlayout.addWidget(self.to_field_combobox, 0, 4, 1, 1)

        # voice
        gridlayout.addWidget(gui_utils.get_medium_label('Voice:'), 1, 0, 1, 2)
        self.voice_label = aqt.qt.QLabel()
        self.voice_label.setText('undefined')
        self.voice = QtWidgets.QComboBox()
        gridlayout.addWidget(self.voice_label, 1, 1, 1, 4)

        vlayout.addLayout(gridlayout)

        self.progress_bar = QtWidgets.QProgressBar()
        vlayout.addWidget(self.progress_bar)        

        vlayout.addStretch()

        buttonBox = QtWidgets.QDialogButtonBox()
        self.applyButton = buttonBox.addButton("Apply To Notes", QtWidgets.QDialogButtonBox.AcceptRole)
        self.applyButton.setEnabled(False)
        self.cancelButton = buttonBox.addButton("Cancel", QtWidgets.QDialogButtonBox.RejectRole)
        self.cancelButton.setStyleSheet(self.languagetools.anki_utils.get_red_stylesheet())

        vlayout.addWidget(buttonBox)

        # wire events
        self.pick_default_fields()
        self.from_field_combobox.currentIndexChanged.connect(self.from_field_index_changed)
        self.to_field_combobox.currentIndexChanged.connect(self.to_field_index_changed)

        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

    def pick_default_fields(self):
        logging.info('pick_default_fields')
        #self.batch_audio_settings
        self.from_field_index = 0
        self.to_field_index = 0

        # logging.debug(f'batch_audio_settings: {self.batch_audio_settings}')
        if len(self.batch_audio_settings) > 0:
            # logging.info(f'some batch audio settings found')
            to_field = list(self.batch_audio_settings.keys())[0]
            from_field = self.batch_audio_settings[to_field]
            try:
                from_field_index = self.from_field_name_list.index(from_field)
                to_field_index = self.to_field_name_list.index(to_field)

                if from_field_index < len(self.from_field_name_list):
                    self.from_field_index = from_field_index
                if to_field_index < len(self.to_field_name_list):
                    self.to_field_index = to_field_index
                
            except ValueError:
                pass

        self.from_field = self.from_field_name_list[self.from_field_index]
        self.to_field = self.to_field_name_list[self.to_field_index]

        self.from_field_index_changed(self.from_field_index)
        self.from_field_combobox.setCurrentIndex(self.from_field_index)

        self.to_field_combobox.setCurrentIndex(self.to_field_index)

    def from_field_index_changed(self, field_index):
        self.from_field_index = field_index
        self.from_field = self.from_field_name_list[self.from_field_index]
        from_language = self.from_field_language[field_index]
        # do we have a voice setup for this language ?

        if from_language in self.voice_selection_settings:
            self.voice = self.voice_selection_settings[from_language]
            voice_description = self.voice['voice_description']
            self.voice_label.setText('<b>' + voice_description + '</b>')
            self.applyButton.setEnabled(True)
            self.applyButton.setStyleSheet(self.languagetools.anki_utils.get_green_stylesheet())
        else:
            language_name = self.languagetools.get_language_name(from_language)
            self.voice_label.setText(f'No Voice setup for <b>{language_name}</b>. Please go to Anki main window, ' +
            '<b>Tools -> Language Tools: Voice Selection </b>')
            self.applyButton.setEnabled(False)
            self.applyButton.setStyleSheet(None)

    def to_field_index_changed(self, field_index):
        self.to_field_index = field_index
        self.to_field = self.to_field_name_list[self.to_field_index]

    def accept(self):
        to_fields_empty = True
        for note_id in self.note_id_list:
            note = aqt.mw.col.getNote(note_id)
            if len(note[self.to_field]) > 0:
                to_fields_empty = False
        if to_fields_empty == False:
            proceed = aqt.utils.askUser(f'Overwrite existing data in field {self.to_field} ?')
            if proceed == False:
                # don't continue
                return

        self.applyButton.setText('Adding Audio...')
        self.applyButton.setEnabled(False)
        self.applyButton.setStyleSheet(None)

        self.progress_bar.setMaximum(len(self.note_id_list))

        deck_note_type_field = self.languagetools.deck_utils.build_dntf_from_dnt(self.deck_note_type, self.to_field)
        self.languagetools.store_batch_audio_setting(deck_note_type_field, self.from_field)

        self.success_count = 0

        action_str = f'Add Audio to {self.to_field}'
        aqt.mw.checkpoint(action_str)

        aqt.mw.taskman.run_in_background(self.add_audio_task, self.add_audio_task_done)

    def add_audio_task(self):
        self.generate_audio_errors = []
        i = 0
        for note_id in self.note_id_list:
            try:
                result = self.languagetools.generate_audio_for_field(note_id, self.from_field, self.to_field, self.voice)
                if result == True:
                    self.success_count += 1
            except errors.LanguageToolsRequestError as err:
                self.generate_audio_errors.append(str(err))
            i += 1
            aqt.mw.taskman.run_on_main(lambda: self.progress_bar.setValue(i))

    def add_audio_task_done(self, future_result):
        # are there any errors ?
        errors_str = ''
        if len(self.generate_audio_errors) > 0:
            error_counts = {}
            for error in self.generate_audio_errors:
                current_count = error_counts.get(error, 0)
                error_counts[error] = current_count + 1
            errors_str = '<p><b>Errors</b>: ' + ', '.join([f'{key} ({value} times)' for key, value in error_counts.items()]) + '</p>'
        completion_message = f"Added Audio to field <b>{self.to_field}</b> using voice <b>{self.voice['voice_description']}</b>. Success: <b>{self.success_count}</b> out of <b>{len(self.note_id_list)}</b>.{errors_str}"
        self.close()
        if len(errors_str) > 0:
            aqt.utils.showWarning(completion_message, title=constants.ADDON_NAME, parent=self)
        else:
            aqt.utils.showInfo(completion_message, title=constants.ADDON_NAME, parent=self)




class YomichanDialog(aqt.qt.QDialog):
    def __init__(self, languagetools: LanguageTools, japanese_voice):
        super(aqt.qt.QDialog, self).__init__()
        self.languagetools = languagetools
        self.japanese_voice = japanese_voice
        
    def setupUi(self):
        self.setWindowTitle(constants.ADDON_NAME)
        self.resize(700, 250)

        vlayout = QtWidgets.QVBoxLayout(self)

        vlayout.addWidget(gui_utils.get_header_label('Yomichan Integration'))

        voice_name = self.japanese_voice['voice_description']

        label_text1 = f'You can use Language Tools voices from within Yomichan. Currently using voice: <b>{voice_name}</b>. You can change this in the <b>Voice Selection</b> dialog.'
        label_text2 = """
        <ol>
            <li>Please go to <b>Yomichan settings</b></li>
            <li>Look for <b>Audio</b></li>
            <li>Configure audio playback sources...</li>
            <li>In <b>Custom audio source</b>, choose <b>Type: Audio</b>, and enter the URL below (it should already be copied to your clipboard)</li>
            <li>In the <b>Audio sources</b> dropdown, choose <b>Custom</b></li>
            <li>Try playing some audio using Yomichan, you should hear it played back in the voice you've chosen.</li>
        </ol>
        """

        label = QtWidgets.QLabel(label_text1)
        label.setWordWrap(True)
        vlayout.addWidget(label)

        label = QtWidgets.QLabel(label_text2)
        vlayout.addWidget(label)        

        # compute URL

        api_key = self.languagetools.config['api_key']
        voice_key_str = urllib.parse.quote_plus(json.dumps(self.japanese_voice['voice_key']))
        service = self.japanese_voice['service']
        url_params = f"api_key={api_key}&service={service}&voice_key={voice_key_str}&text={'{'}expression{'}'}"
        url_end = f'yomichan_audio?{url_params}'        
        full_url = self.languagetools.cloud_language_tools.base_url + '/' + url_end

        QtWidgets.QApplication.clipboard().setText(full_url)

        line_edit = QtWidgets.QLineEdit(full_url)
        vlayout.addWidget(line_edit)
        
        vlayout.addStretch()

        # add buttons
        buttonBox = QtWidgets.QDialogButtonBox()
        self.okButton = buttonBox.addButton("OK", QtWidgets.QDialogButtonBox.AcceptRole)
        vlayout.addWidget(buttonBox)

        # wire events
        # ===========
        buttonBox.accepted.connect(self.accept)




def language_mapping_dialogue(languagetools):
    mapping_dialog = dialog_languagemapping.prepare_language_mapping_dialogue(languagetools)
    mapping_dialog.exec_()

def yomichan_dialog(languagetools):
    if not languagetools.language_detection_done():
        aqt.utils.showInfo(text='Please setup Language Mappings, from the Anki main screen: Tools -> Language Tools: Language Mapping', title=constants.ADDON_NAME)
        return

    # do we have a voice set for japanese ?
    voice_settings = languagetools.get_voice_selection_settings()
    if 'ja' not in voice_settings:
        aqt.utils.showCritical(text='Please choose a Japanese voice, from the Anki main screen: Tools -> Language Tools: Voice Selection', title=constants.ADDON_NAME)
        return

    japanese_voice = voice_settings['ja']

    yomichan_dialog = YomichanDialog(languagetools, japanese_voice)
    yomichan_dialog.setupUi()
    yomichan_dialog.exec_()


def verify_deck_note_type_consistent(note_id_list, deck_utils):
    if len(note_id_list) == 0:
        aqt.utils.showCritical(f'You must select notes before opening this dialog.', title=constants.ADDON_NAME)
        return None

    # ensure we only have one deck/notetype selected
    deck_note_type_map = {}

    for note_id in note_id_list:
        note = aqt.mw.col.getNote(note_id)
        cards = note.cards()
        for card in cards:
            deck_note_type = deck_utils.build_deck_note_type_from_note_card(note, card)
            if deck_note_type not in deck_note_type_map:
                deck_note_type_map[deck_note_type] = 0
            deck_note_type_map[deck_note_type] += 1

    if len(deck_note_type_map) > 1:
        # too many deck / model combinations
        summary_str = ', '.join([f'{numCards} notes from {key}' for key, numCards in deck_note_type_map.items()])
        aqt.utils.showCritical(f'You must select notes from the same Deck / Note Type combination. You have selected {summary_str}', title=constants.ADDON_NAME)
        return None
    
    deck_note_type = list(deck_note_type_map.keys())[0]

    return deck_note_type

def add_transformation_dialog(languagetools, browser: aqt.browser.Browser, note_id_list, transformation_type):
    # print(f'* add_translation_dialog {note_id_list}')

    # did the user perform language mapping ? 
    if not languagetools.language_detection_done():
        aqt.utils.showInfo(text='Please setup Language Mappings, from the Anki main screen: Tools -> Language Tools: Language Mapping', title=constants.ADDON_NAME)
        return

    deck_note_type = verify_deck_note_type_consistent(note_id_list, languagetools.deck_utils)
    if deck_note_type == None:
        return

    try:
        dialog = dialog_batchtransformation.prepare_batch_transformation_dialogue(languagetools, deck_note_type, note_id_list, transformation_type)
        dialog.exec_()

        # force browser to reload notes
        browser.model.reset()
    except errors.LanguageMappingError as exception:
        original_message = str(exception)
        final_message = original_message + '<br/>' + constants.DOCUMENTATION_PERFORM_LANGUAGE_MAPPING
        aqt.utils.showCritical(final_message, title=constants.ADDON_NAME)


def add_translation_dialog(languagetools, browser: aqt.browser.Browser, note_id_list):
    add_transformation_dialog(languagetools, browser, note_id_list, constants.TransformationType.Translation)

def add_transliteration_dialog(languagetools, browser: aqt.browser.Browser, note_id_list):
    add_transformation_dialog(languagetools, browser, note_id_list, constants.TransformationType.Transliteration)

def run_rules_dialog(languagetools, browser: aqt.browser.Browser, note_id_list):
    deck_note_type = verify_deck_note_type_consistent(note_id_list, languagetools.deck_utils)
    if deck_note_type == None:
        return

    dialog = dialog_notesettings.RunRulesDialog(languagetools, deck_note_type, note_id_list)
    dialog.setupUi()
    dialog.exec_()

    # force browser to reload notes
    browser.model.reset()        

def show_settings_dialog(languagetools, browser: aqt.browser.Browser, note_id_list):
    deck_note_type = verify_deck_note_type_consistent(note_id_list, languagetools.deck_utils)
    if deck_note_type == None:
        return

    dialog = dialog_notesettings.NoteSettingsDialog(languagetools, deck_note_type)
    dialog.setupUi()
    dialog.exec_()

def add_audio_dialog(languagetools, browser: aqt.browser.Browser, note_id_list):
    # did the user perform language mapping ? 
    if not languagetools.language_detection_done():
        aqt.utils.showInfo(text='Please setup Language Mappings, from the Anki main screen: Tools -> Language Tools: Language Mapping', title=constants.ADDON_NAME)
        return

    deck_note_type = verify_deck_note_type_consistent(note_id_list, languagetools.deck_utils)
    if deck_note_type == None:
        return

    try:
        dialog = AddAudioDialog(languagetools, deck_note_type, note_id_list)
        dialog.setupUi()
        dialog.exec_()

        # force browser to reload notes
        browser.model.reset()    

    except errors.LanguageMappingError as exception:
        original_message = str(exception)
        final_message = original_message + '<br/>' + constants.DOCUMENTATION_PERFORM_LANGUAGE_MAPPING
        aqt.utils.showCritical(final_message, title=constants.ADDON_NAME)


def show_api_key_dialog(languagetools):
    dialog = dialog_apikey.prepare_api_key_dialog(languagetools)
    dialog.exec_()