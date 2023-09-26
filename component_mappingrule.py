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

    def __init__(self, hypertts, dialog, model_change_callback):
        self.hypertts = hypertts
        self.dialog = dialog
        self.model = None
        self.model_change_callback = model_change_callback

    def load_model(self, model):
        logger.info('load_model')
        self.model = model
        if self.model.rule_type == constants.MappingRuleType.NoteType:
            self.rule_type_note_type.setChecked(True)
        elif self.model.rule_type == constants.MappingRuleType.DeckNoteType:
            self.rule_type_deck_note_type.setChecked(True)

        self.enabled_checkbox.setChecked(self.model.enabled)

    def get_model(self):
        return self.model

    def draw(self, layout):
        self.vlayout = aqt.qt.QVBoxLayout()

        hlayout = aqt.qt.QHBoxLayout()

        self.rule_type_group = aqt.qt.QButtonGroup()
        self.rule_type_note_type = aqt.qt.QRadioButton('Note Type')
        self.rule_type_deck_note_type = aqt.qt.QRadioButton('Deck and Note Type')
        self.rule_type_group.addButton(self.rule_type_note_type)
        self.rule_type_group.addButton(self.rule_type_deck_note_type)

        hlayout.addWidget(self.rule_type_note_type)
        hlayout.addWidget(self.rule_type_deck_note_type)
        # hlayout.addWidget(self.rule_type_group)

        self.enabled_checkbox = aqt.qt.QCheckBox(f'Enabled')
        hlayout.addWidget(self.enabled_checkbox)

        self.vlayout.addLayout(hlayout)

        # wire events
        self.rule_type_note_type.toggled.connect(self.rule_type_toggled)
        self.enabled_checkbox.toggled.connect(self.enabled_toggled)

    def notify_model_update(self):
        self.model_change_callback(self.model)

    def rule_type_toggled(self, checked):
        logger.debug(f'rule_type_toggled: {checked}')
        if self.rule_type_note_type.isChecked():
            logger.debug(f'rule_type_note_type is checked')
            self.model.rule_type = constants.MappingRuleType.NoteType
        elif self.rule_type_deck_note_type.isChecked():
            logger.debug(f'rule_type_deck_note_type is checked')
            self.model.rule_type = constants.MappingRuleType.DeckNoteType
        else:
            raise RuntimeError(f'Unknown rule_type: {self.model.rule_type}')
        self.notify_model_update()

    def enabled_toggled(self, checked):
        logger.debug(f'enabled_toggled: {checked}')
        self.model.enabled = checked
        self.notify_model_update()
