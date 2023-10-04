import sys
import aqt.qt

component_common = __import__('component_common', globals(), locals(), [], sys._addon_import_level_base)
component_mappingrule = __import__('component_mappingrule', globals(), locals(), [], sys._addon_import_level_base)
config_models = __import__('config_models', globals(), locals(), [], sys._addon_import_level_base)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_base)
errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_base)
gui_utils = __import__('gui_utils', globals(), locals(), [], sys._addon_import_level_base)
logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_base)
logger = logging_utils.get_child_logger(__name__)


class ComponentPresetMappingRules(component_common.ConfigComponentBase):

    def __init__(self, hypertts, dialog, deck_note_type: config_models.DeckNoteType, editor, note, add_mode):
        self.hypertts = hypertts
        self.dialog = dialog
        self.model = config_models.PresetMappingRules()
        self.deck_note_type = deck_note_type
        self.editor = editor
        self.note = note
        self.add_mode = add_mode
        self.rules_components = []

    def load_model(self, model):
        logger.info('load_model')
        self.model = model

    def get_model(self):
        return self.model

    def draw(self, layout):
        self.vlayout = aqt.qt.QVBoxLayout()

        hlayout = aqt.qt.QHBoxLayout()
        note_type_description_label = aqt.qt.QLabel('Note Type:')
        self.note_type_label = aqt.qt.QLabel(self.hypertts.anki_utils.get_note_type_name(self.deck_note_type.model_id))
        deck_description_label = aqt.qt.QLabel('Deck:')
        self.deck_name_label = aqt.qt.QLabel(self.hypertts.anki_utils.get_deck_name(self.deck_note_type.deck_id))
        hlayout.addWidget(note_type_description_label)
        hlayout.addWidget(self.note_type_label)
        hlayout.addWidget(deck_description_label)
        hlayout.addWidget(self.deck_name_label)

        self.vlayout.addLayout(hlayout) 

        # display the mapping rules
        self.mapping_rules_gridlayout = aqt.qt.QGridLayout()
        self.vlayout.addLayout(self.mapping_rules_gridlayout)

        self.add_rule_button = aqt.qt.QPushButton('Add Rule')
        self.add_rule_button.setToolTip('Add a new rule which maps a preset to this deck and note type')
        self.vlayout.addWidget(self.add_rule_button)

        # connect events
        self.add_rule_button.clicked.connect(self.add_rule_button_pressed)

        layout.addLayout(self.vlayout)

    def clear_mapping_rules_gridlayout(self):
        self.rules_components = []
        for i in reversed(range(self.mapping_rules_gridlayout.count())): 
            self.mapping_rules_gridlayout.itemAt(i).widget().setParent(None)

    def get_mapping_rule_updated_fn(self, index):
        def mapping_rule_updated_fn(model):
            self.mapping_rule_updated(index, model)
        return mapping_rule_updated_fn

    def mapping_rule_updated(self, index, model):
        self.model.rules[index] = model

    def draw_mapping_rules(self):
        for i, rule in enumerate(self.get_model().rules):
            self.rules_components.append(component_mappingrule.ComponentMappingRule(self.hypertts, 
                self.editor, self.note, self.add_mode, i, self.get_mapping_rule_updated_fn(i)))
            self.rules_components[i].draw(self.mapping_rules_gridlayout, i)
            self.rules_components[i].load_model(rule)

    def refresh_mapping_rules_gridlayout(self):
        self.clear_mapping_rules_gridlayout()
        self.draw_mapping_rules()

    def choose_preset(self) -> str:
        pass

    def add_rule_button_pressed(self):
        preset_id = self.choose_preset()
        new_rule = config_models.MappingRule(preset_id=preset_id, 
            rule_type=constants.MappingRuleType.DeckNoteType,
            model_id=self.deck_note_type.model_id,
            enabled=True,
            automatic=True,
            deck_id=self.deck_note_type.deck_id)
        self.model.rules.append(new_rule)
        self.refresh_mapping_rules_gridlayout()
