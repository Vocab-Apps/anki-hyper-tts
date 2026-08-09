import aqt.qt

from typing import List

from . import component_common
from . import config_models
from . import constants
from . import constants_events
from .constants_events import Event, EventMode
from . import stats
from . import errors
from . import gui_utils
from . import logging_utils
logger = logging_utils.get_child_logger(__name__)

sc = stats.StatsContext(constants_events.EventContext.generate)


class RemoveAudioTableModel(aqt.qt.QAbstractTableModel):
    """shows the fields which will be modified, before and after"""

    COLUMN_HEADERS = ['Note Id', 'Field', 'Before', 'After']

    def __init__(self):
        aqt.qt.QAbstractTableModel.__init__(self, None)
        self.change_list: List[config_models.RemoveAudioFieldChange] = []

    def set_change_list(self, change_list):
        self.beginResetModel()
        self.change_list = change_list
        self.endResetModel()

    def flags(self, index):
        return aqt.qt.Qt.ItemFlag.ItemIsSelectable | aqt.qt.Qt.ItemFlag.ItemIsEnabled

    def rowCount(self, parent=None):
        return len(self.change_list)

    def columnCount(self, parent=None):
        return len(self.COLUMN_HEADERS)

    def data(self, index, role):
        # the before/after columns get elided, so also expose the full text as a tooltip
        if role not in (aqt.qt.Qt.ItemDataRole.DisplayRole, aqt.qt.Qt.ItemDataRole.ToolTipRole):
            return None
        if not index.isValid():
            return aqt.qt.QVariant()
        change = self.change_list[index.row()]
        data = [
            change.note_id,
            change.field_name,
            change.original_text,
            change.new_text,
        ][index.column()]
        return aqt.qt.QVariant(data)

    def headerData(self, col, orientation, role):
        if orientation == aqt.qt.Qt.Orientation.Horizontal and role == aqt.qt.Qt.ItemDataRole.DisplayRole:
            return aqt.qt.QVariant(self.COLUMN_HEADERS[col])
        return aqt.qt.QVariant()


class ComponentRemoveAudio(component_common.ComponentBase):
    """
    standalone dialog which removes sound tags from a collection of notes chosen
    in the browser. Every widget gets a stable objectName so that the GUI can be
    driven from tests and from scripts/gui_automation.
    """

    MIN_WIDTH = 900
    MIN_HEIGHT = 450

    def __init__(self, hypertts, dialog):
        self.hypertts = hypertts
        self.dialog = dialog
        self.note_id_list = []
        self.field_list = []
        self.change_list: List[config_models.RemoveAudioFieldChange] = []
        # snapshot of the options, taken on the main thread before background work
        self.remove_audio_config = config_models.RemoveAudioConfig()
        self.applied = False
        self.modified_note_count = 0
        self.removed_sound_tag_count = 0
        # callbacks fire while we populate the widgets, ignore them until drawn
        self.enable_change_callbacks = False

        self.field_combobox = aqt.qt.QComboBox()
        self.field_combobox.setObjectName('hypertts_remove_audio_field')
        self.hypertts_only_checkbox = aqt.qt.QCheckBox(constants.GUI_TEXT_REMOVE_AUDIO_HYPERTTS_ONLY)
        self.hypertts_only_checkbox.setObjectName('hypertts_remove_audio_hypertts_only')
        self.hypertts_only_checkbox.setToolTip(constants.GUI_TEXT_REMOVE_AUDIO_HYPERTTS_ONLY_TOOLTIP)
        self.hypertts_only_checkbox.setChecked(True)
        self.summary_label = aqt.qt.QLabel()
        self.summary_label.setObjectName('hypertts_remove_audio_summary_label')
        self.summary_label.setWordWrap(True)
        self.table_model = RemoveAudioTableModel()
        self.table_view = aqt.qt.QTableView()
        self.table_view.setObjectName('hypertts_remove_audio_preview_table')
        self.remove_button = aqt.qt.QPushButton('Remove Audio')
        self.remove_button.setObjectName('hypertts_remove_audio_remove_button')
        self.cancel_button = aqt.qt.QPushButton('Cancel')
        self.cancel_button.setObjectName('hypertts_remove_audio_cancel_button')

    def configure_browser(self, note_id_list):
        self.note_id_list = note_id_list
        self.field_list = self.hypertts.get_all_fields_from_notes(note_id_list)
        if len(self.field_list) == 0:
            raise Exception(f'could not find any fields in the selected {len(note_id_list)} notes')

    def get_model(self) -> config_models.RemoveAudioConfig:
        field_name = None
        if self.field_combobox.currentIndex() > 0:
            field_name = self.field_combobox.currentText()
        return config_models.RemoveAudioConfig(
            field_name=field_name,
            hypertts_only=self.hypertts_only_checkbox.isChecked())

    def draw(self, layout):
        self.vlayout = aqt.qt.QVBoxLayout()

        # header
        # ======
        hlayout = aqt.qt.QHBoxLayout()
        hlayout.addWidget(gui_utils.get_medium_label('Remove Audio'))
        hlayout.addStretch()
        hlayout.addLayout(gui_utils.get_hypertts_label_header(self.hypertts.hypertts_pro_enabled()))
        self.vlayout.addLayout(hlayout)

        description_label = aqt.qt.QLabel(constants.GUI_TEXT_REMOVE_AUDIO)
        description_label.setObjectName('hypertts_remove_audio_description_label')
        description_label.setWordWrap(True)
        # be explicit, qt's rich text auto-detection doesn't always pick up on the
        # markup when the text starts with plain words
        description_label.setTextFormat(aqt.qt.Qt.TextFormat.RichText)
        self.vlayout.addWidget(description_label)

        # options
        # =======
        options_group = aqt.qt.QGroupBox('Options')
        options_layout = aqt.qt.QVBoxLayout()

        field_layout = aqt.qt.QHBoxLayout()
        field_label = aqt.qt.QLabel('Remove audio from field:')
        field_label.setObjectName('hypertts_remove_audio_field_label')
        field_layout.addWidget(field_label)
        self.field_combobox.addItem(constants.REMOVE_AUDIO_ALL_FIELDS)
        self.field_combobox.addItems(self.field_list)
        field_layout.addWidget(self.field_combobox, 1)
        options_layout.addLayout(field_layout)

        options_layout.addWidget(self.hypertts_only_checkbox)
        options_group.setLayout(options_layout)
        self.vlayout.addWidget(options_group)

        # preview table
        # =============
        self.table_view.setModel(self.table_model)
        self.table_view.setSelectionMode(aqt.qt.QTableView.SelectionMode.SingleSelection)
        self.table_view.setSelectionBehavior(aqt.qt.QTableView.SelectionBehavior.SelectRows)
        # the note id / field name columns only need to fit their content, the
        # before / after columns hold field text and get all the remaining room
        header = self.table_view.horizontalHeader()
        header.setSectionResizeMode(0, aqt.qt.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, aqt.qt.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, aqt.qt.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, aqt.qt.QHeaderView.ResizeMode.Stretch)
        self.table_view.setTextElideMode(aqt.qt.Qt.TextElideMode.ElideMiddle)
        self.vlayout.addWidget(self.table_view, 1)

        self.vlayout.addWidget(self.summary_label)

        # bottom buttons
        # ==============
        hlayout = aqt.qt.QHBoxLayout()
        hlayout.addStretch()
        self.remove_button.setStyleSheet(self.hypertts.anki_utils.get_green_stylesheet())
        hlayout.addWidget(self.remove_button)
        self.cancel_button.setStyleSheet(self.hypertts.anki_utils.get_red_stylesheet())
        hlayout.addWidget(self.cancel_button)
        self.vlayout.addLayout(hlayout)

        # wire events
        # ===========
        self.field_combobox.currentIndexChanged.connect(self.options_changed)
        self.hypertts_only_checkbox.stateChanged.connect(self.options_changed)
        self.remove_button.pressed.connect(self.remove_button_pressed)
        self.cancel_button.pressed.connect(self.cancel_button_pressed)

        layout.addLayout(self.vlayout)

        self.enable_change_callbacks = True
        self.refresh_preview()

    # preview
    # =======

    def options_changed(self):
        if not self.enable_change_callbacks:
            return
        if self.applied:
            # audio was already removed, don't recompute on top of the summary
            return
        self.refresh_preview()

    def refresh_preview(self):
        # snapshot the widget state here, the background thread must not read widgets
        self.remove_audio_config = self.get_model()
        self.hypertts.anki_utils.run_in_background(self.refresh_preview_task,
            self.refresh_preview_task_done)

    def refresh_preview_task(self):
        return self.hypertts.get_remove_audio_changes(self.note_id_list,
            self.remove_audio_config)

    def refresh_preview_task_done(self, result):
        with self.hypertts.error_manager.get_single_action_context('Previewing Audio Removal'):
            self.change_list = result.result()
            self.hypertts.anki_utils.run_on_main(self.update_preview_table)

    def update_preview_table(self):
        self.table_model.set_change_list(self.change_list)
        note_count = len({change.note_id for change in self.change_list})
        sound_tag_count = sum(change.removed_count for change in self.change_list)
        if sound_tag_count == 0:
            self.summary_label.setText(constants.GUI_TEXT_REMOVE_AUDIO_NOTHING_TO_REMOVE)
            self.remove_button.setEnabled(False)
            self.remove_button.setStyleSheet(None)
        else:
            self.summary_label.setText(f'Will remove <b>{sound_tag_count}</b> sound tag(s) '
                f'from <b>{note_count}</b> note(s), out of {len(self.note_id_list)} selected.')
            self.remove_button.setEnabled(True)
            self.remove_button.setStyleSheet(self.hypertts.anki_utils.get_green_stylesheet())

    # applying
    # ========

    @sc.event(Event.click_remove_audio)
    def remove_button_pressed(self):
        with self.hypertts.error_manager.get_single_action_context('Removing Audio from Notes'):
            if len(self.change_list) == 0:
                raise errors.NoAudioToRemove()
            logger.info(f'removing audio from {len(self.note_id_list)} notes')
            # snapshot the widget state here, the collection op runs in the background
            self.remove_audio_config = self.get_model()
            self.disable_buttons()
            self.remove_button.setText('Removing...')
            self.hypertts.anki_utils.run_in_background_collection_op(
                self.dialog,
                self.remove_audio_task,
                self.remove_audio_task_done,
                undo_entry_name=constants.UNDO_ENTRY_REMOVE_AUDIO)

    def remove_audio_task(self, anki_collection):
        self.modified_note_count, self.removed_sound_tag_count = \
            self.hypertts.remove_audio_from_notes(self.note_id_list,
                self.remove_audio_config, anki_collection)

    def remove_audio_task_done(self, result):
        with self.hypertts.error_manager.get_single_action_context('Removing Audio from Notes'):
            self.hypertts.anki_utils.run_on_main(self.finish_remove_audio)

    def finish_remove_audio(self):
        self.applied = True
        self.table_model.set_change_list([])
        self.summary_label.setText(f'Removed <b>{self.removed_sound_tag_count}</b> sound tag(s) '
            f'from <b>{self.modified_note_count}</b> note(s). '
            f'Use <b>Edit / Undo</b> in the main Anki window to revert.')
        self.remove_button.setEnabled(False)
        self.remove_button.setStyleSheet(None)
        self.remove_button.setText('Done')
        self.field_combobox.setEnabled(False)
        self.hypertts_only_checkbox.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.cancel_button.setText('Close')
        self.cancel_button.setStyleSheet(self.hypertts.anki_utils.get_green_stylesheet())

    @sc.event(Event.click_cancel)
    def cancel_button_pressed(self):
        self.dialog.close()

    def disable_buttons(self):
        self.remove_button.setEnabled(False)
        self.cancel_button.setEnabled(False)


# factory and setup functions for ComponentRemoveAudio: only use those to create one
# ==================================================================================

class RemoveAudioDialog(aqt.qt.QDialog):
    def __init__(self, hypertts):
        super(aqt.qt.QDialog, self).__init__()
        self.hypertts = hypertts
        self.setObjectName('hypertts_remove_audio_dialog')
        self.setWindowTitle(constants.GUI_REMOVE_AUDIO_DIALOG_TITLE)
        self.main_layout = aqt.qt.QVBoxLayout(self)
        self.closed = None

    def configure_browser(self, note_id_list):
        self.remove_audio_component = ComponentRemoveAudio(self.hypertts, self)
        self.remove_audio_component.configure_browser(note_id_list)
        self.remove_audio_component.draw(self.main_layout)
        self.setMinimumSize(self.remove_audio_component.MIN_WIDTH,
            self.remove_audio_component.MIN_HEIGHT)

    @sc.event(Event.close)
    def close(self):
        self.closed = True
        self.accept()


@sc.event(Event.open, EventMode.remove_audio_browser)
def create_component_remove_audio_browser(hypertts, note_id_list):
    if len(note_id_list) == 0:
        raise errors.NoNotesSelected()
    dialog = RemoveAudioDialog(hypertts)
    dialog.configure_browser(note_id_list)
    hypertts.anki_utils.wait_for_dialog_input(dialog, constants.DIALOG_ID_REMOVE_AUDIO)
    return dialog.remove_audio_component
