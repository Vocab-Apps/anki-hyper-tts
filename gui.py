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

from typing import List, Tuple

# addon imports
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_base)
config_models = __import__('config_models', globals(), locals(), [], sys._addon_import_level_base)
errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_base)
component_batch = __import__('component_batch', globals(), locals(), [], sys._addon_import_level_base)
component_realtime = __import__('component_realtime', globals(), locals(), [], sys._addon_import_level_base)
component_presetmappingrules = __import__('component_presetmappingrules', globals(), locals(), [], sys._addon_import_level_base)
component_configuration = __import__('component_configuration', globals(), locals(), [], sys._addon_import_level_base)
component_preferences = __import__('component_preferences', globals(), locals(), [], sys._addon_import_level_base)
text_utils = __import__('text_utils', globals(), locals(), [], sys._addon_import_level_base)
ttsplayer = __import__('ttsplayer', globals(), locals(), [], sys._addon_import_level_base)
logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_base)
gui_utils = __import__('gui_utils', globals(), locals(), [], sys._addon_import_level_base)
logger = logging_utils.get_child_logger(__name__)


class ConfigurationDialog(aqt.qt.QDialog):
    def __init__(self, hypertts):
        super(aqt.qt.QDialog, self).__init__()
        self.configuration = component_configuration.Configuration(hypertts, self)
        self.configuration.load_model(hypertts.get_configuration())

    def setupUi(self):
        self.setMinimumSize(500, 300)
        self.setWindowTitle(constants.GUI_CONFIGURATION_DIALOG_TITLE)
        self.main_layout = aqt.qt.QVBoxLayout(self)
        self.configuration.draw(self.main_layout)
        self.resize(500, 700)

    def close(self):
        self.accept()

class PreferencesDialog(aqt.qt.QDialog):
    def __init__(self, hypertts):
        super(aqt.qt.QDialog, self).__init__()
        self.preferences = component_preferences.ComponentPreferences(hypertts, self)
        self.preferences.load_model(hypertts.get_preferences())

    def setupUi(self):
        self.setWindowTitle(constants.GUI_PREFERENCES_DIALOG_TITLE)
        self.main_layout = aqt.qt.QVBoxLayout(self)
        self.preferences.draw(self.main_layout)
        self.resize(450, 500)

    def close(self):
        self.accept()

class DialogBase(aqt.qt.QDialog):
    def __init__(self):
        super(aqt.qt.QDialog, self).__init__()


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
        dialog.exec()

def launch_preferences_dialog(hypertts):
    with hypertts.error_manager.get_single_action_context('Launching Preferences Dialog'):
        logger.info('launch_preferences_dialog')
        dialog = PreferencesDialog(hypertts)
        dialog.setupUi()
        dialog.exec()        

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
        dialog.exec()

def remove_realtime_tts_tag(hypertts, browser, note_id_list):
    with hypertts.error_manager.get_single_action_context('Removing TTS Tag'):
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

        hypertts.remove_tts_tags(note, card_ord)
        hypertts.anki_utils.info_message(constants.GUI_TEXT_REALTIME_REMOVED_TAG, browser)


def init(hypertts):

    def browerMenusInit(browser: aqt.browser.Browser):
        
        def get_launch_dialog_browser_new_fn(hypertts, browser):
            def launch():
                with hypertts.error_manager.get_single_action_context('Opening HyperTTS Dialog from Browser'):
                    component_batch.create_component_batch_browser_new_preset(hypertts, browser.selectedNotes(), hypertts.get_next_preset_name())
                    # required to make sound tags appear
                    browser.model.reset()
            return launch

        def get_launch_dialog_browser_existing_fn(hypertts, browser, preset_id: str):
            def launch():
                with hypertts.error_manager.get_single_action_context('Opening HyperTTS Dialog from Browser'):
                    component_batch.create_component_batch_browser_existing_preset(hypertts, browser.selectedNotes(), preset_id)
                    # required to make sound tags appear
                    browser.model.reset()
            return launch            

        def get_launch_realtime_dialog_browser_fn(hypertts, browser):
            def launch():
                with hypertts.error_manager.get_single_action_context('Adding Realtime TTS'):
                    launch_realtime_dialog_browser(hypertts, browser.selectedNotes())
            return launch

        def get_remove_realtime_tts_tag_fn(hypertts, browser):
            def launch():
                with hypertts.error_manager.get_single_action_context('Removing Realtime TTS'):
                    remove_realtime_tts_tag(hypertts, browser, browser.selectedNotes())
            return launch

        menu = aqt.qt.QMenu(constants.ADDON_NAME, browser.form.menubar)
        browser.form.menubar.addMenu(menu)

        action = aqt.qt.QAction(f'Add Audio (Collection)...', browser)
        action.triggered.connect(get_launch_dialog_browser_new_fn(hypertts, browser))
        menu.addAction(action)

        # add a menu entry for each preset
        for preset_info in hypertts.get_preset_list():
            action = aqt.qt.QAction(f'Add Audio (Collection): {preset_info.name}...', browser)
            action.triggered.connect(get_launch_dialog_browser_existing_fn(hypertts, browser, preset_info.id))
            menu.addAction(action)

        menu.addSeparator()

        action = aqt.qt.QAction(f'Add Audio (Realtime)...', browser)
        action.triggered.connect(get_launch_realtime_dialog_browser_fn(hypertts, browser))
        menu.addAction(action)

        action = aqt.qt.QAction(f'Remove Audio (Realtime) / TTS Tag...', browser)
        action.triggered.connect(get_remove_realtime_tts_tag_fn(hypertts, browser))
        menu.addAction(action)

    def run_hypertts_settings(editor):
        with hypertts.error_manager.get_single_action_context('Opening Preset Mapping Rules'):
            logger.info(f'clicked hypertts settings, editor: {editor}')
            editor_context = hypertts.get_editor_context(editor)
            deck_note_type = hypertts.get_editor_deck_note_type(editor)
            component_presetmappingrules.create_dialog(hypertts, deck_note_type, editor_context)

    def run_hypertts_preview(editor):
        with hypertts.error_manager.get_single_action_context('Previewing Audio'):
            editor_context = hypertts.get_editor_context(editor)
            hypertts.preview_all_mapping_rules(editor_context)

    def run_hypertts_apply(editor):
        with hypertts.error_manager.get_single_action_context('Generating Audio'):
            editor_context = hypertts.get_editor_context(editor)
            hypertts.apply_all_mapping_rules(editor_context)

    def setup_editor_buttons(buttons, editor):
        preferences = hypertts.get_preferences()

        add_audio_shortcut = ''
        if preferences.keyboard_shortcuts.shortcut_editor_add_audio != None:
            add_audio_shortcut = str(preferences.keyboard_shortcuts.shortcut_editor_add_audio)
        preview_audio_shortcut = ''
        if preferences.keyboard_shortcuts.shortcut_editor_preview_audio != None:
            preview_audio_shortcut = str(preferences.keyboard_shortcuts.shortcut_editor_preview_audio)

        new_button = editor.addButton(gui_utils.get_graphics_path('icon_speaker.png'),
            'hypertts_add_audio',
            run_hypertts_apply,
            tip = f'HyperTTS: Add Audio to your note (based on your preset rules) {add_audio_shortcut}',
            keys = preferences.keyboard_shortcuts.shortcut_editor_add_audio,
            disables=False)
        buttons.append(new_button)

        new_button = editor.addButton(gui_utils.get_graphics_path('icon_play.png'),
            'hypertts_preview_audio',
            run_hypertts_preview,
            tip = f'HyperTTS: Preview Audio (Hear the audio before adding it) {preview_audio_shortcut}',
            keys = preferences.keyboard_shortcuts.shortcut_editor_preview_audio,
            disables=False)
        buttons.append(new_button)

        new_button = editor.addButton(gui_utils.get_graphics_path('icon_settings.png'),
            'hypertts_settings',
            run_hypertts_settings,
            tip = 'HyperTTS: Configure Preset Rules for this Note (do this before being able to add audio)',
            disables=False)
        buttons.append(new_button)        

        return buttons

    # anki tools menu
    action = aqt.qt.QAction(f'{constants.MENU_PREFIX} Services Configuration', aqt.mw)
    action.triggered.connect(lambda: launch_configuration_dialog(hypertts))
    aqt.mw.form.menuTools.addAction(action)    

    action = aqt.qt.QAction(f'{constants.MENU_PREFIX} Preferences', aqt.mw)
    action.triggered.connect(lambda: launch_preferences_dialog(hypertts))
    aqt.mw.form.menuTools.addAction(action)        

    # browser menus
    aqt.gui_hooks.browser_menus_did_init.append(browerMenusInit)

    # editor buttons
    aqt.gui_hooks.editor_did_init_buttons.append(setup_editor_buttons)

    # register TTS player
    aqt.sound.av_player.players.append(ttsplayer.AnkiHyperTTSPlayer(aqt.mw.taskman, hypertts))