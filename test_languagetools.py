import json
import unittest
import errors
import testing_utils

class EmptyFieldConfigGenerator(testing_utils.TestConfigGenerator):
    def __init__(self):
        testing_utils.TestConfigGenerator.__init__(self)
        self.notes_by_id = {
            self.note_id_1: testing_utils.MockNote(self.note_id_1, self.model_id,{
                self.field_chinese: '', # empty
                self.field_english: 'old people',
                self.field_sound: ''
            }, self.all_fields),
            self.note_id_2: testing_utils.MockNote(self.note_id_2, self.model_id, {
                self.field_chinese: '你好',
                self.field_english: 'hello',
                self.field_sound: ''
            }, self.all_fields)
        }                

class DummyHtmlEmptyFieldConfigGenerator(testing_utils.TestConfigGenerator):
    def __init__(self):
        testing_utils.TestConfigGenerator.__init__(self)
        self.notes_by_id = {
            self.note_id_1: testing_utils.MockNote(self.note_id_1, self.model_id,{
                self.field_chinese: '&nbsp;', # empty
                self.field_english: 'old people',
                self.field_sound: ''
            }, self.all_fields),
            self.note_id_2: testing_utils.MockNote(self.note_id_2, self.model_id, {
                self.field_chinese: '你好',
                self.field_english: 'hello',
                self.field_sound: ''
            }, self.all_fields)
        }                        

def test_generate_audio_for_field(qtbot):
    
    # regular case
    # ============

    config_gen = testing_utils.TestConfigGenerator()
    mock_language_tools = config_gen.build_languagetools_instance('default')

    # common variables
    note_id = config_gen.note_id_1
    from_field = config_gen.field_chinese
    to_field = config_gen.field_sound

    voice_list = mock_language_tools.get_tts_voice_list()
    chinese_voices = [x for x in voice_list if x['language_code'] == 'zh_cn']
    voice = chinese_voices[0]

    result = mock_language_tools.generate_audio_for_field(note_id, from_field, to_field, voice)
    assert result == True

    # get the note
    note = config_gen.notes_by_id[config_gen.note_id_1]

    # make sure sound was added
    assert config_gen.field_sound in note.set_values
    assert 'sound:languagetools-' in note.set_values[config_gen.field_sound]
    assert note.flush_called == True

    assert mock_language_tools.anki_utils.added_media_file != None
    assert 'languagetools-' in mock_language_tools.anki_utils.added_media_file

    # empty field
    # ===========

    config_gen = EmptyFieldConfigGenerator()
    mock_language_tools = config_gen.build_languagetools_instance('default')

    result = mock_language_tools.generate_audio_for_field(note_id, from_field, to_field, voice)
    assert result == False    

    # get the note
    note = config_gen.notes_by_id[config_gen.note_id_1]

    # make sure no sound was added
    assert config_gen.field_sound not in note.set_values
    assert note.flush_called == False

    assert mock_language_tools.anki_utils.added_media_file == None

    # empty field but with html junk
    # ==============================

    config_gen = DummyHtmlEmptyFieldConfigGenerator()
    mock_language_tools = config_gen.build_languagetools_instance('default')

    result = mock_language_tools.generate_audio_for_field(note_id, from_field, to_field, voice)
    assert result == False    

    # get the note
    note = config_gen.notes_by_id[config_gen.note_id_1]

    # make sure no sound was added
    assert config_gen.field_sound not in note.set_values
    assert note.flush_called == False

    assert mock_language_tools.anki_utils.added_media_file == None    


def test_get_tts_audio(qtbot):
    # pytest test_languagetools.py -k test_get_tts_audio

    config_gen = testing_utils.TestConfigGenerator()
    mock_language_tools = config_gen.build_languagetools_instance('text_replacement')

    filename = mock_language_tools.get_tts_audio('unter etw', 'Azure', 'de_de', {'name': 'voice1'}, {})
    file_contents = open(filename, 'r').read()
    data = json.loads(file_contents)

    assert data['text'] == 'unter etwas' # after text replacement
    assert data['service'] == 'Azure'
    assert data['language_code'] == 'de_de'
    assert data['voice_key'] == {'name': 'voice1'}
    assert data['options'] == {}


def test_get_translation(qtbot):
    # pytest test_languagetools.py -k test_get_translation

    config_gen = testing_utils.TestConfigGenerator()
    mock_language_tools = config_gen.build_languagetools_instance('text_replacement')

    source_text = 'unter etw'
    mock_language_tools.cloud_language_tools.translation_map = {
        'unter etwas': 'under something'
    }

    translated_text = mock_language_tools.get_translation(source_text, {'translation_key': 'de to en'})
    assert translated_text == 'under something'

def test_get_transliteration(qtbot):
    # pytest test_languagetools.py -k test_get_transliteration

    config_gen = testing_utils.TestConfigGenerator()
    mock_language_tools = config_gen.build_languagetools_instance('text_replacement')

    source_text = 'unter etw'
    mock_language_tools.cloud_language_tools.transliteration_map = {
        'unter etwas': 'ˈʊntɐ ˈɛtvas'
    }

    transliterated_text = mock_language_tools.get_transliteration(source_text, {'transliteration_key': 'de to en'})
    assert transliterated_text == 'ˈʊntɐ ˈɛtvas'

def test_get_voice_for_field(qtbot):
    # pytest test_languagetools.py -k test_get_voice_for_field

    # valid voice
    # ===========

    config_gen = testing_utils.TestConfigGenerator()
    mock_language_tools = config_gen.build_languagetools_instance('batch_audio')

    dntf = config_gen.get_dntf_chinese()
    voice = mock_language_tools.get_voice_for_field(dntf)
    assert voice != None
    assert voice['voice_key'] == config_gen.chinese_voice_key

    # no language mapping
    # ===================
    config_gen = testing_utils.TestConfigGenerator()
    mock_language_tools = config_gen.build_languagetools_instance('no_language_mapping')

    dntf = config_gen.get_dntf_chinese()
    
    testcase_instance = unittest.TestCase()
    testcase_instance.assertRaises(errors.FieldLanguageMappingError, mock_language_tools.get_voice_for_field, dntf)