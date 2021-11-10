
# pyqt
import PyQt5

# anki imports
import aqt.qt
import aqt.editor
import aqt.gui_hooks
import aqt.sound
import anki.sound
import anki.hooks

# addon imports
from . import constants
from . import editor
from . import dialogs
from . import deck_utils
from . import dialog_voiceselection
from . import dialog_textprocessing


def init(languagetools):

    # add context menu handler

    def show_getting_started():
        url = PyQt5.QtCore.QUrl('https://languagetools.anki.study/tutorials/language-tools-getting-started?utm_campaign=langtools_menu&utm_source=languagetools&utm_medium=addon')
        PyQt5.QtGui.QDesktopServices.openUrl(url)

    def show_language_mapping():
        dialogs.language_mapping_dialogue(languagetools)

    def show_voice_selection():
        dialog_voiceselection.voice_selection_dialog(languagetools, aqt.mw)

    def show_text_processing():
        dialog_textprocessing.text_processing_dialog(languagetools)

    def show_yomichan_integration():
        dialogs.yomichan_dialog(languagetools)

    def show_api_key_dialog():
        dialogs.show_api_key_dialog(languagetools)

    def show_change_language(deck_note_type_field: deck_utils.DeckNoteTypeField):
        current_language = languagetools.get_language(deck_note_type_field)

        if current_language == None:
            # perform detection
            current_language = languagetools.guess_language(deck_note_type_field)

        data = languagetools.get_all_language_arrays()
        language_list = data['language_name_list']
        language_code_list = data['language_code_list']

        # locate current language
        if current_language == None:
            current_row = 0
        else:
            current_row = language_code_list.index(current_language)
        chosen_index = aqt.utils.chooseList(f'{constants.MENU_PREFIX} Choose Language for {deck_note_type_field.field_name}', language_list, startrow=current_row)

        new_language = language_code_list[chosen_index]
        languagetools.store_language_detection_result(deck_note_type_field, new_language)


    def show_translation(source_text, from_language, to_language):
        # print(f'translate {source_text} from {from_language} to {to_language}')
        result = languagetools.get_translation_all(source_text, from_language, to_language)

        translations = ''
        for key, value in result.items():
            entry = f'{key}: <b>{value}</b><br/>'
            translations += entry
        text = f"""Translation of <i>{source_text}</i> from {languagetools.get_language_name(from_language)} to {languagetools.get_language_name(to_language)}<br/>
            {translations}
        """
        aqt.utils.showInfo(text, title=f'{constants.MENU_PREFIX} Translation', textFormat="rich")

    def show_transliteration(selected_text, transliteration_option):
        result = languagetools.get_transliteration(selected_text, transliteration_option)
        text = f"""Transliteration of <i>{selected_text}</i>: {result}"""
        aqt.utils.showInfo(text, title=f'{constants.MENU_PREFIX} Transliteration', textFormat="rich")

    def add_inline_translation(note_editor: aqt.editor.Editor, source_language, target_language, deck_note_type_field: deck_utils.DeckNoteTypeField):
        # choose translation service
        translation_options = languagetools.get_translation_options(source_language, target_language)

        # ask the user which one they want
        services = [x['service'] for x in translation_options]
        choice = aqt.utils.chooseList(f'{constants.MENU_PREFIX} Choose Translation Service', services)
        chosen_option = translation_options[choice]

        # determine the ranking of this field in the note type
        languagetools.add_inline_translation(deck_note_type_field, chosen_option, target_language)
        editor.apply_inline_translation_changes(languagetools, note_editor, deck_note_type_field, chosen_option)

    def disable_inline_translation(note_editor: aqt.editor.Editor, deck_note_type_field: deck_utils.DeckNoteTypeField):
        languagetools.remove_inline_translations(deck_note_type_field)
        editor.remove_inline_translation_changes(languagetools, note_editor, deck_note_type_field)

    def on_context_menu(web_view: aqt.editor.EditorWebView, menu: aqt.qt.QMenu):
        # gather some information about the context from the editor
        # =========================================================

        editor: aqt.editor.Editor = web_view.editor

        selected_text = web_view.selectedText()
        current_field_num = editor.currentField
        if current_field_num == None:
            # we don't have a field selected, don't do anything
            return
        note = web_view.editor.note
        if note == None:
            # can't do anything without a note
            return
        model_id = note.mid
        model = aqt.mw.col.models.get(model_id)
        field_name = model['flds'][current_field_num]['name']
        card = web_view.editor.card
        if card == None:
            # we can't get the deck without a a card
            return
        deck_id = card.did

        deck_note_type_field = languagetools.deck_utils.build_deck_note_type_field(deck_id, model_id, field_name)
        language = languagetools.get_language(deck_note_type_field)

        # check whether a language is set
        # ===============================

        if language != None:
            # all pre-requisites for translation/transliteration are met, proceed
            # ===================================================================

            # these options require text to be selected

            if len(selected_text) > 0:
                source_text_max_length = 25
                source_text = selected_text
                if len(selected_text) > source_text_max_length:
                    source_text = selected_text[0:source_text_max_length]

                # add translation options
                # =======================
                menu_text = f'{constants.MENU_PREFIX} translate from {languagetools.get_language_name(language)}'
                submenu = aqt.qt.QMenu(menu_text, menu)
                wanted_languages = languagetools.get_wanted_languages()
                for wanted_language in wanted_languages:
                    if wanted_language != language:
                        menu_text = f'To {languagetools.get_language_name(wanted_language)}'
                        def get_translate_lambda(selected_text, language, wanted_language):
                            def translate():
                                show_translation(selected_text, language, wanted_language)
                            return translate
                        submenu.addAction(menu_text, get_translate_lambda(selected_text, language, wanted_language))
                menu.addMenu(submenu)

                # add transliteration options
                # ===========================

                transliteration_options = languagetools.get_transliteration_options(language)
                if len(transliteration_options) > 0:
                    menu_text = f'{constants.MENU_PREFIX} transliterate {languagetools.get_language_name(language)}'
                    submenu = aqt.qt.QMenu(menu_text, menu)
                    for transliteration_option in transliteration_options:
                        menu_text = transliteration_option['transliteration_name']
                        def get_transliterate_lambda(selected_text, transliteration_option):
                            def transliterate():
                                show_transliteration(selected_text, transliteration_option)
                            return transliterate
                        submenu.addAction(menu_text, get_transliterate_lambda(selected_text, transliteration_option))
                    menu.addMenu(submenu)


        # was language detection run ?
        # ============================

        if languagetools.language_detection_done():

            # show information about the field 
            # ================================

            if language == None:
                menu_text = f'{constants.MENU_PREFIX} No language set'
            else:
                menu_text = f'{constants.MENU_PREFIX} language: {languagetools.get_language_name(language)}'
            submenu = aqt.qt.QMenu(menu_text, menu)

            # add change language option
            menu_text = f'Change Language'
            def get_change_language_lambda(deck_note_type_field):
                def change_language():
                    show_change_language(deck_note_type_field)
                return change_language
            submenu.addAction(menu_text, get_change_language_lambda(deck_note_type_field))

            menu.addMenu(submenu)


    # add menu items to anki deck picker / main screen
    # ================================================
    
    action = aqt.qt.QAction(f"{constants.MENU_PREFIX} Getting Started", aqt.mw)
    action.triggered.connect(show_getting_started)
    aqt.mw.form.menuTools.addAction(action)

    action = aqt.qt.QAction(f"{constants.MENU_PREFIX} Language Mapping", aqt.mw)
    action.triggered.connect(show_language_mapping)
    aqt.mw.form.menuTools.addAction(action)

    action = aqt.qt.QAction(f"{constants.MENU_PREFIX} Voice Selection", aqt.mw)
    action.triggered.connect(show_voice_selection)
    aqt.mw.form.menuTools.addAction(action)

    action = aqt.qt.QAction(f"{constants.MENU_PREFIX} Text Processing", aqt.mw)
    action.triggered.connect(show_text_processing)
    aqt.mw.form.menuTools.addAction(action)

    action = aqt.qt.QAction(f"{constants.MENU_PREFIX} Verify API Key && Account Info", aqt.mw)
    action.triggered.connect(show_api_key_dialog)
    aqt.mw.form.menuTools.addAction(action)    

    action = aqt.qt.QAction(f"{constants.MENU_PREFIX} Yomichan Integration", aqt.mw)
    action.triggered.connect(show_yomichan_integration)
    aqt.mw.form.menuTools.addAction(action)        

    action = aqt.qt.QAction(f"{constants.MENU_PREFIX} About", aqt.mw)
    action.triggered.connect(languagetools.show_about)
    aqt.mw.form.menuTools.addAction(action)

    # right click menu
    aqt.gui_hooks.editor_will_show_context_menu.append(on_context_menu)

    def collectionDidLoad(col: anki.collection.Collection):
        languagetools.setCollectionLoaded()

    def mainWindowInit():
        languagetools.setMainWindowInit()
    
    def deckBrowserDidRender(deck_browser: aqt.deckbrowser.DeckBrowser):
        languagetools.setDeckBrowserRendered()

    # run some stuff after anki has initialized
    aqt.gui_hooks.collection_did_load.append(collectionDidLoad)
    aqt.gui_hooks.main_window_did_init.append(mainWindowInit)
    aqt.gui_hooks.deck_browser_did_render.append(deckBrowserDidRender)

    def browerMenusInit(browser: aqt.browser.Browser):
        menu = aqt.qt.QMenu(constants.ADDON_NAME, browser.form.menubar)
        browser.form.menubar.addMenu(menu)

        action = aqt.qt.QAction(f'Add Translation To Selected Notes...', browser)
        action.triggered.connect(lambda: dialogs.add_translation_dialog(languagetools, browser, browser.selectedNotes()))
        menu.addAction(action)

        action = aqt.qt.QAction(f'Add Transliteration To Selected Notes...', browser)
        action.triggered.connect(lambda: dialogs.add_transliteration_dialog(languagetools, browser, browser.selectedNotes()))
        menu.addAction(action)

        action = aqt.qt.QAction(f'Add Audio To Selected Notes...', browser)
        action.triggered.connect(lambda: dialogs.add_audio_dialog(languagetools, browser, browser.selectedNotes()))
        menu.addAction(action)        

        action = aqt.qt.QAction(f'Run Rules for Selected Notes...', browser)
        action.triggered.connect(lambda: dialogs.run_rules_dialog(languagetools, browser, browser.selectedNotes()))
        menu.addAction(action)                

        action = aqt.qt.QAction(f'Show Rules for Selected Notes...', browser)
        action.triggered.connect(lambda: dialogs.show_settings_dialog(languagetools, browser, browser.selectedNotes()))
        menu.addAction(action)                

    # browser menus
    aqt.gui_hooks.browser_menus_did_init.append(browerMenusInit)