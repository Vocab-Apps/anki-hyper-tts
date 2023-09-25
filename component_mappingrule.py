import sys
import aqt.qt

component_common = __import__('component_common', globals(), locals(), [], sys._addon_import_level_base)
config_models = __import__('config_models', globals(), locals(), [], sys._addon_import_level_base)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_base)
errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_base)
gui_utils = __import__('gui_utils', globals(), locals(), [], sys._addon_import_level_base)
logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_base)
logger = logging_utils.get_child_logger(__name__)


class ComponentMappingRule(component_common.ConfigComponentBase):

    def __init__(self, hypertts, dialog, deck_note_type: config_models.DeckNoteType, model: config_models.PresetMappingRule):
        self.hypertts = hypertts
        self.dialog = dialog
        self.rule_model = model
        self.deck_note_type = deck_note_type

    def load_model(self, model):
        logger.info('load_model')

    def get_model(self):
        return self.rule_model

    def draw(self, layout):
        self.vlayout = aqt.qt.QVBoxLayout()

        hlayout = aqt.qt.QHBoxLayout()

        self.rule_type_group = aqt.qt.QButtonGroup()
        self.rule_type_note_type = aqt.qt.QRadioButton('Note Type')
        self.rule_type_deck_note_type = aqt.qt.QRadioButton('Deck and Note Type')
        self.rule_type_group.addButton(self.rule_type_note_type)
        self.rule_type_group.addButton(self.rule_type_deck_note_type)
        hlayout.addWidget(self.rule_type_group)

        self.enabled_checkbox = aqt.qt.QCheckBox(f'Enabled')
        hlayout.addWidget(self.enabled_checkbox)

        self.vlayout.addLayout(hlayout)

