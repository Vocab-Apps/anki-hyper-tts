import json
import tempfile
import re
import os
import sys
import datetime

import constants
import hypertts
import errors
import servicemanager
import config_models

logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_base)
logger = logging_utils.get_test_child_logger(__name__)

def get_test_services_dir():
    current_script_path = os.path.realpath(__file__)
    current_script_dir = os.path.dirname(current_script_path)    
    return os.path.join(current_script_dir, 'test_services')

def create_simple_batch(hypertts_instance, 
        preset_id='uuid_0', 
        name='my preset 1', 
        save_preset=True, 
        voice_name='voice_a_1',
        target_field='Sound',
        use_selection=False):
    """create simple batch config and optionally save"""
    voice_list = hypertts_instance.service_manager.full_voice_list()
    selected_voice = [x for x in voice_list if x.name == voice_name][0]
    single = config_models.VoiceSelectionSingle()
    single.set_voice(config_models.VoiceWithOptions(selected_voice, {}))

    batch = config_models.BatchConfig(hypertts_instance.anki_utils)
    source = config_models.BatchSource(mode=constants.BatchMode.simple, source_field='Chinese', use_selection=use_selection)
    target = config_models.BatchTarget(target_field, False, True)
    text_processing = config_models.TextProcessing()

    batch.set_source(source)
    batch.set_target(target)
    batch.set_voice_selection(single)
    batch.set_text_processing(text_processing)
    batch.name = name
    batch.uuid = preset_id

    if save_preset:
        hypertts_instance.save_preset(batch)

    return batch    


class MockFuture():
    def __init__(self, result_data):
        self.result_data = result_data

    def result(self):
        return self.result_data

class MockFutureException():
    def __init__(self, exception_value):
        self.exception_value = exception_value

    def result(self):
        # raise stored exception
        raise self.exception_value

class MockWebView():
    def __init__(self):
        self.selected_text = ''

    def selectedText(self):
        return self.selected_text


class MockDeckChooser():
    def __init__(self):
        self.deck_id = None

    def selectedId(self):
        return self.deck_id

class MockAddCards():
    def __init__(self):
        self.deckChooser = MockDeckChooser()

class MockEditor():
    def __init__(self):
        self.set_note_called = None
        self.addMode = False
        self.web = MockWebView()
        self.parentWindow = MockAddCards()

    def set_note(self, note):
        self.set_note_called = True

class MockCollection():
    def __init__(self):
        pass

    def update_note(self, note):
        pass

class MockAnkiUtils():
    def __init__(self, config):
        self.config = config
        self.written_config = None
        self.updated_note_model = None        
        self.editor_set_field_value_calls = []
        self.added_media_file = None
        self.show_loading_indicator_called = None
        self.hide_loading_indicator_called = None
        self.tooltip_messages = []
        self.mock_collection = MockCollection()

        # sounds
        self.all_played_sounds = []

        # undo handling
        self.undo_started = False
        self.undo_finished = False

        # user_files dir
        self.user_files_dir_tempdir = tempfile.TemporaryDirectory(prefix='hypertts_testing_user_files_')
        self.user_files_dir = self.user_files_dir_tempdir.name
        logger.info(f'created userfiles temp dir: {self.user_files_dir}')

        # exception handling
        self.last_exception = None
        self.last_action = None

        # uuid generation
        self.uuid_current_num = 0

        # responses for dialogs
        self.ask_user_bool_response = True
        self.ask_user_get_text_response = None
        self.ask_user_choose_from_list_response = None
        self.ask_user_choose_from_list_response_string = None

        # time
        self.current_time = datetime.datetime.now()

        # dialogs
        self.dialog_input_fn_map = {}

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

    def get_note_type_name(self, model_id: int) -> str:
        return self.get_model(model_id)['name']

    def get_deck(self, deck_id):
        return self.decks[deck_id]

    def get_deck_name(self, deck_id: int) -> str:
        return self.get_deck(deck_id)['name']

    def get_model_id(self, model_name):
        return self.model_by_name[model_name]

    def get_deck_id(self, deck_name):
        return self.deck_by_name[deck_name]

    def media_add_file(self, filename):
        self.added_media_file = filename
        return filename

    def undo_start(self):
        self.undo_started = True

    def undo_tts_tag_start(self):
        self.undo_started = True

    def undo_end(self, undo_id):
        self.undo_finished = True

    def update_note(self, note):
        # even though we don't call note.flush anymore, some of the tests expect this
        note.flush()

    def create_card_from_note(self, note, card_ord, model, template):
        return MockCard(0, note, card_ord, model, template)

    def extract_tts_tags(self, av_tags):
        return av_tags

    def save_note_type_update(self, note_model):
        logger.info('save_note_type_update')
        self.updated_note_model = note_model

    def run_in_background_collection_op(self, parent_widget, update_fn, success_fn):
        # just run update_fn
        self.undo_started = True
        update_fn(None)
        self.undo_finished = True
        success_fn(True)

    def get_anki_collection(self):
        return self.mock_collection

    def run_in_background(self, task_fn, task_done_fn):
        # just run the two tasks immediately
        try:
            result = task_fn()
            task_done_fn(MockFuture(result))
        except Exception as e:
            task_done_fn(MockFutureException(e))
        

    def run_on_main(self, task_fn):
        # just run the task immediately
        task_fn()

    def wire_typing_timer(self, text_input, text_input_changed):
        # just fire the text_input_changed callback immediately, there won't be any typing
        text_input.textChanged.connect(lambda: text_input_changed())
        return None

    def call_on_timer_expire(self, timer_obj, task):
        # just call the task for now
        task()

    def info_message(self, message, parent):
        logger.info(f'info message: {message}')
        self.info_message_received = message

    def critical_message(self, message, parent):
        logger.info(f'critical error message: {message}')
        self.critical_message_received = message

    def tooltip_message(self, message):
        self.tooltip_messages.append(message)

    def play_sound(self, filename):
        logger.info('play_sound')
        # load the json inside the file
        with open(filename) as json_file:
            self.played_sound = json.load(json_file)
            # keep records of all sounds played
            self.all_played_sounds.append(self.played_sound)

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
        # assume true
        return self.ask_user_bool_response

    def ask_user_get_text(self, message, parent, default, title):
        return self.ask_user_get_text_response, 1

    def ask_user_choose_from_list(self, parent, prompt: str, choices: list[str], startrow: int = 0) -> int:
        if self.ask_user_choose_from_list_response_string != None:
            # we need to look for the index of that string inside choices
            chosen_row = choices.index(self.ask_user_choose_from_list_response_string)
            return chosen_row, 1
        return self.ask_user_choose_from_list_response, 1

    def reset_exceptions(self):
        self.last_exception = None
        self.last_action = None
        self.last_exception_dialog_type = None

    def report_known_exception_interactive_dialog(self, exception, action):
        self.last_exception = exception
        self.last_action = action
        self.last_exception_dialog_type = 'dialog'
        logger.error(f'during {action}: {str(exception)}')

    def report_known_exception_interactive_tooltip(self, exception, action):
        self.last_exception = exception
        self.last_action = action
        self.last_exception_dialog_type = 'tooltip'
        logger.error(f'during {action}: {str(exception)}')        

    def report_unknown_exception_interactive(self, exception, action):
        self.last_exception = exception
        self.last_action = action
        logger.critical(exception, exc_info=True)

    def report_unknown_exception_background(self, exception):
        self.last_exception = exception
        logger.critical(exception, exc_info=True)

    def extract_sound_tag_audio_full_path(self, sound_tag):
        filename = re.match('.*\[sound:([^\]]+)\]', sound_tag).groups()[0]
        return os.path.join(self.get_user_files_dir(), filename)

    def extract_mock_tts_audio(self, full_path):
        file_content = open(full_path, 'r').read()
        return json.loads(file_content)

    def get_current_time(self):
        return self.current_time

    def tick_time(self):
        self.current_time = self.current_time + datetime.timedelta(seconds=1)

    def get_uuid(self):
        result = f'uuid_{self.uuid_current_num}'
        logger.debug(f'generating uuid: {result}')
        self.uuid_current_num += 1
        return result

    def wait_for_dialog_input(self, dialog, dialog_id):
        self.dialog_input_fn_map[dialog_id](dialog)

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

    def configure(self, config):
        self.config = config

    def account_info(self, api_key) -> config_models.HyperTTSProAccountConfig:
        logger.debug(f'account_info called with api_key: {api_key}')
        
        self.account_info_called = True
        self.account_info_api_key = api_key

        if api_key == 'exception_key':
            raise Exception('exception_key')


        if api_key == 'valid_key':
            return config_models.HyperTTSProAccountConfig(
                api_key = api_key,
                api_key_valid = True,
                use_vocabai_api = False,
                account_info = {
                'type': '250 chars',
                'email': 'no@spam.com',
                'update_url': 'https://www.vocab.ai/awesometts-plus',
                'cancel_url': 'https://www.vocab.ai/awesometts-plus'
            })

        if api_key == 'trial_key':
            return config_models.HyperTTSProAccountConfig(
                api_key = api_key,
                api_key_valid = True,
                use_vocabai_api = False,
                account_info = {
                'type': 'trial',
                'email': 'no@spam.com'
            })            

        return config_models.HyperTTSProAccountConfig(
            api_key = api_key,
            api_key_valid = False,
            use_vocabai_api = False,
            api_key_error = 'Key invalid')


    def request_trial_key(self, email):
        self.request_trial_key_called = True
        self.request_trial_key_email = email

        if email == 'valid@email.com':
            return {
                'api_key': 'trial_key'
            }

        return {
            'error': 'invalid email'
        }


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


class MockCard():
    def __init__(self, deck_id, note, card_ord, model, template):
        self.did = deck_id
        self.note = note
        self.ord = card_ord
        self.model = model
        self.template = template

    def extract_tts_tags(self, template_format):
        template_format = template_format.replace('\n', ' ')
        m = re.match('.*{{tts.*voices=HyperTTS:(.*)}}.*', template_format)
        if m == None:
            logger.error(f'could not a TTS tag in template: [{template_format}]')
            return []
        field_name = m.groups()[0]
        return [MockTTSTag(self.note[field_name])]

    def question_av_tags(self):
        template_format = self.template['qfmt']
        return self.extract_tts_tags(template_format)

    def answer_av_tags(self):
        template_format = self.template['afmt']
        return self.extract_tts_tags(template_format)

class MockTTSTag():
    def __init__(self, field_text):
        self.field_text = field_text

class MockNote():
    def __init__(self, note_id, model_id, field_dict, field_array, model):
        self.id = note_id
        self.mid = model_id
        self.field_dict = field_dict
        self.fields = field_array
        self.model = model
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

    def note_type(self):
        return self.model

    def flush(self):
        self.flush_called = True

class TestConfigGenerator():
    def __init__(self):
        self.deck_id = 42001
        self.model_id_chinese = 43001

        self.model_id_german = 50001

        self.model_name_chinese = 'Chinese Words'
        self.deck_name = 'deck 1'
        self.field_chinese = 'Chinese'
        self.field_english = 'English'
        self.field_sound = 'Sound'
        self.field_sound_english = 'Sound English'
        self.field_pinyin = 'Pinyin'
        self.field_german_article = 'Article'
        self.field_german_word = 'Word'
        
        self.note_id_1 = 42005
        self.note_id_2 = 43005
        self.note_id_3 = 44005 # empty chinese note
        self.note_id_4 = 45005
        self.note_id_5 = 46005

        # german notes
        self.note_id_german_1 = 51001
        self.note_id_german_2 = 51002

        self.all_fields = [self.field_chinese, self.field_english, self.field_sound, self.field_pinyin, self.field_sound_english]
        self.all_fields_german = [self.field_german_article, self.field_german_word, self.field_english, self.field_sound]

        self.model_chinese = {
            'name': self.model_name_chinese,
            'tmpls': [
                {
                    'qfmt': '{{English}}',
                    'afmt': '{{Chinese}} {{Pinyin}}'
                }
            ]
        }

        self.model_german = {
            'tmpls': [
                {
                    'qfmt': '{{English}}',
                    'afmt': '{{Article}} {{Word}}'
                }
            ]
        }        

        self.notes_by_id = {
            self.note_id_1: MockNote(self.note_id_1, self.model_id_chinese,{
                self.field_chinese: '老人家',
                self.field_english: 'old people',
                self.field_sound: '',
                self.field_sound_english: '',
                self.field_pinyin: ''
            }, self.all_fields, self.model_chinese),
            self.note_id_2: MockNote(self.note_id_2, self.model_id_chinese, {
                self.field_chinese: '你好',
                self.field_english: 'hello',
                self.field_sound: '',
                self.field_sound_english: '',
                self.field_pinyin: ''
            }, self.all_fields, self.model_chinese),
            self.note_id_3: MockNote(self.note_id_3, self.model_id_chinese, {
                self.field_chinese: '',
                self.field_english: 'empty',
                self.field_sound: '',
                self.field_sound_english: '',
                self.field_pinyin: ''
            }, self.all_fields, self.model_chinese),
            self.note_id_4: MockNote(self.note_id_4, self.model_id_chinese, {
                self.field_chinese: '赚钱',
                self.field_english: 'To earn money',
                self.field_sound: '[sound:blabla.mp3]',
                self.field_sound_english: '',
                self.field_pinyin: ''
            }, self.all_fields, self.model_chinese),
            self.note_id_5: MockNote(self.note_id_5, self.model_id_chinese, {
                self.field_chinese: '大使馆',
                self.field_english: 'embassy',
                self.field_sound: 'some content in sound field',
                self.field_sound_english: '',
                self.field_pinyin: ''
            }, self.all_fields, self.model_chinese),            
            # german notes
            self.note_id_german_1: MockNote(self.note_id_german_1, self.model_id_german, {
                self.field_german_article: 'Das',
                self.field_german_word: 'Hund',
                self.field_english: "The Dog",
                self.field_sound: ''
            }, self.all_fields_german, self.model_german)
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
            self.model_id_chinese: {
                'name': self.model_name_chinese,
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
            self.model_name_chinese: self.model_id_chinese
        }

    def get_deckid_modelid_pairs(self):
        return [
            [self.deck_id, self.model_id_chinese]
        ]        

    def get_note_id_list(self):
        notes_by_id, notes = self.get_notes()
        return list(notes_by_id.keys())

    def get_notes(self):
        notes = {
            self.deck_id: {
                self.model_id_chinese: self.notes_by_id
            }
        }
        return self.notes_by_id, notes

    def get_mock_editor_with_note(self, note_id: int, deck_id: int, add_mode: bool = False):
        editor = MockEditor()

        field_array = []
        notes_by_id, notes = self.get_notes()
        note_data = notes_by_id[note_id]        
        model_id = note_data.mid
        model = self.get_model_map()[model_id]
        for field_entry in model['flds']:
            field_name = field_entry['name']
            field_array.append(note_data[field_name])
        editor.note = MockNote(note_id, model_id, note_data, field_array, model)
        editor.card = MockCard(deck_id, editor.note, 0, model, '')

        if add_mode:
            editor.addMode = True
            editor.parentWindow.deckChooser.deck_id = deck_id

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
        manager = servicemanager.ServiceManager(get_test_services_dir(), 'test_services', True, MockCloudLanguageTools())
        manager.init_services()
        manager.get_service('ServiceA').enabled = True
        manager.get_service('ServiceB').enabled = True

        if 'HYPERTTS_SERVICE_FAKE_DELAY' in os.environ:
            delay_int = int(os.environ['HYPERTTS_SERVICE_FAKE_DELAY'])
            manager.get_service('ServiceA').configure({'delay': delay_int, 'api_key': 'valid_key'})

        mock_hypertts = hypertts.HyperTTS(anki_utils, manager)

        anki_utils.models = self.get_model_map()
        anki_utils.decks = self.get_deck_map()
        anki_utils.model_by_name = self.get_model_by_name()
        anki_utils.deck_by_name = self.get_deck_by_name()
        anki_utils.deckid_modelid_pairs = self.get_deckid_modelid_pairs()
        anki_utils.notes_by_id, anki_utils.notes = self.get_notes()

        return mock_hypertts

