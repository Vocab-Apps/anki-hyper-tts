#python imports
import json
import typing
import urllib.parse
import logging
from typing import List, Dict

# anki imports
import aqt
import aqt.gui_hooks
import aqt.editor
import aqt.webview
import aqt.addcards
import anki.notes
import anki.models

# addon imports
# from .languagetools import LanguageTools, DeckNoteTypeField, build_deck_note_type, build_deck_note_type_from_note, build_deck_note_type_from_note_card, build_deck_note_type_from_addcard, LanguageToolsRequestError, AnkiNoteEditorError
from . import constants
from . import errors
from . import deck_utils
from .languagetools import LanguageTools
from . import editor_processing



def configure_editor_fields(editor: aqt.editor.Editor, field_options, live_updates, typing_delay):
    # logging.debug(f'configure_editor_fields, field_options: {field_options}')
    js_command = f"configure_languagetools_fields({json.dumps(field_options)})"
    # print(js_command)
    editor.web.eval(js_command)

    live_updates_str = str(live_updates).lower()
    js_command = f"setLanguageToolsEditorSettings({live_updates_str}, {typing_delay})"
    # print(js_command)
    editor.web.eval(js_command)    



def init(languagetools):
    aqt.mw.addonManager.setWebExports(__name__, r".*(css|js)")
    
    editor_manager = editor_processing.EditorManager(languagetools)

    def on_webview_will_set_content(web_content: aqt.webview.WebContent, context):
        if not isinstance(context, aqt.editor.Editor):
            return
        addon_package = aqt.mw.addonManager.addonFromModule(__name__)
        javascript_path = [
            f"/_addons/{addon_package}/languagetools.js",
            f"/_addons/{addon_package}/editor_javascript.js"
        ]
        css_path =  [
            f"/_addons/{addon_package}/languagetools.css",
            f"/_addons/{addon_package}/editor_style.css"
        ]
        web_content.js.extend(javascript_path)
        web_content.css.extend(css_path)


    def loadNote(editor: aqt.editor.Editor):
        note = editor.note
        deck_note_type = languagetools.deck_utils.build_deck_note_type_from_editor(editor)

        model = note.model()
        fields = model['flds']
        field_options = []
        for index, field in enumerate(fields):
            field_name = field['name']

            field_type ='regular'
            # is this field a sound field ?
            dntf = languagetools.deck_utils.build_dntf_from_dnt(deck_note_type, field_name)
            field_language = languagetools.get_language(dntf)
            if field_language != None:
                if languagetools.get_batch_translation_setting_field(dntf) != None:
                    # add translation settings
                    field_type = 'translation'
                elif field_language == constants.SpecialLanguage.sound.name:
                    # add_play_sound_collection(editor, index, field_name)
                    field_type = 'sound'
                elif field_language in languagetools.get_voice_selection_settings(): # is there a voice associated with this language ?
                    # add_tts_speak(editor, index, field_name)
                    field_type = 'language'
            field_options.append(field_type)
        live_updates = languagetools.get_apply_updates_automatically()
        typing_delay = languagetools.get_live_update_delay()
        configure_editor_fields(editor, field_options, live_updates, typing_delay)


    def onBridge(handled, str, editor):
        # logging.debug(f'bridge str: {str}')

        # return handled # don't do anything for now
        if not isinstance(editor, aqt.editor.Editor):
            return handled

        if str.startswith('playsoundcollection:'):
            logging.debug(f'playsoundcollection command: [{str}]')
            components = str.split(':')
            field_index_str = components[1]
            field_index = int(field_index_str)

            note = editor.note
            sound_tag = note.fields[field_index]
            logging.debug(f'sound tag: {sound_tag}')

            languagetools.anki_utils.play_anki_sound_tag(sound_tag)
            return handled

        if str.startswith('choosetranslation:'):
            editor_manager.process_choosetranslation(editor, str)
            return True, None

        if str.startswith('ttsspeak:'):
            logging.debug(f'ttsspeak command: [{str}]')
            components = str.split(':')
            field_index_str = components[1]
            field_index = int(field_index_str)

            note = editor.note
            source_text = note.fields[field_index]
            logging.debug(f'source_text: {source_text}')

            try:

                from_deck_note_type_field = languagetools.deck_utils.editor_get_dntf(editor, field_index)

                # do we have a voice set ?
                field_language = languagetools.get_language(from_deck_note_type_field)
                if field_language == None:
                    raise errors.AnkiNoteEditorError(f'No language set for field {from_deck_note_type_field}')
                voice_selection_settings = languagetools.get_voice_selection_settings()
                if field_language not in voice_selection_settings:
                    raise errors.AnkiNoteEditorError(f'No voice set for language {languagetools.get_language_name(field_language)}')
                voice = voice_selection_settings[field_language]

                def play_audio(languagetools, source_text, voice):
                    voice_key = voice['voice_key']
                    service = voice['service']
                    language_code = voice['language_code']

                    try:
                        filename = languagetools.get_tts_audio(source_text, service, language_code, voice_key, {})
                        if filename != None:
                            aqt.sound.av_player.play_file(filename)
                    except errors.LanguageToolsRequestError as err:
                        pass

                def play_audio_done(future_result):
                    pass

                aqt.mw.taskman.run_in_background(lambda: play_audio(languagetools, source_text, voice), lambda x: play_audio_done(x))

            except errors.AnkiNoteEditorError as e:
                # logging.error('Could not speak', exc_info=True)
                aqt.utils.showCritical(repr(e))

            return handled

        if str.startswith("languagetools:"):
            editor_manager.process_command(editor, str)
            return True, None

        if str.startswith("key:"):
            # user updated field, see if we need to do any transformations
            editor_manager.process_field_update(editor, str)


        return handled

        


    aqt.gui_hooks.webview_will_set_content.append(on_webview_will_set_content)
    aqt.gui_hooks.editor_did_load_note.append(loadNote)
    aqt.gui_hooks.webview_did_receive_js_message.append(onBridge)
