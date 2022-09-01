import sys
import aqt.qt


component_common = __import__('component_common', globals(), locals(), [], sys._addon_import_level_base)
component_realtime_side = __import__('component_realtime_side', globals(), locals(), [], sys._addon_import_level_base)
config_models = __import__('config_models', globals(), locals(), [], sys._addon_import_level_base)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_base)
errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_base)
gui_utils = __import__('gui_utils', globals(), locals(), [], sys._addon_import_level_base)
logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_base)
logger = logging_utils.get_child_logger(__name__)


class ComponentRealtime(component_common.ConfigComponentBase):
    MIN_WIDTH_COMPONENT = 600
    MIN_HEIGHT = 400

    def __init__(self, hypertts, dialog, card_ord):
        self.hypertts = hypertts
        self.dialog = dialog
        self.card_ord = card_ord
        self.model = config_models.RealtimeConfig()

        self.apply_button = aqt.qt.QPushButton('Apply To Note')
        self.cancel_button = aqt.qt.QPushButton('Cancel')

        self.existing_preset_name = None

        self.manage_apply_button = True

    def configure_note(self, note):
        self.manage_apply_button = False
        self.note = note
        self.front = component_realtime_side.ComponentRealtimeSide(self.hypertts, 
            self.dialog, constants.AnkiCardSide.Front, self.card_ord, self.front_model_updated, self.existing_preset_found)
        self.back = component_realtime_side.ComponentRealtimeSide(self.hypertts, 
            self.dialog, constants.AnkiCardSide.Back, self.card_ord, self.back_model_updated, self.existing_preset_found)
        self.front.configure_note(note)
        self.back.configure_note(note)
        self.manage_apply_button = True

    def load_existing_preset(self):
        self.manage_apply_button = False
        self.front.load_existing_preset()
        self.back.load_existing_preset()
        self.manage_apply_button = True

    def existing_preset_found(self, preset_name):
        self.existing_preset_name = preset_name

    def load_model(self, model):
        self.manage_apply_button = False
        self.model = model
        # disseminate to all components
        self.front.load_model(model.front)
        self.back.load_model(model.back)
        self.manage_apply_button = True

    def get_model(self):
        return self.model

    def front_model_updated(self, model):
        logger.info('front_model_updated')
        self.model.front = model
        if self.manage_apply_button:
            self.enable_apply_button()

    def back_model_updated(self, model):
        logger.info('back_model_update')
        self.model.back = model
        if self.manage_apply_button:
            self.enable_apply_button()

    def draw(self, layout):
        self.vlayout = aqt.qt.QVBoxLayout()

        # header
        # ======

        hlayout = aqt.qt.QHBoxLayout()

        # logo header
        hlayout.addLayout(gui_utils.get_hypertts_label_header(self.hypertts.hypertts_pro_enabled()))
        self.vlayout.addLayout(hlayout)

        # sides tabs
        # ==========

        self.tabs = aqt.qt.QTabWidget()
        self.tabs.setTabPosition(aqt.qt.QTabWidget.TabPosition.West)
        self.tab_front = aqt.qt.QWidget()
        self.tab_back = aqt.qt.QWidget()

        self.tab_front.setLayout(self.front.draw())
        self.tab_back.setLayout(self.back.draw())

        self.tabs.addTab(self.tab_front, 'Front Side')
        self.tabs.addTab(self.tab_back, 'Back Side')

        # self.tabs.setEnabled(False)

        self.vlayout.addWidget(self.tabs)

        # setup bottom buttons
        # ====================

        hlayout = aqt.qt.QHBoxLayout()
        hlayout.addStretch()

        # apply button
        hlayout.addWidget(self.apply_button)
        # cancel button
        self.cancel_button.setStyleSheet(self.hypertts.anki_utils.get_red_stylesheet())
        hlayout.addWidget(self.cancel_button)
        self.vlayout.addLayout(hlayout)

        # wire events
        self.apply_button.pressed.connect(self.apply_button_pressed)
        self.cancel_button.pressed.connect(self.cancel_button_pressed)

        # defaults
        self.cancel_button.setFocus()
        self.disable_apply_button()

        layout.addLayout(self.vlayout)

    def disable_apply_button(self):
        self.apply_button.setEnabled(False)
        self.apply_button.setStyleSheet(None)

    def enable_apply_button(self):
        logger.info('enable_apply_button')
        self.apply_button.setEnabled(True)
        self.apply_button.setStyleSheet(self.hypertts.anki_utils.get_green_stylesheet())

    def apply_button_pressed(self):
        with self.hypertts.error_manager.get_single_action_context('Applying Realtime Audio to Card'):
            self.get_model().validate()
            self.hypertts.persist_realtime_config_update_note_type(self.get_model(), 
                self.note, self.card_ord, self.existing_preset_name)
            self.dialog.close()

    def cancel_button_pressed(self):
        self.dialog.close()


        