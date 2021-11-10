# python imports
import sys
import os
import glob
import re
import random
import requests
import json
import tempfile
import logging
from typing import List, Dict
import hashlib
import anki.utils

# anki imports
import aqt
import aqt.progress
import aqt.addcards
import anki.notes
import anki.cards

if hasattr(sys, '_pytest_mode'):
    import constants
    import version
    import errors
    import deck_utils
    import text_utils
else:
    from . import constants
    from . import version
    from . import errors
    from . import deck_utils
    from . import text_utils


class LanguageTools():

    def __init__(self, anki_utils, deck_utils, cloud_language_tools):
        self.anki_utils = anki_utils
        self.deck_utils = deck_utils
        self.cloud_language_tools = cloud_language_tools
        self.error_manager = errors.ErrorManager(self.anki_utils)
        self.config = self.anki_utils.get_config()
        self.text_utils = text_utils.TextUtils(self.get_text_processing_settings())
        self.error_manager = errors.ErrorManager(self.anki_utils)

        self.language_data_load_error = False

        self.collectionLoaded = False
        self.mainWindowInitialized = False
        self.deckBrowserRendered = False
        self.initDone = False

        self.api_key_checked = False

    def setCollectionLoaded(self):
        self.collectionLoaded = True
        self.checkInitialize()

    def setMainWindowInit(self):
        self.mainWindowInitialized = True
        self.checkInitialize()

    def setDeckBrowserRendered(self):
        self.deckBrowserRendered = True
        self.checkInitialize()

    def checkInitialize(self):
        if self.collectionLoaded and self.mainWindowInitialized and self.deckBrowserRendered and self.initDone == False:
            aqt.mw.taskman.run_in_background(self.initialize, self.initializeDone)

    def initialize(self):
        try:
            self.initDone = True

            # get language data
            self.language_data = self.cloud_language_tools.get_language_data()
            self.language_list = self.language_data['language_list']
            self.translation_language_list = self.language_data['translation_options']
            self.transliteration_language_list = self.language_data['transliteration_options']
            self.voice_list = self.language_data['voice_list']
            self.tokenization_options = self.language_data['tokenization_options']

            # do we have an API key in the config ?
            if len(self.config['api_key']) > 0:
                validation_result = self.cloud_language_tools.api_key_validate_query(self.config['api_key'])
                if validation_result['key_valid'] == True:
                    self.api_key_checked = True
        except:
            self.language_data_load_error = True
            logging.exception(f'could not load language data')

    def initializeDone(self, future):
        if self.language_data_load_error:
            self.anki_utils.critical_message('Could not load language data from server, please try to restart Anki.', aqt.mw)

    def get_config_api_key(self):
        return self.config['api_key']

    def set_config_api_key(self, api_key):
        self.config['api_key'] = api_key
        self.anki_utils.write_config(self.config)
        self.api_key_checked = True

    def verify_api_key(self, api_key):
        result = self.cloud_language_tools.api_key_validate_query(api_key)
        if result['key_valid'] == True:
            message = result['msg']
            return True, message
        else:
            message = result['msg']
            return False, message

    def ensure_api_key_checked(self):
        # print(f'self.api_key_checked: {self.api_key_checked}')
        if self.api_key_checked:
            return True
        aqt.utils.showInfo(f'Please enter API key from menu <b>Tools -> Language Tools: Verify API Key</b>', title=constants.MENU_PREFIX)
        return False


    def language_detection_done(self):
        return len(self.config[constants.CONFIG_DECK_LANGUAGES]) > 0

    def show_about(self):
        text = f'{constants.ADDON_NAME}: v{version.ANKI_LANGUAGE_TOOLS_VERSION}'
        aqt.utils.showInfo(text, title=constants.ADDON_NAME)

    def get_language_name(self, language):
        if language == None:
            return 'Not set'
        if language == constants.SpecialLanguage.transliteration.name:
            return 'Transliteration'
        if language == constants.SpecialLanguage.sound.name:
            return 'Sound'
        return self.language_list[language]

    def language_available_for_translation(self, language):
        if language == None:
            return False
        if language == constants.SpecialLanguage.transliteration.name:
            return False
        if language == constants.SpecialLanguage.sound.name:
            return False
        return True

    def get_all_languages(self):
        return self.language_list

    def get_all_language_arrays(self):
        # return two arrays, one with the codes, one with the human descriptions
        language_dict = self.get_all_languages()
        language_list = []
        for key, name in language_dict.items():
            language_list.append({'key': key, 'name': name})
        # sort by language name
        language_list = sorted(language_list, key=lambda x: x['name'])
        language_code_list = [x['key'] for x in language_list]
        language_name_list = [x['name'] for x in language_list]

        # add the special languages
        language_name_list.append('Transliteration')
        language_code_list.append(constants.SpecialLanguage.transliteration.name)
        language_name_list.append('Sound')
        language_code_list.append(constants.SpecialLanguage.sound.name)

        return {'language_name_list': language_name_list,
                'language_code_list': language_code_list
        }

    def get_wanted_language_arrays(self):
        wanted_languages = self.get_wanted_languages()
        language_dict = self.get_all_languages()

        language_list = []
        for key in wanted_languages:
            language_list.append({'key': key, 'name': language_dict[key]})
        # sort by language name
        language_list = sorted(language_list, key=lambda x: x['name'])
        language_code_list = [x['key'] for x in language_list]
        language_name_list = [x['name'] for x in language_list]

        return {'language_name_list': language_name_list,
                'language_code_list': language_code_list
        }        

    def get_populated_dntf(self) -> List[deck_utils.DeckNoteTypeField]:
        populated_set = self.anki_utils.get_deckid_modelid_pairs()
        
        result: List[deck_utils.DeckNoteTypeField] = []

        for entry in populated_set:
            deck_id = entry[0]
            model_id = entry[1]
            deck_note_type = self.deck_utils.build_deck_note_type(deck_id, model_id)
            model = self.anki_utils.get_model(model_id)
            fields = model['flds']
            for field in fields:
                field_name = field['name']
                deck_note_type_field = self.deck_utils.build_dntf_from_dnt(deck_note_type, field_name)
                result.append(deck_note_type_field)

        return result


    def get_populated_decks(self) -> Dict[str, deck_utils.Deck]:
        deck_note_type_field_list: List[deck_utils.DeckNoteTypeField] = self.get_populated_dntf()
        deck_map = {}
        for deck_note_type_field in deck_note_type_field_list:
            deck_name = deck_note_type_field.deck_note_type.deck_name
            if deck_name not in deck_map:
                deck_map[deck_name] = self.deck_utils.new_deck()
            deck_map[deck_name].add_deck_note_type_field(deck_note_type_field)
        return deck_map
            
    def get_noteids_for_deck_note_type(self, deck_note_type: deck_utils.DeckNoteType, sample_size):
        deck_id = deck_note_type.deck_id
        model_id = deck_note_type.model_id
        return self.anki_utils.get_noteids_for_deck_note_type(deck_id, model_id, sample_size)

    def get_field_samples(self, deck_note_type_field: deck_utils.DeckNoteTypeField, sample_size: int) -> List[str]:
        note_ids = self.get_noteids_for_deck_note_type(deck_note_type_field.deck_note_type, sample_size)

        stripImagesRe = re.compile("(?i)<img[^>]+src=[\"']?([^\"'>]+)[\"']?[^>]*>")
        
        def process_field_value(note_id, field_name):
            note = self.anki_utils.get_note_by_id(note_id)
            if field_name not in note:
                # field was removed
                raise errors.AnkiItemNotFoundError(f'field {field_name} not found')
            original_field_value = note[field_name]
            field_value = stripImagesRe.sub('', original_field_value)
            field_value = anki.utils.htmlToTextLine(field_value)
            max_len = 200 # restrict to 200 characters
            if len(original_field_value) > max_len:
                field_value = original_field_value[:max_len]
            return field_value

        all_field_values = [process_field_value(x, deck_note_type_field.field_name) for x in note_ids]
        non_empty_fields = [x for x in all_field_values if len(x) > 0]

        if len(non_empty_fields) < sample_size:
            field_sample = non_empty_fields
        else:
            field_sample = random.sample(non_empty_fields, sample_size)

        return field_sample

    def get_field_samples_for_language(self, language_code, sample_size):
        # self.config[constants.CONFIG_DECK_LANGUAGES][model_name][deck_name][field_name] = language

        dntf_list = []
        for model_name, model_data in self.config[constants.CONFIG_DECK_LANGUAGES].items():
            for deck_name, deck_data in model_data.items():
                for field_name, field_language_code in deck_data.items():
                    if field_language_code == language_code:
                        try:
                            # found the language we need
                            deck_note_type_field = self.deck_utils.build_deck_note_type_field_from_names(deck_name, model_name, field_name)
                            dntf_list.append(deck_note_type_field)
                        except errors.AnkiItemNotFoundError as error:
                            # this deck probably got deleted
                            pass

        all_field_samples = []
        for dntf in dntf_list:
            try:
                field_samples = self.get_field_samples(dntf, sample_size)
                all_field_samples.extend(field_samples)
            except errors.AnkiItemNotFoundError as error:
                # might be a field missing
                pass                
        
        # pick random sample
        if len(all_field_samples) < sample_size:
            result = all_field_samples
        else:
            result = random.sample(all_field_samples, sample_size)
        
        return result


    def perform_language_detection_deck_note_type_field(self, deck_note_type_field: deck_utils.DeckNoteTypeField):
        # get a random sample of data within this field

        sample_size = 100 # max supported by azure
        field_sample = self.get_field_samples(deck_note_type_field, sample_size)
        if len(field_sample) == 0:
            return None

        return self.cloud_language_tools.language_detection(self.config['api_key'], field_sample)


    def guess_language(self, deck_note_type_field: deck_utils.DeckNoteTypeField):
        # retrieve notes
        return self.perform_language_detection_deck_note_type_field(deck_note_type_field)

    def store_language_detection_result(self, deck_note_type_field: deck_utils.DeckNoteTypeField, language):
        # write per-deck detected languages

        model_name = deck_note_type_field.get_model_name()
        deck_name = deck_note_type_field.get_deck_name()
        field_name = deck_note_type_field.field_name

        if constants.CONFIG_DECK_LANGUAGES not in self.config:
            self.config[constants.CONFIG_DECK_LANGUAGES] = {}
        if model_name not in self.config[constants.CONFIG_DECK_LANGUAGES]:
            self.config[constants.CONFIG_DECK_LANGUAGES][model_name] = {}
        if deck_name not in self.config[constants.CONFIG_DECK_LANGUAGES][model_name]:
            self.config[constants.CONFIG_DECK_LANGUAGES][model_name][deck_name] = {}
        self.config[constants.CONFIG_DECK_LANGUAGES][model_name][deck_name][field_name] = language

        # store the languages we're interested in
        if self.language_available_for_translation(language):
            if constants.CONFIG_WANTED_LANGUAGES not in self.config:
                self.config[constants.CONFIG_WANTED_LANGUAGES] = {}
            self.config[constants.CONFIG_WANTED_LANGUAGES][language] = True

        self.anki_utils.write_config(self.config)

    def store_batch_translation_setting(self, deck_note_type_field: deck_utils.DeckNoteTypeField, source_field: str, translation_option):
        model_name = deck_note_type_field.get_model_name()
        deck_name = deck_note_type_field.get_deck_name()
        field_name = deck_note_type_field.field_name

        if constants.CONFIG_BATCH_TRANSLATION not in self.config:
            self.config[constants.CONFIG_BATCH_TRANSLATION] = {}
        if model_name not in self.config[constants.CONFIG_BATCH_TRANSLATION]:
            self.config[constants.CONFIG_BATCH_TRANSLATION][model_name] = {}
        if deck_name not in self.config[constants.CONFIG_BATCH_TRANSLATION][model_name]:
            self.config[constants.CONFIG_BATCH_TRANSLATION][model_name][deck_name] = {}
        self.config[constants.CONFIG_BATCH_TRANSLATION][model_name][deck_name][field_name] = {
            'from_field': source_field,
            'translation_option': translation_option
        }
        self.anki_utils.write_config(self.config)

    def remove_translation_setting(self, deck_note_type_field: deck_utils.DeckNoteTypeField):
        model_name = deck_note_type_field.get_model_name()
        deck_name = deck_note_type_field.get_deck_name()
        field_name = deck_note_type_field.field_name        
        del self.config[constants.CONFIG_BATCH_TRANSLATION][model_name][deck_name][field_name]
        aqt.mw.addonManager.writeConfig(__name__, self.config)

    def store_batch_transliteration_setting(self, deck_note_type_field: deck_utils.DeckNoteTypeField, source_field: str, transliteration_option):
        model_name = deck_note_type_field.get_model_name()
        deck_name = deck_note_type_field.get_deck_name()
        field_name = deck_note_type_field.field_name

        if constants.CONFIG_BATCH_TRANSLITERATION not in self.config:
            self.config[constants.CONFIG_BATCH_TRANSLITERATION] = {}
        if model_name not in self.config[constants.CONFIG_BATCH_TRANSLITERATION]:
            self.config[constants.CONFIG_BATCH_TRANSLITERATION][model_name] = {}
        if deck_name not in self.config[constants.CONFIG_BATCH_TRANSLITERATION][model_name]:
            self.config[constants.CONFIG_BATCH_TRANSLITERATION][model_name][deck_name] = {}
        self.config[constants.CONFIG_BATCH_TRANSLITERATION][model_name][deck_name][field_name] = {
            'from_field': source_field,
            'transliteration_option': transliteration_option
        }
        self.anki_utils.write_config(self.config)

        # the language for the target field should be set to transliteration
        self.store_language_detection_result(deck_note_type_field, constants.SpecialLanguage.transliteration.name)

    def remove_transliteration_setting(self, deck_note_type_field: deck_utils.DeckNoteTypeField):
        model_name = deck_note_type_field.get_model_name()
        deck_name = deck_note_type_field.get_deck_name()
        field_name = deck_note_type_field.field_name        
        del self.config[constants.CONFIG_BATCH_TRANSLITERATION][model_name][deck_name][field_name]
        aqt.mw.addonManager.writeConfig(__name__, self.config)

    def get_batch_translation_settings(self, deck_note_type: deck_utils.DeckNoteType):
        model_name = deck_note_type.model_name
        deck_name = deck_note_type.deck_name

        return self.config.get(constants.CONFIG_BATCH_TRANSLATION, {}).get(model_name, {}).get(deck_name, {})

    def get_batch_translation_setting_field(self, deck_note_type_field: deck_utils.DeckNoteTypeField):
        return self.get_batch_translation_settings(deck_note_type_field.deck_note_type).get(deck_note_type_field.field_name, None)

    def get_batch_transliteration_settings(self, deck_note_type: deck_utils.DeckNoteType):
        model_name = deck_note_type.model_name
        deck_name = deck_note_type.deck_name

        return self.config.get(constants.CONFIG_BATCH_TRANSLITERATION, {}).get(model_name, {}).get(deck_name, {})

    def store_batch_audio_setting(self, deck_note_type_field: deck_utils.DeckNoteTypeField, source_field: str):
        model_name = deck_note_type_field.get_model_name()
        deck_name = deck_note_type_field.get_deck_name()
        field_name = deck_note_type_field.field_name

        if constants.CONFIG_BATCH_AUDIO not in self.config:
            self.config[constants.CONFIG_BATCH_AUDIO] = {}
        if model_name not in self.config[constants.CONFIG_BATCH_AUDIO]:
            self.config[constants.CONFIG_BATCH_AUDIO][model_name] = {}
        if deck_name not in self.config[constants.CONFIG_BATCH_AUDIO][model_name]:
            self.config[constants.CONFIG_BATCH_AUDIO][model_name][deck_name] = {}
        self.config[constants.CONFIG_BATCH_AUDIO][model_name][deck_name][field_name] = source_field
        aqt.mw.addonManager.writeConfig(__name__, self.config)

        # the language for the target field should be set to sound
        self.store_language_detection_result(deck_note_type_field, constants.SpecialLanguage.sound.name)

    def remove_audio_setting(self, deck_note_type_field: deck_utils.DeckNoteTypeField):
        model_name = deck_note_type_field.get_model_name()
        deck_name = deck_note_type_field.get_deck_name()
        field_name = deck_note_type_field.field_name        
        del self.config[constants.CONFIG_BATCH_AUDIO][model_name][deck_name][field_name]
        aqt.mw.addonManager.writeConfig(__name__, self.config)

    def get_batch_audio_settings(self, deck_note_type: deck_utils.DeckNoteType):
        model_name = deck_note_type.model_name
        deck_name = deck_note_type.deck_name

        # logging.debug(f'get_batch_audio_settings, config: {self.config}')

        return self.config.get(constants.CONFIG_BATCH_AUDIO, {}).get(model_name, {}).get(deck_name, {})

    def get_text_processing_settings(self):
        return self.config.get(constants.CONFIG_TEXT_PROCESSING, {})

    def store_text_processing_settings(self, settings):
        self.config[constants.CONFIG_TEXT_PROCESSING] = settings
        self.anki_utils.write_config(self.config)
        self.text_utils = text_utils.TextUtils(settings)

    def store_voice_selection(self, language_code, voice_mapping):
        self.config[constants.CONFIG_VOICE_SELECTION][language_code] = voice_mapping
        self.anki_utils.write_config(self.config)

    def get_voice_selection_settings(self):
        return self.config.get(constants.CONFIG_VOICE_SELECTION, {})

    def get_voice_for_field(self, dntf):
        language_code = self.get_language(dntf)
        if language_code == None:
            raise errors.FieldLanguageMappingError(dntf)
        if not self.language_available_for_translation(language_code):
            raise errors.FieldLanguageSpecialMappingError(dntf, language_code)
        language_name = self.get_language_name(language_code)
        voice_selection_settings = self.get_voice_selection_settings()
        if language_code not in voice_selection_settings:
            raise errors.NoVoiceSetError(language_name)
        return voice_selection_settings[language_code]

    def get_apply_updates_automatically(self):
        return self.config.get(constants.CONFIG_APPLY_UPDATES_AUTOMATICALLY, True)

    def set_apply_updates_automatically(self, value):
        self.config[constants.CONFIG_APPLY_UPDATES_AUTOMATICALLY] = value
        self.anki_utils.write_config(self.config)

    def get_live_update_delay(self):
        return self.config.get(constants.CONFIG_LIVE_UPDATE_DELAY, 1250)

    def set_live_update_delay(self, value):
        self.config[constants.CONFIG_LIVE_UPDATE_DELAY] = value
        self.anki_utils.write_config(self.config)

    def get_language(self, deck_note_type_field: deck_utils.DeckNoteTypeField):
        """will return None if no language is associated with this field"""
        model_name = deck_note_type_field.get_model_name()
        deck_name = deck_note_type_field.get_deck_name()
        field_name = deck_note_type_field.field_name
        return self.config.get(constants.CONFIG_DECK_LANGUAGES, {}).get(model_name, {}).get(deck_name, {}).get(field_name, None)

    def get_language_validate(self, deck_note_type_field: deck_utils.DeckNoteTypeField):
        language_code = self.get_language(deck_note_type_field)
        if language_code == None:
            raise errors.FieldLanguageMappingError(deck_note_type_field)
        if not self.language_available_for_translation(language_code):
            raise errors.FieldLanguageSpecialMappingError(deck_note_type_field, language_code)
        return language_code

    def get_wanted_languages(self):
        return self.config[constants.CONFIG_WANTED_LANGUAGES].keys()

    def get_translation_async(self, source_text, translation_option):
        processed_text = self.text_utils.process(source_text, constants.TransformationType.Translation)
        logging.info(f'before text processing: [{source_text}], after text processing: [{processed_text}]')
        if self.text_utils.is_empty(processed_text):
            raise errors.LanguageToolsValidationFieldEmpty()
        return self.cloud_language_tools.get_translation(self.config['api_key'], processed_text, translation_option)

    def interpret_translation_response_async(self, response):
        # print(response.status_code)
        if response.status_code == 200:
            data = json.loads(response.content)
            return data['translated_text'] 
        if response.status_code == 400:
            data = json.loads(response.content)
            error_text = f"Could not load translation: {data['error']}"
            raise errors.LanguageToolsRequestError(error_text)
        if response.status_code == 401:
            data = json.loads(response.content)
            raise errors.LanguageToolsRequestError(data['error'])
        error_text = f"Could not load translation: {response.text}"
        raise errors.LanguageToolsRequestError(error_text)

    def get_translation(self, source_text, translation_option):
        return self.interpret_translation_response_async(self.get_translation_async(source_text, translation_option))

    def get_translation_all(self, source_text, from_language, to_language):
        processed_text = self.text_utils.process(source_text, constants.TransformationType.Translation)
        logging.info(f'before text processing: [{source_text}], after text processing: [{processed_text}]')
        if self.text_utils.is_empty(processed_text):
            raise errors.LanguageToolsValidationFieldEmpty()        
        return self.cloud_language_tools.get_translation_all(self.config['api_key'], source_text, from_language, to_language)
    
    # transliteration
    # ===============

    def get_transliteration_async(self, source_text, transliteration_option):
        processed_text = self.text_utils.process(source_text, constants.TransformationType.Transliteration)
        logging.info(f'before text processing: [{source_text}], after text processing: [{processed_text}]')
        if self.text_utils.is_empty(processed_text):
            raise errors.LanguageToolsValidationFieldEmpty()        
        return self.cloud_language_tools.get_transliteration(self.config['api_key'], processed_text, transliteration_option)

    def interpret_transliteration_response_async(self, response):
        if response.status_code == 200:
            data = json.loads(response.content)
            return data['transliterated_text'] 
        if response.status_code == 400:
            data = json.loads(response.content)
            error_text = f"Could not load transliteration: {data['error']}"
            raise errors.LanguageToolsRequestError(error_text)
            return error_text
        if response.status_code == 401:
            data = json.loads(response.content)
            raise errors.LanguageToolsRequestError(data['error'])
        error_text = f"Could not load transliteration: {response.text}"
        raise errors.LanguageToolsRequestError(error_text)

    def get_transliteration(self, source_text, transliteration_option):
        return self.interpret_transliteration_response_async(self.get_transliteration_async(source_text, transliteration_option))

    # breakdown
    # =========

    def get_breakdown_async(self, source_text, tokenization_option, translation_option, transliteration_option):
        return self.cloud_language_tools.get_breakdown(self.config['api_key'], source_text, tokenization_option, translation_option, transliteration_option)

    def interpret_breakdown_response_async(self, response):
        if response.status_code == 200:
            data = json.loads(response.content)
            return data['breakdown'] 
        if response.status_code == 400:
            data = json.loads(response.content)
            error_text = f"Could not load breakdown: {data['error']}"
            raise errors.LanguageToolsRequestError(error_text)
            return error_text
        if response.status_code == 401:
            data = json.loads(response.content)
            raise errors.LanguageToolsRequestError(data['error'])
        error_text = f"Could not load breakdown: {response.text}"
        raise errors.LanguageToolsRequestError(error_text)

    def format_breakdown_entry(self, breakdown_entry):
        components = []
        components.append('<b>'+breakdown_entry['token']+'</b>')
        if breakdown_entry['lemma'] != breakdown_entry['token']:
            components.append('[' + breakdown_entry['lemma'] + ']')
        if 'transliteration' in breakdown_entry:
            components.append('<i>' + breakdown_entry['transliteration'] + '</i>')
        if 'translation' in breakdown_entry:
            components.append(breakdown_entry['translation'])
        if 'pos_description' in breakdown_entry:
            components.append('<i>(' + breakdown_entry['pos_description'] + ')</i>')
        return ' '.join(components)

    def generate_audio_for_field(self, note_id, from_field, to_field, voice):
        note = self.anki_utils.get_note_by_id(note_id)
        source_text = note[from_field]
        if self.text_utils.is_empty(source_text):
            return False
        
        response = self.generate_audio_tag_collection(source_text, voice)
        sound_tag = response['sound_tag']
        if sound_tag != None:
            # write to note
            note[to_field] = sound_tag
            note.flush()
            return True # success

        return False # failure

    def generate_audio_tag_collection(self, source_text, voice):
        result = {'sound_tag': None,
                  'full_filename': None}
        generated_filename = self.get_tts_audio(source_text, voice['service'], voice['language_code'], voice['voice_key'], {})
        if generated_filename != None:
            full_filename = self.anki_utils.media_add_file(generated_filename)
            collection_filename = os.path.basename(full_filename)
            sound_tag = f'[sound:{collection_filename}]'
            result['sound_tag'] = sound_tag
            result['full_filename'] = full_filename
        return result

    def get_hash_for_request(self, url_path, data):
        combined_data = {
            'url': url_path,
            'data': data
        }
        return hashlib.sha224(str(combined_data).encode('utf-8')).hexdigest()

    def get_hash_for_audio_request(self, source_text, service, voice_key, options):
        combined_data = {
            'source_text': source_text,
            'service': service,
            'voice_key': voice_key,
            'options': options
        }
        return hashlib.sha224(str(combined_data).encode('utf-8')).hexdigest()

    def get_user_files_dir(self):
        addon_dir = os.path.dirname(os.path.realpath(__file__))
        user_files_dir = os.path.join(addon_dir, 'user_files')
        return user_files_dir        

    def clean_user_files_audio(self):
        user_files_dir = self.get_user_files_dir()
        files = glob.glob(f'{user_files_dir}/*.mp3')
        for f in files:
            os.remove(f)

    def get_audio_filename(self, source_text, service, voice_key, options):
        user_files_dir = self.get_user_files_dir()
        hash_str = self.get_hash_for_audio_request(source_text, service, voice_key, options)
        filename = f'languagetools-{hash_str}.mp3'
        return os.path.join(user_files_dir, filename)

    def get_tts_audio(self, source_text, service, language_code, voice_key, options):
        processed_text = self.text_utils.process(source_text, constants.TransformationType.Audio)
        logging.info(f'before text processing: [{source_text}], after text processing: [{processed_text}]')
        if self.text_utils.is_empty(processed_text):
            raise errors.LanguageToolsValidationFieldEmpty()
        filename = self.get_audio_filename(processed_text, service, voice_key, options)
        if os.path.isfile(filename):
            return filename
        audio_content = self.cloud_language_tools.get_tts_audio(self.config['api_key'], processed_text, service, language_code, voice_key, options)
        with open(filename, 'wb') as f:
            f.write(audio_content)
        f.close()
        logging.info(f'wrote audio filename {filename}')
        return filename

    def play_tts_audio(self, source_text, service, language_code, voice_key, options):
        audio_filename = self.get_tts_audio(source_text, service, language_code, voice_key, options)
        self.anki_utils.play_sound(audio_filename)

    def get_tts_voice_list(self):
        return self.cloud_language_tools.get_tts_voice_list(self.config['api_key'])

    def get_transliteration_options(self, language):
        candidates = [x for x in self.transliteration_language_list if x['language_code'] == language]
        return candidates

    def build_translation_option(self, service, source_language_id, target_language_id):
        return {
            'service': service,
            'source_language_id': source_language_id,
            'target_language_id': target_language_id
        }
        

    def get_translation_options(self, source_language: str, target_language: str):
        # get list of services which support source_language
        translation_options = []
        source_language_options = [x for x in self.translation_language_list if x['language_code'] == source_language]
        for source_language_option in source_language_options:
            service = source_language_option['service']
            # find out whether target language is supported
            target_language_options = [x for x in self.translation_language_list if x['language_code'] == target_language and x['service'] == service]
            if len(target_language_options) == 1:
                # found an option
                target_language_option = target_language_options[0]
                translation_option = self.build_translation_option(service, source_language_option['language_id'], target_language_option['language_id'])
                translation_options.append(translation_option)
        return translation_options


    def get_tokenization_options(self, source_language):
        tokenization_options = []
        source_language_options = [x for x in self.tokenization_options if x['language_code'] == source_language]
        return source_language_options
