import text_utils
import constants

def test_is_empty(qtbot):
    utils = text_utils.TextUtils({})

    assert utils.is_empty('yo') == False
    assert utils.is_empty('') == True
    assert utils.is_empty(' ') == True
    assert utils.is_empty('&nbsp;') == True
    assert utils.is_empty('&nbsp; ') == True
    assert utils.is_empty(' &nbsp; ') == True
    assert utils.is_empty('<br>') == True
    assert utils.is_empty('<div>\n</div>') == True

def test_process(qtbot):
    utils = text_utils.TextUtils({})

    assert utils.process('<b>hello</b> world', constants.TransformationType.Audio) == 'hello world'
    assert utils.process('<span style="color: var(--field-fg); background: var(--field-bg);">&nbsp;gerund</span>', constants.TransformationType.Audio) == 'gerund'

def test_replace(qtbot):
    utils = text_utils.TextUtils({'replacements': [
        {'pattern': ' / ', 
        'replace': ' ',
        'Audio': True,
        'Translation': False,
        'Transliteration': False},
        {'pattern': r'\(etw \+D\)', 
        'replace': 'etwas +Dativ',
        'Audio': True,
        'Translation': False,
        'Transliteration': False},        
    ]})

    assert utils.process('word1 / word2', constants.TransformationType.Audio) == 'word1 word2'
    assert utils.process('word1 / word2', constants.TransformationType.Translation) == 'word1 / word2'
    assert utils.process('word1 / word2', constants.TransformationType.Transliteration) == 'word1 / word2'
    assert utils.process('<b>word1</b> / word2', constants.TransformationType.Audio) == 'word1 word2'
    assert utils.process('unter (etw +D)', constants.TransformationType.Audio) == 'unter etwas +Dativ'
    assert utils.process('<b>unter</b> (etw +D)', constants.TransformationType.Audio) == 'unter etwas +Dativ'
    assert utils.process('<b>unter</b> (etw +D)', constants.TransformationType.Transliteration) == 'unter (etw +D)'


def test_replacement(qtbot):
    text_replacement = text_utils.TextReplacement({
        'pattern': ' / ', 
        'replace': ' ',
        'Audio': True,
        'Translation': False,
        'Transliteration': False        
    })
    
    assert text_replacement.process('word1 / word2', constants.TransformationType.Audio) == 'word1 word2'
    assert text_replacement.process('word1 / word2', constants.TransformationType.Transliteration) == 'word1 / word2'
    assert text_replacement.process('word1 / word2', constants.TransformationType.Translation) == 'word1 / word2'

    actual_dict_data = text_replacement.to_dict()
    expected_dict_data = {
        'pattern': ' / ', 
        'replace': ' ',
        'replace_type': 'regex',
        'Audio': True,
        'Translation': False,
        'Transliteration': False
    }

    assert actual_dict_data == expected_dict_data

    # try to re-create from the dict
    text_replacement_2 = text_utils.TextReplacement(actual_dict_data)
    assert text_replacement_2.process('word1 / word2', constants.TransformationType.Audio) == 'word1 word2'
    assert text_replacement_2.process('word1 / word2', constants.TransformationType.Transliteration) == 'word1 / word2'
    assert text_replacement_2.process('word1 / word2', constants.TransformationType.Translation) == 'word1 / word2'    

    # malformed input
    text_replacement = text_utils.TextReplacement({
        'pattern': ' / ', 
        'Audio': True,
        'Translation': False,
        'Transliteration': False        
    })
    assert text_replacement.process('word1', constants.TransformationType.Audio) == 'word1'

def test_replacement_regexp_error(qtbot):
    text_replacement = text_utils.TextReplacement({
        'pattern': 'yoyo)', 
        'replace': 'rep',
        'Audio': True,
        'Translation': True,
        'Transliteration': True
    })
    
    assert text_replacement.process('yoyo', constants.TransformationType.Audio) == 'yoyo'


def test_replacement_simple(qtbot):
    text_replacement = text_utils.TextReplacement({
        'pattern': 'yoyo)', 
        'replace': 'rep',
        'replace_type': 'simple',
        'Audio': True,
        'Translation': True,
        'Transliteration': True
    })
    
    assert text_replacement.process('yoyo', constants.TransformationType.Audio) == 'yoyo'
    assert text_replacement.process('yoyo)', constants.TransformationType.Audio) == 'rep'

    expected_dict = {
        'pattern': 'yoyo)', 
        'replace': 'rep',
        'replace_type': 'simple',
        'Audio': True,
        'Translation': True,
        'Transliteration': True        
    }
    assert text_replacement.to_dict() == expected_dict

    text_replacement2 = text_utils.TextReplacement(expected_dict)
    assert text_replacement2.process('yoyo)', constants.TransformationType.Audio) == 'rep'