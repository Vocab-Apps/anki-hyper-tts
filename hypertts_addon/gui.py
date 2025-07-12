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
from . import constants
from . import constants_events
from . import stats
from . import config_models
from . import errors
from . import component_batch
from . import component_realtime
from . import component_presetmappingrules
from . import component_configuration
from . import component_preferences
from . import component_easy
from . import component_choose_easy_advanced
from . import component_services_configuration
from . import component_trialsignup
from . import text_utils
from . import ttsplayer
from . import logging_utils
from . import gui_utils
from . import stats
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

def launch_trial_signup_dialog(hypertts):
    # this dialog asks the user to sign up for a trial
    with hypertts.error_manager.get_single_action_context('Launching Trial Signup Dialog'):
        logger.info('launch_trial_signup_dialog')
        component_trialsignup.show_trial_signup_dialog(hypertts)

def launch_services_configuration(hypertts):
    # this dialog asks the user to choose between trial and manual configuration
    with hypertts.error_manager.get_single_action_context('Launching Services Configuration Dialog'):
        logger.info('launch_services_configuration')
        result: config_models.ServicesConfigurationMode = component_services_configuration.show_services_configuration_dialog(hypertts)
        if result == config_models.ServicesConfigurationMode.TRIAL:
            launch_trial_signup_dialog(hypertts)
        elif result == config_models.ServicesConfigurationMode.MANUAL_CONFIGURATION:
            launch_configuration_dialog(hypertts)

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
            if component_choose_easy_advanced.ensure_easy_advanced_choice_made(hypertts):
                editor_context = hypertts.get_editor_context(editor)
                if hypertts.load_mapping_rules().use_easy_mode:
                    logger.debug('use easy mode')
                    deck_note_type: config_models.DeckNoteType = hypertts.get_editor_deck_note_type(editor)
                    component_easy.create_dialog_editor(hypertts, deck_note_type, editor_context)
                else:
                    hypertts.preview_all_mapping_rules(editor_context)

    def run_hypertts_apply(editor):
        with hypertts.error_manager.get_single_action_context('Generating Audio'):
            if component_choose_easy_advanced.ensure_easy_advanced_choice_made(hypertts):
                editor_context = hypertts.get_editor_context(editor)
                if hypertts.load_mapping_rules().use_easy_mode:
                    logger.debug('use easy mode')
                    deck_note_type: config_models.DeckNoteType = hypertts.get_editor_deck_note_type(editor)
                    component_easy.create_dialog_editor(hypertts, deck_note_type, editor_context)
                else:
                    hypertts.apply_all_mapping_rules(editor_context)

    def setup_editor_buttons(buttons, editor):
        with hypertts.error_manager.get_single_action_context('Setting up HyperTTS editor buttons'):
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

    # 


    def should_show_welcome_message(hypertts):
        configuration = hypertts.get_configuration()
        if configuration.display_introduction_message:
            if configuration.trial_registration_step in [config_models.TrialRegistrationStep.new_install, config_models.TrialRegistrationStep.pending_add_audio]:
                return True
        return False

    def on_deck_browser_will_render_content(deck_browser, content):
        # initialize stats
        if hasattr(sys, '_hypertts_stats_global'):
            # load required data
            sys._hypertts_stats_global.init_load()

        if should_show_welcome_message(hypertts):
            configuration = hypertts.get_configuration()
            trial_step = configuration.trial_registration_step
            
            # Check if night mode is enabled
            night_mode = hypertts.anki_utils.night_mode_enabled()
            
            # Set colors based on night mode
            bg_color = "#2f2f31" if night_mode else "white"
            border_color = "#555555" if night_mode else "#cccccc"
            text_color = "#ffffff" if night_mode else "#000000"
            
            # Determine which buttons to show based on trial registration step
            show_configure_services = trial_step == config_models.TrialRegistrationStep.new_install
            show_add_audio = trial_step == config_models.TrialRegistrationStep.pending_add_audio
            
            # Set initial visibility styles
            configure_services_style = "" if show_configure_services else "display: none;"
            add_audio_style = "" if show_add_audio else "display: none;"
            
            # Generate button content - only non-large variant
            configure_services_content = f"""
                <p id="hypertts-important-text"><b class="important-gradient-text">Important</b>: you have to configure services before adding audio.</p>
                <button class="hypertts-welcome-button">
                    <div><b style="font-size: 1.2em;">Configure Services</b></div>
                    <div style="font-size: 0.8em;">Click here before adding audio</div>
                </button>
            """
            add_audio_content = f"""
                <p>It looks like you haven't added audio yet.</p>
                <button class="hypertts-welcome-button">
                    <div><b style="font-size: 1.2em;">Adding Audio</b></div>
                    <div style="font-size: 0.8em;">Click to learn how to add audio</div>
                </button>
            """
            
            welcome_html = f"""
            <div id="hypertts-welcome-message" style="margin: 1em 2em; padding: 1em; background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 15px; color: {text_color};">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h3 style="margin: 0; text-align: center; flex-grow: 1;">HyperTTS - Add Audio to your Flashcards</h3>
                    <button id="hypertts-welcome-close" style="background: none; border: none; cursor: pointer; font-size: 1.2em; color: {text_color};">× Close</button>
                </div>
                <div style="text-align: center; margin-top: 10px;">
                    <div id="hypertts-configure-services" style="{configure_services_style}">
                        {configure_services_content}
                    </div>
                    <div id="hypertts-how-to-add-audio" style="{add_audio_style}">
                        {add_audio_content}
                    </div>
                </div>
            </div>
            """
            
            
            welcome_html += f"""
            <style>
                .hypertts-welcome-button {{
                    cursor: pointer;
                }}
                
                #hypertts-configure-services button,
                #hypertts-how-to-add-audio button {{
                    background: linear-gradient(to bottom, {constants.COLOR_GRADIENT_PURPLE_START}, {constants.COLOR_GRADIENT_PURPLE_END});
                    border: none;
                    border-radius: 12px;
                    color: white;
                    padding: 10px 20px;
                    font-weight: bold;
                }}
                
                #hypertts-configure-services button:hover,
                #hypertts-how-to-add-audio button:hover {{
                    background: linear-gradient(to bottom, {constants.COLOR_GRADIENT_PURPLE_HOVER_START}, {constants.COLOR_GRADIENT_PURPLE_HOVER_END});
                }}
                
                #hypertts-configure-services button:active,
                #hypertts-how-to-add-audio button:active {{
                    background: linear-gradient(to bottom, {constants.COLOR_GRADIENT_PURPLE_PRESSED_START}, {constants.COLOR_GRADIENT_PURPLE_PRESSED_END});
                }}
                
                .gradient-text {{
                    background: linear-gradient(to right, #6975dd, #7355b0);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                }}
                
                .important-gradient-text {{
                    background: linear-gradient(to right, #ff748d, #ff7daf);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                }}
            </style>
            <script>
                (function() {{
                    function hideConfigureServicesShowAddAudio() {{
                        document.getElementById('hypertts-configure-services').style.display = 'none';
                        var importantText = document.getElementById('hypertts-important-text');
                        if (importantText) {{
                            importantText.style.display = 'none';
                        }}
                        document.getElementById('hypertts-how-to-add-audio').style.display = '';
                    }}
                    
                    function closeWelcomeMessage() {{
                        document.getElementById('hypertts-welcome-message').style.display = 'none';
                        pycmd('hypertts:welcome_closed');
                    }}
                    
                    document.getElementById('hypertts-welcome-close').addEventListener('click', function() {{
                        closeWelcomeMessage();
                    }});
                    
                    var configureServicesDiv = document.getElementById('hypertts-configure-services');
                    if (configureServicesDiv) {{
                        configureServicesDiv.addEventListener('click', function() {{
                            pycmd('hypertts:configure_services');
                        }});
                    }}
                    
                    var addAudioDiv = document.getElementById('hypertts-how-to-add-audio');
                    if (addAudioDiv) {{
                        addAudioDiv.addEventListener('click', function() {{
                            pycmd('hypertts:how_to_add_audio');
                        }});
                    }}
                    
                    // Make functions available globally if needed
                    window.hyperTTSWelcome = {{
                        hideConfigureServicesShowAddAudio: hideConfigureServicesShowAddAudio,
                        closeWelcomeMessage: closeWelcomeMessage
                    }};
                }})();
            </script>
            """
            content.stats += welcome_html
            logger.debug('deck browser will render content, added welcome message')
    
    aqt.gui_hooks.deck_browser_will_render_content.append(on_deck_browser_will_render_content)
    
    def on_bridge_cmd(handled, cmd, context):
        if cmd.startswith('hypertts:welcome_closed'):
            configuration = hypertts.get_configuration()
            configuration.display_introduction_message = False
            hypertts.save_configuration(configuration)
            return (True, None)
        elif cmd.startswith('hypertts:configure_services'):
            stats.event_global(constants_events.Event.click_welcome_configure_services)
            launch_services_configuration(hypertts)
            return (True, None)
        elif cmd.startswith('hypertts:how_to_add_audio'):
            stats.event_global(constants_events.Event.click_welcome_add_audio)
            configuration = hypertts.get_configuration()
            user_uuid = configuration.user_uuid
            help_url = gui_utils.get_vocab_ai_url('tips/hypertts-adding-audio', 'deckbrowser_welcome', user_uuid)
            aqt.utils.openLink(help_url)
            logger.info(f'opening url: {help_url}')
            return (True, None)
        return handled
    
    aqt.gui_hooks.webview_did_receive_js_message.append(on_bridge_cmd)
    
