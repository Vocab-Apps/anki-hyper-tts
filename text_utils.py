import sys
import logging
import anki.utils
import re

if hasattr(sys, '_pytest_mode'):
    import constants
else:
    from . import constants


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
        self.transformation_type_map = {}
        for transformation_type in constants.TransformationType:
            self.transformation_type_map[transformation_type] = options.get(transformation_type.name, True)

    def to_dict(self):
        transformation_type_map = {key.name:value for (key, value) in self.transformation_type_map.items()}
        data = {
            'pattern': self.pattern,
            'replace': self.replace,
            'replace_type': self.replace_type.name
        }
        data.update(transformation_type_map)
        return data

    def process(self, text, transformation_type):
        result = text
        if self.transformation_type_map[transformation_type]:
            if self.pattern != None and self.replace != None:
                try:
                    if self.replace_type == constants.ReplaceType.regex:
                        result = re.sub(self.pattern, self.replace, text)
                    elif self.replace_type == constants.ReplaceType.simple:
                        result = result.replace(self.pattern,  self.replace)
                    else:
                        raise Exception(f'unsupported replacement type: {self.replace_type}')
                except Exception as e:
                    logging.error(f'error while processing regular expression {self.pattern} / {self.replace}: {e}')
        return result

class TextUtils():
    def __init__(self, options):
        self.options = options
        replacements_array = self.options.get('replacements', [])
        self.replacements = [TextReplacement(replacement) for replacement in replacements_array]

    def is_empty(self, text):
        stripped_field_value = anki.utils.htmlToTextLine(text)
        return len(stripped_field_value) == 0

    def process(self, text, transformation_type: constants.TransformationType):
        result = anki.utils.htmlToTextLine(text)

        # apply replacements
        for replacement in self.replacements:
            result = replacement.process(result, transformation_type)

        return result