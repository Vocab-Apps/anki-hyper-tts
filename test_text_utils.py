import text_utils
import errors
import constants
import unittest
import config_models

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
    assert text_utils.process_text('<b>unter</b> (etw +D)', text_processing) == 'unter etwas +Dativ'


def test_replacement_regexp_error(qtbot):
    
    # regex replacement with error
    text_processing = config_models.TextProcessing()
    rule = config_models.TextReplacementRule(constants.TextReplacementRuleType.Regex)
    rule.source = 'yoyo)'
    rule.target = 'rep'
    text_processing.add_text_replacement_rule(rule)

    testcase_instance = unittest.TestCase()
    testcase_instance.assertRaises(errors.TextReplacementError, text_utils.process_text, 'yoyo', text_processing)