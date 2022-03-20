import sys
import json

# pyqt
import aqt.qt
import pprint

# anki imports
import aqt.qt
import aqt.editor
import aqt.gui_hooks
import aqt.sound
import aqt.utils
import anki.hooks

# addon imports
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_base)
errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_base)
component_batch = __import__('component_batch', globals(), locals(), [], sys._addon_import_level_base)
component_realtime = __import__('component_realtime', globals(), locals(), [], sys._addon_import_level_base)
component_configuration = __import__('component_configuration', globals(), locals(), [], sys._addon_import_level_base)
text_utils = __import__('text_utils', globals(), locals(), [], sys._addon_import_level_base)
ttsplayer = __import__('ttsplayer', globals(), locals(), [], sys._addon_import_level_base)
logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_base)
logger = logging_utils.get_child_logger(__name__)


class ConfigurationDialog(aqt.qt.QDialog):
    def __init__(self, hypertts):
        super(aqt.qt.QDialog, self).__init__()
        self.configuration = component_configuration.Configuration(hypertts, self)
        self.configuration.load_model(hypertts.get_configuration())

    def setupUi(self):
        self.setMinimumSize(500, 700)
        self.setWindowTitle(constants.GUI_CONFIGURATION_DIALOG_TITLE)
        self.main_layout = aqt.qt.QVBoxLayout(self)
        self.configuration.draw(self.main_layout)

    def close(self):
        self.accept()

class DialogBase(aqt.qt.QDialog):
    def __init__(self):
        super(aqt.qt.QDialog, self).__init__()

class BatchDialog(DialogBase):
    def __init__(self, hypertts):
        super(DialogBase, self).__init__()
        self.batch_component = component_batch.ComponentBatch(hypertts, self)

    def setupUi(self):
        self.setWindowTitle(constants.GUI_COLLECTION_DIALOG_TITLE)
        self.main_layout = aqt.qt.QVBoxLayout(self)
        self.batch_component.draw(self.main_layout)

    def configure_browser(self, note_id_list, batch_name=None):
        self.batch_component.configure_browser(note_id_list)
        self.setupUi()
        if batch_name != None:
            self.batch_component.load_batch(batch_name)
            # collapse splitter
            self.batch_component.collapse_settings()
        else:
            self.batch_component.display_settings()

    def configure_editor(self, note, editor, add_mode):
        self.batch_component.configure_editor(note, editor, add_mode)
        self.setupUi()
        self.batch_component.no_settings_editor()


    def close(self):
        self.accept()

class RealtimeDialog(DialogBase):
    def __init__(self, hypertts, card_ord):
        super(DialogBase, self).__init__()
        self.realtime_component = component_realtime.ComponentRealtime(hypertts, self, card_ord)

    def setupUi(self):
        self.setWindowTitle(constants.GUI_REALTIME_DIALOG_TITLE)
        self.main_layout = aqt.qt.QVBoxLayout(self)
        self.realtime_component.draw(self.main_layout)

    def configure_note(self, note):
        self.realtime_component.configure_note(note)
        self.setupUi()
        self.realtime_component.load_existing_preset()

    def close(self):
        self.accept()        

def launch_configuration_dialog(hypertts):
    with hypertts.error_manager.get_single_action_context('Launching Configuration Dialog'):
        logger.info('launch_configuration_dialog')
        dialog = ConfigurationDialog(hypertts)
        dialog.setupUi()
        dialog.exec_()

def launch_batch_dialog_browser(hypertts, browser, note_id_list, batch_name):
    with hypertts.error_manager.get_single_action_context('Launching HyperTTS Batch Dialog from Browser'):
        logger.info('launch_batch_dialog_browser')
        if len(note_id_list) == 0:
            raise errors.NoNotesSelected()
        dialog = BatchDialog(hypertts)
        dialog.configure_browser(note_id_list, batch_name=batch_name)
        dialog.exec_()
        browser.model.reset()

def launch_batch_dialog_editor(hypertts, note, editor, add_mode):
    with hypertts.error_manager.get_single_action_context('Launching HyperTTS Batch Dialog from Editor'):
        logger.info('launch_batch_dialog_editor')
        dialog = BatchDialog(hypertts)
        dialog.configure_editor(note, editor, add_mode)
        dialog.exec_()

def launch_realtime_dialog_browser(hypertts, note_id_list):
    with hypertts.error_manager.get_single_action_context('Launching HyperTTS Realtime Dialog from Browser'):
        if len(note_id_list) != 1:
            aqt.utils.showCritical(constants.GUI_TEXT_REALTIME_SINGLE_NOTE)
            return

        note = hypertts.anki_utils.get_note_by_id(note_id_list[0])
        note_model = note.note_type()
        templates = note_model['tmpls']
        card_ord = 0 # default
        if len(templates) > 1:
            # ask user to choose a template
            card_template_names = [x['name'] for x in templates]
            chosen_row = aqt.utils.chooseList(constants.TITLE_PREFIX + constants.GUI_TEXT_REALTIME_CHOOSE_TEMPLATE, card_template_names)
            logger.info(f'user chose row {chosen_row}')
            card_ord = chosen_row

        dialog = RealtimeDialog(hypertts, card_ord)
        dialog.configure_note(note)
        dialog.exec_()


def update_editor_batch_list(hypertts, editor: aqt.editor.Editor):
    batch_name_list = hypertts.get_batch_config_list_editor()
    configure_editor(editor, batch_name_list, hypertts.get_latest_saved_batch_name())

def configure_editor(editor: aqt.editor.Editor, batch_name_list, latest_saved_batch_name):
    default_batch_name = 'null'
    if latest_saved_batch_name != None:
        default_batch_name = f'"{latest_saved_batch_name}"'
    js_command = f"configureEditorHyperTTS({json.dumps(batch_name_list)}, {default_batch_name})"
    print(js_command)
    editor.web.eval(js_command)    

def init(hypertts):
    aqt.mw.addonManager.setWebExports(__name__, r".*(css|js)")

    def browerMenusInit(browser: aqt.browser.Browser):

        def get_launch_dialog_browser_fn(hypertts, browser, batch_name):
            def launch():
                launch_batch_dialog_browser(hypertts, browser, browser.selectedNotes(), batch_name)
            return launch

        def get_launch_realtime_dialog_browser_fn(hypertts, browser):
            def launch():
                launch_realtime_dialog_browser(hypertts, browser.selectedNotes())
            return launch



        menu = aqt.qt.QMenu(constants.ADDON_NAME, browser.form.menubar)
        browser.form.menubar.addMenu(menu)

        action = aqt.qt.QAction(f'Add Audio (Collection)...', browser)
        action.triggered.connect(get_launch_dialog_browser_fn(hypertts, browser, None))
        menu.addAction(action)

        # add a menu entry for each preset
        for batch_name in hypertts.get_batch_config_list():
            action = aqt.qt.QAction(f'Add Audio (Collection): {batch_name}...', browser)
            action.triggered.connect(get_launch_dialog_browser_fn(hypertts, browser, batch_name))
            menu.addAction(action)

        menu.addSeparator()

        action = aqt.qt.QAction(f'Add Audio (Realtime)...', browser)
        action.triggered.connect(get_launch_realtime_dialog_browser_fn(hypertts, browser))
        menu.addAction(action)            

    def on_webview_will_set_content(web_content: aqt.webview.WebContent, context):
        if not isinstance(context, aqt.editor.Editor):
            return
        addon_package = aqt.mw.addonManager.addonFromModule(__name__)
        javascript_path = [
            f"/_addons/{addon_package}/hypertts.js",
        ]
        css_path =  [
            f"/_addons/{addon_package}/hypertts.css",
        ]
        web_content.js.extend(javascript_path)
        web_content.css.extend(css_path)

    def loadNote(editor: aqt.editor.Editor):
        update_editor_batch_list(hypertts, editor)

    def onBridge(handled, str, editor):
        # logger.debug(f'bridge str: {str}')

        # return handled # don't do anything for now
        if not isinstance(editor, aqt.editor.Editor):
            return handled

        if str.startswith(constants.PYCMD_ADD_AUDIO_PREFIX):
            logger.info(f'{str}')
            if str == constants.PYCMD_ADD_AUDIO_PREFIX + constants.BATCH_CONFIG_NEW:
                hypertts.clear_latest_saved_batch_name()
                launch_batch_dialog_editor(hypertts, editor.note, editor, editor.addMode)
                update_editor_batch_list(hypertts, editor)
            else:
                with hypertts.error_manager.get_single_action_context('Adding Audio to Note'):
                    # logger.info(f'received message: {str}')
                    batch_name = str.replace(constants.PYCMD_ADD_AUDIO_PREFIX, '')
                    batch = hypertts.load_batch_config(batch_name)
                    hypertts.editor_note_add_audio(batch, editor, editor.note, editor.addMode)
            return True, None

        if str.startswith(constants.PYCMD_PREVIEW_AUDIO_PREFIX):
            with hypertts.error_manager.get_single_action_context('Previewing Audio'):
                # logger.info(f'received message: {str}')
                batch_name = str.replace(constants.PYCMD_PREVIEW_AUDIO_PREFIX, '')
                batch = hypertts.load_batch_config(batch_name)
                hypertts.preview_note_audio(batch, editor.note)
            return True, None            

        return handled

    # anki tools menu
    action = aqt.qt.QAction(f'{constants.MENU_PREFIX} Configuration', aqt.mw)
    action.triggered.connect(lambda: launch_configuration_dialog(hypertts))
    aqt.mw.form.menuTools.addAction(action)    

    # browser menus
    aqt.gui_hooks.browser_menus_did_init.append(browerMenusInit)

    # editor setup
    aqt.gui_hooks.editor_did_load_note.append(loadNote)
    aqt.gui_hooks.webview_will_set_content.append(on_webview_will_set_content)
    aqt.gui_hooks.webview_did_receive_js_message.append(onBridge)

    # register TTS player
    aqt.sound.av_player.players.append(ttsplayer.AnkiHyperTTSPlayer(aqt.mw.taskman, hypertts))