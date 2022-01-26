import text_utils
import errors
import constants
import unittest
import config_models

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

    assert utils.process('<b>hello</b> world') == 'hello world'
    assert utils.process('<span style="color: var(--field-fg); background: var(--field-bg);">&nbsp;gerund</span>') == 'gerund'

def test_replace(qtbot):
    utils = text_utils.TextUtils({'replacements': [
        {'pattern': ' / ', 
        'replace': ' '},
        {'pattern': r'\(etw \+D\)', 
        'replace': 'etwas +Dativ'},        
    ]})

    assert utils.process('word1 / word2') == 'word1 word2'
    assert utils.process('<b>word1</b> / word2') == 'word1 word2'
    assert utils.process('unter (etw +D)') == 'unter etwas +Dativ'
    assert utils.process('<b>unter</b> (etw +D)') == 'unter etwas +Dativ'


def test_replacement(qtbot):
    text_replacement = text_utils.TextReplacement({
        'pattern': ' / ', 
        'replace': ' '
    })
    
    assert text_replacement.process('word1 / word2') == 'word1 word2'

    actual_dict_data = text_replacement.to_dict()
    expected_dict_data = {
        'pattern': ' / ', 
        'replace': ' ',
        'replace_type': 'regex'
    }

    assert actual_dict_data == expected_dict_data

    # try to re-create from the dict
    text_replacement_2 = text_utils.TextReplacement(actual_dict_data)
    assert text_replacement_2.process('word1 / word2') == 'word1 word2'

    # malformed input
    text_replacement = text_utils.TextReplacement({
        'pattern': ' / '
    })
    assert text_replacement.process('word1') == 'word1'

def test_replacement_regexp_error(qtbot):
    text_replacement = text_utils.TextReplacement({
        'pattern': 'yoyo)', 
        'replace': 'rep'
    })

    testcase_instance = unittest.TestCase()
    testcase_instance.assertRaises(errors.TextReplacementError, text_replacement.process, 'yoyo')

def test_replacement_simple(qtbot):
    text_replacement = text_utils.TextReplacement({
        'pattern': 'yoyo)', 
        'replace': 'rep',
        'replace_type': 'simple'
    })
    
    assert text_replacement.process('yoyo') == 'yoyo'
    assert text_replacement.process('yoyo)') == 'rep'

    expected_dict = {
        'pattern': 'yoyo)', 
        'replace': 'rep',
        'replace_type': 'simple'
    }
    assert text_replacement.to_dict() == expected_dict

    text_replacement2 = text_utils.TextReplacement(expected_dict)
    assert text_replacement2.process('yoyo)') == 'rep'

def test_process_text(qtbot):

    # simple replacement
    text_processing = config_models.TextProcessing()
    rule = config_models.TextReplacementRule(constants.TextReplacementRuleType.Simple)
    rule.source = 'word_a'
    rule.target = 'word_b'
    text_processing.add_text_replacement_rule(rule)

    assert text_utils.process_text('sentence word_a word_c', text_processing) == 'sentence word_b word_c'

    # regex replacement
    rule = config_models.TextReplacementRule(constants.TextReplacementRuleType.Regex)
    rule.source = '\(etw \+D\)'
    rule.target = 'etwas +Dativ'
    text_processing.add_text_replacement_rule(rule)

    assert text_utils.process_text('unter (etw +D)', text_processing) == 'unter etwas +Dativ'
