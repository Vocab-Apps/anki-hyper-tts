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

class NoteSettingsDialogBase(PyQt5.QtWidgets.QDialog):
    def __init__(self, languagetools: LanguageTools, deck_note_type: deck_utils.DeckNoteType):
        super(PyQt5.QtWidgets.QDialog, self).__init__()
        self.languagetools = languagetools
        self.deck_note_type = deck_note_type

        self.remove_translation_map = {}
        self.remove_transliteration_map = {}
        self.remove_audio_map = {}

        self.apply_updates_setting_changed = False
        self.apply_updates_value = True

    def layout_rules(self, vlayout):

        font_bold = PyQt5.QtGui.QFont()
        font_bold.setBold(True)

        # do we have translation rules for this deck_note_type
        translation_settings = self.languagetools.get_batch_translation_settings(self.deck_note_type)
        if len(translation_settings) > 0:
            vlayout.addWidget(gui_utils.get_medium_label(f'Translation Rules'))
            gridlayout = PyQt5.QtWidgets.QGridLayout()
            i = 0
            for to_field, setting in translation_settings.items():
                from_field = setting['from_field']
                from_dntf = self.languagetools.deck_utils.build_dntf_from_dnt(self.deck_note_type, from_field)
                to_dntf = self.languagetools.deck_utils.build_dntf_from_dnt(self.deck_note_type, to_field)
                from_language_name = self.languagetools.get_language_name(self.languagetools.get_language(from_dntf))
                to_language_name = self.languagetools.get_language_name(self.languagetools.get_language(to_dntf))

                from_field_label = PyQt5.QtWidgets.QLabel(f'{from_field}')
                from_field_label.setFont(font_bold)

                to_field_label = PyQt5.QtWidgets.QLabel(f'{to_field}')
                to_field_label.setFont(font_bold)

                x_offset = 0
                if self.add_rule_enable_checkbox():
                    self.target_field_enabled_map[to_field] = True
                    checkbox = PyQt5.QtWidgets.QCheckBox()
                    checkbox.setChecked(True)
                    self.target_field_checkbox_map[to_field] = checkbox
                    gridlayout.addWidget(checkbox, i, 0, 1, 1)    
                    x_offset = 1

                gridlayout.addWidget(PyQt5.QtWidgets.QLabel(f'From:'), i, x_offset + 0, 1, 1)
                gridlayout.addWidget(from_field_label, i, x_offset + 1, 1, 1)
                gridlayout.addWidget(PyQt5.QtWidgets.QLabel(f'({from_language_name})'), i, x_offset + 2, 1, 1)
                gridlayout.addWidget(PyQt5.QtWidgets.QLabel(f'To:'), i, x_offset + 3, 1, 1)
                gridlayout.addWidget(to_field_label, i, x_offset + 4, 1, 1)
                gridlayout.addWidget(PyQt5.QtWidgets.QLabel(f'({to_language_name})'), i, x_offset + 5, 1, 1)
                
                if self.add_delete_button():
                    delete_button = PyQt5.QtWidgets.QPushButton()
                    delete_button.setText('Remove')
                    def get_remove_lambda(to_dntf, button):
                        def remove():
                            button.setEnabled(False)
                            button.setText('Removed')
                            self.remove_translation(to_dntf)
                        return remove
                    delete_button.pressed.connect(get_remove_lambda(to_dntf, delete_button))
                    gridlayout.addWidget(delete_button, i, 6, 1, 1)
                i += 1

            x_offset = 0
            if self.add_rule_enable_checkbox():
                gridlayout.setColumnStretch(0, 10) # enable checkbox
                x_offset = 1
            gridlayout.setColumnStretch(x_offset + 0, 10) # from:
            gridlayout.setColumnStretch(x_offset + 1, 20) # from field label
            gridlayout.setColumnStretch(x_offset + 2, 30) # from language name
            gridlayout.setColumnStretch(x_offset + 3, 10) # to:
            gridlayout.setColumnStretch(x_offset + 4, 20) # to field label
            gridlayout.setColumnStretch(x_offset + 5, 30) # to language name
            if self.add_delete_button():
                gridlayout.setColumnStretch(6, 10) # remove button
            gridlayout.setContentsMargins(10, 0, 10, 0)
            vlayout.addLayout(gridlayout)

        # do we have transliteration rules for this deck_note_type
        transliteration_settings = self.languagetools.get_batch_transliteration_settings(self.deck_note_type)
        if len(transliteration_settings) > 0:
            vlayout.addWidget(gui_utils.get_medium_label(f'Transliteration Rules'))
            gridlayout = PyQt5.QtWidgets.QGridLayout()
            i = 0
            for to_field, setting in transliteration_settings.items():
                from_field = setting['from_field']
                from_dntf = self.languagetools.deck_utils.build_dntf_from_dnt(self.deck_note_type, from_field)
                to_dntf = self.languagetools.deck_utils.build_dntf_from_dnt(self.deck_note_type, to_field)
                from_language_name = self.languagetools.get_language_name(self.languagetools.get_language(from_dntf))
                transliteration_name = setting['transliteration_option']['transliteration_name']

                from_field_label = PyQt5.QtWidgets.QLabel(f'{from_field}')
                from_field_label.setFont(font_bold)

                to_field_label = PyQt5.QtWidgets.QLabel(f'{to_field}')
                to_field_label.setFont(font_bold)

                x_offset = 0
                if self.add_rule_enable_checkbox():
                    self.target_field_enabled_map[to_field] = True
                    checkbox = PyQt5.QtWidgets.QCheckBox()
                    checkbox.setChecked(True)
                    self.target_field_checkbox_map[to_field] = checkbox
                    gridlayout.addWidget(checkbox, i, 0, 1, 1)    
                    x_offset = 1                

                gridlayout.addWidget(PyQt5.QtWidgets.QLabel(f'From:'), i, x_offset + 0, 1, 1)
                gridlayout.addWidget(from_field_label, i, x_offset + 1, 1, 1)
                gridlayout.addWidget(PyQt5.QtWidgets.QLabel(f'({from_language_name})'), i, x_offset + 2, 1, 1)
                gridlayout.addWidget(PyQt5.QtWidgets.QLabel(f'To:'), i, x_offset + 3, 1, 1)
                gridlayout.addWidget(to_field_label, i, x_offset + 4, 1, 1)
                gridlayout.addWidget(PyQt5.QtWidgets.QLabel(f'({transliteration_name})'), i, x_offset + 5, 1, 1)
                
                if self.add_delete_button():
                    delete_button = PyQt5.QtWidgets.QPushButton()
                    delete_button.setText('Remove')
                    def get_remove_lambda(to_dntf, button):
                        def remove():
                            button.setEnabled(False)
                            button.setText('Removed')                        
                            self.remove_transliteration(to_dntf)
                        return remove
                    delete_button.pressed.connect(get_remove_lambda(to_dntf, delete_button))
                    gridlayout.addWidget(delete_button, i, 6, 1, 1)
                i += 1

            x_offset = 0
            if self.add_rule_enable_checkbox():
                gridlayout.setColumnStretch(0, 10) # enable checkbox
                x_offset = 1
            gridlayout.setColumnStretch(x_offset + 0, 10) # from:
            gridlayout.setColumnStretch(x_offset + 1, 20) # from field label
            gridlayout.setColumnStretch(x_offset + 2, 30) # from language name
            gridlayout.setColumnStretch(x_offset + 3, 10) # to:
            gridlayout.setColumnStretch(x_offset + 4, 20) # to field label
            gridlayout.setColumnStretch(x_offset + 5, 30) # to language name
            if self.add_delete_button():
                gridlayout.setColumnStretch(6, 10) # remove button          
            gridlayout.setContentsMargins(10, 0, 10, 0)      
            vlayout.addLayout(gridlayout)            

        # do we have any audio rules for this deck_note_type
        audio_settings = self.languagetools.get_batch_audio_settings(self.deck_note_type)
        if len(audio_settings) > 0:
            vlayout.addWidget(gui_utils.get_medium_label(f'Audio Rules'))
            gridlayout = PyQt5.QtWidgets.QGridLayout()
            i = 0
            for to_field, from_field in audio_settings.items():
                from_dntf = self.languagetools.deck_utils.build_dntf_from_dnt(self.deck_note_type, from_field)
                to_dntf = self.languagetools.deck_utils.build_dntf_from_dnt(self.deck_note_type, to_field)
                from_language_code = self.languagetools.get_language(from_dntf)
                from_language_name = self.languagetools.get_language_name(from_language_code)
                # get the assigned voice for this langugae
                voice_selection_settings = self.languagetools.get_voice_selection_settings()
                voice_description = 'No Voice Selected'
                if from_language_code in voice_selection_settings:
                    voice_description = voice_selection_settings[from_language_code]['voice_description']

                from_field_label = PyQt5.QtWidgets.QLabel(f'{from_field}')
                from_field_label.setFont(font_bold)

                to_field_label = PyQt5.QtWidgets.QLabel(f'{to_field}')
                to_field_label.setFont(font_bold)

                x_offset = 0
                if self.add_rule_enable_checkbox():
                    self.target_field_enabled_map[to_field] = True
                    checkbox = PyQt5.QtWidgets.QCheckBox()
                    checkbox.setChecked(True)
                    self.target_field_checkbox_map[to_field] = checkbox
                    gridlayout.addWidget(checkbox, i, 0, 1, 1)
                    x_offset = 1                

                gridlayout.addWidget(PyQt5.QtWidgets.QLabel(f'From:'), i, x_offset + 0, 1, 1)
                gridlayout.addWidget(from_field_label, i, x_offset + 1, 1, 1)
                gridlayout.addWidget(PyQt5.QtWidgets.QLabel(f'({from_language_name})'), i, x_offset + 2, 1, 1)
                gridlayout.addWidget(PyQt5.QtWidgets.QLabel(f'To:'), i, x_offset + 3, 1, 1)
                gridlayout.addWidget(to_field_label, i, x_offset + 4, 1, 1)
                gridlayout.addWidget(PyQt5.QtWidgets.QLabel(f'({voice_description})'), i, x_offset + 5, 1, 1)
                
                if self.add_delete_button():
                    delete_button = PyQt5.QtWidgets.QPushButton()
                    delete_button.setText('Remove')
                    def get_remove_lambda(to_dntf, button):
                        def remove():
                            button.setEnabled(False)
                            button.setText('Removed')                        
                            self.remove_audio(to_dntf)
                        return remove
                    delete_button.pressed.connect(get_remove_lambda(to_dntf, delete_button))                
                    gridlayout.addWidget(delete_button, i, 6, 1, 1)
                i += 1

            x_offset = 0
            if self.add_rule_enable_checkbox():
                gridlayout.setColumnStretch(0, 10) # enable checkbox
                x_offset = 1
            gridlayout.setColumnStretch(x_offset + 0, 10) # from:
            gridlayout.setColumnStretch(x_offset + 1, 20) # from field label
            gridlayout.setColumnStretch(x_offset + 2, 30) # from language name
            gridlayout.setColumnStretch(x_offset + 3, 10) # to:
            gridlayout.setColumnStretch(x_offset + 4, 20) # to field label
            gridlayout.setColumnStretch(x_offset + 5, 30) # to language name
            if self.add_delete_button():
                gridlayout.setColumnStretch(6, 10) # remove button
            gridlayout.setContentsMargins(10, 0, 10, 0)    
            vlayout.addLayout(gridlayout)                        



class NoteSettingsDialog(NoteSettingsDialogBase):
    def __init__(self, languagetools: LanguageTools, deck_note_type: deck_utils.DeckNoteType):
        super(NoteSettingsDialog, self).__init__(languagetools, deck_note_type)

    def get_header_text(self):
        return f'Rules for {self.deck_note_type}'

    def add_delete_button(self):
        return True

    def add_rule_enable_checkbox(self):
        return False

    def setupUi(self):
        self.setWindowTitle(constants.ADDON_NAME)
        self.resize(700, 500)

        vlayout = PyQt5.QtWidgets.QVBoxLayout(self)

        vlayout.addWidget(gui_utils.get_header_label(self.get_header_text()))

        vlayout.addWidget(PyQt5.QtWidgets.QLabel('You can visualize and remove Audio / Translation / Transliteration rules from here.'))

        self.layout_rules(vlayout)

        vlayout.addWidget(gui_utils.get_medium_label(f'Apply Changes While Typing'))
        self.checkbox = PyQt5.QtWidgets.QCheckBox("Language Tools will automatically apply field translations / transliterations / audio when typing into the From field")
        self.checkbox.setChecked(self.languagetools.get_apply_updates_automatically())
        self.checkbox.setContentsMargins(10, 0, 10, 0)
        vlayout.addWidget(self.checkbox)

        vlayout.addStretch()

        # buttom buttons
        buttonBox = PyQt5.QtWidgets.QDialogButtonBox()
        self.applyButton = buttonBox.addButton("Save Settings", PyQt5.QtWidgets.QDialogButtonBox.AcceptRole)
        self.applyButton.setEnabled(False)
        self.cancelButton = buttonBox.addButton("Cancel", PyQt5.QtWidgets.QDialogButtonBox.RejectRole)
        self.cancelButton.setStyleSheet(self.languagetools.anki_utils.get_red_stylesheet())
        vlayout.addWidget(buttonBox)
  
        # wire events
        self.checkbox.stateChanged.connect(self.apply_updates_state_changed)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

    def remove_translation(self, deck_note_type_field):
        # print(f'remove_translation, dntf: {deck_note_type_field}')
        self.remove_translation_map[deck_note_type_field] = True
        self.enable_apply_button()

    def remove_transliteration(self, deck_note_type_field):
        # print(f'remove_transliteration, dntf: {deck_note_type_field}')
        self.remove_transliteration_map[deck_note_type_field] = True
        self.enable_apply_button()

    def remove_audio(self, deck_note_type_field):
        # print(f'remove_audio, dntf: {deck_note_type_field}')
        self.remove_audio_map[deck_note_type_field] = True
        self.enable_apply_button()

    def apply_updates_state_changed(self, state):
        self.apply_updates_setting_changed = True
        self.apply_updates_value = self.checkbox.isChecked()
        self.enable_apply_button()
    
    def enable_apply_button(self):
        self.applyButton.setEnabled(True)
        self.applyButton.setStyleSheet(self.languagetools.anki_utils.get_green_stylesheet())


    def accept(self):
        if self.apply_updates_setting_changed:
            self.languagetools.set_apply_updates_automatically(self.apply_updates_value)

        for dntf in self.remove_translation_map.keys():
            self.languagetools.remove_translation_setting(dntf)
        for dntf in self.remove_transliteration_map.keys():
            self.languagetools.remove_transliteration_setting(dntf)
        for dntf in self.remove_audio_map.keys():
            self.languagetools.remove_audio_setting(dntf)
        
        self.close()



class RunRulesDialog(NoteSettingsDialogBase):
    def __init__(self, languagetools: LanguageTools, deck_note_type: deck_utils.DeckNoteType, note_id_list):
        super(RunRulesDialog, self).__init__(languagetools, deck_note_type)
        self.note_id_list = note_id_list
        self.target_field_enabled_map = {}
        self.target_field_checkbox_map = {}

    def get_header_text(self):
        return f'Run Rules for {self.deck_note_type}'

    def add_delete_button(self):
        return False

    def add_rule_enable_checkbox(self):
        return True        

    def setupUi(self):
        self.setWindowTitle(constants.ADDON_NAME)
        self.resize(700, 300)

        vlayout = PyQt5.QtWidgets.QVBoxLayout(self)

        vlayout.addWidget(gui_utils.get_header_label(self.get_header_text()))

        vlayout.addWidget(PyQt5.QtWidgets.QLabel('Select the rules you want to run, then click Apply Rules.'))

        self.layout_rules(vlayout)

        # progress bar
        hlayout = PyQt5.QtWidgets.QHBoxLayout()
        hlayout.setContentsMargins(0, 20, 0, 0)
        self.progress_bar = PyQt5.QtWidgets.QProgressBar()
        hlayout.addWidget(self.progress_bar)
        vlayout.addLayout(hlayout)

        # buttom buttons
        buttonBox = PyQt5.QtWidgets.QDialogButtonBox()
        self.applyButton = buttonBox.addButton("Apply Rules", PyQt5.QtWidgets.QDialogButtonBox.AcceptRole)
        self.applyButton.setStyleSheet(self.languagetools.anki_utils.get_green_stylesheet())
        self.cancelButton = buttonBox.addButton("Cancel", PyQt5.QtWidgets.QDialogButtonBox.RejectRole)
        self.cancelButton.setStyleSheet(self.languagetools.anki_utils.get_red_stylesheet())
        vlayout.addWidget(buttonBox)

        vlayout.addStretch()        
  
        # wire events
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

    def accept(self):
        proceed = self.languagetools.anki_utils.ask_user(f'Overwrite existing data in target fields ?', self)
        if proceed == False:
            # don't continue
            return

        self.languagetools.anki_utils.run_in_background(self.process_rules_task, self.process_rules_task_done)

    def verify_to_from_fields(self, note, from_dntf, to_dntf):
        if from_dntf.field_name not in note:
            raise errors.FieldNotFoundError(from_dntf)
        if to_dntf.field_name not in note:
            raise errors.FieldNotFoundError(to_dntf)



    def process_rules_task(self):
        self.batch_error_manager = self.languagetools.error_manager.get_batch_error_manager('processing rules')

        translation_settings = self.languagetools.get_batch_translation_settings(self.deck_note_type)
        transliteration_settings = self.languagetools.get_batch_transliteration_settings(self.deck_note_type)
        audio_settings = self.languagetools.get_batch_audio_settings(self.deck_note_type)

        num_rules = 0
        for rule_list in [translation_settings, transliteration_settings, audio_settings]:
            for to_field, setting in rule_list.items():
                if self.target_field_checkbox_map[to_field].isChecked():
                    num_rules += 1

        logging.debug(f'num rules enabled: {num_rules}')
        self.languagetools.anki_utils.run_on_main(lambda: self.progress_bar.setMaximum(len(self.note_id_list) * num_rules))

        progress_value = 0
        self.generate_errors = []
        for note_id in self.note_id_list:
            note = self.languagetools.anki_utils.get_note_by_id(note_id)
            need_to_flush = False
            for to_field, setting in translation_settings.items():
                if self.target_field_checkbox_map[to_field].isChecked():
                    with self.batch_error_manager.get_batch_action_context(f'adding translation to field {to_field}'):
                        from_field = setting['from_field']
                        from_dntf = self.languagetools.deck_utils.build_dntf_from_dnt(self.deck_note_type, from_field)
                        to_dntf = self.languagetools.deck_utils.build_dntf_from_dnt(self.deck_note_type, to_field)
                        self.verify_to_from_fields(note, from_dntf, to_dntf)
                        logging.info(f'generating translation from {from_dntf} to {to_dntf}')

                        field_data = note[from_field]
                        translation_option = setting['translation_option']
                        translation_result = self.languagetools.get_translation(field_data, translation_option)
                        note[to_field] = translation_result
                        need_to_flush = True
                    progress_value += 1
                    self.languagetools.anki_utils.run_on_main(lambda: self.progress_bar.setValue(progress_value))
            for to_field, setting in transliteration_settings.items():
                if self.target_field_checkbox_map[to_field].isChecked():
                    with self.batch_error_manager.get_batch_action_context(f'adding transliteration to field {to_field}'):
                        from_field = setting['from_field']
                        from_dntf = self.languagetools.deck_utils.build_dntf_from_dnt(self.deck_note_type, from_field)
                        to_dntf = self.languagetools.deck_utils.build_dntf_from_dnt(self.deck_note_type, to_field)
                        self.verify_to_from_fields(note, from_dntf, to_dntf)
                        logging.info(f'generating transliteration from {from_dntf} to {to_dntf}')

                        field_data = note[from_field]
                        transliteration_option = setting['transliteration_option']
                        transliteration_result = self.languagetools.get_transliteration(field_data, transliteration_option)
                        note[to_field] = transliteration_result
                        need_to_flush = True
                    progress_value += 1
                    self.languagetools.anki_utils.run_on_main(lambda: self.progress_bar.setValue(progress_value))
            for to_field, from_field in audio_settings.items():
                if self.target_field_checkbox_map[to_field].isChecked():
                    with self.batch_error_manager.get_batch_action_context(f'adding audio to field {to_field}'):
                        from_dntf = self.languagetools.deck_utils.build_dntf_from_dnt(self.deck_note_type, from_field)
                        to_dntf = self.languagetools.deck_utils.build_dntf_from_dnt(self.deck_note_type, to_field)
                        self.verify_to_from_fields(note, from_dntf, to_dntf)
                        logging.info(f'generating audio from {from_dntf} to {to_dntf}')

                        field_data = note[from_field]
                        voice = self.languagetools.get_voice_for_field(from_dntf)
                        result = self.languagetools.generate_audio_tag_collection(field_data, voice)
                        note[to_field] = result['sound_tag']
                        need_to_flush = True
                    progress_value += 1
                    self.languagetools.anki_utils.run_on_main(lambda: self.progress_bar.setValue(progress_value))

            # write output to note
            if need_to_flush:
                note.flush()


    def process_rules_task_done(self, future_result):
        self.close()
        self.batch_error_manager.display_stats(self)

