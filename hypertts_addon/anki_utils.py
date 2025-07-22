import sys
import os
import datetime
import uuid
import aqt
import anki.template
import anki.sound
import anki.collection
import aqt.qt
from typing import List
from . import constants    
from . import constants_events
from . import errors
from . import stats

from . import logging_utils
logger = logging_utils.get_child_logger(__name__)

sc_error = stats.StatsContext(constants_events.EventContext.addon)

if hasattr(sys, '_sentry_crash_reporting'):
    import sentry_sdk

def ensure_anki_collection_open():
    if not aqt.mw.col:
        raise errors.CollectionNotOpen()

class TextInputTypingTimer():
    def __init__(self, text_input, text_input_changed_fn):
        self.enabled = True
        self.typing_timer = aqt.qt.QTimer()
        self.typing_timer.setSingleShot(True)
        # this is the external callback
        self.typing_timer.timeout.connect(text_input_changed_fn)
        # this is the internal callback which will start the timer
        text_input.textChanged.connect(self.text_input_changed)

    def text_input_changed(self):
        # start the timer if callbacks are enabled only
        if self.enabled:
            self.typing_timer.start(1000)

class AnkiUtils():
    def __init__(self):
        pass

    def get_config(self):
        return aqt.mw.addonManager.getConfig(constants.CONFIG_ADDON_NAME)

    def write_config(self, config):
        aqt.mw.addonManager.writeConfig(constants.CONFIG_ADDON_NAME, config)

    def night_mode_enabled(self):
        night_mode = aqt.theme.theme_manager.night_mode
        return night_mode

    def get_green_css_color(self):
        night_mode = self.night_mode_enabled()
        if night_mode:
            return constants.GREEN_COLOR_NIGHTMODE
        return constants.GREEN_COLOR_REGULAR

    def get_red_css_color(self):
        night_mode = self.night_mode_enabled()
        if night_mode:
            return constants.RED_COLOR_NIGHTMODE
        return constants.RED_COLOR_REGULAR

    def get_green_stylesheet(self):
        night_mode = self.night_mode_enabled()
        if night_mode:
            return constants.GREEN_STYLESHEET_NIGHTMODE
        return constants.GREEN_STYLESHEET

    def get_red_stylesheet(self):
        night_mode = self.night_mode_enabled()
        if night_mode:
            return constants.RED_STYLESHEET_NIGHTMODE
        return constants.RED_STYLESHEET

    def get_user_files_dir(self):
        addon_dir = os.path.dirname(os.path.realpath(__file__))
        user_files_dir = os.path.join(addon_dir, '..', 'user_files')
        return user_files_dir        

    def play_anki_sound_tag(self, text):
        ensure_anki_collection_open()
        out = aqt.mw.col.backend.extract_av_tags(text=text, question_side=True)
        file_list = [
            x.filename
            for x in anki.template.av_tags_to_native(out.av_tags)
            if isinstance(x, anki.sound.SoundOrVideoTag)
        ]   
        if len(file_list) >= 1:
            filename = file_list[0]
            aqt.sound.av_player.play_file(filename)

    def get_note_by_id(self, note_id):
        ensure_anki_collection_open()
        note = aqt.mw.col.get_note(note_id)
        return note

    def get_model(self, model_id):
        ensure_anki_collection_open()
        return aqt.mw.col.models.get(model_id)

    def get_note_type_name(self, model_id: int) -> str:
        return self.get_model(model_id)['name']

    def get_deck(self, deck_id):
        ensure_anki_collection_open()
        return aqt.mw.col.decks.get(deck_id)

    def get_deck_name(self, deck_id: int) -> str:
        return self.get_deck(deck_id)['name']

    def get_model_id(self, model_name):
        ensure_anki_collection_open()
        return aqt.mw.col.models.id_for_name(model_name)

    def get_deck_id(self, deck_name):
        ensure_anki_collection_open()
        return aqt.mw.col.decks.id_for_name(deck_name)

    def media_add_file(self, filename):
        ensure_anki_collection_open()
        full_filename = aqt.mw.col.media.add_file(filename)
        return full_filename

    def undo_start(self):
        ensure_anki_collection_open()
        undo_id = aqt.mw.col.add_custom_undo_entry(constants.UNDO_ENTRY_NAME)
        logger.debug(f'undo_start, undo_id: {undo_id}')
        return undo_id

    def undo_tts_tag_start(self):
        ensure_anki_collection_open()
        undo_id = aqt.mw.col.add_custom_undo_entry(constants.UNDO_ENTRY_ADD_TTS_TAG)
        logger.debug(f'undo_tts_tag_start, undo_id: {undo_id}')
        return undo_id

    def undo_end(self, undo_id):
        def undo_end_fn():
            logger.debug(f'unfo_end_fn, undo_id: {undo_id}')
            try:
                ensure_anki_collection_open()
                aqt.mw.col.merge_undo_entries(undo_id)
                aqt.mw.update_undo_actions()
                aqt.mw.autosave()
            except Exception as e:
                logger.warning(f'exception in undo_end_fn: {str(e)}, undo_id: {undo_id}')
        self.run_on_main(undo_end_fn)

    def update_note(self, note):
        ensure_anki_collection_open()
        aqt.mw.col.update_note(note)

    def create_card_from_note(self, note, card_ord, model, template):
        return note.ephemeral_card(
            card_ord,
            custom_note_type=model,
            custom_template=template
        )

    def extract_tts_tags(self, av_tags):
        tts_tags = [x for x in av_tags if isinstance(x, anki.sound.TTSTag)]
        return tts_tags

    def save_note_type_update(self, note_model):
        ensure_anki_collection_open()
        logger.info(f"""updating note type: {note_model['name']}""")
        aqt.mw.col.models.update_dict(note_model)

    def run_in_background_collection_op(self, parent_widget, update_fn, success_fn):
        # update fn takes collection as a parameter
        def update_fn_with_undo(col):
            # start new undo entry
            undo_id = aqt.mw.col.add_custom_undo_entry(constants.UNDO_ENTRY_NAME)
            # run actual operation
            update_fn(col)
            # merge undo entries
            try:
                return aqt.mw.col.merge_undo_entries(undo_id)
            except Exception as e:
                # this tends to happen after a large number of updates, and when the collection has been accessed in the middle
                # to avoid this , I need to rework how updates are batched together. most likely we need to do one single
                # collection update at the end of all operations
                logger.warning(f'exception in undo_end_fn: {str(e)}, undo_id: {undo_id}')
                return False

        collection_op = aqt.operations.QueryOp(parent=parent_widget, op=update_fn_with_undo, success=success_fn)
        collection_op.run_in_background()

    def get_anki_collection(self):
        ensure_anki_collection_open()
        return aqt.mw.col

    def run_in_background(self, task_fn, task_done_fn):
        aqt.mw.taskman.run_in_background(task_fn, task_done_fn)

    def run_on_main(self, task_fn):
        aqt.mw.taskman.run_on_main(task_fn)

    def wire_typing_timer(self, text_input, text_input_changed):
        typing_timer = TextInputTypingTimer(text_input, text_input_changed)
        return typing_timer

    def call_on_timer_expire(self, timer, task):
        if timer.timer_obj != None:
            # stop it first
            timer.timer_obj.stop()
        timer.timer_obj = aqt.qt.QTimer()
        timer.timer_obj.setSingleShot(True)
        timer.timer_obj.timeout.connect(task)
        timer.timer_obj.start(timer.delay_ms)

    def restrict_message_length(self, message):
        if len(message) > constants.MESSAGE_TEXT_MAX_LENGTH:
            message = message[0:constants.MESSAGE_TEXT_MAX_LENGTH] + '...'
        return message

    def info_message(self, message, parent):
        message = self.restrict_message_length(message)
        aqt.utils.showInfo(message, title=constants.ADDON_NAME, textFormat='rich', parent=parent)

    def critical_message(self, message, parent):
        message = self.restrict_message_length(message)
        aqt.utils.showCritical(message, title=constants.ADDON_NAME, parent=parent)

    def tooltip_message(self, message):
        message = self.restrict_message_length(message)
        aqt.utils.tooltip(message)

    def display_preset_rules_status(self, status):
        message = str(status)
        self.run_on_main(lambda: aqt.utils.closeTooltip())
        self.run_on_main(lambda: aqt.utils.tooltip(message, period=5000))

    def ask_user(self, message, parent):
        result = aqt.utils.askUser(message, parent=parent, title=constants.ADDON_NAME)
        return result

    def ask_user_get_text(self, message, parent, default, title):
        return aqt.utils.getText(message, parent, default=default, title=f'{constants.TITLE_PREFIX}{title}')

    def ask_user_choose_from_list(self, parent, prompt: str, choices: List[str], startrow: int = 0) -> int:
        d = aqt.qt.QDialog(parent)
        d.setWindowModality(aqt.qt.Qt.WindowModality.WindowModal)
        l = aqt.qt.QVBoxLayout()
        d.setLayout(l)
        t = aqt.qt.QLabel(prompt)
        l.addWidget(t)
        c = aqt.qt.QListWidget()
        c.addItems(choices)
        c.setCurrentRow(startrow)
        l.addWidget(c)
        bb = aqt.qt.QDialogButtonBox(aqt.qt.QDialogButtonBox.StandardButton.Ok|aqt.qt.QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(d.accept)
        bb.rejected.connect(d.reject)
        l.addWidget(bb)
        retvalue = d.exec() # 1 for OK, 0 for canceled
        current_row = c.currentRow()
        logger.debug(f'returning current row: {current_row}, retvalue: {retvalue}')
        return current_row, retvalue

    def get_clipboard_content(self):
        # return self.clipboard_content
        return aqt.qt.QApplication.clipboard().text()

    def clear_clipboard_contents(self):
        aqt.qt.QApplication.clipboard().clear()

    def play_sound(self, filename):
        # play files one after another
        # Ensure sound playback happens on the main thread
        # note: running on background thread seems to have been the cause of these issues:
        # https://github.com/Vocab-Apps/anki-hyper-tts/issues/278
        self.run_on_main(lambda: aqt.sound.av_player.insert_file(filename))

    def show_progress_bar(self, message):
        aqt.mw.progress.start(immediate=True, label=f'{constants.MENU_PREFIX} {message}')

    def stop_progress_bar(self):
        aqt.mw.progress.finish()

    def get_current_time(self):
        return datetime.datetime.now()

    def editor_set_field_value(self, editor, field_index, text):
        if field_index >= len(editor.note.fields):
            raise Exception(f'there are {len(editor.note.fields)} fields in this note, field index {field_index} not found')
        # set the field value on the note
        editor.note.fields[field_index] = text
        # update the webview
        js_command = f"""set_field_value({field_index}, "{text}")"""
        editor.web.eval(js_command)

    def show_loading_indicator(self, editor: aqt.editor.Editor, field_index):
        js_command = f"show_loading_indicator({field_index})"
        if editor != None and editor.web != None:
            editor.web.eval(js_command)

    def hide_loading_indicator(self, editor: aqt.editor.Editor, field_index, original_field_value):
        js_command = f"""hide_loading_indicator({field_index}, "{original_field_value}")"""
        if editor != None and editor.web != None:
            editor.web.eval(js_command)

    def broadcast_audio_added(self):
        # when audio has been added, we need to update the deck browser webview
        logger.debug('broadcast_audio_added')
        self.send_deck_browser_webview_command("window.hyperTTSWelcome.closeWelcomeMessage();")

    def broadcast_services_configured(self):
        # when services have been configured, we need to update the deck browser webview
        logger.debug('broadcast_services_configured')
        self.send_deck_browser_webview_command("window.hyperTTSWelcome.hideConfigureServicesShowAddAudio();")

    def send_deck_browser_webview_command(self, command):
        if aqt.mw.deckBrowser and aqt.mw.deckBrowser.web:
            logger.debug(f'sending command to deck browser webview: {command}')
            aqt.mw.deckBrowser.web.eval(command)

    def display_dialog(self, dialog):
        return dialog.exec()

    def report_error_event(self, error_message):
        sc_error.send_event(constants_events.Event.error, 
                            event_mode = None,
                            properties = {
                                'error_message': error_message
                            })

    def report_known_exception_interactive_dialog(self, exception, action):
        error_message = f'Encountered an error while {action}: {str(exception)}'
        self.critical_message(error_message, None)
        self.report_error_event(error_message)

    def report_known_exception_interactive_tooltip(self, exception, action):
        error_message = f'Encountered an error while {action}: {str(exception)}'
        self.tooltip_message(error_message)
        self.report_error_event(error_message)

    def report_unknown_exception_interactive(self, exception, action):
        error_message = f'Encountered an unknown error while {action}: {str(exception)}'
        if hasattr(sys, '_sentry_crash_reporting'):
            sentry_sdk.capture_exception(exception)
        else:
            logger.critical(exception, exc_info=True)
        self.critical_message(error_message, None)
        self.report_error_event(error_message)

    def report_unknown_exception_background(self, exception):
        if hasattr(sys, '_sentry_crash_reporting'):
            sentry_sdk.capture_exception(exception)
        else:
            logger.critical(exception, exc_info=True)

    def get_uuid(self):
        return str(uuid.uuid4())

    def wait_for_dialog_input(self, dialog, dialog_id):
        logger.info(f'waiting for dialog input: {dialog_id}')
        dialog.exec()