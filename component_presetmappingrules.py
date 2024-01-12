import sys
import aqt.qt

component_common = __import__('component_common', globals(), locals(), [], sys._addon_import_level_base)
component_mappingrule = __import__('component_mappingrule', globals(), locals(), [], sys._addon_import_level_base)
component_choosepreset = __import__('component_choosepreset', globals(), locals(), [], sys._addon_import_level_base)
config_models = __import__('config_models', globals(), locals(), [], sys._addon_import_level_base)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_base)
errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_base)
gui_utils = __import__('gui_utils', globals(), locals(), [], sys._addon_import_level_base)
logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_base)
logger = logging_utils.get_child_logger(__name__)


class ComponentPresetMappingRules(component_common.ConfigComponentBase):

    def __init__(self, hypertts, dialog, deck_note_type: config_models.DeckNoteType, editor_context: config_models.EditorContext):
        self.hypertts = hypertts
        self.dialog = dialog
        self.model = config_models.PresetMappingRules()
        self.deck_note_type = deck_note_type
        self.editor_context = editor_context
        self.rules_components = []
        self.model_changed = False

    def load_model(self, model: config_models.PresetMappingRules):
        logger.info('load_model')
        self.model = model
        # draw the presets
        self.refresh_mapping_rules_gridlayout()
        self.model_changed = False
        self.update_button_states() 

    def get_model(self) -> config_models.PresetMappingRules:
        return self.model

    def draw(self, layout):
        self.vlayout = aqt.qt.QVBoxLayout()

        # dialog header 
        # =============

        # logo should appear on the right
        hlayout = aqt.qt.QHBoxLayout()
        hlayout.addStretch()
        # logo header
        hlayout.addLayout(gui_utils.get_hypertts_label_header(self.hypertts.hypertts_pro_enabled()))
        self.vlayout.addLayout(hlayout)

        # font setup
        # ==========

        bold_font = aqt.qt.QFont()
        bold_font.setBold(True)

        top_hlayout = aqt.qt.QHBoxLayout()

        # deck and note type
        # ==================
        deck_note_type_vlayout = aqt.qt.QVBoxLayout()

        # note type
        hlayout = aqt.qt.QHBoxLayout()
        hlayout.addWidget(aqt.qt.QLabel(f'<b>Note Type:</b>'))
        self.note_type_label = aqt.qt.QLabel(self.hypertts.anki_utils.get_note_type_name(self.deck_note_type.model_id))
        hlayout.addWidget(self.note_type_label)
        hlayout.addStretch()
        deck_note_type_vlayout.addLayout(hlayout)

        # deck info
        hlayout = aqt.qt.QHBoxLayout()
        hlayout.addWidget(aqt.qt.QLabel(f'<b>Deck:</b>'))
        self.deck_name_label = aqt.qt.QLabel(self.hypertts.anki_utils.get_deck_name(self.deck_note_type.deck_id))
        hlayout.addWidget(self.deck_name_label)
        hlayout.addStretch()
        deck_note_type_vlayout.addLayout(hlayout)

        deck_note_type_vlayout.addStretch()

        self.note_info_groupbox = aqt.qt.QGroupBox('Note Info')
        self.note_info_groupbox.setLayout(deck_note_type_vlayout)
        top_hlayout.addWidget(self.note_info_groupbox)
        # ==================

        # instructions
        # ============
        instructions_label = aqt.qt.QLabel(gui_utils.process_label_text(constants.GUI_TEXT_MAPPING_RULES))
        instructions_label.setWordWrap(True)
        instructions_groubox = aqt.qt.QGroupBox('Need Help ?')
        instructions_layout = aqt.qt.QVBoxLayout()
        instructions_layout.addWidget(instructions_label)
        instructions_groubox.setLayout(instructions_layout)
        # self.vlayout.addWidget(instructions_label)
        top_hlayout.addWidget(instructions_groubox, 1)
        # ============

        self.vlayout.addLayout(top_hlayout)


        # display the mapping rules
        self.mapping_rules_gridlayout = aqt.qt.QGridLayout()
        vlayout = aqt.qt.QVBoxLayout()
        vlayout.addLayout(self.mapping_rules_gridlayout)


        hlayout = aqt.qt.QHBoxLayout()
        hlayout.addStretch()

        self.preview_all_button = aqt.qt.QPushButton('Preview All')
        self.preview_all_button.setToolTip('Preview all Presets (Hear all the audio)')
        hlayout.addWidget(self.preview_all_button)

        self.run_all_button = aqt.qt.QPushButton('Run All')
        self.run_all_button.setToolTip('Run all Presets (Add all audio to your note)')
        hlayout.addWidget(self.run_all_button)

        self.add_rule_button = aqt.qt.QPushButton('Add Rule')
        self.add_rule_button.setToolTip('Add a new rule which maps a preset to this deck and note type')
        hlayout.addWidget(self.add_rule_button)
        hlayout.addStretch()

        vlayout.addLayout(hlayout)

        self.mapping_rules_groupbox = aqt.qt.QGroupBox('Preset Rules')
        self.mapping_rules_groupbox.setLayout(vlayout)
        # self.vlayout.addLayout(self.mapping_rules_gridlayout)
        self.vlayout.addWidget(self.mapping_rules_groupbox, 1)

        
        # add buttons at the bottom
        hlayout = aqt.qt.QHBoxLayout()
        hlayout.addStretch()
        self.save_button = aqt.qt.QPushButton('Save and Close')
        self.cancel_button = aqt.qt.QPushButton('Cancel')
        self.cancel_button.setStyleSheet(self.hypertts.anki_utils.get_red_stylesheet())
        hlayout.addWidget(self.save_button)
        hlayout.addWidget(self.cancel_button)
        self.vlayout.addStretch()
        self.vlayout.addLayout(hlayout)
        self.update_button_states()

        # connect events
        self.add_rule_button.clicked.connect(self.add_rule_button_pressed)
        self.save_button.pressed.connect(self.save_button_pressed)
        self.cancel_button.pressed.connect(self.cancel_button_pressed)
        self.preview_all_button.pressed.connect(self.preview_all_button_pressed)
        self.run_all_button.pressed.connect(self.run_all_button_pressed)

        layout.addLayout(self.vlayout)

    def clear_mapping_rules_gridlayout(self):
        self.rules_components = []
        for i in reversed(range(self.mapping_rules_gridlayout.count())): 
            self.mapping_rules_gridlayout.itemAt(i).widget().setParent(None)

    def get_mapping_rule_updated_fn(self, absolute_index):
        def mapping_rule_updated_fn(model):
            self.mapping_rule_updated(absolute_index, model)
        return mapping_rule_updated_fn

    def get_mapping_rule_deleted_fn(self, absolute_index):
        def mapping_rule_delete_fn():
            self.mapping_rule_deleted(absolute_index)
        return mapping_rule_delete_fn

    def preview_started_fn(self):
        for rules_component in self.rules_components:
            rules_component.disable_preview_run()
        self.preview_all_button.setEnabled(False)
        self.run_all_button.setEnabled(False)

    def preview_finished_fn(self):
        for rules_component in self.rules_components:
            rules_component.enable_preview_run()
        self.preview_all_button.setEnabled(True)
        self.run_all_button.setEnabled(True)

    def mapping_rule_updated(self, absolute_index, model):
        self.model.rules[absolute_index] = model
        self.model_changed = True
        self.update_button_states() 

    def mapping_rule_deleted(self, absolute_index):
        del self.model.rules[absolute_index]
        self.refresh_mapping_rules_gridlayout()
        self.model_changed = True
        self.update_button_states() 

    def draw_mapping_rules(self):
        for absolute_index, subset_index, rule in self.get_model().iterate_related_rules(self.deck_note_type):
            self.rules_components.append(component_mappingrule.ComponentMappingRule(
                self.hypertts, 
                self.editor_context, 
                self.get_mapping_rule_updated_fn(absolute_index),
                self.get_mapping_rule_deleted_fn(absolute_index),
                self.preview_started_fn,
                self.preview_finished_fn))
            self.rules_components[subset_index].draw(self.mapping_rules_gridlayout, subset_index)
            self.rules_components[subset_index].load_model(rule)

    def refresh_mapping_rules_gridlayout(self):
        self.clear_mapping_rules_gridlayout()
        self.draw_mapping_rules()

    def choose_preset(self) -> str:
        """returns the preset id of the chosen preset, or None if user cancels"""
        return component_choosepreset.get_preset_id(self.hypertts, self.editor_context)

    def add_rule_button_pressed(self):
        with self.hypertts.error_manager.get_single_action_context('Adding Preset Rule'):
            preset_id = self.choose_preset()
            if preset_id != None:
                new_rule = config_models.MappingRule(preset_id=preset_id, 
                    rule_type=constants.MappingRuleType.DeckNoteType,
                    model_id=self.deck_note_type.model_id,
                    enabled=True,
                    automatic=True,
                    deck_id=self.deck_note_type.deck_id)
                self.model.rules.append(new_rule)
                self.refresh_mapping_rules_gridlayout()
                self.model_changed = True
                self.update_button_states()

    def save_button_pressed(self):
        self.save()
        self.dialog.close()

    def cancel_button_pressed(self):
        self.save_if_changed()
        self.dialog.close()

    def save(self):
        with self.hypertts.error_manager.get_single_action_context('Saving Rules'):
            logger.info('saving mapping rules')
            self.hypertts.save_mapping_rules(self.get_model())
            self.model_changed = False
            self.update_button_states()

    def save_if_changed(self):
        if self.model_changed:
            # does the user want to save the profile ?
            proceed = self.hypertts.anki_utils.ask_user('Save changes to mapping rules ?', self.dialog)
            if proceed:
                self.save()

    def update_button_states(self):
        if self.model_changed:
            self.enable_save_button()
        else:
            self.disable_save_button()
        
        # preview all / run all buttons

        at_least_one_rule = len(list(self.get_model().iterate_related_rules(self.deck_note_type))) > 0
        self.preview_all_button.setEnabled(at_least_one_rule)
        self.run_all_button.setEnabled(at_least_one_rule)

        # if there are no rules, set the green stylesheet on the add rule button
        if at_least_one_rule:
            self.add_rule_button.setStyleSheet(None)
        else:
            self.add_rule_button.setStyleSheet(self.hypertts.anki_utils.get_green_stylesheet())
        

    def enable_save_button(self):
        self.save_button.setEnabled(True)
        self.save_button.setStyleSheet(self.hypertts.anki_utils.get_green_stylesheet())

    def disable_save_button(self):
        self.save_button.setEnabled(False)
        self.save_button.setStyleSheet(None)

    def preview_all_button_pressed(self):
        logger.debug('preview_all_button_pressed')
        self.hypertts.preview_all_mapping_rules(self.editor_context, self.get_model())

    def run_all_button_pressed(self):
        logger.debug('run_all_button_pressed')
        self.hypertts.apply_all_mapping_rules(self.editor_context, self.get_model())

# factory and setup functions for ComponentPresetMappingRules
# ===========================================================

class PresetMappingRulesDialog(aqt.qt.QDialog):
    def __init__(self, hypertts, deck_note_type: config_models.DeckNoteType, editor_context: config_models.EditorContext):
        super(aqt.qt.QDialog, self).__init__()
        self.setupUi()
        self.mapping_rules = ComponentPresetMappingRules(hypertts, 
            self, deck_note_type, editor_context)
        self.mapping_rules.draw(self.main_layout)
        self.mapping_rules.load_model(hypertts.load_mapping_rules())        
    
    def setupUi(self):
        self.setWindowTitle(constants.GUI_PRESET_MAPPING_RULES_DIALOG_TITLE)
        self.main_layout = aqt.qt.QVBoxLayout(self)

    def verify_rules_saved(self):
        self.mapping_rules.save_if_changed()

    def closeEvent(self, evnt):
        self.verify_rules_saved()
        super(aqt.qt.QDialog, self).closeEvent(evnt)

    def close(self):
        self.verify_rules_saved()
        self.closed = True
        self.accept()

def create_dialog(hypertts, deck_note_type: config_models.DeckNoteType, editor_context: config_models.EditorContext) -> ComponentPresetMappingRules:
    dialog = PresetMappingRulesDialog(hypertts, deck_note_type, editor_context)
    hypertts.anki_utils.wait_for_dialog_input(dialog, constants.DIALOG_ID_PRESET_MAPPING_RULES) 