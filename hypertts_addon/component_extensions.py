import os
import aqt.qt
import aqt.utils

from . import component_common
from . import config_models
from . import constants
from . import servicemanager
from . import logging_utils
logger = logging_utils.get_child_logger(__name__)


class Extensions(component_common.ConfigComponentBase):
    """preferences tab which lets the user point HyperTTS at a checkout of the
    anki-hyper-tts-extensions repository, so that third party services survive addon upgrades"""

    def __init__(self, hypertts, dialog, model_change_callback):
        self.hypertts = hypertts
        self.dialog = dialog
        self.model = config_models.Extensions()
        self.model_change_callback = model_change_callback
        self.propagate_model_change = True

        self.enable_extensions = aqt.qt.QCheckBox(constants.GUI_TEXT_EXTENSIONS_ENABLE)
        self.enable_extensions.setObjectName('hypertts_extensions_enable')

        self.extensions_directory = aqt.qt.QLineEdit()
        self.extensions_directory.setObjectName('hypertts_extensions_directory')

        self.browse_button = aqt.qt.QPushButton('Browse...')
        self.browse_button.setObjectName('hypertts_extensions_browse_button')

        self.status_label = aqt.qt.QLabel()
        self.status_label.setObjectName('hypertts_extensions_status_label')
        self.status_label.setWordWrap(True)

        self.tutorial_link = aqt.qt.QLabel(
            f'<a href="{constants.EXTENSIONS_TUTORIAL_URL}">{constants.GUI_TEXT_EXTENSIONS_TUTORIAL}</a>')
        self.tutorial_link.setObjectName('hypertts_extensions_tutorial_link')

    def get_model(self):
        return self.model

    def load_model(self, model):
        self.model = model
        self.propagate_model_change = False
        self.enable_extensions.setChecked(self.model.enabled)
        self.extensions_directory.setText(self.model.extensions_directory or '')
        self.propagate_model_change = True
        self.update_status()
        self.update_enabled_state()

    def notify_model_update(self):
        if self.propagate_model_change == True:
            self.model_change_callback(self.model)

    def draw(self):
        layout_widget = aqt.qt.QWidget()
        layout = aqt.qt.QVBoxLayout(layout_widget)

        description_label = aqt.qt.QLabel(constants.GUI_TEXT_EXTENSIONS)
        description_label.setObjectName('hypertts_extensions_description_label')
        description_label.setWordWrap(True)
        layout.addWidget(description_label)

        # third party services group
        # ==========================

        extensions_groupbox = aqt.qt.QGroupBox('Third Party Services')
        extensions_vlayout = aqt.qt.QVBoxLayout()

        extensions_vlayout.addWidget(self.enable_extensions)

        directory_label = aqt.qt.QLabel(constants.GUI_TEXT_EXTENSIONS_DIRECTORY)
        extensions_vlayout.addWidget(directory_label)

        directory_hlayout = aqt.qt.QHBoxLayout()
        directory_hlayout.addWidget(self.extensions_directory)
        directory_hlayout.addWidget(self.browse_button)
        extensions_vlayout.addLayout(directory_hlayout)

        extensions_vlayout.addWidget(self.status_label)

        extensions_groupbox.setLayout(extensions_vlayout)
        layout.addWidget(extensions_groupbox)

        # warning and restart notice
        # ==========================

        warning_label = aqt.qt.QLabel(constants.GUI_TEXT_EXTENSIONS_WARNING)
        warning_label.setObjectName('hypertts_extensions_warning_label')
        warning_label.setWordWrap(True)
        layout.addWidget(warning_label)

        restart_label = aqt.qt.QLabel(constants.GUI_TEXT_EXTENSIONS_ANKI_RESTART)
        restart_label.setObjectName('hypertts_extensions_restart_label')
        restart_label.setWordWrap(True)
        layout.addWidget(restart_label)

        layout.addWidget(self.tutorial_link)

        layout.addStretch()

        # wire events
        self.enable_extensions.stateChanged.connect(self.enable_extensions_changed)
        self.extensions_directory.textChanged.connect(self.extensions_directory_changed)
        self.browse_button.pressed.connect(self.browse_button_pressed)
        self.tutorial_link.linkActivated.connect(self.tutorial_link_clicked)

        self.update_status()
        self.update_enabled_state()

        return layout_widget

    # events
    # ======

    def enable_extensions_changed(self, state):
        logger.info(f'enable_extensions_changed {state}')
        self.model.enabled = bool(state)
        self.update_enabled_state()
        self.notify_model_update()

    def extensions_directory_changed(self, text):
        directory = text.strip()
        self.model.extensions_directory = directory if len(directory) > 0 else None
        self.update_status()
        self.notify_model_update()

    def browse_button_pressed(self):
        directory = aqt.qt.QFileDialog.getExistingDirectory(
            self.dialog, 'Select the anki-hyper-tts-extensions directory',
            self.model.extensions_directory or '')
        if directory:
            # triggers extensions_directory_changed, which updates the model
            self.extensions_directory.setText(directory)

    def tutorial_link_clicked(self, url):
        logger.info(f'tutorial_link_clicked {url}')
        aqt.utils.openLink(url)

    # status
    # ======

    def update_enabled_state(self):
        self.extensions_directory.setEnabled(self.model.enabled)
        self.browse_button.setEnabled(self.model.enabled)

    def get_status_message(self):
        """validate the configured directory here, in the dialog. this is the only opportunity to
        give the user useful feedback: at startup, a bad path just means no services show up."""
        directory = self.model.extensions_directory
        if directory == None:
            return constants.GUI_TEXT_EXTENSIONS_NOT_CONFIGURED
        if not os.path.isdir(os.path.expanduser(directory.strip())):
            return constants.GUI_TEXT_EXTENSIONS_DIRECTORY_NOT_FOUND
        services_directory = servicemanager.resolve_extensions_services_directory(directory)
        if services_directory == None:
            return constants.GUI_TEXT_EXTENSIONS_NO_SERVICES_FOUND
        service_count = len(servicemanager.find_service_files(services_directory))
        return f'Found {service_count} services in {services_directory}'

    def update_status(self):
        self.status_label.setText(self.get_status_message())
