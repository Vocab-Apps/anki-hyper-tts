
# python imports
import os
import sys
import re
import hashlib
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
import aqt.operations

constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_base)
options = __import__('options', globals(), locals(), [], sys._addon_import_level_base)
errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_base)
text_utils = __import__('text_utils', globals(), locals(), [], sys._addon_import_level_base)
config_models = __import__('config_models', globals(), locals(), [], sys._addon_import_level_base)
context = __import__('context', globals(), locals(), [], sys._addon_import_level_base)
logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_base)
gui = __import__('gui', globals(), locals(), [], sys._addon_import_level_base)
logger = logging_utils.get_child_logger(__name__)


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
        self.latest_saved_batch_name = None

        # do maintenance on the configuration
        self.perform_config_migration()


    def process_batch_audio(self, note_id_list, batch, batch_status, anki_collection):
        # for each note, generate audio
        with batch_status.get_batch_running_action_context():

            modified_notes = []

            for note_id in note_id_list:
                with batch_status.get_note_action_context(note_id, False) as note_action_context:
                    note = self.anki_utils.get_note_by_id(note_id)
                    # process note
                    source_text, processed_text, sound_file, full_filename = self.process_note_audio(batch, note, False,
                        context.AudioRequestContext(constants.AudioRequestReason.batch), None, anki_collection)
                    # update note action context
                    note_action_context.set_source_text(source_text)
                    note_action_context.set_processed_text(processed_text)
                    note_action_context.set_sound(sound_file)
                    note_action_context.set_status(constants.BatchNoteStatus.Done)                    
                    
                    modified_notes.append(note)
                if batch_status.must_continue == False:
                    logger.info('batch_status execution interrupted')
                    break

    def process_note_audio(self, batch: config_models.BatchConfig, note, add_mode, audio_request_context, text_override, anki_collection):
        target_field = batch.target.target_field

        if target_field not in note:
            raise errors.TargetFieldNotFoundError(target_field)

        source_text = self.get_source_text(note, batch.source, text_override)
        processed_text = self.process_text(source_text, batch.text_processing)

        full_filename, audio_filename = self.get_audio_file(processed_text, batch.voice_selection, audio_request_context)
        sound_tag, sound_file = self.get_collection_sound_tag(full_filename, audio_filename)

        target_field_content = note[target_field]
        
        # do we need to remove existing sound tags ?
        if batch.target.remove_sound_tag == True:
            target_field_content = self.strip_sound_tag(target_field_content)
        
        if batch.target.text_and_sound_tag == True:
            # user wants text and sound tag together, append the sound tag
            target_field_content = f'{target_field_content} {sound_tag}'
        else:
            # user only wants sound tags
            target_field_content = self.keep_only_sound_tags(target_field_content)
            target_field_content = f'{target_field_content} {sound_tag}'

        target_field_content = target_field_content.strip()

        note[target_field] = target_field_content
        if not add_mode:
            anki_collection.update_note(note)

        return source_text, processed_text, sound_file, full_filename

    def get_note_audio(self, batch, note, audio_request_context, text_override):
        source_text = self.get_source_text(note, batch.source, text_override)
        processed_text = text_utils.process_text(source_text, batch.text_processing)
        if len(processed_text) == 0:
            raise errors.SourceTextEmpty()        
        return self.get_audio_file(processed_text, batch.voice_selection, audio_request_context)

    def get_realtime_audio(self, realtime_model: config_models.RealtimeConfigSide, text):
        source_text = text
        processed_text = text_utils.process_text(source_text, realtime_model.text_processing)
        if len(processed_text) == 0:
            raise errors.SourceTextEmpty()
        return self.get_audio_file(processed_text, realtime_model.voice_selection, context.AudioRequestContext(constants.AudioRequestReason.realtime))

    def get_audio_file(self, processed_text, voice_selection, audio_request_context):
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
                logger.debug(f'about to generate audio file and write to file for {processed_text}')
                full_filename, audio_filename = self.generate_audio_write_file(processed_text, 
                    voice_with_options.voice, voice_with_options.options, audio_request_context)
                logger.debug(f'finished generating audio file and write to file for {processed_text}')
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
            logger.info(f'choosing from {len(voice_selection.voice_list)} voices')
            choice = random.choices(voice_selection.voice_list, weights=[x.random_weight for x in voice_selection.voice_list])
            return choice[0]
        elif voice_selection.selection_mode == constants.VoiceSelectionMode.priority:
            # remove that voice from possible list
            voice = voice_list.pop(0)
            return voice

    def editor_note_add_audio(self, batch: config_models.BatchConfig, editor_context: config_models.EditorContext):
        # used by :
        #  - component_batch.py
        #  - component_mappingrule.py

        logger.debug(f'editor_note_add_audio, editor_context: {editor_context}')
        # editor, note, add_mode, text_override
        # don't perform undo, it doesn't actually work, because of the way we call update_note
        audio_request_context = context.AudioRequestContext(constants.AudioRequestReason.editor_browser)
        if editor_context.add_mode:
            audio_request_context = context.AudioRequestContext(constants.AudioRequestReason.editor_add)
        text_override = None
        if batch.source.use_selection:
            if editor_context.selected_text != None:
                text_override = editor_context.selected_text
        logger.debug(f'text_override: {text_override}')
        source_text, processed_text, sound_file, full_filename = self.process_note_audio(batch, editor_context.note, editor_context.add_mode,
            audio_request_context, text_override, self.anki_utils.get_anki_collection())
        logger.debug('after process_note_audio')
        logger.debug(f'about to call editor.set_note: {editor_context.note}')
        def get_set_note_lambda(editor, note):
            def editor_set_note():
                editor.set_note(note)
            return editor_set_note
        self.anki_utils.run_on_main(get_set_note_lambda(editor_context.editor, editor_context.note))
        logger.debug('after set_note')
        self.anki_utils.play_sound(full_filename)

    def editor_note_process_rule(self, rule: config_models.MappingRule, editor_context: config_models.EditorContext):
        """process a single rule, unconditionally"""
        preset = self.load_preset(rule.preset_id)
        self.editor_note_add_audio(preset, editor_context)


    # editor related functions
    # ========================

    def get_editor_context(self, editor) -> config_models.EditorContext:
        selected_text = None
        selected_text_fieldname = None
        
        if len(editor.web.selectedText()) > 0:
            # need to get the field name for selected text
            deck_note_type = self.get_editor_deck_note_type(editor)
            current_field_num = editor.currentField
            if current_field_num != None:
                model = aqt.mw.col.models.get(deck_note_type.model_id)
                selected_text_fieldname = model['flds'][current_field_num]['name']
                selected_text = editor.web.selectedText()

        editor_context = config_models.EditorContext(note=editor.note, 
            editor=editor, 
            add_mode=editor.addMode,
            selected_text=selected_text,
            selected_text_fieldname=selected_text_fieldname)
        logger.debug(f'editor_context: {editor_context}')
        return editor_context

    def get_editor_deck_note_type(self, editor) -> config_models.DeckNoteType:
        note = editor.note
        if note == None:
            raise RuntimeError(f'editor.note not found')

        if editor.addMode:
            add_cards: aqt.addcards.AddCards = editor.parentWindow
            return config_models.DeckNoteType(model_id=note.mid, deck_id=add_cards.deckChooser.selectedId())
        else:
            if editor.card == None:
                raise RuntimeError(f'editor.card not found')
            return config_models.DeckNoteType(model_id=note.mid, deck_id=editor.card.did)


    # text processing
    # ===============

    def get_source_text(self, note, batch_source, text_override):
        if text_override != None:
            return text_override

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
        # logger.info(f'field_values: {field_values}')
        try:
            return source_template.format_map(field_values)
        except Exception as e:
            raise errors.TemplateExpansionError(e)

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
        # logger.info(f'before text processing: [{source_text}], after text processing: [{processed_text}]')
        if len(processed_text) == 0:
            raise errors.SourceTextEmpty()
        return processed_text

    # sound generation
    # ================

    def preview_note_audio_editor(self, batch, editor_context: config_models.EditorContext):
        text_override = None
        if batch.source.use_selection:
            if editor_context.selected_text != None:
                text_override = editor_context.selected_text
        self.preview_note_audio(batch, editor_context.note, text_override)

    def preview_note_audio(self, batch, note, text_override):
        batch.validate()
        full_filename, audio_filename = self.get_note_audio(batch, 
            note, context.AudioRequestContext(constants.AudioRequestReason.preview), text_override)
        self.anki_utils.play_sound(full_filename)
    
    def play_realtime_audio(self, realtime_model: config_models.RealtimeConfigSide, text):
        full_filename, audio_filename = self.get_realtime_audio(realtime_model, text)
        self.anki_utils.play_sound(full_filename)

    def play_sound(self, source_text, voice, options):
        logger.info(f'playing audio for {source_text}')
        if source_text == None or len(source_text) == 0:
            raise errors.SourceTextEmpty()        
        full_filename, audio_filename = self.generate_audio_write_file(source_text, voice, options, context.AudioRequestContext(constants.AudioRequestReason.preview))
        self.anki_utils.play_sound(full_filename)

    def get_preview_all_rules_task(self, deck_note_type: config_models.DeckNoteType,editor_context: config_models.EditorContext, preset_mapping_rules: config_models.PresetMappingRules):
        def preview_fn():
            for absolute_index, subset_index, rule in preset_mapping_rules.iterate_applicable_rules(deck_note_type, False):
                logger.debug(f'previewing audio for rule {rule}')
                preset = self.load_preset(rule.preset_id)
                # self.anki_utils.tooltip_message(f'Previewing audio for rule {preset.name}')
                self.anki_utils.run_on_main(lambda: self.anki_utils.tooltip_message(f'Previewing audio for {preset.name}'))
                self.preview_note_audio_editor(preset, editor_context)
        return preview_fn

    def get_preview_all_rules_done(self):
        def done_fn(result):
            with self.error_manager.get_single_action_context('Previewing Audio'):
                result = result.result()
        return done_fn

    def preview_all_mapping_rules(self, editor_context: config_models.EditorContext, preset_mapping_rules: config_models.PresetMappingRules = None):
        if preset_mapping_rules == None:
            # load the saved rules
            preset_mapping_rules = self.load_mapping_rules()

        if len(preset_mapping_rules.rules) == 0:
            raise errors.NoPresetMappingRulesDefined()

        deck_note_type = self.get_editor_deck_note_type(editor_context.editor)
        # we want audio generation to happen in the background, but the tooltips will be generated in foreground to display immediately
        self.anki_utils.run_in_background(self.get_preview_all_rules_task(deck_note_type, editor_context, preset_mapping_rules), self.get_preview_all_rules_done())

    def get_apply_all_rules_task(self, deck_note_type: config_models.DeckNoteType,editor_context: config_models.EditorContext, preset_mapping_rules: config_models.PresetMappingRules):
        def apply_fn():
            for absolute_index, subset_index, rule in preset_mapping_rules.iterate_applicable_rules(deck_note_type, False):
                logger.debug(f'previewing audio for rule {rule}')
                preset = self.load_preset(rule.preset_id)
                # self.anki_utils.tooltip_message(f'Previewing audio for rule {preset.name}')
                self.anki_utils.run_on_main(lambda: self.anki_utils.tooltip_message(f'Generating audio for {preset.name}'))
                self.editor_note_add_audio(preset, editor_context)
        return apply_fn

    def get_apply_all_rules_done(self):
        def done_fn(result):
            with self.error_manager.get_single_action_context('Running all rules'):
                result = result.result()
        return done_fn

    def apply_all_mapping_rules(self, editor_context: config_models.EditorContext, preset_mapping_rules: config_models.PresetMappingRules = None):
        if preset_mapping_rules == None:
            # load the saved rules
            preset_mapping_rules = self.load_mapping_rules()

        if len(preset_mapping_rules.rules) == 0:
            raise errors.NoPresetMappingRulesDefined()

        deck_note_type = self.get_editor_deck_note_type(editor_context.editor)
        # we want audio generation to happen in the background, but the tooltips will be generated in foreground to display immediately
        self.anki_utils.run_in_background(self.get_apply_all_rules_task(deck_note_type, editor_context, preset_mapping_rules), self.get_apply_all_rules_done())


    # processing of sound tags / collection stuff
    # ===========================================

    def generate_audio_write_file(self, source_text, voice, voice_options, audio_request_context):
        format = options.AudioFormat.mp3 # default to mp3
        if options.AUDIO_FORMAT_PARAMETER in voice_options:
            format = options.AudioFormat[voice_options[options.AUDIO_FORMAT_PARAMETER]]

        # write to user files directory
        hash_str = self.get_hash_for_audio_request(source_text, voice, voice_options)
        audio_filename = self.get_audio_filename(hash_str, format)
        full_filename = self.get_full_audio_file_name(hash_str, format)
        logger.info(f'requesting audio for hash {hash_str}, full filename {full_filename}')
        if not os.path.exists(full_filename) or os.path.getsize(full_filename) == 0:
            audio_data = self.service_manager.get_tts_audio(source_text, voice, voice_options, audio_request_context)
            logger.info(f'not found in cache, requesting')
            logger.debug(f'opening {full_filename}')
            f = open(full_filename, 'wb')
            logger.debug(f'done opening {full_filename}')
            f.write(audio_data)
            logger.debug(f'wrote audio data')
            f.close()
        else:
            logger.info(f'file exists in cache')
        return full_filename, audio_filename

    def get_collection_sound_tag(self, full_filename, audio_filename):
        self.anki_utils.media_add_file(full_filename)
        return f'[sound:{audio_filename}]', audio_filename

    def get_full_audio_file_name(self, hash_str, format: options.AudioFormat):
        # return the absolute path of the audio file in the user_files directory
        user_files_dir = self.anki_utils.get_user_files_dir()
        # check whether the directory exists
        if not os.path.isdir(user_files_dir):
            raise errors.MissingDirectory(user_files_dir)
        filename = self.get_audio_filename(hash_str, format)
        return os.path.join(user_files_dir, filename)
    
    def get_audio_filename(self, hash_str, format: options.AudioFormat):
        extension_map = {
            options.AudioFormat.mp3: 'mp3',
            options.AudioFormat.ogg_vorbis: 'ogg',
            options.AudioFormat.ogg_opus: 'ogg',
        }
        extension = extension_map[format]
        filename = f'hypertts-{hash_str}.{extension}'
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

    def keep_only_sound_tags(self, field_value):
        matches = re.findall(r'\[sound:[^\]]+\]', field_value)
        return ' '.join(matches)


    # processing of Anki TTS tags
    # ===========================

    def get_audio_filename_tts_tag(self, tts_tag):
        hypertts_preset = self.extract_hypertts_preset(tts_tag.other_args)
        realtime_side_model = self.get_realtime_side_config(hypertts_preset)
        full_filename, audio_filename = self.get_realtime_audio(realtime_side_model, tts_tag.field_text)
        return full_filename

    def build_realtime_tts_tag(self, realtime_side_model: config_models.RealtimeConfigSide, setting_key):
        logger.debug('build_realtime_tts_tag')
        if realtime_side_model.source.mode == constants.RealtimeSourceType.AnkiTTSTag:
            logger.debug(f'build_realtime_tts_tag, realtime_side_model: {realtime_side_model}')
            # get the audio language of the first voice
            voice_selection = realtime_side_model.voice_selection
            logger.debug(f'voice_selection.selection_mode: {voice_selection.selection_mode}')
            if voice_selection.selection_mode == constants.VoiceSelectionMode.single:
                audio_language = voice_selection.voice.voice.language
            else:
                audio_language = voice_selection.get_voice_list()[0].voice.language
            field_format = realtime_side_model.source.field_name
            if realtime_side_model.source.field_type == constants.AnkiTTSFieldType.Cloze:
                field_format = f'cloze:{realtime_side_model.source.field_name}'
            elif realtime_side_model.source.field_type == constants.AnkiTTSFieldType.ClozeOnly:
                field_format = f'cloze-only:{realtime_side_model.source.field_name}'
            return '{{tts ' + f"""{audio_language.name} {constants.TTS_TAG_HYPERTTS_PRESET}={setting_key} voices={constants.TTS_TAG_VOICE}:{field_format}""" + '}}'
        else:
            raise Exception(f'unsupported RealtimeSourceType: {realtime_side_model.source.mode}')

    def extract_hypertts_preset(self, extra_args_array):
        subset = [x for x in extra_args_array if constants.TTS_TAG_HYPERTTS_PRESET in x]
        if len(subset) != 1:
            logger.error(f'could not process TTS tag extra args: {extra_args_array}')
            raise errors.TTSTagProcessingError()
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


    def card_template_has_tts_tag(self, note, side, card_ord):
        # return preset name if found
        note_model = note.note_type()
        card_template = note_model["tmpls"][card_ord]
        side_template_key = 'qfmt'
        if side == constants.AnkiCardSide.Back:
            side_template_key = 'afmt'
        side_template = card_template[side_template_key]
        side_template = side_template.replace('\n', ' ')
        m = re.match('.*{{tts.*' + constants.TTS_TAG_HYPERTTS_PRESET + '=([^\s]+).*}}.*', side_template)
        if m != None:
            preset_name = m.groups()[0]
            preset_name = preset_name.replace(side.name + '_', '')
            logger.info(f'found preset name in TTS tag inside card template: {preset_name}')
            return preset_name
        else:
            logger.info(f'didnt find a TTS tag in card template: {side_template}')
        return None


    def remove_tts_tag(self, card_template):
        return re.sub('{{tts.*}}', '', card_template)

    def set_tts_tag_note_model(self, realtime_side_model: config_models.RealtimeConfigSide, setting_key, note_model, side, card_ord, clear_only):
        logger.debug('set_tts_tag_note_model')
        # build tts tag
        tts_tag = self.build_realtime_tts_tag(realtime_side_model, setting_key)
        logger.info(f'tts tag: {tts_tag}')

        return self.alter_tts_tag_note_model(note_model, side, card_ord, clear_only, tts_tag)


    def alter_tts_tag_note_model(self, note_model, side, card_ord, clear_only, tts_tag):
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
        logger.debug(f'render_card_template_extract_tts_tag, note_model {pprint.pformat(note_model, compact=True, width=500)}')

        card = self.anki_utils.create_card_from_note(note, card_ord, note_model, note_model["tmpls"][card_ord])
        if side == constants.AnkiCardSide.Front:
            return self.anki_utils.extract_tts_tags(card.question_av_tags())
        elif side == constants.AnkiCardSide.Back:
            return self.anki_utils.extract_tts_tags(card.answer_av_tags())

    def build_side_settings_key(self, card_side: constants.AnkiCardSide, settings_key):
        return f'{card_side.name}_{settings_key}'


    def persist_realtime_config_update_note_type(self, realtime_model: config_models.RealtimeConfig, note, card_ord, current_settings_key):
        logger.debug('persist_realtime_config_update_note_type')
        undo_id = self.anki_utils.undo_tts_tag_start()

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

        self.anki_utils.undo_end(undo_id)

    def remove_tts_tags(self, note, card_ord):
        logger.debug('remove_tts_tags')
        undo_id = self.anki_utils.undo_tts_tag_start()
        note_model = note.note_type()
        side = constants.AnkiCardSide.Front
        note_model = self.alter_tts_tag_note_model(note_model, side, card_ord, True, None)
        side = constants.AnkiCardSide.Back
        note_model = self.alter_tts_tag_note_model(note_model, side, card_ord, True, None)
        self.anki_utils.save_note_type_update(note_model)
        self.anki_utils.undo_end(undo_id)        


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
                    logger.info('batch_status execution interrupted')
                    break

    def get_source_processed_text(self, note, batch_source, text_processing):
        source_text = self.get_source_text(note, batch_source, None)
        logger.debug(f'get_source_processed_text: source_text: {source_text}')
        processed_text = text_utils.process_text(source_text, text_processing)
        return source_text, processed_text

    # functions related to addon config
    # =================================

    # presets
    
    def get_preset_list(self) -> List[config_models.PresetInfo]:
        if constants.CONFIG_PRESETS not in self.config:
            return []
        preset_list = []
        for preset_id, preset_data in self.config[constants.CONFIG_PRESETS].items():
            preset_list.append(config_models.PresetInfo(id=preset_id, name=preset_data['name']))
        # sort alphabetically
        preset_list.sort(key=lambda x: x.name)
        return preset_list

    def save_preset(self, preset: config_models.BatchConfig):
        preset.validate()
        if constants.CONFIG_PRESETS not in self.config:
            self.config[constants.CONFIG_PRESETS] = {}
        self.config[constants.CONFIG_PRESETS][preset.uuid] = preset.serialize()
        self.anki_utils.write_config(self.config)
        logger.info(f'saved preset [{preset.name}]')

    def load_preset(self, preset_id: str) -> config_models.BatchConfig:
        logger.info(f'loading preset [{preset_id}]')
        if preset_id not in self.config[constants.CONFIG_PRESETS]:
            raise errors.PresetNotFound(preset_id)
        return self.deserialize_batch_config(self.config[constants.CONFIG_PRESETS][preset_id])

    def get_preset_name(self, preset_id: str) -> str:
        if preset_id not in self.config[constants.CONFIG_PRESETS]:
            raise errors.PresetNotFound(preset_id)        
        return self.config[constants.CONFIG_PRESETS][preset_id]['name']

    def delete_preset(self, preset_id: str):
        if preset_id not in self.config[constants.CONFIG_PRESETS]:
            raise errors.PresetNotFound(preset_id)
        del self.config[constants.CONFIG_PRESETS][preset_id]
        self.anki_utils.write_config(self.config)        

    def get_next_preset_name(self) -> str:
        """returns the next available preset name which doesn't collide with others"""
        preset_list: List[config_models.PresetInfo] = self.get_preset_list()
        preset_name_dict = {}
        for preset_info in preset_list:
            preset_name_dict[preset_info.name] = True
        i = 1
        new_preset_name = f'Preset {i}'
        while new_preset_name in preset_name_dict:
            i += 1
            new_preset_name = f'Preset {i}'
        return new_preset_name

    # mapping rules
    def save_mapping_rules(self, mapping_rules: config_models.PresetMappingRules):
        self.config[constants.CONFIG_MAPPING_RULES] = config_models.serialize_preset_mapping_rules(mapping_rules)
        self.anki_utils.write_config(self.config)
        logger.info('saved mapping rules')

    def load_mapping_rules(self) -> config_models.PresetMappingRules:
        if constants.CONFIG_MAPPING_RULES not in self.config:
            return config_models.PresetMappingRules()
        return config_models.deserialize_preset_mapping_rules(self.config[constants.CONFIG_MAPPING_RULES])
    
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
        self.anki_utils.write_config(self.config)
        return final_key

    def load_realtime_config(self, settings_key):
        logger.info(f'loading realtime config [{settings_key}]')
        if settings_key not in self.config[constants.CONFIG_REALTIME_CONFIG]:
            raise errors.RealtimePresetNotFound(settings_key)
        realtime_config = self.config[constants.CONFIG_REALTIME_CONFIG][settings_key]
        logger.info(f'loaded realtime config {pprint.pformat(realtime_config, compact=True, width=500)}')
        return self.deserialize_realtime_config(realtime_config)

    # services config

    def save_configuration(self, configuration_model):
        configuration_model = self.service_manager.remove_non_existent_services(configuration_model)
        configuration_model.validate()
        self.config[constants.CONFIG_CONFIGURATION] = config_models.serialize_configuration(configuration_model)
        self.anki_utils.write_config(self.config)

    def get_configuration(self):
        return self.deserialize_configuration(self.config.get(constants.CONFIG_CONFIGURATION, {}))

    def hypertts_pro_enabled(self):
        return self.get_configuration().hypertts_pro_api_key_set()

    def set_editor_use_selection(self, use_selection):
        self.config[constants.CONFIG_USE_SELECTION] = use_selection
        self.anki_utils.write_config(self.config)

    def get_editor_use_selection(self):
        return self.config.get(constants.CONFIG_USE_SELECTION, False)

    # preferences
    def get_preferences(self):
        return self.deserialize_preferences(self.config.get(constants.CONFIG_PREFERENCES, {}))

    def save_preferences(self, preferences_model):
        self.config[constants.CONFIG_PREFERENCES] = config_models.serialize_preferences(preferences_model)
        self.anki_utils.write_config(self.config)

    # deserialization routines for loading from config
    # ================================================

    def perform_config_migration(self):
        self.config = config_models.migrate_configuration(self.anki_utils, self.config)
        self.anki_utils.write_config(self.config)

    def deserialize_batch_config(self, batch_config):
        batch = config_models.BatchConfig(self.anki_utils)
        source = config_models.deserialize_batchsource(batch_config['source'])
        batch_target_config = batch_config['target']
        target = config_models.BatchTarget(batch_target_config['target_field'], batch_target_config['text_and_sound_tag'], batch_target_config['remove_sound_tag'])
        voice_selection = self.deserialize_voice_selection(batch_config['voice_selection'])

        text_processing_config = batch_config.get('text_processing', {})
        text_processing = self.deserialize_text_processing(text_processing_config)

        batch.set_source(source)
        batch.set_target(target)
        batch.set_voice_selection(voice_selection)
        batch.text_processing = text_processing
        batch.uuid = batch_config['uuid']
        batch.name = batch_config['name']
        
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
        text_processing.strip_brackets = text_processing_config.get('strip_brackets', constants.TEXT_PROCESSING_DEFAULT_STRIP_BRACKETS)
        text_processing.ssml_convert_characters = text_processing_config.get('ssml_convert_characters', constants.TEXT_PROCESSING_DEFAULT_SSML_CHARACTERS)
        text_processing.run_replace_rules_after = text_processing_config.get('run_replace_rules_after', constants.TEXT_PROCESSING_DEFAULT_REPLACE_AFTER)
        text_processing.ignore_case = text_processing_config.get('ignore_case', constants.TEXT_PROCESSING_DEFAULT_IGNORE_CASE)
        rules = text_processing_config.get('text_replacement_rules', [])
        for rule in rules:
            rule_obj = config_models.TextReplacementRule(constants.TextReplacementRuleType[rule['rule_type']])
            rule_obj.source = rule['source']
            rule_obj.target = rule['target']
            text_processing.add_text_replacement_rule(rule_obj)
        return text_processing

    def deserialize_configuration(self, configuration_config):
        return config_models.deserialize_configuration(configuration_config)

    def deserialize_preferences(self, preferences_config):
        return config_models.deserialize_preferences(preferences_config)

    # error handling
    # ==============
    def get_tts_player_action_context(self):
        return self.error_manager.get_single_action_context_configurable('Playing Realtime Audio', 
            self.get_preferences().error_handling.realtime_tts_errors_dialog_type)