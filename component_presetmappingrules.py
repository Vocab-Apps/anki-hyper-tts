import sys
import aqt.qt

component_common = __import__('component_common', globals(), locals(), [], sys._addon_import_level_base)
config_models = __import__('config_models', globals(), locals(), [], sys._addon_import_level_base)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_base)
errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_base)
gui_utils = __import__('gui_utils', globals(), locals(), [], sys._addon_import_level_base)
logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_base)
logger = logging_utils.get_child_logger(__name__)


class ComponentPresetMappingRules(component_common.ConfigComponentBase):

    def __init__(self, hypertts, dialog, deck_note_type: config_models.DeckNoteType):
        self.hypertts = hypertts
        self.dialog = dialog
        self.mapping_rules_model = config_models.PresetMappingRules()
        self.deck_note_type = deck_note_type

    def load_model(self, model):
        logger.info('load_model')

    def get_model(self):
        return self.mapping_rules_model

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

