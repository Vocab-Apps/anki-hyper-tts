import sys
import aqt.qt

component_common = __import__('component_common', globals(), locals(), [], sys._addon_import_level_base)
component_shortcuts = __import__('component_shortcuts', globals(), locals(), [], sys._addon_import_level_base)
component_errorhandling = __import__('component_errorhandling', globals(), locals(), [], sys._addon_import_level_base)
config_models = __import__('config_models', globals(), locals(), [], sys._addon_import_level_base)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_base)
errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_base)
gui_utils = __import__('gui_utils', globals(), locals(), [], sys._addon_import_level_base)
logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_base)
logger = logging_utils.get_child_logger(__name__)

class ComponentPreferences(component_common.ConfigComponentBase):
    def __init__(self, hypertts, dialog):
        self.hypertts = hypertts
        self.dialog = dialog
        self.model = config_models.Preferences()
        self.shortcuts = component_shortcuts.Shortcuts(self.hypertts, self.dialog, self.shortcuts_updated)
        self.error_handling = component_errorhandling.ErrorHandling(self.hypertts, self.dialog, self.error_handling_updated)

        self.save_button = aqt.qt.QPushButton('Apply')   
        self.cancel_button = aqt.qt.QPushButton('Cancel')        

    def load_model(self, model):
        logger.info('load_model')
        self.model = model
        self.shortcuts.load_model(self.model.keyboard_shortcuts)
        self.error_handling.load_model(self.model.error_handling)

    def get_model(self):
        return self.model

    def shortcuts_updated(self, model):
        self.model.keyboard_shortcuts = model
        self.model_part_updated_common()

    def error_handling_updated(self, model):
        self.model.error_handling = model
        self.model_part_updated_common()

    def model_part_updated_common(self):
        self.save_button.setEnabled(True)
        self.save_button.setStyleSheet(self.hypertts.anki_utils.get_green_stylesheet())        

    def draw(self, layout):
        vlayout = aqt.qt.QVBoxLayout()

        # dialog header 
        # =============

        hlayout = aqt.qt.QHBoxLayout()
        hlayout.addStretch()
        # logo header
        hlayout.addLayout(gui_utils.get_hypertts_label_header(self.hypertts.hypertts_pro_enabled()))
        vlayout.addLayout(hlayout)                

        layout.addLayout(vlayout)

        # preferences tabs
        # ====================

        self.tabs = aqt.qt.QTabWidget()
        self.tabs.addTab(self.shortcuts.draw(), 'Keyboard Shortcuts')
        self.tabs.addTab(self.error_handling.draw(), 'Error Handling')
        layout.addWidget(self.tabs)

        # setup bottom buttons
        # ====================

        hlayout = aqt.qt.QHBoxLayout()
        hlayout.addStretch()

        # apply button
        self.save_button.setEnabled(False)
        hlayout.addWidget(self.save_button)
        # cancel button
        self.cancel_button.setStyleSheet(self.hypertts.anki_utils.get_red_stylesheet())
        hlayout.addWidget(self.cancel_button)

        self.save_button.pressed.connect(self.save_button_pressed)
        self.cancel_button.pressed.connect(self.cancel_button_pressed)

        layout.addLayout(hlayout)        
    

    def save_button_pressed(self):
        with self.hypertts.error_manager.get_single_action_context('Saving Preferences'):
            self.hypertts.save_preferences(self.model)
            self.dialog.close()

    def cancel_button_pressed(self):
        self.dialog.close()    