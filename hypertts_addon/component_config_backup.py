import aqt.qt

from typing import List, Optional

from . import component_common
from . import config_backup
from . import constants

from . import logging_utils
logger = logging_utils.get_child_logger(__name__)

COLUMN_HEADERS = ['Saved', 'Status', 'Presets', 'Preset Rules', 'Services', 'API Key', 'Size']
COLUMN_INDEX_SAVED = 0
COLUMN_INDEX_STATUS = 1
COLUMN_INDEX_PRESETS = 2
COLUMN_INDEX_RULES = 3
COLUMN_INDEX_SERVICES = 4
COLUMN_INDEX_API_KEY = 5
COLUMN_INDEX_SIZE = 6


def format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f'{size_bytes} B'
    return f'{size_bytes / 1024:.1f} KB'


class ConfigBackup(component_common.ComponentBase):
    """the Configuration Backups tab of the preferences screen. lists the configuration backups
    HyperTTS keeps in user_files/config_backup and allows restoring one of them (github issue
    #360)"""

    def __init__(self, hypertts, dialog):
        self.hypertts = hypertts
        self.dialog = dialog
        self.backup_manager = hypertts.config_backup_manager
        self.backup_list: List[config_backup.ConfigBackupInfo] = []

        self.description_label = aqt.qt.QLabel(constants.GUI_TEXT_CONFIG_BACKUP)
        self.description_label.setObjectName('hypertts_config_backup_description_label')
        self.description_label.setWordWrap(True)

        self.current_config_label = aqt.qt.QLabel()
        self.current_config_label.setObjectName('hypertts_config_backup_current_config_label')
        self.current_config_label.setWordWrap(True)

        self.backup_directory_label = aqt.qt.QLabel()
        self.backup_directory_label.setObjectName('hypertts_config_backup_directory_label')
        self.backup_directory_label.setWordWrap(True)
        self.backup_directory_label.setTextInteractionFlags(
            aqt.qt.Qt.TextInteractionFlag.TextSelectableByMouse)

        self.table = aqt.qt.QTableWidget()
        self.table.setObjectName('hypertts_config_backup_table')
        self.table.setColumnCount(len(COLUMN_HEADERS))
        self.table.setHorizontalHeaderLabels(COLUMN_HEADERS)
        self.table.setEditTriggers(aqt.qt.QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(aqt.qt.QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(aqt.qt.QTableWidget.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        # the status column takes up the remaining width, it's the one which can contain a long
        # message when a backup file is damaged
        self.table.horizontalHeader().setSectionResizeMode(COLUMN_INDEX_STATUS,
            aqt.qt.QHeaderView.ResizeMode.Stretch)

        self.restore_button = aqt.qt.QPushButton('Restore Selected Backup')
        self.restore_button.setObjectName('hypertts_config_backup_restore_button')
        self.restore_button.setEnabled(False)

        self.refresh_button = aqt.qt.QPushButton('Refresh')
        self.refresh_button.setObjectName('hypertts_config_backup_refresh_button')

    def draw(self):
        layout_widget = aqt.qt.QWidget()
        layout_widget.setObjectName('hypertts_config_backup_tab')
        layout = aqt.qt.QVBoxLayout(layout_widget)

        layout.addWidget(self.description_label)
        layout.addWidget(self.current_config_label)
        layout.addWidget(self.table)

        hlayout = aqt.qt.QHBoxLayout()
        hlayout.addWidget(self.refresh_button)
        hlayout.addStretch()
        hlayout.addWidget(self.restore_button)
        layout.addLayout(hlayout)

        layout.addWidget(self.backup_directory_label)

        self.refresh_button.pressed.connect(self.refresh)
        self.restore_button.pressed.connect(self.restore_button_pressed)
        self.table.itemSelectionChanged.connect(self.selection_changed)

        self.refresh()

        return layout_widget

    # displaying backups
    # ==================

    def refresh(self):
        with self.hypertts.error_manager.get_single_action_context('Listing Configuration Backups'):
            self.backup_list = self.backup_manager.list_backups()
            logger.info(f'found {len(self.backup_list)} configuration backups')
            self.backup_directory_label.setText(
                f'Backup directory: {self.backup_manager.get_backup_dir()}')
            self.current_config_label.setText(self.get_current_config_description())
            self.populate_table()
            self.selection_changed()

    def get_current_config_description(self) -> str:
        stats = config_backup.analyze_config(self.hypertts.config)
        if stats.looks_empty():
            color = self.hypertts.anki_utils.get_red_text_color()
            return (f'<b>Current configuration:</b> <span style="color: {color};"><b>empty</b></span> '
                f'({stats.describe()})')
        return f'<b>Current configuration:</b> {stats.describe()}'

    def populate_table(self):
        self.table.clearContents()
        self.table.setRowCount(len(self.backup_list))
        for row, backup_info in enumerate(self.backup_list):
            stats = backup_info.stats
            self.set_table_item(row, COLUMN_INDEX_SAVED, backup_info.timestamp_str())
            self.set_table_item(row, COLUMN_INDEX_STATUS, backup_info.status_str(),
                valid=backup_info.looks_valid())
            self.set_table_item(row, COLUMN_INDEX_PRESETS,
                str(stats.preset_count) if stats != None else '')
            self.set_table_item(row, COLUMN_INDEX_RULES,
                str(stats.mapping_rule_count) if stats != None else '')
            self.set_table_item(row, COLUMN_INDEX_SERVICES,
                str(stats.service_config_count) if stats != None else '')
            self.set_table_item(row, COLUMN_INDEX_API_KEY,
                ('yes' if stats.pro_api_key_set else 'no') if stats != None else '')
            self.set_table_item(row, COLUMN_INDEX_SIZE, format_size(backup_info.size_bytes))
        self.table.resizeColumnsToContents()

    def set_table_item(self, row: int, column: int, text: str, valid: bool = True):
        item = aqt.qt.QTableWidgetItem(text)
        if not valid:
            item.setForeground(aqt.qt.QColor(self.hypertts.anki_utils.get_red_text_color()))
        self.table.setItem(row, column, item)

    # restoring
    # =========

    def selection_changed(self):
        backup_info = self.get_selected_backup()
        self.restore_button.setEnabled(backup_info != None and backup_info.looks_valid())

    def get_selected_backup(self) -> Optional[config_backup.ConfigBackupInfo]:
        selected_row = self.table.currentRow()
        if selected_row < 0 or selected_row >= len(self.backup_list):
            return None
        if len(self.table.selectedItems()) == 0:
            return None
        return self.backup_list[selected_row]

    def restore_button_pressed(self):
        backup_info = self.get_selected_backup()
        if backup_info == None:
            return
        stats = backup_info.stats
        confirmation_message = (f'Restore the HyperTTS configuration saved on '
            f'{backup_info.timestamp_str()} ({stats.describe()})?<br/><br/>'
            f'{constants.GUI_TEXT_CONFIG_BACKUP_RESTORE_WARNING}')
        if not self.hypertts.anki_utils.ask_user(confirmation_message, self.dialog):
            logger.info('user cancelled configuration restore')
            return
        with self.hypertts.error_manager.get_single_action_context('Restoring Configuration Backup'):
            self.hypertts.restore_config_backup(backup_info.filename)
            self.hypertts.anki_utils.info_message(constants.GUI_TEXT_CONFIG_BACKUP_RESTART,
                self.dialog)
            self.refresh()
