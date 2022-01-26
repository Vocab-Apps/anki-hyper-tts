import logging
import json
import tempfile
import re
import os

import constants
import hypertts
import errors
import servicemanager


def get_test_services_dir():
    current_script_path = os.path.realpath(__file__)
    current_script_dir = os.path.dirname(current_script_path)    
    return os.path.join(current_script_dir, 'test_services')

class MockFuture():
    def __init__(self, result_data):
        self.result_data = result_data

    def result(self):
        return self.result_data


class MockAnkiUtils():
    def __init__(self, config):
        self.config = config
        self.written_config = None
        self.editor_set_field_value_calls = []
        self.added_media_file = None
        self.show_loading_indicator_called = None
        self.hide_loading_indicator_called = None

        # undo handling
        self.undo_started = False
        self.undo_finished = False

        # user_files dir
        self.user_files_dir = tempfile.gettempdir()

        # exception handling
        self.last_exception = None
        self.last_action = None

    def get_config(self):
        return self.config

    def write_config(self, config):
        self.written_config = config

    def get_user_files_dir(self):
        return self.user_files_dir

    def get_green_stylesheet(self):
        return constants.GREEN_STYLESHEET

    def get_red_stylesheet(self):
        return constants.RED_STYLESHEET

    def play_anki_sound_tag(self, text):
        self.last_played_sound_tag = text

    def get_deckid_modelid_pairs(self):
        return self.deckid_modelid_pairs

    def get_noteids_for_deck_note_type(self, deck_id, model_id, sample_size):

        note_id_list = self.notes[deck_id][model_id].keys()

        return note_id_list

    def get_note_by_id(self, note_id):
        return self.notes_by_id[note_id]


    def get_model(self, model_id):
        # should return a dict which has flds
        return self.models[model_id]

    def get_deck(self, deck_id):
        return self.decks[deck_id]

    def get_model_id(self, model_name):
        return self.model_by_name[model_name]

    def get_deck_id(self, deck_name):
        return self.deck_by_name[deck_name]

    def media_add_file(self, filename):
        self.added_media_file = filename
        return filename

    def undo_start(self):
        self.undo_started = True

    def undo_end(self, undo_id):
        self.undo_finished = True

    def update_note(self, note):
        # even though we don't call note.flush anymore, some of the tests expect this
        note.flush()

    def run_in_background(self, task_fn, task_done_fn):
        # just run the two tasks immediately
        result = task_fn()
        task_done_fn(MockFuture(result))

    def run_on_main(self, task_fn):
        # just run the task immediately
        task_fn()

    def wire_typing_timer(self, text_input, text_input_changed):
        # just fire the text_input_changed callback immediately, there won't be any typing
        text_input.textChanged.connect(text_input_changed)
        return None

    def call_on_timer_expire(self, timer_obj, task):
        # just call the task for now
        task()

    def info_message(self, message, parent):
        logging.info(f'info message: {message}')
        self.info_message_received = message

    def critical_message(self, message, parent):
        logging.info(f'critical error message: {message}')
        self.critical_message_received = message

    def play_sound(self, filename):
        logging.info('play_sound')
        # load the json inside the file
        with open(filename) as json_file:
            self.played_sound = json.load(json_file)

    def show_progress_bar(self, message):
        self.show_progress_bar_called = True

    def stop_progress_bar(self):
        self.stop_progress_bar_called = True

    def editor_set_field_value(self, editor, field_index, text):
        self.editor_set_field_value_calls.append({
            'field_index': field_index,
            'text': text
        })

    def show_loading_indicator(self, editor, field_index):
        self.show_loading_indicator_called = True

    def hide_loading_indicator(self, editor, field_index, original_field_value):
        self.hide_loading_indicator_called = True

    def ask_user(self, message, parent):
        return True

    def checkpoint(self, action_str):
        self.checkpoint_name = action_str

    def reset_exceptions(self):
        self.last_exception = None
        self.last_action = None

    def report_known_exception_interactive(self, exception, action):
        self.last_exception = exception
        self.last_action = action

    def report_unknown_exception_interactive(self, exception, action):
        self.last_exception = exception
        self.last_action = action
        logging.critical(exception, exc_info=True)

    def report_unknown_exception_background(self, exception):
        self.last_exception = exception
        logging.critical(exception, exc_info=True)

    def extract_sound_tag_audio_full_path(self, sound_tag):
        filename = re.match('.*\[sound:([^\]]+)\]', sound_tag).groups()[0]
        return os.path.join(self.get_user_files_dir(), filename)

    def extract_mock_tts_audio(self, full_path):
        file_content = open(full_path, 'r').read()
        return json.loads(file_content)

class MockServiceManager():
    def __init__(self):
        pass

    def get_tts_audio(self, source_text, voice):
        if voice['voice_key']['name'] == 'notfound':
            # simulate audio not found
            raise errors.AudioNotFoundError(source_text, voice)
        self.requested_audio = {
            'source_text': source_text,
            'voice': voice
        }
        encoded_dict = json.dumps(self.requested_audio, indent=2).encode('utf-8')
        return encoded_dict    




class MockCloudLanguageTools():
    def __init__(self):
        self.verify_api_key_called = False
        self.verify_api_key_input = None
        self.verify_api_key_is_valid = True

        self.account_info_called = False

        # used to simulate translation errors
        self.translation_error_map = {}

        # unhandled exceptions
        self.translation_unhandled_exception_map = {}

        self.language_data = {
            'language_list': {
                'en': 'English',
                'zh_cn': 'Chinese',
                'mg': 'Malagasy'
            },
            'translation_options': [
                {
                    'service': "Azure",
                    'language_code': "en",
                    'language_name': "English",
                    'language_id': "en"
                },
                {
                    'service': "Azure",
                    'language_code': "zh_cn",
                    'language_name': "Chinese",
                    'language_id': "zh-hans"
                },            
            ],
            'transliteration_options': [
                {
                    'language_code': 'zh_cn',
                    'transliteration_name': 'pinyin1',
                    'transliteration_key': {'name': 'pinyin1'}
                },
                {
                    'language_code': 'zh_cn',
                    'transliteration_name': 'pinyin2',
                    'transliteration_key': {'name': 'pinyin2'}
                },                
            ],
            'voice_list': [
                {
                    "audio_language_code": "en_US",
                    "audio_language_name": "English (US)",
                    "gender": "Male",
                    "language_code": "en",
                    "options": {
                        "pitch": {
                            "default": 0,
                            "max": 100,
                            "min": -100,
                            "type": "number"
                        },
                        "rate": {
                            "default": 1.0,
                            "max": 3.0,
                            "min": 0.5,
                            "type": "number"
                        }
                    },
                    "service": "Azure",
                    "voice_description": "English (US), Male, Guy (Neural), Azure",
                    "voice_key": {
                        "name": "Microsoft Server Speech Text to Speech Voice (en-US, GuyNeural)"
                    }
                },            
                {
                    "audio_language_code": "en_US",
                    "audio_language_name": "English (US)",
                    "gender": "Female",
                    "language_code": "en",
                    "options": {
                        "pitch": {
                            "default": 0,
                            "max": 100,
                            "min": -100,
                            "type": "number"
                        },
                        "rate": {
                            "default": 1.0,
                            "max": 3.0,
                            "min": 0.5,
                            "type": "number"
                        }
                    },
                    "service": "Azure",
                    "voice_description": "English (US), Female, Aria (Neural), Azure",
                    "voice_key": {
                        "name": "Microsoft Server Speech Text to Speech Voice (en-US, AriaNeural)"
                    }
                },
                {
                    "audio_language_code": "zh_CN",
                    "audio_language_name": "Chinese (Mandarin, Simplified)",
                    "gender": "Female",
                    "language_code": "zh_cn",
                    "options": {
                        "pitch": {
                            "default": 0,
                            "max": 100,
                            "min": -100,
                            "type": "number"
                        },
                        "rate": {
                            "default": 1.0,
                            "max": 3.0,
                            "min": 0.5,
                            "type": "number"
                        }
                    },
                    "service": "Azure",
                    "voice_description": "Chinese (Mandarin, Simplified), Female, Xiaoxiao 晓晓 (Neural), Azure",
                    "voice_key": {
                        "name": "Microsoft Server Speech Text to Speech Voice (zh-CN, XiaoxiaoNeural)"
                    }
                },
                {
                    "audio_language_code": "zh_CN",
                    "audio_language_name": "Chinese (Mandarin, Simplified)",
                    "gender": "Male",
                    "language_code": "zh_cn",
                    "options": {
                        "pitch": {
                            "default": 0,
                            "max": 100,
                            "min": -100,
                            "type": "number"
                        },
                        "rate": {
                            "default": 1.0,
                            "max": 3.0,
                            "min": 0.5,
                            "type": "number"
                        }
                    },
                    "service": "Azure",
                    "voice_description": "Chinese (Mandarin, Simplified), Male, Yunyang 云扬 (Neural), Azure",
                    "voice_key": {
                        "name": "Microsoft Server Speech Text to Speech Voice (zh-CN, YunyangNeural)"
                    }
                }
            ],
            'tokenization_options': [
                {
                    "language_code": "zh_cn",
                    "language_name": "Chinese (Simplified)",
                    "service": "Spacy",
                    "tokenization_key": {
                        "model_name": "chinese_char"
                    },
                    "tokenization_name": "Chinese (Simplified) (Characters) Spacy"
                },
                {
                    "language_code": "zh_cn",
                    "language_name": "Chinese (Simplified)",
                    "service": "Spacy",
                    "tokenization_key": {
                        "model_name": "chinese_jieba"
                    },
                    "tokenization_name": "Chinese (Simplified) (Jieba (words)) Spacy"
                }                
            ]
        }

        self.language_list = self.language_data['language_list']
        self.translation_language_list = self.language_data['translation_options']
        self.transliteration_language_list = self.language_data['transliteration_options']
        self.voice_list = self.language_data['voice_list']

    def get_language_data(self):
        return self.language_data

    def get_language_list(self):
        return self.language_list

    def get_translation_language_list(self):
        return self.translation_language_list

    def get_transliteration_language_list(self):
        return self.transliteration_language_list

    def get_tts_voice_list(self, api_key):
        return self.voice_list

    def api_key_validate_query(self, api_key):

        self.verify_api_key_called = True
        self.verify_api_key_input = api_key

        return {
            'key_valid': self.verify_api_key_is_valid,
            'msg': f'api key: {self.verify_api_key_is_valid}'
        }     

    def account_info(self, api_key):
        self.account_info_called = True
        self.account_info_api_key = api_key

        return {
            'type': '250 chars',
            'email': 'no@spam.com'
        }


    def language_detection(self, api_key, field_sample):
        return self.language_detection_result[field_sample[0]]

    def get_tts_audio(self, api_key, source_text, service, language_code, voice_key, options):
        self.requested_audio = {
            'text': source_text,
            'service': service,
            'language_code': language_code,
            'voice_key': voice_key,
            'options': options
        }
        encoded_dict = json.dumps(self.requested_audio, indent=2).encode('utf-8')
        return encoded_dict

    def get_translation_all(self, api_key, source_text, from_language, to_language):
        if source_text in self.translation_unhandled_exception_map:
            raise Exception(self.translation_unhandled_exception_map[source_text])
        return self.translate_all_result[source_text]

    def get_translation(self, api_key, source_text, translation_option):
        if source_text in self.translation_error_map:
            return MockTranslationResponse(400, {'error': self.translation_error_map[source_text]})
        translated_text = self.translation_map[source_text]
        return MockTranslationResponse(200, {'translated_text': translated_text})

    def get_transliteration(self, api_key, source_text, transliteration_option):
        # if needed, error simulation can be added here
        transliterated_text = self.transliteration_map[source_text]
        return MockTranslationResponse(200, {'transliterated_text': transliterated_text})

    def get_breakdown(self, api_key, source_text, tokenization_option, translation_option, transliteration_option):
        breakdown_response = self.breakdown_map[source_text]
        return MockBreakdownResponse(200, {'breakdown': breakdown_response})

class MockCard():
    def __init__(self, deck_id):
        self.did = deck_id

class MockNote():
    def __init__(self, note_id, model_id, field_dict, field_array):
        self.id = note_id
        self.mid = model_id
        self.field_dict = field_dict
        self.fields = field_array
        self.set_values = {}
        self.flush_called = False
    
    def __contains__(self, key):
        return key in self.field_dict

    def __getitem__(self, key):
        return self.field_dict[key]

    def __setitem__(self, key, value):
        self.set_values[key] = value

    def keys(self):
        return self.field_dict.keys()

    def flush(self):
        self.flush_called = True


class MockEditor():
    def __init__(self):
        self.addMode = False

class TestConfigGenerator():
    def __init__(self):
        self.deck_id = 42001
        self.model_id = 43001

        self.model_id_german = 50001

        self.model_name = 'note-type'
        self.deck_name = 'deck 1'
        self.field_chinese = 'Chinese'
        self.field_english = 'English'
        self.field_sound = 'Sound'
        self.field_pinyin = 'Pinyin'
        self.field_german_article = 'Article'
        self.field_german_word = 'Word'
        
        self.note_id_1 = 42005
        self.note_id_2 = 43005
        self.note_id_3 = 44005 # empty chinese note
        self.note_id_4 = 45005

        # german notes
        self.note_id_german_1 = 51001
        self.note_id_german_2 = 51002

        self.all_fields = [self.field_chinese, self.field_english, self.field_sound, self.field_pinyin]
        self.all_fields_german = [self.field_german_article, self.field_german_word, self.field_english, self.field_sound]

        self.notes_by_id = {
            self.note_id_1: MockNote(self.note_id_1, self.model_id,{
                self.field_chinese: '老人家',
                self.field_english: 'old people',
                self.field_sound: '',
                self.field_pinyin: ''
            }, self.all_fields),
            self.note_id_2: MockNote(self.note_id_2, self.model_id, {
                self.field_chinese: '你好',
                self.field_english: 'hello',
                self.field_sound: '',
                self.field_pinyin: ''
            }, self.all_fields),
            self.note_id_3: MockNote(self.note_id_3, self.model_id, {
                self.field_chinese: '',
                self.field_english: 'empty',
                self.field_sound: '',
                self.field_pinyin: ''
            }, self.all_fields),
            self.note_id_4: MockNote(self.note_id_4, self.model_id, {
                self.field_chinese: '赚钱',
                self.field_english: 'To earn money',
                self.field_sound: '[sound:blabla.mp3]',
                self.field_pinyin: ''
            }, self.all_fields),
            # german notes
            self.note_id_german_1: MockNote(self.note_id_german_1, self.model_id_german, {
                self.field_german_article: 'Das',
                self.field_german_word: 'Hund',
                self.field_english: "The Dog",
                self.field_sound: ''
            }, self.all_fields_german)
        }        

        self.chinese_voice_key = 'chinese voice'
        self.chinese_voice_description = 'this is a chinese voice'

    # different languagetools configs available
    # =========================================

    def get_default_config(self):
        hypertts_config = {
        }
        return hypertts_config

    def get_config_batch_audio(self):
        base_config = self.get_default_config()
        base_config[constants.CONFIG_BATCH_AUDIO] = {
            self.model_name: {
                self.deck_name: {
                   self.field_sound: self.field_chinese
                }
            }
        }
        return base_config

    def get_config_text_replacement(self):
        base_config = self.get_default_config()    
        base_config[constants.CONFIG_TEXT_PROCESSING] = {
            'replacements': [
                {'pattern': r'etw', 
                'replace': 'etwas',
                'Audio': True,
                'Translation': True,
                'Transliteration': True},
            ]
        }
        return base_config

    def get_addon_config(self, scenario):

        fn_map = {
            'default': self.get_default_config,
            'text_replacement': self.get_config_text_replacement
        }

        fn_instance = fn_map[scenario]
        return fn_instance()


    def get_model_map(self):
        return {
            self.model_id: {
                'name': self.model_name,
                'flds': [
                    {'name': self.field_chinese},
                    {'name': self.field_english},
                    {'name': self.field_sound},
                    {'name': self.field_pinyin}
                ]
            }
        }
    
    def get_deck_map(self):
        return {
            self.deck_id: {
                'name': self.deck_name
            }
        }

    def get_deck_by_name(self):
        return {
            self.deck_name: self.deck_id
        }

    def get_model_by_name(self):
        return {
            self.model_name: self.model_id
        }

    def get_deckid_modelid_pairs(self):
        return [
            [self.deck_id, self.model_id]
        ]        

    def get_note_id_list(self):
        notes_by_id, notes = self.get_notes()
        return list(notes_by_id.keys())

    def get_notes(self):
        notes = {
            self.deck_id: {
                self.model_id: self.notes_by_id
            }
        }
        return self.notes_by_id, notes

    def get_mock_editor_with_note(self, note_id):
        editor = MockEditor()
        editor.card = MockCard(self.deck_id)
        field_array = []
        notes_by_id, notes = self.get_notes()
        note_data = notes_by_id[note_id]        
        for field_entry in self.get_model_map()[self.model_id]['flds']:
            field_name = field_entry['name']
            field_array.append(note_data[field_name])
        editor.note = MockNote(note_id, self.model_id, note_data, field_array)
        return editor


    def build_hypertts_instance(self, scenario):
        addon_config = self.get_addon_config(scenario)

        anki_utils = MockAnkiUtils(addon_config)
        service_manager = MockServiceManager()
        mock_hypertts = hypertts.HyperTTS(anki_utils, service_manager)

        anki_utils.models = self.get_model_map()
        anki_utils.decks = self.get_deck_map()
        anki_utils.model_by_name = self.get_model_by_name()
        anki_utils.deck_by_name = self.get_deck_by_name()
        anki_utils.deckid_modelid_pairs = self.get_deckid_modelid_pairs()
        anki_utils.notes_by_id, anki_utils.notes = self.get_notes()

        return mock_hypertts

    def build_hypertts_instance_test_servicemanager(self, scenario):
        addon_config = self.get_addon_config(scenario)

        anki_utils = MockAnkiUtils(addon_config)
        manager = servicemanager.ServiceManager(get_test_services_dir(), 'test_services')
        manager.init_services()
        manager.get_service('ServiceA').set_enabled(True)
        manager.get_service('ServiceB').set_enabled(True)

        mock_hypertts = hypertts.HyperTTS(anki_utils, manager)

        anki_utils.models = self.get_model_map()
        anki_utils.decks = self.get_deck_map()
        anki_utils.model_by_name = self.get_model_by_name()
        anki_utils.deck_by_name = self.get_deck_by_name()
        anki_utils.deckid_modelid_pairs = self.get_deckid_modelid_pairs()
        anki_utils.notes_by_id, anki_utils.notes = self.get_notes()

        return mock_hypertts

