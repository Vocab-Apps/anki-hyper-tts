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


    text_processing = config_models.TextProcessing()
    rule = config_models.TextReplacementRule(constants.TextReplacementRuleType.Regex)
    rule.source = None
    rule.target = None
    text_processing.add_text_replacement_rule(rule)

    testcase_instance = unittest.TestCase()
    testcase_instance.assertRaises(errors.TextReplacementError, text_utils.process_text, 'yoyo', text_processing)    

def test_process_text_rules(qtbot):
    # by default, html processing enabled
    text_processing = config_models.TextProcessing()
    assert text_utils.process_text('word1<br/>word2', text_processing) == 'word1word2'
    # disable html processing
    text_processing.html_to_text_line = False
    text_processing.ssml_convert_characters = False
    assert text_utils.process_text('word1<br/>word2', text_processing) == 'word1<br/>word2'

    # add a replacement rule which targets the HTML tag
    rule = config_models.TextReplacementRule(constants.TextReplacementRuleType.Simple)
    rule.source = '<br/>'
    rule.target = ' linebreak '
    text_processing.add_text_replacement_rule(rule)
    text_processing.html_to_text_line = True
    # the expected replacement is not done, because text replacement rules have run after HTML replacement
    assert text_utils.process_text('word1<br/>word2', text_processing) == 'word1word2'
    text_processing.run_replace_rules_after = False
    # now, our replacement rules will run first
    assert text_utils.process_text('word1<br/>word2', text_processing) == 'word1 linebreak word2'

    # SSML replacements
    text_processing = config_models.TextProcessing()
    text_processing.ssml_convert_characters = True
    assert text_utils.process_text('patients age < 30', text_processing) == 'patients age &lt; 30'
    text_processing.ssml_convert_characters = False
    assert text_utils.process_text('patients age < 30', text_processing) == 'patients age < 30'
