import copy

import aqt.qt

from . import component_common
from . import config_models
from . import constants
from . import constants_events
from .constants_events import Event
from . import logging_utils
from . import stats

logger = logging_utils.get_child_logger(__name__)

sc = stats.StatsContext(constants_events.EventContext.services)

# columns of the services grid
COLUMN_ENABLED = 0
COLUMN_PRO = 1
COLUMN_NAME = 2
COLUMN_FEE = 3
COLUMN_TYPE = 4
COLUMN_ACTIONS = 5
COLUMN_COUNT = 6

PRO_CHECKMARK = '✓'


class ScrollAreaCustom(aqt.qt.QScrollArea):
    def __init__(self):
        aqt.qt.QScrollArea.__init__(self)

    def sizeHint(self):
        return aqt.qt.QSize(100, 100)


class ServiceRow():
    """widgets and transient state for a single service in the grid. the configuration panel sits
    on the grid row underneath the service row, and is hidden until the user opens it."""

    def __init__(self, service):
        self.service = service
        self.name = service.name
        self.config_options = service.configuration_options()
        self.has_config_options = len(self.config_options) > 0
        # widgets, populated by Services.draw_service_row
        self.enable_checkbox = None
        self.pro_label = None
        self.name_label = None
        self.fee_label = None
        self.type_label = None
        self.configure_button = None
        self.pro_badge_label = None
        self.panel = None
        self.config_widgets = {}
        # panel state
        self.config_snapshot = None
        self.opened_by_checkbox = False

    def panel_open(self):
        return self.panel != None and self.panel.isVisibleTo(self.panel.parentWidget())


class Services(component_common.ConfigComponentBase):
    """the Services tab of the services configuration screen. shows every service as a compact
    grid row, with the service's configuration options in a panel below the row."""

    def __init__(self, hypertts, dialog, model_change_callback):
        self.hypertts = hypertts
        self.dialog = dialog
        self.model = config_models.Configuration()
        self.model_change_callback = model_change_callback
        # set to False while widgets are being populated programmatically, so that the resulting
        # signals don't write back into the model or pop configuration panels open
        self.propagate_model_change = False
        # set to False during bulk enable/disable, so that we don't pop open a configuration panel
        # for every single service at once
        self.auto_open_panels = True
        self.pro_enabled = False
        self.drawn = False
        self.rows = {}

    def get_model(self):
        return self.model

    def load_model(self, model):
        self.model = model
        if self.drawn:
            self.refresh_all_rows()

    def notify_model_update(self):
        if self.propagate_model_change:
            self.model_change_callback()

    def set_pro_enabled(self, pro_enabled):
        """called by the parent component whenever the HyperTTS Pro API key changes"""
        logger.debug(f'set_pro_enabled: {pro_enabled}')
        self.pro_enabled = pro_enabled
        if self.drawn:
            self.refresh_all_rows()

    def get_service_list(self):
        def service_sort_key(service):
            return service.name
        service_list = self.hypertts.service_manager.get_all_services()
        service_list.sort(key=service_sort_key)
        return service_list

    def service_enabled_in_model(self, service_name):
        return self.model.get_service_enabled(service_name) == True

    def pro_managed(self, row):
        """true when HyperTTS Pro provides this service, in which case the user doesn't get to
        enable or configure it individually (servicemanager.configure enables it automatically)"""
        return self.pro_enabled and row.service.cloudlanguagetools_enabled()

    def any_service_enabled(self):
        # only services which still exist count. the enabled map can hold services which are long
        # gone (they're only pruned on save, by servicemanager.remove_non_existent_services), and
        # those don't give the user any audio
        return True in [self.service_enabled_in_model(service_name) for service_name in self.rows]

    # drawing
    # =======

    def draw(self):
        layout_widget = aqt.qt.QWidget()
        vlayout = aqt.qt.QVBoxLayout(layout_widget)

        description_label = aqt.qt.QLabel(constants.GUI_TEXT_SERVICES_GRID_HEADER)
        description_label.setObjectName('hypertts_services_description_label')
        description_label.setWordWrap(True)
        vlayout.addWidget(description_label)

        buttons_layout = aqt.qt.QHBoxLayout()
        self.enable_all_free_services_button = aqt.qt.QPushButton('Enable All Free Services')
        self.enable_all_free_services_button.setObjectName('hypertts_services_enable_all_free_button')
        self.disable_all_services_button = aqt.qt.QPushButton('Disable All Services')
        self.disable_all_services_button.setObjectName('hypertts_services_disable_all_button')
        buttons_layout.addWidget(self.enable_all_free_services_button)
        buttons_layout.addWidget(self.disable_all_services_button)
        vlayout.addLayout(buttons_layout)

        services_scroll_area = ScrollAreaCustom()
        services_scroll_area.setObjectName('hypertts_services_scroll_area')
        services_scroll_area.setWidgetResizable(True)
        services_scroll_area.setHorizontalScrollBarPolicy(aqt.qt.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        services_widget = aqt.qt.QWidget()
        self.services_gridlayout = aqt.qt.QGridLayout(services_widget)
        self.services_gridlayout.setObjectName('hypertts_services_gridlayout')

        self.draw_grid_header()
        # a QGridLayout can't have rows inserted after the fact, so every service gets two rows
        # reserved up front: the service row, and the (hidden) configuration panel below it
        grid_row = 1
        for service in self.get_service_list():
            row = ServiceRow(service)
            self.rows[service.name] = row
            self.draw_service_row(row, grid_row)
            grid_row += 2

        self.services_gridlayout.setColumnStretch(COLUMN_NAME, 1)
        self.services_gridlayout.setRowStretch(grid_row, 1)
        services_scroll_area.setWidget(services_widget)
        vlayout.addWidget(services_scroll_area, 1)

        self.enable_all_free_services_button.pressed.connect(self.enable_all_free_services)
        self.disable_all_services_button.pressed.connect(self.disable_all_services)

        self.drawn = True
        self.refresh_all_rows()
        self.propagate_model_change = True

        return layout_widget

    def draw_grid_header(self):
        header_labels = [
            (COLUMN_ENABLED, constants.GUI_TEXT_SERVICES_COLUMN_ENABLED),
            (COLUMN_PRO, constants.GUI_TEXT_SERVICES_COLUMN_PRO),
            (COLUMN_NAME, constants.GUI_TEXT_SERVICES_COLUMN_NAME),
            (COLUMN_FEE, constants.GUI_TEXT_SERVICES_COLUMN_FEE),
            (COLUMN_TYPE, constants.GUI_TEXT_SERVICES_COLUMN_TYPE),
        ]
        header_font = aqt.qt.QFont()
        header_font.setBold(True)
        for column, text in header_labels:
            label = aqt.qt.QLabel(text)
            label.setFont(header_font)
            self.services_gridlayout.addWidget(label, 0, column, 1, 1)

    def draw_service_row(self, row, grid_row):
        service = row.service

        row.enable_checkbox = aqt.qt.QCheckBox()
        row.enable_checkbox.setObjectName(self.get_service_enabled_widget_name(service))
        self.services_gridlayout.addWidget(row.enable_checkbox, grid_row, COLUMN_ENABLED, 1, 1)

        row.pro_label = aqt.qt.QLabel(PRO_CHECKMARK if service.cloudlanguagetools_enabled() else '')
        row.pro_label.setObjectName(f'hypertts_services_pro_{service.name}')
        self.services_gridlayout.addWidget(row.pro_label, grid_row, COLUMN_PRO, 1, 1)

        name_font = aqt.qt.QFont()
        name_font.setBold(True)
        row.name_label = aqt.qt.QLabel(service.name)
        row.name_label.setObjectName(f'hypertts_services_name_{service.name}')
        row.name_label.setFont(name_font)
        self.services_gridlayout.addWidget(row.name_label, grid_row, COLUMN_NAME, 1, 1)

        row.fee_label = aqt.qt.QLabel(service.service_fee.name)
        row.fee_label.setObjectName(f'hypertts_services_fee_{service.name}')
        self.services_gridlayout.addWidget(row.fee_label, grid_row, COLUMN_FEE, 1, 1)

        row.type_label = aqt.qt.QLabel(service.service_type.short_label)
        row.type_label.setObjectName(f'hypertts_services_type_{service.name}')
        self.services_gridlayout.addWidget(row.type_label, grid_row, COLUMN_TYPE, 1, 1)

        # actions cell: either the configure button, or a note that HyperTTS Pro takes care of it
        actions_widget = aqt.qt.QWidget()
        actions_layout = aqt.qt.QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        row.configure_button = aqt.qt.QPushButton('Configure')
        row.configure_button.setObjectName(f'hypertts_services_configure_{service.name}')
        row.pro_badge_label = aqt.qt.QLabel(constants.GUI_TEXT_SERVICES_ENABLED_BY_PRO)
        row.pro_badge_label.setObjectName(f'hypertts_services_pro_badge_{service.name}')
        actions_layout.addStretch()
        actions_layout.addWidget(row.pro_badge_label)
        actions_layout.addWidget(row.configure_button)
        self.services_gridlayout.addWidget(actions_widget, grid_row, COLUMN_ACTIONS, 1, 1)

        if row.has_config_options:
            row.panel = self.draw_service_config_panel(row)
            row.panel.setVisible(False)
            self.services_gridlayout.addWidget(row.panel, grid_row + 1, 0, 1, COLUMN_COUNT)

        row.enable_checkbox.stateChanged.connect(self.get_service_enable_change_fn(row))
        row.configure_button.pressed.connect(self.get_configure_button_pressed_fn(row))

    def draw_service_config_panel(self, row):
        service = row.service
        panel = aqt.qt.QGroupBox()
        panel.setObjectName(f'hypertts_services_panel_{service.name}')
        panel_vlayout = aqt.qt.QVBoxLayout(panel)

        options_gridlayout = aqt.qt.QGridLayout()
        options_row = 0
        for key, option_type in row.config_options.items():
            widget_name = self.get_service_config_widget_name(service, key)
            options_gridlayout.addWidget(aqt.qt.QLabel(key + ':'), options_row, 0, 1, 1)
            if option_type == str:
                widget = aqt.qt.QLineEdit()
                widget.textChanged.connect(self.get_service_config_str_change_fn(service, key))
            elif option_type == int:
                widget = aqt.qt.QSpinBox()
                widget.valueChanged.connect(self.get_service_config_int_change_fn(service, key))
            elif option_type == float:
                widget = aqt.qt.QDoubleSpinBox()
                widget.valueChanged.connect(self.get_service_config_float_change_fn(service, key))
            elif option_type == bool:
                widget = aqt.qt.QCheckBox()
                widget.stateChanged.connect(self.get_service_config_bool_change_fn(service, key))
            elif isinstance(option_type, list):
                widget = aqt.qt.QComboBox()
                widget.addItems(option_type)
                widget.currentTextChanged.connect(self.get_service_config_list_change_fn(service, key))
            else:
                logger.warning(f'{service.name}: unsupported configuration option type for {key}: {option_type}')
                continue
            widget.setObjectName(widget_name)
            row.config_widgets[key] = widget
            options_gridlayout.addWidget(widget, options_row, 1, 1, 1)
            options_row += 1
        options_gridlayout.setColumnStretch(1, 1)
        panel_vlayout.addLayout(options_gridlayout)

        buttons_layout = aqt.qt.QHBoxLayout()
        row.panel_ok_button = aqt.qt.QPushButton('OK')
        row.panel_ok_button.setObjectName(f'hypertts_services_panel_ok_{service.name}')
        row.panel_cancel_button = aqt.qt.QPushButton('Cancel')
        row.panel_cancel_button.setObjectName(f'hypertts_services_panel_cancel_{service.name}')
        buttons_layout.addStretch()
        buttons_layout.addWidget(row.panel_ok_button)
        buttons_layout.addWidget(row.panel_cancel_button)
        panel_vlayout.addLayout(buttons_layout)

        row.panel_ok_button.pressed.connect(self.get_panel_ok_fn(row))
        row.panel_cancel_button.pressed.connect(self.get_panel_cancel_fn(row))

        return panel

    # widget names
    # ============

    def get_service_enabled_widget_name(self, service):
        return f'hypertts_services_enable_{service.name}'

    def get_service_config_widget_name(self, service, key):
        return f'hypertts_services_config_{service.name}_{key}'

    # row state
    # =========

    def refresh_all_rows(self):
        for row in self.rows.values():
            self.refresh_row(row)

    def refresh_row(self, row):
        """brings a row's widgets in line with the model and the current HyperTTS Pro state.
        never writes to the model - signals are suppressed while widgets are updated."""
        pro_managed = self.pro_managed(row)
        model_enabled = self.service_enabled_in_model(row.name)
        # when HyperTTS Pro covers the service it is always enabled, whatever the model says
        display_enabled = True if pro_managed else model_enabled

        previous_propagate = self.propagate_model_change
        self.propagate_model_change = False
        row.enable_checkbox.setChecked(display_enabled)
        self.propagate_model_change = previous_propagate

        row.enable_checkbox.setEnabled(not pro_managed)
        for label in [row.pro_label, row.name_label, row.fee_label, row.type_label]:
            label.setEnabled(display_enabled)
        row.pro_badge_label.setVisible(pro_managed)
        # no point offering to open the configuration panel when it's already open
        row.configure_button.setVisible(
            not pro_managed and model_enabled and row.has_config_options and not row.panel_open())

        if pro_managed and row.panel_open():
            self.close_panel(row)

    def refresh_config_widgets(self, row):
        """populates the panel's widgets from the model"""
        previous_propagate = self.propagate_model_change
        self.propagate_model_change = False
        for key, widget in row.config_widgets.items():
            value = self.model.get_service_configuration_key(row.name, key)
            if isinstance(widget, aqt.qt.QLineEdit):
                widget.setText(value if value != None else '')
            elif isinstance(widget, aqt.qt.QCheckBox):
                widget.setChecked(value == True)
            elif isinstance(widget, aqt.qt.QComboBox):
                widget.setCurrentText(value if value != None else '')
            elif isinstance(widget, (aqt.qt.QSpinBox, aqt.qt.QDoubleSpinBox)):
                if value != None:
                    widget.setValue(value)
        self.propagate_model_change = previous_propagate

    # configuration panel
    # ===================

    def get_configure_button_pressed_fn(self, row):
        def configure_button_pressed():
            self.open_panel(row, opened_by_checkbox=False)
        return configure_button_pressed

    @sc.event(Event.open_service_config)
    def open_panel(self, row, opened_by_checkbox):
        logger.debug(f'opening configuration panel for {row.name}')
        if row.panel == None:
            return
        # snapshot the service's configuration so that Cancel can restore it
        row.config_snapshot = copy.deepcopy(self.model.get_service_config().get(row.name, {}))
        row.opened_by_checkbox = opened_by_checkbox
        self.refresh_config_widgets(row)
        row.panel.setVisible(True)
        self.refresh_row(row)

    def close_panel(self, row):
        row.config_snapshot = None
        row.opened_by_checkbox = False
        if row.panel != None:
            row.panel.setVisible(False)
            self.refresh_row(row)

    def get_panel_ok_fn(self, row):
        @sc.event(Event.click_service_config_ok)
        def panel_ok():
            logger.debug(f'keeping configuration for {row.name}')
            self.close_panel(row)
            self.notify_model_update()
        return panel_ok

    def get_panel_cancel_fn(self, row):
        @sc.event(Event.click_service_config_cancel)
        def panel_cancel():
            logger.debug(f'discarding configuration changes for {row.name}')
            # restore the configuration as it was when the panel was opened
            if row.config_snapshot != None:
                service_config = self.model.get_service_config()
                service_config[row.name] = row.config_snapshot
                self.model.set_service_config(service_config)
                self.refresh_config_widgets(row)
            opened_by_checkbox = row.opened_by_checkbox
            self.close_panel(row)
            if opened_by_checkbox:
                # the user enabled the service to configure it, undo that too
                row.enable_checkbox.setChecked(False)
        return panel_cancel

    # events
    # ======

    def get_service_enable_change_fn(self, row):
        def enable_change(value):
            if not self.propagate_model_change:
                return
            enabled = value == 2
            logger.info(f'{row.name} enabled: {enabled}')
            self.model.set_service_enabled(row.name, enabled)
            self.refresh_row(row)
            if enabled:
                if row.has_config_options and self.auto_open_panels:
                    self.open_panel(row, opened_by_checkbox=True)
            else:
                self.close_panel(row)
            self.notify_model_update()
        return enable_change

    def get_service_config_str_change_fn(self, service, key):
        def str_change(text):
            if not self.propagate_model_change:
                return
            logger.info(f'{service.name} {key}: {text}')
            self.model.set_service_configuration_key(service.name, key, text)
        return str_change

    def get_service_config_int_change_fn(self, service, key):
        def int_change(value):
            if not self.propagate_model_change:
                return
            logger.info(f'{service.name} {key}: {value}')
            self.model.set_service_configuration_key(service.name, key, value)
        return int_change

    def get_service_config_float_change_fn(self, service, key):
        def float_change(value):
            if not self.propagate_model_change:
                return
            logger.info(f'{service.name} {key}: {value}')
            self.model.set_service_configuration_key(service.name, key, value)
        return float_change

    def get_service_config_list_change_fn(self, service, key):
        def list_change(text):
            if not self.propagate_model_change:
                return
            logger.info(f'{service.name} {key}: {text}')
            self.model.set_service_configuration_key(service.name, key, text)
        return list_change

    def get_service_config_bool_change_fn(self, service, key):
        def bool_change(checkbox_value):
            if not self.propagate_model_change:
                return
            value = checkbox_value == 2
            logger.info(f'{service.name} {key}: {value}')
            self.model.set_service_configuration_key(service.name, key, value)
        return bool_change

    @sc.event(Event.click_disable_all_services)
    def disable_all_services(self):
        self.auto_open_panels = False
        try:
            for row in self.rows.values():
                if not self.pro_managed(row):
                    row.enable_checkbox.setChecked(False)
        finally:
            self.auto_open_panels = True

    @sc.event(Event.click_enable_free_services)
    def enable_all_free_services(self):
        self.auto_open_panels = False
        try:
            for row in self.rows.values():
                if row.service.service_fee == constants.ServiceFee.free and not self.pro_managed(row):
                    row.enable_checkbox.setChecked(True)
        finally:
            self.auto_open_panels = True
