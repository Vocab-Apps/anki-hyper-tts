import sys
import abc
import copy

constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_base)
voice = __import__('voice', globals(), locals(), [], sys._addon_import_level_base)
errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_base)

"""
the various objects here dictate how HyperTTS is configured and these objects will serialize to/from the anki config
"""

class ConfigModelBase(abc.ABC):
    @abc.abstractmethod
    def serialize(self):
        pass

    # @abc.abstractmethod
    # def validate(self):
    #     pass    

class BatchConfig(ConfigModelBase):
    def __init__(self):
        self._source = None
        self._target = None
        self._voice_selection = None
        self._text_processing = None

    def get_source(self):
        return self._source
    def set_source(self, source):
        self._source = source

    def get_target(self):
        return self._target
    def set_target(self, target):
        self._target = target

    def get_voice_selection(self):
        return self._voice_selection
    def set_voice_selection(self, voice_selection):
        self._voice_selection = voice_selection

    def get_text_processing(self):
        return self._text_processing
    def set_text_processing(self, text_processing):
        self._text_processing = text_processing

    source = property(get_source, set_source)
    target = property(get_target, set_target)
    voice_selection = property(get_voice_selection, set_voice_selection)
    text_processing = property(get_text_processing, set_text_processing)

    def __str__(self):
        return f"""<b>Source:</b> {self.source}
<b>Target:</b> {self.target}
<b>Voice Selection:</b> {self.voice_selection}
"""

    def serialize(self):
        return {
            'source': self.source.serialize(),
            'target': self.target.serialize(),
            'voice_selection': self.voice_selection.serialize(),
            'text_processing': self.text_processing.serialize()
        }

class BatchSource(ConfigModelBase):
    def __init__(self):
        self.mode = None
        self.source_field = None
        self.source_template = None
        self.template_format_version = constants.TemplateFormatVersion.v1

    def serialize(self):
        if self.mode == constants.BatchMode.simple:
            return {
                'mode': self.mode.name,
                'source_field': self.source_field
            }
        else:
            return {
                'mode': self.mode.name,
                'template_format_version': self.template_format_version.name,
                'source_template': self.source_template
            }
    
    def __str__(self):
        if self.mode == constants.BatchMode.simple:
            return f'{self.source_field}'
        else:
            return 'template'


class BatchSourceSimple(BatchSource):
    def __init__(self, source_field):
        BatchSource.__init__(self)
        self.mode = constants.BatchMode.simple
        self.source_field = source_field

    def validate(self):
        if self.source_field == None or len(self.source_field) == 0:
            raise errors.SourceFieldNotSet()


class BatchSourceTemplate(BatchSource):
    def __init__(self, mode, source_template: str, template_format_version: constants.TemplateFormatVersion):
        BatchSource.__init__(self)
        self.mode = mode
        self.source_template = source_template
        self.template_format_version = template_format_version


class BatchTarget(ConfigModelBase):
    def __init__(self, target_field, text_and_sound_tag, remove_sound_tag):
        self.target_field = target_field
        self.text_and_sound_tag = text_and_sound_tag
        self.remove_sound_tag = remove_sound_tag

    def serialize(self):
        return {
            'target_field': self.target_field,
            'text_and_sound_tag': self.text_and_sound_tag,
            'remove_sound_tag': self.remove_sound_tag
        }

    def __str__(self):
        return f'{self.target_field}'

# voice selection models
# ======================

class VoiceWithOptions():
    def __init__(self, voice: voice.VoiceBase, options):
        self.voice = voice
        self.options = copy.copy(options)

    def serialize(self):
        return {
            'voice': self.voice.serialize(),
            'options': self.options
        }

    def options_str(self):
        options_array = []
        for key, value in self.options.items():
            if value != self.voice.options[key]['default']:
                options_array.append(f'{key}: {value}')
        if len(options_array) > 0:
            return ' (' + ', '.join(options_array) + ')'
        return ''


    def __str__(self):
        return f'{self.voice}{self.options_str()}'

class VoiceWithOptionsRandom(VoiceWithOptions):
    def __init__(self, voice: voice.VoiceBase, options, random_weight=1):
        VoiceWithOptions.__init__(self, voice, options)
        self._random_weight = random_weight

    def serialize(self):
        return {
            'voice': self.voice.serialize(),
            'options': self.options,
            'weight': self.random_weight
        }        

    def get_random_weight(self):
        return self._random_weight

    def set_random_weight(self, weight):
        self._random_weight = weight

    random_weight = property(get_random_weight, set_random_weight)

class VoiceWithOptionsPriority(VoiceWithOptions):
    def __init__(self, voice: voice.VoiceBase, options):
        VoiceWithOptions.__init__(self, voice, options)


class VoiceSelectionBase(ConfigModelBase):
    def __init__(self):
        self._selection_mode = None

    def get_selection_mode(self):
        return self._selection_mode

    # properties
    selection_mode = property(get_selection_mode, None)

    def __str__(self):
        return 'voices'

class VoiceSelectionSingle(VoiceSelectionBase):
    def __init__(self):
        VoiceSelectionBase.__init__(self)
        self._selection_mode = constants.VoiceSelectionMode.single
        self._voice_with_options = None
    
    def serialize(self):
        return {
            'voice_selection_mode': self._selection_mode.name,
            'voice': self._voice_with_options.serialize()
        }

    def get_voice(self):
        return self._voice_with_options
    def set_voice(self, voice_with_options):
        self._voice_with_options = voice_with_options

    voice = property(get_voice, set_voice)

    def __str__(self):
        return 'Single'

class VoiceSelectionMultipleBase(VoiceSelectionBase):
    def __init__(self):
        VoiceSelectionBase.__init__(self)
        self._voice_list = []

    def get_voice_list(self):
        return self._voice_list

    def clear_voice_list(self):
        self._voice_list = []

    def add_voice(self, voice):
        self._voice_list.append(voice)

    def remove_voice(self, voice):
        self._voice_list.remove(voice)

    def move_up_voice(self, voice):
        index = self._voice_list.index(voice)
        if index == 0:
            return
        entry_1 = self._voice_list[index - 1]
        entry_2 = self._voice_list[index]
        self._voice_list[index - 1] = entry_2
        self._voice_list[index] = entry_1

    def move_down_voice(self, voice):
        index = self._voice_list.index(voice)
        if index == len(self._voice_list) - 1:
            return
        entry_1 = self._voice_list[index]
        entry_2 = self._voice_list[index + 1]
        self._voice_list[index] = entry_2
        self._voice_list[index + 1] = entry_1

    voice_list = property(get_voice_list, None)

    def serialize(self):
        return {
            'voice_selection_mode': self._selection_mode.name,
            'voice_list': [x.serialize() for x in self._voice_list]
        }

    def __str__(self):
        return f'{self.selection_mode.name} ({len(self.get_voice_list())} voices)'

class VoiceSelectionRandom(VoiceSelectionMultipleBase):
    def __init__(self):
        VoiceSelectionMultipleBase.__init__(self)
        self._selection_mode = constants.VoiceSelectionMode.random

    def set_random_weight(self, voice_index, weight):
        self._voice_list[voice_index].random_weight = weight



class VoiceSelectionPriority(VoiceSelectionMultipleBase):
    def __init__(self):
        VoiceSelectionMultipleBase.__init__(self)
        self._selection_mode = constants.VoiceSelectionMode.priority

# text processing
# ===============

class TextReplacementRule(ConfigModelBase):
    def __init__(self, rule_type):
        self._rule_type = rule_type
        self._source = None
        self._target = None

    def get_rule_type(self):
        return self._rule_type

    def get_source(self):
        return self._source

    def set_source(self, source):
        self._source = source

    def get_target(self):
        return self._target

    def set_target(self, target):
        self._target = target

    rule_type = property(get_rule_type, None)
    source = property(get_source, set_source)
    target = property(get_target, set_target)

    def serialize(self):
        return {
            'rule_type': self._rule_type.name,
            'source': self.source,
            'target': self.target
        }

class TextProcessing(ConfigModelBase):
    def __init__(self):
        self._text_replacement_rules = []
        self.html_to_text_line = constants.TEXT_PROCESSING_DEFAULT_HTMLTOTEXTLINE
        self.ssml_convert_characters = constants.TEXT_PROCESSING_DEFAULT_SSML_CHARACTERS
        self.run_replace_rules_after = constants.TEXT_PROCESSING_DEFAULT_REPLACE_AFTER

    def add_text_replacement_rule(self, rule):
        self._text_replacement_rules.append(rule)

    def remove_text_replacement_rule(self, row):
        del self.text_replacement_rules[row]

    def get_text_replacement_rule_row(self, row):
        return self.text_replacement_rules[row]

    def get_text_replacement_rules(self):
        return self._text_replacement_rules

    def set_text_replacement_rules(self, rules):
        self._text_replacement_rules = rules

    text_replacement_rules = property(get_text_replacement_rules, set_text_replacement_rules)

    def serialize(self):
        return {
            'html_to_text_line': self.html_to_text_line,
            'ssml_convert_characters': self.ssml_convert_characters,
            'run_replace_rules_after': self.run_replace_rules_after,
            'text_replacement_rules': [x.serialize() for x in self.text_replacement_rules]
        }

# service configuration
# =====================

class Configuration(ConfigModelBase):
    def __init__(self):
        self._service_enabled = {}
        self._service_config = {}
        self._hypertts_pro_api_key = None

    # pro api key
    # ===========

    def get_hypertts_pro_api_key(self):
        return self._hypertts_pro_api_key

    def set_hypertts_pro_api_key(self, api_key):
        self._hypertts_pro_api_key = api_key

    def hypertts_pro_api_key_set(self):
        return self.hypertts_pro_api_key != None and len(self.hypertts_pro_api_key)

    hypertts_pro_api_key = property(get_hypertts_pro_api_key, set_hypertts_pro_api_key)

    def check_service_config_key(self, service_name):
        if service_name not in self._service_config:
            self._service_config[service_name] = {}

    # service enabled / disabled
    # ==========================

    def get_service_enabled(self, service_name):
        return self._service_enabled.get(service_name, None)

    def set_service_enabled(self, service_name, enabled):
        self._service_enabled[service_name] = enabled

    def get_service_enabled_map(self):
        return self._service_enabled

    def set_service_enabled_map(self, service_enabled):
        self._service_enabled = service_enabled

    # service configuration 
    # =====================

    def set_service_configuration_key(self, service_name, key, value):
        self.check_service_config_key(service_name)
        self._service_config[service_name][key] = value

    def get_service_configuration_key(self, service_name, key):
        service_config = self._service_config.get(service_name, {})
        return service_config.get(key, None) 

    def set_service_config(self, service_config):
        self._service_config = service_config

    def get_service_config(self):
        return self._service_config

    def serialize(self):
        return {
            'hypertts_pro_api_key': self.hypertts_pro_api_key,
            'service_enabled': self._service_enabled,
            'service_config': self._service_config
        }