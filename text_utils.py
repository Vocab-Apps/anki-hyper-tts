import sys
import logging
import aqt
import anki.utils
import re

if hasattr(sys, '_pytest_mode'):
    import constants
    import errors
else:
    from . import constants
    from . import errors


REGEXP_REALTIME_SIMPLE_TEMPLATE = '.*<hypertts-template\s+setting="(.*)"\s+version="(.*)">(.*)</hypertts-template>.*'
REGEXP_REALTIME_ADVANCED_TEMPLATE = '.*<hypertts-template-advanced\s+setting="(.*)"\s+version="(.*)">\n(.*)</hypertts-template-advanced>.*'

# convert characters which are problematic on SSML TTS APIs
SSML_CONVERSION_MAP ={
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '，': ',', # chinese comma 
}

def extract_template_regexp(input, regexp):
    match_result = re.match(regexp, input, re.DOTALL)
    if match_result == None:
        return None
    setting = match_result.group(1).strip()
    version_str = match_result.group(2).strip()
    version = constants.TemplateFormatVersion[version_str]
    content = match_result.group(3).strip()
    return setting, version, content

def extract_simple_template(input):
    return extract_template_regexp(input, REGEXP_REALTIME_SIMPLE_TEMPLATE)

def extract_advanced_template(input):
    return extract_template_regexp(input, REGEXP_REALTIME_ADVANCED_TEMPLATE)

def process_text_replacement(text, text_processing_model):
    for text_replacement_rule in text_processing_model.text_replacement_rules:
        text = process_text_replacement_rule(text, text_replacement_rule)    
    return text

def process_text_rules(text, text_processing_model):
    if text_processing_model.html_to_text_line:
        text = anki.utils.htmlToTextLine(text)
    if text_processing_model.ssml_convert_characters:
        for pattern, replace in SSML_CONVERSION_MAP.items():
            text = text.replace(pattern, replace)
    return text

def process_text(source_text, text_processing_model):
    if text_processing_model.run_replace_rules_after:
        # text replacement rules run after other text rules
        text = process_text_rules(source_text, text_processing_model)
        processed_text = process_text_replacement(text, text_processing_model)
    else:
        # text replacement rules run before other text rules, useful to process HTML
        text = process_text_replacement(source_text, text_processing_model)
        processed_text = process_text_rules(text, text_processing_model)
    return processed_text

def process_text_replacement_rule(input_text, rule):
    try:
        if rule.source == None:
            raise Exception('missing pattern in text replacement rule')
        if rule.target == None:
            raise Exception('missing replacement in text replacement rule')
        if rule.rule_type == constants.TextReplacementRuleType.Regex:
            result = re.sub(rule.source, rule.target, input_text)
        elif rule.rule_type == constants.TextReplacementRuleType.Simple:
            result = input_text.replace(rule.source,  rule.target)
        else:
            raise Exception(f'unsupported replacement rule type: {rule.rule_type}')
        return result
    except Exception as e:
        raise errors.TextReplacementError(input_text, rule.source, rule.target, str(e))
