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

class NoteTableModel(PyQt5.QtCore.QAbstractTableModel):
    def __init__(self):
        PyQt5.QtCore.QAbstractTableModel.__init__(self, None)
        self.from_field_data = []
        self.to_field_data = []
        self.from_field = 'From'
        self.to_field = 'To'

    def flags(self, index):
        if index.column() == 1: # second column is editable
            return PyQt5.QtCore.Qt.ItemIsEditable | PyQt5.QtCore.Qt.ItemIsSelectable | PyQt5.QtCore.Qt.ItemIsEnabled
        # return default
        return PyQt5.QtCore.Qt.ItemIsSelectable | PyQt5.QtCore.Qt.ItemIsEnabled

    def setFromField(self, field_name):
        self.from_field = field_name
        self.headerDataChanged.emit(PyQt5.QtCore.Qt.Horizontal, 0, 1)
    
    def setToField(self, field_name):
        self.to_field = field_name
        self.headerDataChanged.emit(PyQt5.QtCore.Qt.Horizontal, 0, 1)

    def setFromFieldData(self, data):
        self.from_field_data = data
        self.to_field_data = [None] * len(self.from_field_data)
        # print(f'**** len(self.to_field_data): {len(self.to_field_data)}')
        start_index = self.createIndex(0, 0)
        end_index = self.createIndex(len(self.from_field_data)-1, 0)
        self.dataChanged.emit(start_index, end_index)

    def setToFieldData(self, row, to_field_result):
        # print(f'**** setToFieldData:, row: {row}')
        self.to_field_data[row] = to_field_result
        start_index = self.createIndex(row, 1)
        end_index = self.createIndex(row, 1)
        self.dataChanged.emit(start_index, end_index)

    def rowCount(self, parent):
        return len(self.from_field_data)

    def columnCount(self, parent):
        return 2

    def data(self, index, role):
        if not index.isValid():
            return PyQt5.QtCore.QVariant()
        elif role != PyQt5.QtCore.Qt.DisplayRole and role != PyQt5.QtCore.Qt.EditRole: # only support display and edit
           return PyQt5.QtCore.QVariant()
        if index.column() == 0:
            # from field
            return PyQt5.QtCore.QVariant(self.from_field_data[index.row()])
        else:
            # result field
            return PyQt5.QtCore.QVariant(self.to_field_data[index.row()])

    def setData(self, index, value, role):
        if index.column() != 1:
            return False
        if index.isValid() and role == PyQt5.QtCore.Qt.EditRole:
            # memorize the value
            row = index.row()
            self.to_field_data[row] = value
            # emit change signal
            start_index = self.createIndex(row, 1)
            end_index = self.createIndex(row, 1)
            self.dataChanged.emit(start_index, end_index)            
            return True
        else:
            return False

    def headerData(self, col, orientation, role):
        if orientation == PyQt5.QtCore.Qt.Horizontal and role == PyQt5.QtCore.Qt.DisplayRole:
            if col == 0:
                return PyQt5.QtCore.QVariant(self.from_field)
            else:
                return PyQt5.QtCore.QVariant(self.to_field)
        return PyQt5.QtCore.QVariant()

class BatchConversionDialog(PyQt5.QtWidgets.QDialog):
    def __init__(self, languagetools: LanguageTools, deck_note_type: deck_utils.DeckNoteType, note_id_list, transformation_type):
        super(PyQt5.QtWidgets.QDialog, self).__init__()
        self.languagetools = languagetools
        self.deck_note_type = deck_note_type
        self.note_id_list = note_id_list
        self.transformation_type = transformation_type

        # get field list
        field_names = self.languagetools.deck_utils.get_field_names(deck_note_type)

        # these are the available fields
        self.field_name_list = []
        self.deck_note_type_field_list = []
        self.field_language = []

        self.from_field_data = []
        self.to_field_data = []

        self.to_fields_empty = True

        self.noteTableModel = NoteTableModel()

        at_least_one_field_language_set = False

        # retain fields which have a language set
        for field_name in field_names:
            deck_note_type_field = languagetools.deck_utils.build_dntf_from_dnt(deck_note_type, field_name)
            language = self.languagetools.get_language(deck_note_type_field)

            if self.languagetools.language_available_for_translation(language):
                at_least_one_field_language_set = True

            if self.transformation_type == constants.TransformationType.Translation:
                if self.languagetools.language_available_for_translation(language):
                    self.field_name_list.append(field_name)
                    self.deck_note_type_field_list.append(deck_note_type_field)
                    self.field_language.append(language)
            elif self.transformation_type == constants.TransformationType.Transliteration:
                self.field_name_list.append(field_name)
                self.deck_note_type_field_list.append(deck_note_type_field)
                self.field_language.append(language)                

        if at_least_one_field_language_set == False:
            error_message = f'No fields available for {self.transformation_type.name} in {self.deck_note_type}'
            # no fields were found, could be that no fields have a language set
            raise errors.LanguageMappingError(error_message)


    def setupUi(self):
        self.setWindowTitle(constants.ADDON_NAME)
        self.resize(700, 500)

        vlayout = PyQt5.QtWidgets.QVBoxLayout(self)

        header_label_text_map = {
            constants.TransformationType.Translation: 'Add Translation',
            constants.TransformationType.Transliteration: 'Add Transliteration'
        }

        vlayout.addWidget(gui_utils.get_header_label(header_label_text_map[self.transformation_type]))

        description_label = PyQt5.QtWidgets.QLabel(f'After adding {self.transformation_type.name.lower()} to notes, the setting will be memorized.')
        vlayout.addWidget(description_label)

        # setup to/from fields
        # ====================

        gridlayout = PyQt5.QtWidgets.QGridLayout()

        # "from" side
        # -----------

        label_font_size = 13
        font1 = PyQt5.QtGui.QFont()
        font1.setBold(True)
        font1.setPointSize(label_font_size)

        from_label = PyQt5.QtWidgets.QLabel()
        from_label.setText('From Field:')
        from_label.setFont(font1)
        gridlayout.addWidget(from_label, 0, 0, 1, 1)

        self.from_combobox = PyQt5.QtWidgets.QComboBox()
        self.from_combobox.addItems(self.field_name_list)
        gridlayout.addWidget(self.from_combobox, 0, 1, 1, 1)

        gridlayout.addWidget(PyQt5.QtWidgets.QLabel('Language:'), 1, 0, 1, 1)

        self.from_language_label = PyQt5.QtWidgets.QLabel()
        gridlayout.addWidget(self.from_language_label, 1, 1, 1, 1)


        # "to" side
        # ---------

        to_label = PyQt5.QtWidgets.QLabel()
        to_label.setText('To Field:')
        to_label.setFont(font1)
        gridlayout.addWidget(to_label, 0, 3, 1, 1)

        self.to_combobox = PyQt5.QtWidgets.QComboBox()
        self.to_combobox.addItems(self.field_name_list)
        gridlayout.addWidget(self.to_combobox, 0, 4, 1, 1)

        gridlayout.addWidget(PyQt5.QtWidgets.QLabel('Language:'), 1, 3, 1, 1)
        self.to_language_label = PyQt5.QtWidgets.QLabel()
        gridlayout.addWidget(self.to_language_label, 1, 4, 1, 1)

        gridlayout.setColumnStretch(0, 50)
        gridlayout.setColumnStretch(1, 50)
        gridlayout.setColumnStretch(2, 30)
        gridlayout.setColumnStretch(3, 50)
        gridlayout.setColumnStretch(4, 50)

        gridlayout.setContentsMargins(20, 30, 20, 30)

        vlayout.addLayout(gridlayout)

        # setup translation service
        # =========================

        gridlayout = PyQt5.QtWidgets.QGridLayout()
        service_label = PyQt5.QtWidgets.QLabel()
        service_label.setFont(font1)
        service_label.setText('Service:')
        gridlayout.addWidget(service_label, 0, 0, 1, 1)

        self.service_combobox = PyQt5.QtWidgets.QComboBox()
        gridlayout.addWidget(self.service_combobox, 0, 1, 1, 1)


        self.load_translations_button = PyQt5.QtWidgets.QPushButton()
        self.load_button_text_map = {
            constants.TransformationType.Translation: 'Load Translations',
            constants.TransformationType.Transliteration: 'Load Transliterations'
        }        
        self.load_translations_button.setText(self.load_button_text_map[self.transformation_type])
        self.load_translations_button.setStyleSheet(self.languagetools.anki_utils.get_green_stylesheet())
        gridlayout.addWidget(self.load_translations_button, 0, 3, 1, 2)

        if self.transformation_type == constants.TransformationType.Translation:
            gridlayout.setColumnStretch(0, 50)
            gridlayout.setColumnStretch(1, 50)
            gridlayout.setColumnStretch(2, 30)
            gridlayout.setColumnStretch(3, 50)
            gridlayout.setColumnStretch(4, 50)
        elif self.transformation_type == constants.TransformationType.Transliteration:
            # need to provide more space for the services combobox
            gridlayout.setColumnStretch(0, 20)
            gridlayout.setColumnStretch(1, 120)
            gridlayout.setColumnStretch(2, 0)
            gridlayout.setColumnStretch(3, 20)
            gridlayout.setColumnStretch(4, 20)            

        gridlayout.setContentsMargins(20, 0, 20, 10)

        vlayout.addLayout(gridlayout)

        # setup progress bar
        # ==================

        self.progress_bar = PyQt5.QtWidgets.QProgressBar()
        vlayout.addWidget(self.progress_bar)

        # setup preview table
        # ===================

        self.table_view = PyQt5.QtWidgets.QTableView()
        self.table_view.setModel(self.noteTableModel)
        header = self.table_view.horizontalHeader()       
        header.setSectionResizeMode(0, PyQt5.QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, PyQt5.QtWidgets.QHeaderView.Stretch)
        vlayout.addWidget(self.table_view)

        # setup bottom buttons
        # ====================

        buttonBox = PyQt5.QtWidgets.QDialogButtonBox()
        self.applyButton = buttonBox.addButton("Apply To Notes", PyQt5.QtWidgets.QDialogButtonBox.AcceptRole)
        self.applyButton.setEnabled(False)
        self.cancelButton = buttonBox.addButton("Cancel", PyQt5.QtWidgets.QDialogButtonBox.RejectRole)
        self.cancelButton.setStyleSheet(self.languagetools.anki_utils.get_red_stylesheet())

        
        vlayout.addWidget(buttonBox)

        self.pickDefaultFromToFields()
        self.updateTranslationOptions()

        # wire events
        # ===========
        self.from_combobox.currentIndexChanged.connect(self.fromFieldIndexChanged)
        self.to_combobox.currentIndexChanged.connect(self.toFieldIndexChanged)
        self.load_translations_button.pressed.connect(self.loadTranslations)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

    def pickDefaultFromToFields(self):
        # defaults in case nothing is set
        from_field_index = 0
        to_field_index = 1

        # do we have a batch translation setting set ?
        if self.transformation_type == constants.TransformationType.Translation:
            batch_translation_settings = self.languagetools.get_batch_translation_settings(self.deck_note_type)
            if len(batch_translation_settings) >= 1:
                # pick the first one
                setting_key = list(batch_translation_settings.keys())[0]
                setting = batch_translation_settings[setting_key]
                from_field = setting['from_field']
                to_field = setting_key
                # service = setting['translation_option']['service']
                if from_field in self.field_name_list:
                    from_field_index = self.field_name_list.index(from_field)
                if to_field in self.field_name_list:
                    to_field_index = self.field_name_list.index(to_field)
        if self.transformation_type == constants.TransformationType.Transliteration:
            batch_transliteration_settings = self.languagetools.get_batch_transliteration_settings(self.deck_note_type)
            if len(batch_transliteration_settings) >= 1:
                # pick the first one
                setting_key = list(batch_transliteration_settings.keys())[0]
                setting = batch_transliteration_settings[setting_key]
                from_field = setting['from_field']
                to_field = setting_key
                if from_field in self.field_name_list:
                    from_field_index = self.field_name_list.index(from_field)
                if to_field in self.field_name_list:
                    to_field_index = self.field_name_list.index(to_field)                

        # set some defaults
        # don't crash
        from_field_index = min(from_field_index, len(self.field_name_list) - 1)
        to_field_index = min(to_field_index, len(self.field_name_list) - 1)
        self.from_field = self.field_name_list[from_field_index]
        self.to_field = self.field_name_list[to_field_index]

        # set languages
        self.from_language = self.field_language[from_field_index]
        self.to_language = self.field_language[to_field_index]

        self.from_combobox.setCurrentIndex(from_field_index)
        self.to_combobox.setCurrentIndex(to_field_index)
        
        self.fromFieldIndexChanged(from_field_index, initialization=True)
        self.toFieldIndexChanged(to_field_index, initialization=True)
        
    

    def fromFieldIndexChanged(self, currentIndex, initialization=False):
        self.from_field = self.field_name_list[currentIndex]
        language_code = self.field_language[currentIndex]
        self.from_language = language_code
        language_name = self.languagetools.get_language_name(language_code)
        self.from_language_label.setText(language_name)
        self.updateTranslationOptions()
        self.updateSampleData()


    def toFieldIndexChanged(self, currentIndex, initialization=False):
        self.to_field = self.field_name_list[currentIndex]
        language_code = self.field_language[currentIndex]
        self.to_language = language_code
        language_name = self.languagetools.get_language_name(language_code)
        self.to_language_label.setText(language_name)
        self.updateTranslationOptions()
        self.updateSampleData()

    def updateTranslationOptions(self):
        if self.transformation_type == constants.TransformationType.Translation:
            self.translation_options = self.languagetools.get_translation_options(self.from_language, self.to_language)
            self.translation_service_names = [x['service'] for x in self.translation_options]
            self.service_combobox.clear()
            self.service_combobox.addItems(self.translation_service_names)
            # do we have a user preference ?
            batch_translation_settings = self.languagetools.get_batch_translation_settings(self.deck_note_type)
            if len(batch_translation_settings) >= 1:
                # pick the first one
                setting_key = list(batch_translation_settings.keys())[0]
                setting = batch_translation_settings[setting_key]
                service = setting['translation_option']['service']
                if service in self.translation_service_names:
                    service_index = self.translation_service_names.index(service)
                    self.service_combobox.setCurrentIndex(service_index)
        if self.transformation_type == constants.TransformationType.Transliteration:
            self.transliteration_options = self.languagetools.get_transliteration_options(self.from_language)
            self.transliteration_service_names = [x['transliteration_name'] for x in self.transliteration_options]
            self.service_combobox.clear()
            self.service_combobox.addItems(self.transliteration_service_names)
            # do we have a user preference ?
            batch_transliteration_settings = self.languagetools.get_batch_transliteration_settings(self.deck_note_type)
            if len(batch_transliteration_settings) >= 1:
                # pick the first one
                setting_key = list(batch_transliteration_settings.keys())[0]
                setting = batch_transliteration_settings[setting_key]
                # find the index of the service we want
                transliteration_name = setting['transliteration_option']['transliteration_name']
                if transliteration_name in self.transliteration_service_names:
                    service_index = self.transliteration_service_names.index(transliteration_name)
                    self.service_combobox.setCurrentIndex(service_index)

    def updateSampleData(self):
        # self.from_field
        self.noteTableModel.setFromField(self.from_field)
        self.noteTableModel.setToField(self.to_field)
        from_field_data = []
        self.to_fields_empty = True
        for note_id in self.note_id_list:
            note = self.languagetools.anki_utils.get_note_by_id(note_id)
            field_data = note[self.from_field]
            from_field_data.append(field_data)
            # self.to_fields_empty = True
            if len(note[self.to_field]) > 0:
                self.to_fields_empty = False
        self.from_field_data = from_field_data
        self.noteTableModel.setFromFieldData(from_field_data)

    def loadTranslations(self):
        if self.languagetools.ensure_api_key_checked() == False:
            return
        if self.transformation_type == constants.TransformationType.Translation:
            if len(self.translation_options) == 0:
                self.languagetools.anki_utils.critical_message(f'No service found for translation from language {self.languagetools.get_language_name(self.from_language)}', self)
                return
        elif self.transformation_type == constants.TransformationType.Transliteration:
            if len(self.transliteration_options) == 0:
                self.languagetools.anki_utils.critical_message(f'No service found for transliteration from language {self.languagetools.get_language_name(self.from_language)}', self)
                return
        self.languagetools.anki_utils.run_in_background(self.loadTranslationsTask, self.loadTranslationDone)

    def loadTranslationsTask(self):
        self.load_errors = []

        try:
            self.languagetools.anki_utils.run_on_main(lambda: self.load_translations_button.setDisabled(True))
            self.languagetools.anki_utils.run_on_main(lambda: self.load_translations_button.setStyleSheet(None))
            self.languagetools.anki_utils.run_on_main(lambda: self.applyButton.setDisabled(True))
            self.languagetools.anki_utils.run_on_main(lambda: self.applyButton.setStyleSheet(None))
            self.languagetools.anki_utils.run_on_main(lambda: self.load_translations_button.setText('Loading...'))

            self.languagetools.anki_utils.run_on_main(lambda: self.progress_bar.setValue(0))
            self.languagetools.anki_utils.run_on_main(lambda: self.progress_bar.setMaximum(len(self.from_field_data)))

            # get service
            if self.transformation_type == constants.TransformationType.Translation:
                service = self.translation_service_names[self.service_combobox.currentIndex()]
                translation_options = self.languagetools.get_translation_options(self.from_language, self.to_language)
                translation_option_subset = [x for x in translation_options if x['service'] == service]
                assert(len(translation_option_subset) == 1)
                self.translation_option = translation_option_subset[0]
            elif self.transformation_type == constants.TransformationType.Transliteration:
                self.transliteration_option = self.transliteration_options[self.service_combobox.currentIndex()]

            def get_set_to_field_lambda(i, translation_result):
                def set_to_field():
                    self.noteTableModel.setToFieldData(i, translation_result)
                return set_to_field

        except Exception as e:
            self.load_errors.append(e)
            return


        i = 0
        for field_data in self.from_field_data:
            try:
                if self.transformation_type == constants.TransformationType.Translation:
                    translation_result = self.languagetools.get_translation(field_data, self.translation_option)
                elif self.transformation_type == constants.TransformationType.Transliteration:
                    translation_result = self.languagetools.get_transliteration(field_data, self.transliteration_option)
                self.languagetools.anki_utils.run_on_main(get_set_to_field_lambda(i, translation_result))
            except errors.LanguageToolsError as e:
                self.load_errors.append(e)
            except Exception as e:
                logging.exception(e)
                self.load_errors.append(e)
            i += 1
            self.languagetools.anki_utils.run_on_main(lambda: self.progress_bar.setValue(i))

        self.languagetools.anki_utils.run_on_main(lambda: self.applyButton.setDisabled(False))
        self.languagetools.anki_utils.run_on_main(lambda: self.applyButton.setStyleSheet(self.languagetools.anki_utils.get_green_stylesheet()))


        self.languagetools.anki_utils.run_on_main(lambda: self.load_translations_button.setDisabled(False))
        self.languagetools.anki_utils.run_on_main(lambda: self.load_translations_button.setStyleSheet(self.languagetools.anki_utils.get_green_stylesheet()))
        self.languagetools.anki_utils.run_on_main(lambda: self.load_translations_button.setText(self.load_button_text_map[self.transformation_type]))


    def loadTranslationDone(self, future_result):
        if len(self.load_errors) > 0:
            error_counts = {}
            for error_exception in self.load_errors:
                error = str(error_exception)
                current_count = error_counts.get(error, 0)
                error_counts[error] = current_count + 1
            error_message = '<p><b>Errors</b>: ' + ', '.join([f'{key} ({value} times)' for key, value in error_counts.items()]) + '</p>'
            complete_message = f'<p>Encountered errors while generating {self.transformation_type.name}. You can still click <b>Apply to Notes</b> to apply the values retrieved to your notes.</p>' + error_message
            self.languagetools.anki_utils.critical_message(complete_message, self)

    def accept(self):
        if self.to_fields_empty == False:
            proceed = self.languagetools.anki_utils.ask_user(f'Overwrite existing data in field {self.to_field} ?', self)
            if proceed == False:
                return
        # set field on notes
        action_str = f'Translate from {self.languagetools.get_language_name(self.from_language)} to {self.languagetools.get_language_name(self.to_language)}'
        self.languagetools.anki_utils.checkpoint(action_str)
        for (note_id, i) in zip(self.note_id_list, range(len(self.note_id_list))):
            to_field_data = self.noteTableModel.to_field_data[i]
            if to_field_data != None:
                note = self.languagetools.anki_utils.get_note_by_id(note_id)
                note[self.to_field] = to_field_data
                note.flush()
        self.close()
        # memorize this setting
        deck_note_type_field = self.languagetools.deck_utils.build_dntf_from_dnt(self.deck_note_type, self.to_field)
        if self.transformation_type == constants.TransformationType.Translation:
            self.languagetools.store_batch_translation_setting(deck_note_type_field, self.from_field, self.translation_option)
        elif self.transformation_type == constants.TransformationType.Transliteration:
            self.languagetools.store_batch_transliteration_setting(deck_note_type_field, self.from_field, self.transliteration_option)


def prepare_batch_transformation_dialogue(languagetools, deck_note_type, note_id_list, transformation_type):
    deck_map: Dict[str, Deck] = languagetools.get_populated_decks()

    dialog = BatchConversionDialog(languagetools, deck_note_type, note_id_list, transformation_type)
    dialog.setupUi()
    return dialog

