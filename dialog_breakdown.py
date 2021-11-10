import sys
import logging
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


class BreakdownDialog(PyQt5.QtWidgets.QDialog):
    def __init__(self, languagetools: LanguageTools, text, from_language, editor, deck_note_type):
        super(PyQt5.QtWidgets.QDialog, self).__init__()
        self.languagetools = languagetools

        self.text = text
        self.from_language = from_language
        self.editor = editor
        self.deck_note_type = deck_note_type

    def setupUi(self):
        self.setWindowTitle(constants.ADDON_NAME)
        self.resize(500, 350)

        vlayout = PyQt5.QtWidgets.QVBoxLayout(self)
        vlayout.addWidget(gui_utils.get_header_label('Breakdown'))
        vlayout.addWidget(gui_utils.get_medium_label(f'{self.text} ({self.languagetools.get_language_name(self.from_language)})'))

        gridlayout = PyQt5.QtWidgets.QGridLayout()

        # show tokenization options
        # show translation options, with checkbox
        # show transliteration options, with checkbox

        # create all widgets
        # ==================

        font1 = PyQt5.QtGui.QFont()
        font1.setBold(True)

        self.target_language_dropdown = PyQt5.QtWidgets.QComboBox()
        
        self.tokenization_dropdown = PyQt5.QtWidgets.QComboBox()
        self.translation_checkbox = PyQt5.QtWidgets.QCheckBox()
        self.translation_checkbox.setText('Enable')
        self.translation_dropdown = PyQt5.QtWidgets.QComboBox()
        self.transliteration_checkbox = PyQt5.QtWidgets.QCheckBox()
        self.transliteration_checkbox.setText('Enable')
        self.transliteration_dropdown = PyQt5.QtWidgets.QComboBox()
        self.target_field_dropdown = PyQt5.QtWidgets.QComboBox()
        self.target_field_dropdown.setDisabled(True)

        self.breakdown_result = PyQt5.QtWidgets.QLabel()
        self.breakdown_result.setTextInteractionFlags(PyQt5.QtCore.Qt.TextSelectableByMouse)
        self.breakdown_result.setText('<i>Press Load Breakdown to see result</i>')

        target_language_label = PyQt5.QtWidgets.QLabel()
        target_language_label.setText('Target Language:')
        target_language_label.setFont(font1)

        segmentation_label = PyQt5.QtWidgets.QLabel()
        segmentation_label.setText('Segmentation:')
        segmentation_label.setFont(font1)

        translation_label = PyQt5.QtWidgets.QLabel()
        translation_label.setText('Translation:')
        translation_label.setFont(font1)

        transliteration_label = PyQt5.QtWidgets.QLabel()
        transliteration_label.setText('Transliteration:')
        transliteration_label.setFont(font1)

        self.load_button = PyQt5.QtWidgets.QPushButton()
        self.load_button.setText('Load Breakdown')
        self.load_button.setDisabled(False)
        self.load_button.setStyleSheet(self.languagetools.anki_utils.get_green_stylesheet())
        self.load_button.setFont(gui_utils.get_large_button_font())

        self.copy_to_field_button = PyQt5.QtWidgets.QPushButton()
        self.copy_to_field_button.setText('Copy to Field')
        self.copy_to_field_button.setDisabled(True)

        vlayout.addWidget(gui_utils.get_medium_label('Options'))

        # place widgets on grid
        # =====================

        regular_width = 2
        row = 0
        gridlayout.addWidget(segmentation_label, row, 0, 1, 1)
        gridlayout.addWidget(self.tokenization_dropdown, row, 1, 1, regular_width)
        row = 1
        gridlayout.addWidget(target_language_label, row, 0, 1, 1)
        gridlayout.addWidget(self.target_language_dropdown, row, 1, 1, regular_width)
        row = 2
        gridlayout.addWidget(translation_label, row, 0, 1, 1)
        gridlayout.addWidget(self.translation_checkbox, row, 1, 1, 1)
        gridlayout.addWidget(self.translation_dropdown, row, 2, 1, 1)
        row = 3
        gridlayout.addWidget(transliteration_label, row, 0, 1, 1)
        gridlayout.addWidget(self.transliteration_checkbox, row, 1, 1, 1)
        gridlayout.addWidget(self.transliteration_dropdown, row, 2, 1, 1)

        gridlayout.setContentsMargins(10, 10, 10, 10)
        vlayout.addLayout(gridlayout)

        # add result label
        # ================
        vlayout.addWidget(gui_utils.get_medium_label('Breakdown Result'))
        self.breakdown_result.setContentsMargins(10, 10, 10, 10)
        vlayout.addWidget(self.breakdown_result)

        # load button
        # ===========
        vlayout.addWidget(self.load_button)

        hlayout = PyQt5.QtWidgets.QHBoxLayout(self)
        hlayout.addWidget(self.copy_to_field_button)
        hlayout.addWidget(self.target_field_dropdown)
        vlayout.addLayout(hlayout)

        self.populate_target_languages()
        self.populate_controls()

        self.load_button.pressed.connect(self.load_breakdown)
        self.copy_to_field_button.pressed.connect(self.copy_to_field)

    def copy_to_field(self):
        # get index of field selected
        target_field_index = self.target_field_dropdown.currentIndex()
        self.languagetools.anki_utils.editor_set_field_value(self.editor, target_field_index, self.result_html)
        self.accept()

    def load_breakdown(self):
        self.load_button.setText('Loading Breakdown...')
        self.load_button.setDisabled(True)
        self.languagetools.anki_utils.run_in_background(self.query_breakdown, self.query_breakdown_done)

    def query_breakdown(self):
        # tokenization option
        tokenization_option = self.tokenization_options[self.tokenization_dropdown.currentIndex()]
        # transliteration option
        transliteration_option = None
        if self.transliteration_checkbox.isChecked() and len(self.transliteration_options) > 0:
            transliteration_option = self.transliteration_options[self.transliteration_dropdown.currentIndex()]
        # translation option
        translation_option = None
        if self.translation_checkbox.isChecked() and len(self.translation_options) > 0:
            translation_option = self.translation_options[self.translation_dropdown.currentIndex()]

        return self.languagetools.get_breakdown_async(self.text,
            tokenization_option,
            translation_option,
            transliteration_option)

    def query_breakdown_done(self, future_result):
        with self.languagetools.error_manager.get_single_action_context(f'loading breakdown'):

            self.load_button.setText('Load Breakdown')
            self.load_button.setDisabled(False)

            self.target_field_dropdown.setDisabled(False)
            self.copy_to_field_button.setDisabled(False)

            breakdown_result = self.languagetools.interpret_breakdown_response_async(future_result.result())
            lines = [self.languagetools.format_breakdown_entry(x) for x in breakdown_result]
            self.result_html = '<br/>'.join(lines)
            self.breakdown_result.setText(self.result_html)

            logging.info(breakdown_result)


    def populate_target_languages(self):
        self.wanted_language_arrays = self.languagetools.get_wanted_language_arrays()
        self.target_language_dropdown.addItems(self.wanted_language_arrays['language_name_list'])

        self.target_language_dropdown.currentIndexChanged.connect(self.target_language_index_changed)
        # run once
        self.target_language_index_changed(0)

    def target_language_index_changed(self, current_index):
        # populate translation options
        target_language = self.wanted_language_arrays['language_code_list'][current_index]
        self.translation_options = self.languagetools.get_translation_options(self.from_language, target_language)
        self.translation_dropdown.clear()
        self.translation_dropdown.addItems([x['service'] for x in self.translation_options])


    def populate_controls(self):
        # target language
        # ===============

        # tokenization
        # ============
        self.tokenization_options = self.languagetools.get_tokenization_options(self.from_language)
        if len(self.tokenization_options) == 0:
            message = f'breakdown not supported for {self.languagetools.get_language_name(self.from_language)}'
            self.languagetools.anki_utils.critical_message(message, self)
            # disable load button
            self.load_button.setDisabled(True)
        tokenization_option_names = [x['tokenization_name'] for x in self.tokenization_options]
        self.tokenization_dropdown.addItems(tokenization_option_names)

        # translation
        # ===========
        # dropdown populated separately
        self.translation_checkbox.setChecked(True)

        # transliteration
        # ===============
        self.transliteration_checkbox.setChecked(True)
        self.transliteration_options = self.languagetools.get_transliteration_options(self.from_language)
        self.transliteration_dropdown.addItems([x['transliteration_name'] for x in self.transliteration_options])

        # target field
        # ============
        self.target_field_dropdown.addItems(self.languagetools.deck_utils.get_field_names(self.deck_note_type))









def prepare_dialog(languagetools, text, from_language, editor, deck_note_type):
    dialog = BreakdownDialog(languagetools, text, from_language, editor, deck_note_type)
    dialog.setupUi()
    return dialog