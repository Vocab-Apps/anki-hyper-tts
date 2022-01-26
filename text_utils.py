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


def process_text(source_text, text_processing_model):
    processed_text = anki.utils.htmlToTextLine(source_text)
    for text_replacement_rule in text_processing_model.text_replacement_rules:
        processed_text = process_text_replacement_rule(processed_text, text_replacement_rule)
    return processed_text

def process_text_replacement_rule(input_text, rule):
    if rule.rule_type == constants.TextReplacementRuleType.Regex:
        result = re.sub(rule.source, rule.target, input_text)
    elif rule.rule_type == constants.TextReplacementRuleType.Simple:
        result = input_text.replace(rule.source,  rule.target)
    return result

def create_text_replacement():
    return TextReplacement({
        'pattern': None,
        'replace': None,
        'replace_type': constants.ReplaceType.simple.name
    })


class TextReplacement():
    def __init__(self, options):
        self.pattern = options.get('pattern', None)
        self.replace = options.get('replace', None)
        replace_type_str = options.get('replace_type', constants.ReplaceType.regex.name)
        self.replace_type = constants.ReplaceType[replace_type_str]

    def to_dict(self):
        data = {
            'pattern': self.pattern,
            'replace': self.replace,
            'replace_type': self.replace_type.name
        }
        return data

    def process(self, text):
        result = text
        if self.pattern != None and self.replace != None:
            try:
                if self.replace_type == constants.ReplaceType.regex:
                    result = re.sub(self.pattern, self.replace, text)
                elif self.replace_type == constants.ReplaceType.simple:
                    result = result.replace(self.pattern,  self.replace)
                else:
                    raise Exception(f'unsupported replacement type: {self.replace_type}')
            except Exception as e:
                raise errors.TextReplacementError(text, self.pattern, self.replace, str(e))
        return result

class TextUtils():
    def __init__(self, options):
        self.options = options
        replacements_array = self.options.get('replacements', [])
        self.replacements = [TextReplacement(replacement) for replacement in replacements_array]

    def is_empty(self, text):
        stripped_field_value = anki.utils.htmlToTextLine(text)
        return len(stripped_field_value) == 0

    def process(self, text):
        result = anki.utils.htmlToTextLine(text)

        # apply replacements
        for replacement in self.replacements:
            result = replacement.process(result)

        return result