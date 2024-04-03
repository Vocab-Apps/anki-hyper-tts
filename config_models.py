import sys
import abc
import copy
from dataclasses import dataclass, field
import databind.json
from typing import List, Optional, Mapping, Any

constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_base)
voice = __import__('voice', globals(), locals(), [], sys._addon_import_level_base)
errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_base)
logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_base)
logger = logging_utils.get_child_logger(__name__)

"""
the various objects here dictate how HyperTTS is configured and these objects will serialize to/from the anki config
"""

class ConfigModelBase(abc.ABC):
    @abc.abstractmethod
    def serialize(self):
        pass

    @abc.abstractmethod
    def validate(self):
        pass    

class BatchConfig(ConfigModelBase):
    def __init__(self, anki_utils):
        self._source = None
        self._target = None
        self._voice_selection = None
        self._text_processing = None
        self.uuid = anki_utils.get_uuid()
        self.name = None

    def reset_uuid(self, anki_utils):
        self.uuid = anki_utils.get_uuid()

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
            'uuid': self.uuid,
            'name': self.name,
            'source': serialize_batchsource(self.source),
            'target': self.target.serialize(),
            'voice_selection': self.voice_selection.serialize(),
            'text_processing': self.text_processing.serialize()
        }

    def validate(self):
        if self.name == None or len(self.name) == 0:
            raise errors.PresetNameNotSet()
        if self.uuid == None or len(self.uuid) == 0:
            raise RuntimeError('uuid not set')
        self.source.validate(),
        self.target.validate(),
        self.voice_selection.validate(),
        self.text_processing.validate()


@dataclass
class BatchSource():
    mode: constants.BatchMode
    source_field: Optional[str] = None
    source_template: Optional[str] = None
    template_format_version: constants.TemplateFormatVersion = constants.TemplateFormatVersion.v1
    use_selection: Optional[bool] = False

    def validate(self):
        if self.mode == constants.BatchMode.simple:
            if self.source_field == None or len(self.source_field) == 0:
                raise errors.SourceFieldNotSet()
        if self.mode == constants.BatchMode.template:
            if self.source_template == None or len(self.source_template) == 0:
                raise errors.SourceTemplateNotSet()

    def __str__(self):
        if self.mode == constants.BatchMode.simple:
            return f'{self.source_field}'
        if self.mode in [constants.BatchMode.template, constants.BatchMode.advanced_template]:
            return f'template'
        return None

def serialize_batchsource(batch_source):
    return databind.json.dump(batch_source, BatchSource)
        
def deserialize_batchsource(batch_source_config):
    return databind.json.load(batch_source_config, BatchSource)


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

    def validate(self):
        if self.target_field == None or len(self.target_field) == 0:
            raise errors.TargetFieldNotSet()

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

    def validate(self):
        logger.debug('VoiceSelectionSingle.validate')
        if self.voice == None:
            raise errors.NoVoiceSet()

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

    def validate(self):
        logger.debug(f'VoiceSelectionMultipleBase.validate, len(voice_list): {len(self._voice_list)}')
        if len(self._voice_list) == 0:
            raise errors.NoVoiceSet()

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

    def validate(self):
        pass

class TextProcessing(ConfigModelBase):
    def __init__(self):
        self._text_replacement_rules = []
        self.html_to_text_line = constants.TEXT_PROCESSING_DEFAULT_HTMLTOTEXTLINE
        self.strip_brackets = constants.TEXT_PROCESSING_DEFAULT_STRIP_BRACKETS
        self.ssml_convert_characters = constants.TEXT_PROCESSING_DEFAULT_SSML_CHARACTERS
        self.run_replace_rules_after = constants.TEXT_PROCESSING_DEFAULT_REPLACE_AFTER
        self.ignore_case = constants.TEXT_PROCESSING_DEFAULT_IGNORE_CASE

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
            'strip_brackets': self.strip_brackets,
            'ssml_convert_characters': self.ssml_convert_characters,
            'run_replace_rules_after': self.run_replace_rules_after,
            'ignore_case': self.ignore_case,
            'text_replacement_rules': [x.serialize() for x in self.text_replacement_rules]
        }

    def validate(self):
        pass

# service configuration
# =====================
@dataclass
class HyperTTSProAccountConfig:
    api_key: str = None
    api_key_valid: bool = False
    use_vocabai_api:bool = False
    api_key_error: Optional[str] = None
    account_info: Optional[Mapping[str, Any]] = None

    def clear_api_key(self):
        self.api_key = None
        self.api_key_valid = False
        self.api_key_error = None
        self.account_info = None

@dataclass
class Configuration:
    service_enabled: Mapping[str, bool] = field(default_factory=dict)
    service_config: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    hypertts_pro_api_key: Optional[str] = None
    # use vocabai API url and conventions
    use_vocabai_api: Optional[bool] = False
    # allow overriding vocab.ai api url during testing
    vocabai_api_url_override: Optional[str] = None

    # pro api key
    # ===========

    def update_hypertts_pro_config(self, config: HyperTTSProAccountConfig):
        self.hypertts_pro_api_key = config.api_key
        self.use_vocabai_api = config.use_vocabai_api

    def get_hypertts_pro_config(self) -> HyperTTSProAccountConfig:
        return HyperTTSProAccountConfig(
            api_key=self.hypertts_pro_api_key,
            use_vocabai_api=self.use_vocabai_api
        )

    def get_hypertts_pro_api_key(self):
        return self.hypertts_pro_api_key

    def set_hypertts_pro_api_key(self, api_key):
        self.hypertts_pro_api_key = api_key

    def hypertts_pro_api_key_set(self):
        return self.hypertts_pro_api_key != None and len(self.hypertts_pro_api_key) > 0

    def check_service_config_key(self, service_name):
        if service_name not in self.service_config:
            self.service_config[service_name] = {}

    # service enabled / disabled
    # ==========================

    def get_service_enabled(self, service_name):
        return self.service_enabled.get(service_name, None)

    def set_service_enabled(self, service_name, enabled):
        self.service_enabled[service_name] = enabled

    def get_service_enabled_map(self):
        return self.service_enabled

    def set_service_enabled_map(self, service_enabled):
        self.service_enabled = service_enabled

    # service configuration 
    # =====================

    def set_service_configuration_key(self, service_name, key, value):
        self.check_service_config_key(service_name)
        self.service_config[service_name][key] = value

    def get_service_configuration_key(self, service_name, key):
        service_config = self.service_config.get(service_name, {})
        return service_config.get(key, None) 

    def set_service_config(self, service_config):
        self.service_config = service_config

    def get_service_config(self):
        return self.service_config

    def validate(self):
        pass


def serialize_configuration(service_config):
    return databind.json.dump(service_config, Configuration)

def deserialize_configuration(service_config):
    return databind.json.load(service_config, Configuration)

# realtime config models
# ======================

class RealtimeConfig(ConfigModelBase):
    def __init__(self):
        self.front = None
        self.back = None

    def serialize(self):
        return {
            'front': self.front.serialize(),
            'back': self.back.serialize(),
        }

    def validate(self):
        logger.debug('RealtimeConfig.validate')
        logger.debug('self.front.validate()')
        self.front.validate()
        logger.debug('self.back.validate()')
        self.back.validate()

class RealtimeConfigSide(ConfigModelBase):
    def __init__(self):
        self.side_enabled = False
        self.source = None
        self.voice_selection = None
        self.text_processing = None

    def serialize(self):
        if self.side_enabled:
            return {
                'side_enabled': self.side_enabled,
                'source': self.source.serialize(),
                'voice_selection': self.voice_selection.serialize(),
                'text_processing': self.text_processing.serialize()
            }
        else:
            return {
                'side_enabled': self.side_enabled,
            }            

    def validate(self):
        logger.debug('RealtimeConfigSide.validate')
        if self.side_enabled:
            self.source.validate()
            if self.voice_selection == None:
                raise errors.VoiceSelectionNotSet()
            self.voice_selection.validate()
            if self.text_processing == None:
                raise errors.TextProcessingNotSet()
            self.text_processing.validate()

    def __str__(self):
        return f"""<b>Source:</b> {self.source}
<b>Voice Selection:</b> {self.voice_selection}
"""        

class RealtimeSourceAnkiTTS(ConfigModelBase):
    def __init__(self):
        self.mode = constants.RealtimeSourceType.AnkiTTSTag
        self.field_name = None
        self.field_type = None

    def serialize(self):
        return {
            'mode': self.mode.name,
            'field_name':  self.field_name,
            'field_type': self.field_type.name
        }

    def validate(self):
        if self.field_name == None:
            raise errors.SourceFieldNotSet()
        if self.field_type == None:
            raise errors.SourceFieldTypeNotSet()

    def __str__(self):
        if self.field_name == None or self.field_type == None:
            return f"""Undefined"""
        return f"""field: {self.field_name} ({self.field_type.name})"""

    
@dataclass
class KeyboardShortcuts:
    shortcut_editor_add_audio: Optional[str] = None
    shortcut_editor_preview_audio: Optional[str] = None

@dataclass
class ErrorHandling:
    realtime_tts_errors_dialog_type: constants.ErrorDialogType = constants.ErrorDialogType.Dialog

@dataclass
class Preferences:
    keyboard_shortcuts: KeyboardShortcuts = field(default_factory=KeyboardShortcuts)
    error_handling: ErrorHandling = field(default_factory=ErrorHandling)

def serialize_preferences(preferences):
    return databind.json.dump(preferences, Preferences)
        
def deserialize_preferences(preferences_config):
    return databind.json.load(preferences_config, Preferences)

@dataclass
class PresetInfo:
    id: str
    name: str

@dataclass
class DeckNoteType:
    model_id: int
    deck_id: int

@dataclass
class EditorContext:
    note: any
    editor: any
    add_mode: bool
    selected_text: str
    selected_text_fieldname: str

@dataclass
class MappingRule:
    preset_id: str
    rule_type: constants.MappingRuleType
    model_id: int
    enabled: bool
    automatic: bool
    deck_id: Optional[int] = None

    def rule_related(self, deck_note_type: DeckNoteType):
        """used to determine whether we should display a rule in the mapping rule editor"""
        if self.rule_type == constants.MappingRuleType.DeckNoteType:
            return self.model_id == deck_note_type.model_id and self.deck_id == deck_note_type.deck_id
        # for note-type rules, just match on model_id
        return self.model_id == deck_note_type.model_id

    def rule_applies(self, deck_note_type: DeckNoteType, automated: bool) -> bool:
        if self.enabled == False:
            # rule is disabled
            return False
        if self.model_id != deck_note_type.model_id:
            # note type doesn't match
            return False
        if self.rule_type == constants.MappingRuleType.DeckNoteType:
            if self.deck_id != deck_note_type.deck_id:
                # deck doesn't match
                return False
        if automated == True:
            if self.automatic == False:
                # rule is not automatic
                return False
        return True

@dataclass
class PresetMappingRules:
    rules: list[MappingRule] = field(default_factory=list)

    def iterate_applicable_rules(self, deck_note_type: DeckNoteType, automated: bool):
        subset_index = 0
        for absolute_index, rule in enumerate(self.rules):
            logger.info(f'evaluating rule {rule} with deck_note_type {deck_note_type}')
            if rule.rule_applies(deck_note_type, automated):
                logger.info(f'rule applies: {rule} on deck_note_type {deck_note_type}')
                yield absolute_index, subset_index, rule
                subset_index += 1

    def iterate_related_rules(self, deck_note_type: DeckNoteType):
        """get list of rules to display in the GUI"""
        subset_index = 0
        for absolute_index, rule in enumerate(self.rules):
            if rule.rule_related(deck_note_type):
                yield absolute_index, subset_index, rule
                subset_index += 1


def serialize_preset_mapping_rules(preset_mapping_rules):
    return databind.json.dump(preset_mapping_rules, PresetMappingRules)

def deserialize_preset_mapping_rules(preset_mapping_rules_config):
    return databind.json.load(preset_mapping_rules_config, PresetMappingRules)

def migrate_configuration(anki_utils, config):
    current_config_schema_version = config.get(constants.CONFIG_SCHEMA, 0)
    if current_config_schema_version < 2:
        config[constants.CONFIG_PRESETS] = {}
        # need to convert presets to the uuid format
        if constants.CONFIG_BATCH_CONFIG in config:
            for key, value in config[constants.CONFIG_BATCH_CONFIG].items():
                batch_name = key
                batch = value
                batch_uuid = anki_utils.get_uuid()
                batch['uuid'] = batch_uuid
                batch['name'] = batch_name
                config[constants.CONFIG_PRESETS][batch_uuid] = batch
    # write current config
    config[constants.CONFIG_SCHEMA] = constants.CONFIG_SCHEMA_VERSION

    return config
    