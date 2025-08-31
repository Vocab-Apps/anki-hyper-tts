import unittest

from hypertts_addon import text_utils
from hypertts_addon import errors
from hypertts_addon import constants
from hypertts_addon import config_models

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
    assert text_utils.process_text('M&A', text_processing) == 'M&amp;A'
    text_processing.ssml_convert_characters = False
    assert text_utils.process_text('patients age < 30', text_processing) == 'patients age < 30'


def test_regex_backref(qtbot):
    text_processing = config_models.TextProcessing()
    rule = config_models.TextReplacementRule(constants.TextReplacementRuleType.Regex)
    rule.source = '(.*)\s+\((.*)\)'
    rule.target = '\\2 \\1'
    text_processing.add_text_replacement_rule(rule)

    source_text = 'word1 (word2)'
    expected_result = 'word2 word1'
    assert text_utils.process_text(source_text, text_processing) == expected_result

def test_regex_ignore_case_default(qtbot):
    text_processing = config_models.TextProcessing()
    rule = config_models.TextReplacementRule(constants.TextReplacementRuleType.Regex)
    rule.source = 'abc'
    rule.target = 'def'
    text_processing.add_text_replacement_rule(rule)

    source_text = 'ABC123'
    expected_result = 'ABC123'
    assert text_utils.process_text(source_text, text_processing) == expected_result    

def test_regex_ignore_case(qtbot):
    text_processing = config_models.TextProcessing()
    text_processing.ignore_case = True
    rule = config_models.TextReplacementRule(constants.TextReplacementRuleType.Regex)
    rule.source = 'abc'
    rule.target = 'def'
    text_processing.add_text_replacement_rule(rule)

    source_text = 'ABC123'
    expected_result = 'def123'
    assert text_utils.process_text(source_text, text_processing) == expected_result    


def test_strip_brackets(qtbot):
    text_processing = config_models.TextProcessing()

    text_processing.strip_brackets = False
    assert text_utils.process_text('word1 (word2)', text_processing) == 'word1 (word2)'

    text_processing.strip_brackets = True
    text_processing.html_to_text_line = False
    assert text_utils.process_text('word1 (word2)', text_processing) == 'word1 '
    assert text_utils.process_text('word1 [word2]', text_processing) == 'word1 '
    assert text_utils.process_text('word1 [word2][word3]', text_processing) == 'word1 '
    assert text_utils.process_text('word1[word2]', text_processing) == 'word1'
    assert text_utils.process_text('word1 {word2}', text_processing) == 'word1 '
    assert text_utils.process_text('word1 <word2>', text_processing) == 'word1 '
    assert text_utils.process_text('word1 <word2>(word3)[word4]', text_processing) == 'word1 '
    assert text_utils.process_text('word1 (word2) word3 (word4)', text_processing) == 'word1  word3 '
    assert text_utils.process_text('word1 [word2] word3 [word4]', text_processing) == 'word1  word3 '
    assert text_utils.process_text('word1 {word2} word3 {word4}', text_processing) == 'word1  word3 '
    assert text_utils.process_text('word1 <word2> word3 <word4>', text_processing) == 'word1  word3 '


def test_strip_sound_tags(qtbot):
    """Test that sound tags are always stripped during text processing"""
    text_processing = config_models.TextProcessing()
    
    # Basic sound tag removal
    assert text_utils.process_text('Hello [sound:test.mp3]', text_processing) == 'Hello'
    assert text_utils.process_text('[sound:test.mp3] Hello', text_processing) == 'Hello'
    assert text_utils.process_text('Hello [sound:test.mp3] World', text_processing) == 'Hello  World'
    
    # Multiple sound tags
    assert text_utils.process_text('[sound:first.mp3] Hello [sound:second.mp3]', text_processing) == 'Hello'
    assert text_utils.process_text('Text [sound:a.mp3] with [sound:b.mp3] multiple [sound:c.mp3] tags', text_processing) == 'Text  with  multiple  tags'
    
    # Complex filename in sound tag
    assert text_utils.process_text('Test [sound:hypertts-4f299a66baeb457f5d7f8d5db347857d29cbe927cde694320c1c36c9.mp3]', text_processing) == 'Test'
    
    # Japanese text with sound tag (from the GitHub issue)
    japanese_text = 'ここで一旦、区切ります。 続けて説明します。 [sound:hypertts-4f299a66baeb457f5d7f8d5db347857d29cbe927cde694320c1c36c9.mp3]'
    expected_japanese = 'ここで一旦、区切ります。 続けて説明します。'
    assert text_utils.process_text(japanese_text, text_processing) == expected_japanese
    
    # Sound tags with different extensions
    assert text_utils.process_text('Audio [sound:file.ogg] formats', text_processing) == 'Audio  formats'
    assert text_utils.process_text('Audio [sound:file.wav] formats', text_processing) == 'Audio  formats'
    
    # Edge cases - malformed tags (should not be stripped)
    assert text_utils.process_text('[sound:missing_bracket', text_processing) == '[sound:missing_bracket'
    assert text_utils.process_text('sound:not_a_tag.mp3]', text_processing) == 'sound:not_a_tag.mp3]'
    assert text_utils.process_text('[sound missing colon]', text_processing) == '[sound missing colon]'
    
    # Sound tags are stripped even when other text processing is disabled
    text_processing.html_to_text_line = False
    text_processing.ssml_convert_characters = False
    assert text_utils.process_text('Hello [sound:test.mp3] <b>World</b>', text_processing) == 'Hello  <b>World</b>'
    
    # Sound tags with brackets processing enabled
    text_processing.strip_brackets = True
    # Note: strip_brackets removes (comment) and [bracket] and leaves spaces
    assert text_utils.process_text('Hello [sound:test.mp3] (comment)', text_processing) == 'Hello  '
    assert text_utils.process_text('Hello [bracket] [sound:test.mp3]', text_processing) == 'Hello '
    
    # Test with text replacement rules
    text_processing = config_models.TextProcessing()
    rule = config_models.TextReplacementRule(constants.TextReplacementRuleType.Simple)
    rule.source = 'Hello'
    rule.target = 'Hi'
    text_processing.add_text_replacement_rule(rule)
    
    # Sound tags should be stripped regardless of replacement rules
    assert text_utils.process_text('Hello [sound:test.mp3] World', text_processing) == 'Hi  World'
    
    # Test that strip_sound_tag is called as part of process_text_rules
    text_processing = config_models.TextProcessing()
    text_with_sound = 'Text [sound:audio.mp3] content'
    # Using process_text_rules directly
    processed = text_utils.process_text_rules(text_with_sound, text_processing)
    assert processed == 'Text  content'


def test_strip_sound_tag_function(qtbot):
    """Test the strip_sound_tag function directly"""
    # Basic cases
    assert text_utils.strip_sound_tag('[sound:test.mp3]') == ''
    assert text_utils.strip_sound_tag('Hello [sound:test.mp3]') == 'Hello'
    assert text_utils.strip_sound_tag('[sound:test.mp3] Hello') == 'Hello'
    assert text_utils.strip_sound_tag('Hello [sound:test.mp3] World') == 'Hello  World'
    
    # Multiple tags
    assert text_utils.strip_sound_tag('[sound:a.mp3][sound:b.mp3]') == ''
    assert text_utils.strip_sound_tag('A [sound:1.mp3] B [sound:2.mp3] C') == 'A  B  C'
    
    # Complex filenames
    assert text_utils.strip_sound_tag('[sound:file-with-dashes.mp3]') == ''
    assert text_utils.strip_sound_tag('[sound:file_with_underscores.mp3]') == ''
    assert text_utils.strip_sound_tag('[sound:file.with.dots.mp3]') == ''
    assert text_utils.strip_sound_tag('[sound:日本語.mp3]') == ''
    
    # Edge cases
    assert text_utils.strip_sound_tag('') == ''
    assert text_utils.strip_sound_tag('No sound tags here') == 'No sound tags here'
    assert text_utils.strip_sound_tag('[not a sound tag]') == '[not a sound tag]'
    assert text_utils.strip_sound_tag('[sound:] empty') == '[sound:] empty'  # Empty sound tag (malformed)