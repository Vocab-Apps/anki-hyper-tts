import aqt.qt

from . import component_common
from . import component_extensions
from . import component_hyperttspro
from . import component_services
from . import config_models
from . import constants
from . import constants_events
from .constants_events import Event
from . import gui_utils
from . import logging_utils
from . import stats

logger = logging_utils.get_child_logger(__name__)

sc = stats.StatsContext(constants_events.EventContext.services)

class Configuration(component_common.ConfigComponentBase):
    """the services configuration screen. three tabs (HyperTTS Pro, Services, Extensions) which all
    edit a single config_models.Configuration model, saved in one go by the Save button."""

    STACK_LEVEL_LITE = 0
    STACK_LEVEL_PRO = 1

    TAB_INDEX_HYPERTTS_PRO = 0
    TAB_INDEX_SERVICES = 1
    TAB_INDEX_EXTENSIONS = 2

    TAB_EVENTS = {
        TAB_INDEX_HYPERTTS_PRO: Event.click_tab_hypertts_pro,
        TAB_INDEX_SERVICES: Event.click_tab_services,
        TAB_INDEX_EXTENSIONS: Event.click_tab_extensions,
    }

    @sc.event(Event.open)
    def __init__(self, hypertts, dialog):
        self.hypertts = hypertts
        self.dialog = dialog
        self.enable_model_change = False
        self.api_key_valid = False

        self.hyperttspro = component_hyperttspro.HyperTTSPro(self.hypertts, self.hyperttspro_account_config_change)
        self.services = component_services.Services(self.hypertts, self.dialog, self.services_updated)
        self.extensions = component_extensions.Extensions(self.hypertts, self.dialog, self.extensions_updated)

        # created here rather than in draw() so that callbacks fired while the tabs are being drawn
        # always have something to update
        self.alert_label = aqt.qt.QLabel(constants.GUI_TEXT_NO_SERVICES_CONFIGURED)
        self.alert_label.setObjectName('hypertts_configuration_alert')
        self.alert_label.setWordWrap(True)
        self.alert_label.setStyleSheet('border: 1px solid palette(mid); border-radius: 4px; padding: 6px;')

        self.save_button = aqt.qt.QPushButton('Save')
        self.save_button.setObjectName('hypertts_configuration_save_button')
        self.cancel_button = aqt.qt.QPushButton('Cancel')
        self.cancel_button.setObjectName('hypertts_configuration_cancel_button')

        # the sub-components edit parts of this same model, so they all have to be handed the very
        # same instance, including the empty one we start with
        self.load_model(config_models.Configuration())

    def get_model(self):
        return self.model

    def load_model(self, model):
        self.model = model
        self.hyperttspro.load_model(self.model.get_hypertts_pro_config())
        self.services.load_model(self.model)
        self.extensions.load_model(self.model.extensions)
        self.update_alert()

    # model changes
    # =============

    def hyperttspro_account_config_change(self, account_config: config_models.HyperTTSProAccountConfig):
        self.api_key_valid = account_config.api_key_valid
        is_change = self.model.get_hypertts_pro_api_key() != account_config.api_key
        self.model.update_hypertts_pro_config(account_config)
        self.set_cloud_language_tools_enabled()
        if is_change:
            self.model_change()

    def services_updated(self):
        self.update_alert()
        self.model_change()

    def extensions_updated(self, model):
        self.model.extensions = model
        self.model_change()

    def model_change(self):
        if self.enable_model_change:
            self.save_button.setEnabled(True)
            self.save_button.setStyleSheet(self.hypertts.anki_utils.get_green_stylesheet())

    # hypertts pro state
    # ==================

    def cloud_language_tools_enabled(self):
        return self.api_key_valid

    def set_cloud_language_tools_enabled(self):
        if self.cloud_language_tools_enabled():
            self.header_logo_stack_widget.setCurrentIndex(self.STACK_LEVEL_PRO)
        else:
            self.header_logo_stack_widget.setCurrentIndex(self.STACK_LEVEL_LITE)
        # services covered by HyperTTS Pro don't need to be enabled or configured individually
        self.services.set_pro_enabled(self.cloud_language_tools_enabled())
        self.update_alert()

    # bottom alert
    # ============

    def no_services_configured(self):
        """the user can either use HyperTTS Pro, or enable individual services. if they've done
        neither, HyperTTS can't generate any audio at all."""
        if self.model.hypertts_pro_api_key_set():
            return False
        return not self.services.any_service_enabled()

    def update_alert(self):
        self.alert_label.setVisible(self.no_services_configured())

    # drawing
    # =======

    def draw(self, layout):
        self.global_vlayout = aqt.qt.QVBoxLayout()

        # logo header
        # ===========
        lite_stack = aqt.qt.QWidget()
        pro_stack = aqt.qt.QWidget()

        lite_stack.setLayout(gui_utils.get_hypertts_label_header(False))
        pro_stack.setLayout(gui_utils.get_hypertts_label_header(True))

        self.header_logo_stack_widget = aqt.qt.QStackedWidget()
        self.header_logo_stack_widget.addWidget(lite_stack)
        self.header_logo_stack_widget.addWidget(pro_stack)

        self.header_logo_stack_widget.setCurrentIndex(self.STACK_LEVEL_LITE) # lite
        self.global_vlayout.addWidget(self.header_logo_stack_widget)

        # tabs
        # ====

        self.tabs = aqt.qt.QTabWidget()
        self.tabs.setObjectName('hypertts_configuration_tabs')
        # the services tab is drawn first, so that it's ready for the callbacks which the hypertts
        # pro tab fires while verifying a saved API key
        services_widget = self.services.draw()
        hyperttspro_widget = self.hyperttspro.draw_widget()
        extensions_widget = self.extensions.draw()
        self.tabs.addTab(hyperttspro_widget, 'HyperTTS Pro')
        self.tabs.addTab(services_widget, 'Services')
        self.tabs.addTab(extensions_widget, 'Extensions')
        self.global_vlayout.addWidget(self.tabs, 1)

        # alert, outside of the tabs
        # ==========================

        self.global_vlayout.addWidget(self.alert_label)

        # bottom buttons
        # ==============

        buttons_layout = aqt.qt.QHBoxLayout()
        self.save_button.setEnabled(False)
        self.cancel_button.setStyleSheet(self.hypertts.anki_utils.get_red_stylesheet())
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.save_button)
        buttons_layout.addWidget(self.cancel_button)
        self.global_vlayout.addLayout(buttons_layout)

        # wire events
        # ===========

        self.tabs.currentChanged.connect(self.tab_changed)
        self.save_button.pressed.connect(self.save_button_pressed)
        self.cancel_button.pressed.connect(self.cancel_button_pressed)

        self.update_alert()
        self.enable_model_change = True

        layout.addLayout(self.global_vlayout)

    # events
    # ======

    def tab_changed(self, index):
        event = self.TAB_EVENTS.get(index, None)
        if event != None:
            sc.send_event(event)

    @sc.event(Event.click_save)
    def save_button_pressed(self):
        with self.hypertts.error_manager.get_single_action_context('Saving Service Configuration'):
            self.hypertts.save_configuration(self.model)
            self.hypertts.reconfigure_service_manager()
            self.dialog.close()

    @sc.event(Event.click_cancel)
    def cancel_button_pressed(self):
        self.dialog.close()
