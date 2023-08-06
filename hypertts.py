
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


    def process_batch_audio(self, note_id_list, batch, batch_status):
        # for each note, generate audio
        with batch_status.get_batch_running_action_context():
            undo_id = self.anki_utils.undo_start()
            for note_id in note_id_list:
                with batch_status.get_note_action_context(note_id, False) as note_action_context:
                    note = self.anki_utils.get_note_by_id(note_id)
                    # process note
                    source_text, processed_text, sound_file, full_filename = self.process_note_audio(batch, note, False,
                        context.AudioRequestContext(constants.AudioRequestReason.batch), None)
                    # update note action context
                    note_action_context.set_source_text(source_text)
                    note_action_context.set_processed_text(processed_text)
                    note_action_context.set_sound(sound_file)
                    note_action_context.set_status(constants.BatchNoteStatus.Done)                    
                if batch_status.must_continue == False:
                    logger.info('batch_status execution interrupted')
                    break
            self.anki_utils.undo_end(undo_id)

    def process_note_audio(self, batch, note, add_mode, audio_request_context, text_override):
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
            self.anki_utils.update_note(note)

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

    def editor_note_add_audio(self, batch, editor, note, add_mode, text_override):
        logger.debug('editor_note_add_audio')
        undo_id = self.anki_utils.undo_start()
        audio_request_context = context.AudioRequestContext(constants.AudioRequestReason.editor_browser)
        if add_mode:
            audio_request_context = context.AudioRequestContext(constants.AudioRequestReason.editor_add)
        logger.debug('before process_note_audio')
        source_text, processed_text, sound_file, full_filename = self.process_note_audio(batch, note, add_mode,
            audio_request_context, text_override)
        logger.debug('after process_note_audio')
        logger.debug(f'about to call editor.set_note: {note}')
        def get_set_note_lambda(editor, note):
            def editor_set_note():
                editor.set_note(note)
            return editor_set_note
        self.anki_utils.run_on_main(get_set_note_lambda(editor, note))
        logger.debug('after set_note')
        self.anki_utils.undo_end(undo_id)
        self.anki_utils.play_sound(full_filename)

    # editor pycmd commands processing 
    # ================================

    def decode_preview_add_message(self, msg):
        components = msg.split(':')
        command = components[1]
        enable_selection_str = components[2]
        enable_selection = enable_selection_str == 'true'
        final_components = components[3:]
        batch_name = ':'.join(final_components)
        return command, batch_name, enable_selection

    def process_bridge_cmd(self, str, editor, handled):
        if str.startswith(constants.PYCMD_ADD_AUDIO_PREFIX) or str.startswith(constants.PYCMD_PREVIEW_AUDIO_PREFIX):
            command, batch_name, enable_selection = self.decode_preview_add_message(str)
            text_override = None
            if enable_selection:
                if len(editor.web.selectedText()) > 0:
                    text_override = editor.web.selectedText()

            self.set_editor_use_selection(enable_selection)

            if command == constants.PYCMD_ADD_AUDIO:
                logger.info(f'processing pycmd bridge command: {str}')
                if batch_name == constants.BATCH_CONFIG_NEW:
                    self.clear_latest_saved_batch_name()
                    gui.launch_batch_dialog_editor(self, editor.note, editor, editor.addMode)
                    gui.update_editor_batch_list(self, editor)
                else:
                    with self.error_manager.get_single_action_context('Adding Audio to Note'):
                        logger.info(f'received message: {str}')
                        # logger.debug(f'editor.web.selectedText(): {type(editor.web)} {editor.web.selectedText()}')

                        batch = self.load_batch_config(batch_name)
                        self.set_editor_last_used_batch_name(batch_name)
                        self.editor_note_add_audio(batch, editor, editor.note, editor.addMode, text_override)
                return True, None

            if command == constants.PYCMD_PREVIEW_AUDIO:
                with self.error_manager.get_single_action_context('Previewing Audio'):
                    logger.info(f'received message: {str}')
                    batch = self.load_batch_config(batch_name)
                    self.set_editor_last_used_batch_name(batch_name)
                    self.preview_note_audio(batch, editor.note, text_override)
                return True, None        

        return handled            

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

    # batch config

    def save_batch_config(self, batch_name, batch):
        batch.validate()
        if constants.CONFIG_BATCH_CONFIG not in self.config:
            self.config[constants.CONFIG_BATCH_CONFIG] = {}
        self.config[constants.CONFIG_BATCH_CONFIG][batch_name] = batch.serialize()
        self.anki_utils.write_config(self.config)
        self.set_latest_saved_batch_name(batch_name)
        logger.info(f'saved batch config [{batch_name}]')

    def load_batch_config(self, batch_name):
        logger.info(f'loading batch config [{batch_name}]')
        if batch_name not in self.config[constants.CONFIG_BATCH_CONFIG]:
            raise errors.PresetNotFound(batch_name)
        return self.deserialize_batch_config(self.config[constants.CONFIG_BATCH_CONFIG][batch_name])

    def delete_batch_config(self, batch_name):
        logger.info(f'deleting batch config [{batch_name}]')
        if batch_name not in self.config[constants.CONFIG_BATCH_CONFIG]:
            raise errors.PresetNotFound(batch_name)
        del self.config[constants.CONFIG_BATCH_CONFIG][batch_name]
        self.anki_utils.write_config(self.config)

    def get_batch_config_list(self):
        if constants.CONFIG_BATCH_CONFIG not in self.config:
            return []
        batch_config_list = list(self.config[constants.CONFIG_BATCH_CONFIG].keys())
        batch_config_list.sort()
        return batch_config_list

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
        self.config[constants.CONFIG_CONFIGURATION] = configuration_model.serialize()
        self.anki_utils.write_config(self.config)

    def get_configuration(self):
        return self.deserialize_configuration(self.config.get(constants.CONFIG_CONFIGURATION, {}))

    def hypertts_pro_enabled(self):
        return self.get_configuration().hypertts_pro_api_key_set()

    def clear_latest_saved_batch_name(self):
        self.latest_saved_batch_name = None

    def set_latest_saved_batch_name(self, batch_name):
        self.latest_saved_batch_name = batch_name

    def set_editor_last_used_batch_name(self, batch_name):
        self.latest_saved_batch_name = None
        self.config[constants.CONFIG_LAST_USED_BATCH] = batch_name
        self.anki_utils.write_config(self.config)

    def get_editor_default_batch_name(self):
        if self.latest_saved_batch_name != None:
            return self.latest_saved_batch_name
        latest_used_editor_batch_name = self.config.get(constants.CONFIG_LAST_USED_BATCH, None)
        if latest_used_editor_batch_name != None:
            return latest_used_editor_batch_name
        return constants.BATCH_CONFIG_NEW

    def set_editor_use_selection(self, use_selection):
        self.config[constants.CONFIG_USE_SELECTION] = use_selection
        self.anki_utils.write_config(self.config)

    def get_editor_use_selection(self):
        return self.config.get(constants.CONFIG_USE_SELECTION, False)

    # preferences
    def get_preferences(self):
        return self.deserialize_preferences(self.config.get(constants.CONFIG_PREFERENCES, {}))

    def save_preferences(self, preferences_model):
        preferences_model.validate()
        self.config[constants.CONFIG_PREFERENCES] = preferences_model.serialize()
        self.anki_utils.write_config(self.config)

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
        configuration = config_models.Configuration()
        configuration.hypertts_pro_api_key = configuration_config.get('hypertts_pro_api_key', None)
        configuration.set_service_enabled_map(configuration_config.get('service_enabled', {}))
        configuration.set_service_config(configuration_config.get('service_config', {}))
        return configuration

    def deserialize_preferences(self, preferences_config):
        return config_models.Preferences(**preferences_config)

    # error handling
    # ==============
    def get_tts_player_action_context(self):
        return self.error_manager.get_single_action_context_configurable('Playing Realtime Audio', constants.ErrorDialogType)