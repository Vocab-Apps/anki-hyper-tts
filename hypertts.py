
# python imports
import os
import sys
import re
import hashlib
import logging
import random
import copy
import json
from typing import List, Dict
import pprint

# anki imports
import aqt
import aqt.progress
import aqt.addcards
import anki.notes
import anki.cards

constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_base)
errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_base)
text_utils = __import__('text_utils', globals(), locals(), [], sys._addon_import_level_base)
config_models = __import__('config_models', globals(), locals(), [], sys._addon_import_level_base)


class HyperTTS():
    """
    should have awareness of:
    - anki concepts such as notes, editor
    - understand how user has configured their presets
    should not have awareness of:
    - services (route through servicemanager)
    """

    def __init__(self, anki_utils, service_manager):
        self.anki_utils = anki_utils
        self.service_manager = service_manager
        self.error_manager = errors.ErrorManager(self.anki_utils)
        self.config = self.anki_utils.get_config()
        self.error_manager = errors.ErrorManager(self.anki_utils)
        self.latest_saved_batch_name = None


    def process_batch_audio(self, note_id_list, batch, batch_status):
        # for each note, generate audio
        with batch_status.get_batch_running_action_context():
            undo_id = self.anki_utils.undo_start()
            for note_id in note_id_list:
                with batch_status.get_note_action_context(note_id, False) as note_action_context:
                    note = self.anki_utils.get_note_by_id(note_id)
                    # process note
                    source_text, processed_text, sound_file, full_filename = self.process_note_audio(batch, note, False)
                    # update note action context
                    note_action_context.set_source_text(source_text)
                    note_action_context.set_processed_text(processed_text)
                    note_action_context.set_sound(sound_file)
                    note_action_context.set_status(constants.BatchNoteStatus.Done)                    
                if batch_status.must_continue == False:
                    logging.info('batch_status execution interrupted')
                    break
            self.anki_utils.undo_end(undo_id)

    def process_note_audio(self, batch, note, add_mode):
        target_field = batch.target.target_field

        if target_field not in note:
            raise errors.TargetFieldNotFoundError(target_field)

        source_text = self.get_source_text(note, batch.source)
        processed_text = self.process_text(source_text, batch.text_processing)

        full_filename, audio_filename = self.get_audio_file(processed_text, batch.voice_selection)
        sound_tag, sound_file = self.get_collection_sound_tag(full_filename, audio_filename)

        target_field_content = note[target_field]
        
        # do we need to remove existing sound tags ?
        if batch.target.remove_sound_tag == True:
                target_field_content = self.strip_sound_tag(target_field_content)
        
        # does the user want text and sound together?
        if batch.target.text_and_sound_tag == True:
            target_field_content = f'{target_field_content} {sound_tag}'
        else:
            target_field_content = f'{sound_tag}'

        note[target_field] = target_field_content
        if not add_mode:
            self.anki_utils.update_note(note)

        return source_text, processed_text, sound_file, full_filename

    def get_note_audio(self, batch, note):
        source_text = self.get_source_text(note, batch.source)
        processed_text = text_utils.process_text(source_text, batch.text_processing)
        return self.get_audio_file(processed_text, batch.voice_selection)        

    def get_realtime_audio(self, realtime_model: config_models.RealtimeConfigSide, text):
        source_text = text
        processed_text = text_utils.process_text(source_text, realtime_model.text_processing)
        return self.get_audio_file(processed_text, realtime_model.voice_selection)

    def get_audio_file(self, processed_text, voice_selection):
        # sanity checks
        if voice_selection.selection_mode in [constants.VoiceSelectionMode.priority, constants.VoiceSelectionMode.random]:
            if len(voice_selection.voice_list) == 0:
                raise errors.NoVoicesAdded()

        # this voice_list copy is only used for priority mode
        voice_list = None
        priority_mode = voice_selection.selection_mode == constants.VoiceSelectionMode.priority
        if priority_mode:
            voice_list = copy.copy(voice_selection.voice_list)
        sound_found = False
        # loop while we haven't found the sound. this will be used for priority mode
        loop_condition = True
        while loop_condition:
            try:
                voice_with_options = self.choose_voice(voice_selection, voice_list)
                full_filename, audio_filename = self.generate_audio_write_file(processed_text, voice_with_options.voice, voice_with_options.options)
                return full_filename, audio_filename
            except errors.AudioNotFoundError as exc:
                # try the next voice, as long as one is available
                if not priority_mode:
                    # re-raise the exception
                    raise exc
            loop_condition = priority_mode and sound_found == False and len(voice_list) > 0
        raise errors.AudioNotFoundAnyVoiceError(processed_text)

    def choose_voice(self, voice_selection, voice_list) -> config_models.VoiceWithOptions:
        if voice_selection.selection_mode == constants.VoiceSelectionMode.single:
            return voice_selection.voice
        elif voice_selection.selection_mode == constants.VoiceSelectionMode.random:
            logging.info(f'choosing from {len(voice_selection.voice_list)} voices')
            choice = random.choices(voice_selection.voice_list, weights=[x.random_weight for x in voice_selection.voice_list])
            return choice[0]
        elif voice_selection.selection_mode == constants.VoiceSelectionMode.priority:
            # remove that voice from possible list
            voice = voice_list.pop(0)
            return voice

    def editor_note_add_audio(self, batch, editor, note, add_mode):
        undo_id = self.anki_utils.undo_start()
        source_text, processed_text, sound_file, full_filename = self.process_note_audio(batch, note, add_mode)
        editor.set_note(note)
        self.anki_utils.undo_end(undo_id)
        self.anki_utils.play_sound(full_filename)

    # text processing
    # ===============

    def get_source_text(self, note, batch_source):
        if batch_source.mode == constants.BatchMode.simple:
            if batch_source.source_field not in note:
                raise errors.SourceFieldNotFoundError(batch_source.source_field)
            source_text = note[batch_source.source_field]
        elif batch_source.mode == constants.BatchMode.template:
            source_text = self.expand_simple_template(note, batch_source.source_template)
        elif batch_source.mode == constants.BatchMode.advanced_template:
            source_text = self.expand_advanced_template(note, batch_source.source_template)
        return source_text

    def expand_simple_template(self, note, source_template):
        field_values = self.get_field_values(note)
        # logging.info(f'field_values: {field_values}')
        return source_template.format_map(field_values)

    def expand_advanced_template(self, note, source_template):
        local_variables = {
            'template_fields': self.get_field_values(note)
        }
        try:
            expanded_template = exec(source_template, {}, local_variables)
        except Exception as e:
            raise errors.TemplateExpansionError(e)
        if 'result' not in local_variables:
            raise errors.NoResultVar()
        result = local_variables['result']
        return result

    def get_field_values(self, note):
        field_values = {}
        for field_name in list(note.keys()):
            field_values[field_name] = note[field_name]
        return field_values

    def process_text(self, source_text, batch_text_processing):
        processed_text = text_utils.process_text(source_text, batch_text_processing)
        # logging.info(f'before text processing: [{source_text}], after text processing: [{processed_text}]')
        if len(processed_text) == 0:
            raise errors.SourceTextEmpty()
        return processed_text

    # sound generation
    # ================

    def preview_note_audio(self, batch, note):
        batch.validate()
        full_filename, audio_filename = self.get_note_audio(batch, note)
        self.anki_utils.play_sound(full_filename)

    def play_realtime_audio(self, realtime_model: config_models.RealtimeConfigSide, text):
        full_filename, audio_filename = self.get_realtime_audio(realtime_model, text)
        self.anki_utils.play_sound(full_filename)

    def play_sound(self, source_text, voice, options):
        logging.info(f'playing audio for {source_text}')
        full_filename, audio_filename = self.generate_audio_write_file(source_text, voice, options)
        self.anki_utils.play_sound(full_filename)

    # processing of sound tags / collection stuff
    # ===========================================

    def generate_audio_write_file(self, source_text, voice, options):
        # write to user files directory
        hash_str = self.get_hash_for_audio_request(source_text, voice, options)
        audio_filename = self.get_audio_filename(hash_str)
        full_filename = self.get_full_audio_file_name(hash_str)
        with open(full_filename, 'wb') as f:
            f.write(self.service_manager.get_tts_audio(source_text, voice, options))
        return full_filename, audio_filename

    def get_collection_sound_tag(self, full_filename, audio_filename):
        self.anki_utils.media_add_file(full_filename)
        return f'[sound:{audio_filename}]', audio_filename

    def get_full_audio_file_name(self, hash_str):
        # return the absolute path of the audio file in the user_files directory
        user_files_dir = self.anki_utils.get_user_files_dir()
        filename = self.get_audio_filename(hash_str)
        return os.path.join(user_files_dir, filename)
    
    def get_audio_filename(self, hash_str):
        filename = f'hypertts-{hash_str}.mp3'
        return filename

    def get_hash_for_audio_request(self, source_text, voice, options):
        combined_data = {
            'source_text': source_text,
            'voice_key': voice.voice_key,
            'options': options
        }
        return hashlib.sha224(str(combined_data).encode('utf-8')).hexdigest()

    def strip_sound_tag(self, field_value):
        field_value = re.sub('\[sound:[^\]]+\]', '', field_value)
        return field_value.strip()

    # processing of Anki TTS tags
    # ===========================

    def play_tts_tag(self, tts_tag):
        hypertts_preset = self.extract_hypertts_preset(tts_tag.other_args)
        realtime_side_model = self.get_realtime_side_config(hypertts_preset)
        self.play_realtime_audio(realtime_side_model, tts_tag.field_text)

    def build_realtime_tts_tag(self, realtime_side_model: config_models.RealtimeConfigSide, setting_key):
        if realtime_side_model.source.mode == constants.RealtimeSourceType.AnkiTTSTag:
            # get the audio language of the first voice
            voice_selection = realtime_side_model.voice_selection
            if voice_selection.selection_mode == constants.VoiceSelectionMode.single:
                audio_language = voice_selection.voice.voice.language
            else:
                audio_language = voice_selection.get_voice_list()[0].voice.language
            field_format = realtime_side_model.source.field_name
            if realtime_side_model.source.field_type == constants.AnkiTTSFieldType.Cloze:
                field_format = f'cloze:{realtime_side_model.source.field_name}'
            elif realtime_side_model.source.field_type == constants.AnkiTTSFieldType.ClozeOnly:
                field_format = f'cloze-only:{realtime_side_model.source.field_name}'
            return '{{tts ' + f"""{audio_language.name} {constants.TTS_TAG_HYPERTTS_PRESET}={setting_key} voices=HyperTTS:{field_format}""" + '}}'
        else:
            raise Exception(f'unsupported RealtimeSourceType: {realtime_side_model.source.mode}')

    def extract_hypertts_preset(self, extra_args_array):
        subset = [x for x in extra_args_array if constants.TTS_TAG_HYPERTTS_PRESET in x]
        array_entry = subset[0]
        components = array_entry.split('=')
        return components[1]

    def get_realtime_side_config(self, hypertts_preset):
        # based 
        if constants.AnkiCardSide.Front.name in hypertts_preset:
            # front
            preset_name = hypertts_preset.replace(constants.AnkiCardSide.Front.name + '_', '')
            return self.load_realtime_config(preset_name).front
        else:
            # back
            preset_name = hypertts_preset.replace(constants.AnkiCardSide.Back.name + '_', '')
            return self.load_realtime_config(preset_name).back


    def remove_tts_tag(self, card_template):
        return re.sub('{{tts.*}}', '', card_template)

    def set_tts_tag_note_model(self, realtime_side_model: config_models.RealtimeConfigSide, setting_key, note_model, side, card_ord, clear_only):
        # build tts tag
        tts_tag = self.build_realtime_tts_tag(realtime_side_model, setting_key)
        logging.info(f'tts tag: {tts_tag}')

        # alter card template
        card_template = note_model["tmpls"][card_ord]
        side_template_key = 'qfmt'
        if side == constants.AnkiCardSide.Back:
            side_template_key = 'afmt'
        side_template = card_template[side_template_key]
        side_template = self.remove_tts_tag(side_template)
        if not clear_only:
            side_template += '\n' + tts_tag
        card_template[side_template_key] = side_template

        note_model["tmpls"][card_ord] = card_template

        return note_model

    def render_card_template_extract_tts_tag(self, realtime_model: config_models.RealtimeConfig, note, side, card_ord):
        realtime_model.validate()
        note_model = note.note_type()
        note_model = copy.deepcopy(note_model)
        note_model = self.set_tts_tag_note_model(realtime_model, 'preview', note_model, side, card_ord, False)
        # pprint.pprint(note_model)        

        card = self.anki_utils.create_card_from_note(note, card_ord, note_model, note_model["tmpls"][card_ord])
        if side == constants.AnkiCardSide.Front:
            return self.anki_utils.extract_tts_tags(card.question_av_tags())
        elif side == constants.AnkiCardSide.Back:
            return self.anki_utils.extract_tts_tags(card.answer_av_tags())

    def build_side_settings_key(self, card_side: constants.AnkiCardSide, settings_key):
        return f'{card_side.name}_{settings_key}'


    def persist_realtime_config_update_note_type(self, realtime_model: config_models.RealtimeConfig, note, card_ord, current_settings_key):
        settings_key = self.save_realtime_config(realtime_model, current_settings_key)
        note_model = note.note_type()
        
        # proces front side
        side = constants.AnkiCardSide.Front
        if realtime_model.front.side_enabled:
            side_settings_key = self.build_side_settings_key(side, settings_key)
            note_model = self.set_tts_tag_note_model(realtime_model.front, side_settings_key, note_model, side, card_ord, False)
        else:
            note_model = self.set_tts_tag_note_model(realtime_model.front, None, note_model, side, card_ord, True)

        # process back side
        side = constants.AnkiCardSide.Back
        if realtime_model.back.side_enabled:
            side_settings_key = self.build_side_settings_key(side, settings_key)
            note_model = self.set_tts_tag_note_model(realtime_model.back, side_settings_key, note_model, side, card_ord, False)
        else:
            note_model = self.set_tts_tag_note_model(realtime_model.back, None, note_model, side, card_ord, True)

        # save note model
        self.anki_utils.save_note_type_update(note_model)

    # functions related to getting data from notes
    # ============================================

    def get_all_fields_from_notes(self, note_id_list):
        field_name_set = {}
        for note_id in note_id_list:
            note = self.anki_utils.get_note_by_id(note_id)
            for field in self.get_fields_from_note(note):
                field_name_set[field] = True
        return sorted(field_name_set.keys())

    def get_fields_from_note(self, note):
        return list(note.keys())

    def populate_batch_status_processed_text(self, note_id_list, batch_source, text_processing, batch_status):
        with batch_status.get_batch_running_action_context():
            for note_id in note_id_list:
                with batch_status.get_note_action_context(note_id, True) as note_action_context:
                    note = self.anki_utils.get_note_by_id(note_id)
                    source_text, processed_text = self.get_source_processed_text(note, batch_source, text_processing)
                    note_action_context.set_source_text(source_text)
                    note_action_context.set_processed_text(processed_text)
                    note_action_context.set_status(constants.BatchNoteStatus.OK)
                if batch_status.must_continue == False:
                    logging.info('batch_status execution interrupted')
                    break

    def get_source_processed_text(self, note, batch_source, text_processing):
        source_text = self.get_source_text(note, batch_source)
        processed_text = text_utils.process_text(source_text, text_processing)
        return source_text, processed_text

    # functions related to addon config
    # =================================

    # batch config

    def save_batch_config(self, batch_name, batch):
        batch.validate()
        if constants.CONFIG_BATCH_CONFIG not in self.config:
            self.config[constants.CONFIG_BATCH_CONFIG] = {}
        self.config[constants.CONFIG_BATCH_CONFIG][batch_name] = batch.serialize()
        self.anki_utils.write_config(self.config)
        self.latest_saved_batch_name = batch_name
        logging.info(f'saved batch config [{batch_name}]')

    def load_batch_config(self, batch_name):
        logging.info(f'loading batch config [{batch_name}]')
        if batch_name not in self.config[constants.CONFIG_BATCH_CONFIG]:
            raise errors.PresetNotFound(batch_name)
        return self.deserialize_batch_config(self.config[constants.CONFIG_BATCH_CONFIG][batch_name])

    def delete_batch_config(self, batch_name):
        logging.info(f'deleting batch config [{batch_name}]')
        if batch_name not in self.config[constants.CONFIG_BATCH_CONFIG]:
            raise errors.PresetNotFound(batch_name)
        del self.config[constants.CONFIG_BATCH_CONFIG][batch_name]
        self.anki_utils.write_config(self.config)

    def get_batch_config_list(self):
        if constants.CONFIG_BATCH_CONFIG not in self.config:
            return []
        return list(self.config[constants.CONFIG_BATCH_CONFIG].keys())

    def get_batch_config_list_editor(self):
        return [constants.BATCH_CONFIG_NEW] + self.get_batch_config_list()

    def get_next_batch_name(self):
        existing_batch_names = self.get_batch_config_list()
        i = 1
        batch_name = f'Preset {i}'
        while batch_name in existing_batch_names:
            i += 1
            batch_name = f'Preset {i}'
        return batch_name

    # realtime config

    def save_realtime_config(self, realtime_model, settings_key):
        realtime_model.validate()
        if constants.CONFIG_REALTIME_CONFIG not in self.config:
            self.config[constants.CONFIG_REALTIME_CONFIG] = {}
        
        if settings_key == None:
            # find a free name
            key_index = 0
            candidate_key = f'realtime_{key_index}'
            while candidate_key in self.config[constants.CONFIG_REALTIME_CONFIG]:
                key_index += 1
                candidate_key = f'realtime_{key_index}'
            final_key = candidate_key
        else:
            # use the key provided
            final_key = settings_key
        self.config[constants.CONFIG_REALTIME_CONFIG][final_key] = realtime_model.serialize()
        return final_key

    def load_realtime_config(self, settings_key):
        logging.info(f'loading realtime config [{settings_key}]')
        if settings_key not in self.config[constants.CONFIG_REALTIME_CONFIG]:
            raise errors.PresetNotFound(settings_key)
        return self.deserialize_batch_config(self.config[constants.CONFIG_REALTIME_CONFIG][settings_key])

    # services config

    def save_configuration(self, configuration_model):
        configuration_model.validate()
        self.config[constants.CONFIG_CONFIGURATION] = configuration_model.serialize()
        self.anki_utils.write_config(self.config)

    def get_configuration(self):
        return self.deserialize_configuration(self.config.get(constants.CONFIG_CONFIGURATION, {}))

    def hypertts_pro_enabled(self):
        return self.get_configuration().hypertts_pro_api_key_set()

    def clear_latest_saved_batch_name(self):
        self.latest_saved_batch_name = None

    def get_latest_saved_batch_name(self):
        return self.latest_saved_batch_name

    # deserialization routines for loading from config
    # ================================================

    def deserialize_batch_config(self, batch_config):
        batch = config_models.BatchConfig()
        batch_mode = constants.BatchMode[batch_config['source']['mode']]
        if batch_mode == constants.BatchMode.simple:
            source = config_models.BatchSourceSimple(batch_config['source']['source_field'])
        else:
            source = config_models.BatchSourceTemplate(batch_mode, batch_config['source']['source_template'],
                constants.TemplateFormatVersion[batch_config['source']['template_format_version']])
        batch_target_config = batch_config['target']
        target = config_models.BatchTarget(batch_target_config['target_field'], batch_target_config['text_and_sound_tag'], batch_target_config['remove_sound_tag'])
        voice_selection = self.deserialize_voice_selection(batch_config['voice_selection'])

        text_processing_config = batch_config.get('text_processing', {})
        text_processing = self.deserialize_text_processing(text_processing_config)

        batch.set_source(source)
        batch.set_target(target)
        batch.set_voice_selection(voice_selection)
        batch.text_processing = text_processing
        
        return batch

    def deserialize_realtime_config(self, realtime_config):
        realtime = config_models.RealtimeConfig()
        realtime.front = self.deserialize_realtime_side_config(realtime_config['front'])
        realtime.back = self.deserialize_realtime_side_config(realtime_config['back'])
        return realtime

    def deserialize_realtime_side_config(self, realtime_side_config):
        realtime_side = config_models.RealtimeConfigSide()
        realtime_side.side_enabled = realtime_side_config['side_enabled']
        if not realtime_side.side_enabled:
            return realtime_side

        realtime_source_type = constants.RealtimeSourceType[realtime_side_config['source']['mode']]
        if realtime_source_type == constants.RealtimeSourceType.AnkiTTSTag:
            source = config_models.RealtimeSourceAnkiTTS()
            source.field_name = realtime_side_config['source']['field_name']
            source.field_type = constants.AnkiTTSFieldType[realtime_side_config['source']['field_type']]
        else:
            raise Exception(f'unsupported RealtimeSourceType: {realtime_source_type}')
        voice_selection = self.deserialize_voice_selection(realtime_side_config['voice_selection'])
        text_processing_config = realtime_side_config.get('text_processing', {})
        text_processing = self.deserialize_text_processing(text_processing_config)

        realtime_side.source = source
        realtime_side.voice_selection = voice_selection
        realtime_side.text_processing = text_processing
        
        return realtime_side       

    def deserialize_voice_selection(self, voice_selection_config):
        voice_selection_mode = constants.VoiceSelectionMode[voice_selection_config['voice_selection_mode']]
        if voice_selection_mode == constants.VoiceSelectionMode.single:
            single = config_models.VoiceSelectionSingle()
            voice = self.service_manager.deserialize_voice(voice_selection_config['voice']['voice'])
            single.set_voice(config_models.VoiceWithOptions(voice, voice_selection_config['voice']['options']))
            return single
        elif voice_selection_mode == constants.VoiceSelectionMode.random:
            random = config_models.VoiceSelectionRandom()
            for voice_data in voice_selection_config['voice_list']:
                voice = self.service_manager.deserialize_voice(voice_data['voice'])
                random.add_voice(config_models.VoiceWithOptionsRandom(voice, voice_data['options'], voice_data['weight']))
            return random
        elif voice_selection_mode == constants.VoiceSelectionMode.priority:
            priority = config_models.VoiceSelectionPriority()
            for voice_data in voice_selection_config['voice_list']:
                voice = self.service_manager.deserialize_voice(voice_data['voice'])
                priority.add_voice(config_models.VoiceWithOptionsPriority(voice, voice_data['options']))
            return priority

    def deserialize_text_processing(self, text_processing_config):
        text_processing = config_models.TextProcessing()
        text_processing.html_to_text_line = text_processing_config.get('html_to_text_line', constants.TEXT_PROCESSING_DEFAULT_HTMLTOTEXTLINE)
        text_processing.ssml_convert_characters = text_processing_config.get('ssml_convert_characters', constants.TEXT_PROCESSING_DEFAULT_SSML_CHARACTERS)
        text_processing.run_replace_rules_after = text_processing_config.get('run_replace_rules_after', constants.TEXT_PROCESSING_DEFAULT_REPLACE_AFTER)
        rules = text_processing_config.get('text_replacement_rules', [])
        for rule in rules:
            rule_obj = config_models.TextReplacementRule(constants.TextReplacementRuleType[rule['rule_type']])
            rule_obj.source = rule['source']
            rule_obj.target = rule['target']
            text_processing.add_text_replacement_rule(rule_obj)
        return text_processing

    def deserialize_configuration(self, configuration_config):
        configuration = config_models.Configuration()
        configuration.hypertts_pro_api_key = configuration_config.get('hypertts_pro_api_key', None)
        configuration.set_service_enabled_map(configuration_config.get('service_enabled', {}))
        configuration.set_service_config(configuration_config.get('service_config', {}))
        return configuration