import unittest
from unittest import mock
import datetime
import requests.exceptions

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from hypertts_addon import errors
from hypertts_addon import context
from hypertts_addon import constants
from hypertts_addon import config_models
from hypertts_addon import batch_status
from hypertts_addon import cloudlanguagetools as clt_module
from hypertts_addon import voice as voice_module
from test_utils import testing_utils


def make_mock_voice():
    v = mock.Mock()
    v.service = 'Azure'
    v.name = 'TestVoice'
    v.voice_key = {'name': 'test-voice'}
    v.service_fee = mock.Mock()
    v.service_fee.name = 'free'
    return v


def make_mock_context():
    ctx = context.AudioRequestContext(constants.AudioRequestReason.batch)
    return ctx


class TestErrorHierarchy(unittest.TestCase):

    def test_service_request_error_is_hypertts_error(self):
        e = errors.ServiceRequestError('text', None, 'msg')
        self.assertIsInstance(e, errors.HyperTTSError)

    def test_permanent_error_hierarchy(self):
        e = errors.PermanentError('text', None, 'msg')
        self.assertIsInstance(e, errors.ServiceRequestError)
        self.assertIsInstance(e, errors.HyperTTSError)

    def test_transient_error_hierarchy(self):
        e = errors.TransientError('text', None, 'msg')
        self.assertIsInstance(e, errors.ServiceRequestError)
        self.assertIsInstance(e, errors.HyperTTSError)

    def test_rate_limit_error(self):
        e = errors.RateLimitRetryAfterError('text', None, 'rate limited', 30)
        self.assertIsInstance(e, errors.TransientError)
        self.assertEqual(e.retry_after, 30)

    def test_timeout_error(self):
        e = errors.ServiceTimeoutError('text', None, 'timed out')
        self.assertIsInstance(e, errors.TransientError)

    def test_unknown_service_error(self):
        e = errors.UnknownServiceError('text', None, 'unknown')
        self.assertIsInstance(e, errors.TransientError)

    def test_audio_not_found_is_permanent(self):
        voice = make_mock_voice()
        e = errors.AudioNotFoundError('hello', voice)
        self.assertIsInstance(e, errors.PermanentError)
        self.assertIsInstance(e, errors.ServiceRequestError)
        self.assertIsInstance(e, errors.HyperTTSError)
        self.assertEqual(e.source_text, 'hello')
        self.assertEqual(e.voice, voice)

    def test_audio_not_found_str_backward_compatible(self):
        voice = make_mock_voice()
        e = errors.AudioNotFoundError('hello', voice)
        self.assertIn('Audio not found', str(e))

    def test_audio_not_found_any_voice_is_permanent(self):
        e = errors.AudioNotFoundAnyVoiceError('hello')
        self.assertIsInstance(e, errors.PermanentError)
        self.assertEqual(e.source_text, 'hello')
        self.assertIsNone(e.voice)

    def test_audio_not_found_any_voice_str_backward_compatible(self):
        e = errors.AudioNotFoundAnyVoiceError('hello')
        self.assertIn('Audio not found in any voices', str(e))

    def test_permission_error_is_permanent(self):
        voice = make_mock_voice()
        e = errors.ServicePermissionError('text', voice, 'Forbidden')
        self.assertIsInstance(e, errors.PermanentError)
        self.assertIsInstance(e, errors.ServiceRequestError)
        self.assertIsInstance(e, errors.HyperTTSError)
        self.assertEqual(e.error_message, 'Forbidden')

    def test_service_request_error_attributes(self):
        voice = make_mock_voice()
        e = errors.ServiceRequestError('text', voice, 'some error')
        self.assertEqual(e.source_text, 'text')
        self.assertEqual(e.voice, voice)
        self.assertEqual(e.error_message, 'some error')

    def test_request_error_unchanged(self):
        """RequestError should still be a HyperTTSError but NOT a ServiceRequestError."""
        voice = make_mock_voice()
        e = errors.RequestError('text', voice, 'msg')
        self.assertIsInstance(e, errors.HyperTTSError)
        self.assertNotIsInstance(e, errors.ServiceRequestError)


class TestCloudLanguageToolsVocabAiErrorMapping(unittest.TestCase):

    def setUp(self):
        self.clt = clt_module.CloudLanguageTools()
        self.clt.config = mock.Mock()
        self.clt.config.use_vocabai_api = True
        self.clt.config.hypertts_pro_api_key = 'test_key'
        self.clt.config.user_uuid = 'test_uuid'
        self.clt.config.vocabai_api_url_override = None
        self.clt.disable_ssl_verification = False
        self.voice = make_mock_voice()
        self.ctx = make_mock_context()
        # mock get_audio_language_for_voice
        self.lang_patcher = mock.patch.object(voice_module, 'get_audio_language_for_voice')
        mock_get_lang = self.lang_patcher.start()
        mock_lang = mock.Mock()
        mock_lang.lang.name = 'fr'
        mock_get_lang.return_value = mock_lang

    def tearDown(self):
        self.lang_patcher.stop()

    @mock.patch('requests.post')
    def test_200_success(self, mock_post):
        mock_post.return_value = mock.Mock(status_code=200, content=b'audio_data')
        result = self.clt.get_tts_audio('bonjour', self.voice, {}, self.ctx)
        self.assertEqual(result, b'audio_data')

    @mock.patch('requests.post')
    def test_400_with_error_key(self, mock_post):
        mock_post.return_value = mock.Mock(
            status_code=400,
            json=lambda: {'error': 'invalid voice key'}
        )
        with self.assertRaises(errors.PermanentError) as cm:
            self.clt.get_tts_audio('bonjour', self.voice, {}, self.ctx)
        self.assertEqual(cm.exception.error_message, 'invalid voice key')

    @mock.patch('requests.post')
    def test_400_validation_error(self, mock_post):
        mock_post.return_value = mock.Mock(
            status_code=400,
            json=lambda: {'text': ['This field is required.']}
        )
        with self.assertRaises(errors.PermanentError):
            self.clt.get_tts_audio('bonjour', self.voice, {}, self.ctx)

    @mock.patch('requests.post')
    def test_403_forbidden(self, mock_post):
        mock_post.return_value = mock.Mock(
            status_code=403,
            json=lambda: {'detail': 'insufficient character credit'}
        )
        with self.assertRaises(errors.ServicePermissionError) as cm:
            self.clt.get_tts_audio('bonjour', self.voice, {}, self.ctx)
        self.assertIsInstance(cm.exception, errors.PermanentError)
        self.assertIn('insufficient character credit', cm.exception.error_message)

    @mock.patch('requests.post')
    def test_503_rate_limit(self, mock_post):
        mock_post.return_value = mock.Mock(
            status_code=503,
            json=lambda: {'error': 'rate limited', 'retry_after': 32}
        )
        with self.assertRaises(errors.RateLimitRetryAfterError) as cm:
            self.clt.get_tts_audio('bonjour', self.voice, {}, self.ctx)
        self.assertEqual(cm.exception.retry_after, 32)

    @mock.patch('requests.post')
    def test_504_transient(self, mock_post):
        mock_post.return_value = mock.Mock(
            status_code=504,
            json=lambda: {'error': 'temporary failure'}
        )
        with self.assertRaises(errors.TransientError) as cm:
            self.clt.get_tts_audio('bonjour', self.voice, {}, self.ctx)
        self.assertEqual(cm.exception.error_message, 'temporary failure')

    @mock.patch('requests.post')
    def test_404_audio_not_found(self, mock_post):
        mock_post.return_value = mock.Mock(status_code=404)
        with self.assertRaises(errors.AudioNotFoundError) as cm:
            self.clt.get_tts_audio('bonjour', self.voice, {}, self.ctx)
        self.assertEqual(cm.exception.source_text, 'bonjour')

    @mock.patch('requests.post')
    def test_timeout(self, mock_post):
        mock_post.side_effect = requests.exceptions.Timeout('timed out')
        with self.assertRaises(errors.ServiceTimeoutError):
            self.clt.get_tts_audio('bonjour', self.voice, {}, self.ctx)

    @mock.patch('requests.post')
    def test_unknown_status_code(self, mock_post):
        mock_post.return_value = mock.Mock(
            status_code=502,
            content=b'bad gateway'
        )
        with self.assertRaises(errors.UnknownServiceError):
            self.clt.get_tts_audio('bonjour', self.voice, {}, self.ctx)

    @mock.patch('requests.post')
    def test_v5_url_used(self, mock_post):
        mock_post.return_value = mock.Mock(status_code=200, content=b'audio')
        self.clt.get_tts_audio('bonjour', self.voice, {}, self.ctx)
        call_args = mock_post.call_args
        url = call_args[1].get('url', call_args[0][0] if call_args[0] else None)
        self.assertIn('/v5/audio', url)

    @mock.patch('requests.post')
    def test_retry_fields_in_request(self, mock_post):
        mock_post.return_value = mock.Mock(status_code=200, content=b'audio')
        self.ctx.retry_count = 1
        self.ctx.retry_max = 3
        self.clt.get_tts_audio('bonjour', self.voice, {}, self.ctx)
        call_args = mock_post.call_args
        data = call_args[1].get('json', call_args[0][1] if len(call_args[0]) > 1 else None)
        self.assertEqual(data['retry_count'], 1)
        self.assertEqual(data['retry_max'], 3)


    @mock.patch('requests.post')
    def test_non_timeout_request_exception(self, mock_post):
        """Non-Timeout exception from requests.post is logged and raised as UnknownServiceError."""
        mock_post.side_effect = requests.exceptions.ConnectionError('connection refused')
        with self.assertRaises(errors.UnknownServiceError) as cm:
            self.clt.get_tts_audio('bonjour', self.voice, {}, self.ctx)
        self.assertIn('connection refused', cm.exception.error_message)

    @mock.patch('requests.post')
    def test_400_unparseable_json_raises_permanent(self, mock_post):
        """400 with unparseable JSON body raises PermanentError."""
        resp = mock.Mock(status_code=400, content=b'not json')
        resp.json.side_effect = ValueError('No JSON')
        mock_post.return_value = resp
        with self.assertRaises(errors.PermanentError):
            self.clt.get_tts_audio('bonjour', self.voice, {}, self.ctx)

    @mock.patch('requests.post')
    def test_403_unparseable_json_raises_permission(self, mock_post):
        """403 with unparseable JSON body raises ServicePermissionError."""
        resp = mock.Mock(status_code=403, content=b'not json')
        resp.json.side_effect = ValueError('No JSON')
        mock_post.return_value = resp
        with self.assertRaises(errors.ServicePermissionError) as cm:
            self.clt.get_tts_audio('bonjour', self.voice, {}, self.ctx)
        self.assertEqual(cm.exception.error_message, 'Forbidden')

    @mock.patch('requests.post')
    def test_503_unparseable_json_raises_rate_limit(self, mock_post):
        """503 with unparseable JSON body raises RateLimitRetryAfterError with defaults."""
        resp = mock.Mock(status_code=503, content=b'not json')
        resp.json.side_effect = ValueError('No JSON')
        mock_post.return_value = resp
        with self.assertRaises(errors.RateLimitRetryAfterError) as cm:
            self.clt.get_tts_audio('bonjour', self.voice, {}, self.ctx)
        self.assertEqual(cm.exception.retry_after, 30)

    @mock.patch('requests.post')
    def test_504_unparseable_json_raises_transient(self, mock_post):
        """504 with unparseable JSON body raises TransientError."""
        resp = mock.Mock(status_code=504, content=b'not json')
        resp.json.side_effect = ValueError('No JSON')
        mock_post.return_value = resp
        with self.assertRaises(errors.TransientError):
            self.clt.get_tts_audio('bonjour', self.voice, {}, self.ctx)

    @mock.patch('requests.post')
    def test_403_default_detail(self, mock_post):
        """403 with JSON but no 'detail' key uses 'Forbidden' as default."""
        mock_post.return_value = mock.Mock(
            status_code=403,
            json=lambda: {'other_key': 'value'}
        )
        with self.assertRaises(errors.ServicePermissionError) as cm:
            self.clt.get_tts_audio('bonjour', self.voice, {}, self.ctx)
        self.assertEqual(cm.exception.error_message, 'Forbidden')


class TestCloudLanguageToolsCLTErrorMapping(unittest.TestCase):

    def setUp(self):
        self.clt = clt_module.CloudLanguageTools()
        self.clt.config = mock.Mock()
        self.clt.config.use_vocabai_api = False
        self.clt.config.hypertts_pro_api_key = 'test_key'
        self.clt.disable_ssl_verification = False
        self.voice = make_mock_voice()
        self.ctx = make_mock_context()
        self.lang_patcher = mock.patch.object(voice_module, 'get_audio_language_for_voice')
        mock_get_lang = self.lang_patcher.start()
        mock_lang = mock.Mock()
        mock_lang.lang.name = 'fr'
        mock_get_lang.return_value = mock_lang

    def tearDown(self):
        self.lang_patcher.stop()

    @mock.patch('requests.post')
    def test_200_success(self, mock_post):
        mock_post.return_value = mock.Mock(status_code=200, content=b'audio_data')
        result = self.clt.get_tts_audio('bonjour', self.voice, {}, self.ctx)
        self.assertEqual(result, b'audio_data')

    @mock.patch('requests.post')
    def test_404_audio_not_found(self, mock_post):
        mock_post.return_value = mock.Mock(status_code=404)
        with self.assertRaises(errors.AudioNotFoundError):
            self.clt.get_tts_audio('bonjour', self.voice, {}, self.ctx)

    @mock.patch('requests.post')
    def test_other_status_unknown_service_error(self, mock_post):
        mock_post.return_value = mock.Mock(status_code=500, content=b'error')
        with self.assertRaises(errors.UnknownServiceError):
            self.clt.get_tts_audio('bonjour', self.voice, {}, self.ctx)

    @mock.patch('requests.post')
    def test_timeout(self, mock_post):
        mock_post.side_effect = requests.exceptions.Timeout('timed out')
        with self.assertRaises(errors.ServiceTimeoutError):
            self.clt.get_tts_audio('bonjour', self.voice, {}, self.ctx)

    @mock.patch('requests.post')
    def test_connection_error(self, mock_post):
        """Non-Timeout exception from requests.post is wrapped as UnknownServiceError."""
        mock_post.side_effect = requests.exceptions.ConnectionError('connection refused')
        with self.assertRaises(errors.UnknownServiceError) as cm:
            self.clt.get_tts_audio('bonjour', self.voice, {}, self.ctx)
        self.assertIn('connection refused', cm.exception.error_message)


class TestServiceManagerNoRetry(unittest.TestCase):
    """Verify that ServiceManager no longer retries — errors propagate directly."""

    def _make_service_manager(self, mock_clt):
        """Create a minimal ServiceManager with a mock CloudLanguageTools."""
        from hypertts_addon import servicemanager
        manager = mock.Mock(spec=servicemanager.ServiceManager)
        manager.cloudlanguagetools = mock_clt
        manager.use_cloud_language_tools = mock.Mock(return_value=True)
        manager.services = {}
        manager.get_tts_audio_implementation = servicemanager.ServiceManager.get_tts_audio_implementation.__get__(manager)
        manager._get_tts_audio_service = servicemanager.ServiceManager._get_tts_audio_service.__get__(manager)
        return manager

    def test_transient_error_propagates(self):
        voice = make_mock_voice()
        ctx = make_mock_context()
        mock_clt = mock.Mock()
        mock_clt.get_tts_audio.side_effect = errors.TransientError('text', voice, 'temp fail')
        manager = self._make_service_manager(mock_clt)
        with self.assertRaises(errors.TransientError):
            manager.get_tts_audio_implementation('text', voice, {}, ctx)
        self.assertEqual(mock_clt.get_tts_audio.call_count, 1)

    def test_permanent_error_propagates(self):
        voice = make_mock_voice()
        ctx = make_mock_context()
        mock_clt = mock.Mock()
        mock_clt.get_tts_audio.side_effect = errors.PermanentError('text', voice, 'permanent')
        manager = self._make_service_manager(mock_clt)
        with self.assertRaises(errors.PermanentError):
            manager.get_tts_audio_implementation('text', voice, {}, ctx)
        self.assertEqual(mock_clt.get_tts_audio.call_count, 1)

    def test_audio_not_found_propagates(self):
        voice = make_mock_voice()
        ctx = make_mock_context()
        mock_clt = mock.Mock()
        mock_clt.get_tts_audio.side_effect = errors.AudioNotFoundError('text', voice)
        manager = self._make_service_manager(mock_clt)
        with self.assertRaises(errors.AudioNotFoundError):
            manager.get_tts_audio_implementation('text', voice, {}, ctx)
        self.assertEqual(mock_clt.get_tts_audio.call_count, 1)

    def test_success(self):
        voice = make_mock_voice()
        ctx = make_mock_context()
        mock_clt = mock.Mock()
        mock_clt.get_tts_audio.return_value = b'audio_data'
        manager = self._make_service_manager(mock_clt)
        result = manager.get_tts_audio_implementation('text', voice, {}, ctx)
        self.assertEqual(result, b'audio_data')


class TestServiceManagerDirectServiceErrorWrapping(unittest.TestCase):

    def _make_service_manager_direct(self, mock_service):
        from hypertts_addon import servicemanager
        manager = mock.Mock(spec=servicemanager.ServiceManager)
        manager.cloudlanguagetools = None
        manager.use_cloud_language_tools = mock.Mock(return_value=False)
        manager.services = {'TestService': mock_service}
        manager.get_tts_audio_implementation = servicemanager.ServiceManager.get_tts_audio_implementation.__get__(manager)
        manager._get_tts_audio_service = servicemanager.ServiceManager._get_tts_audio_service.__get__(manager)
        return manager

    def test_timeout_translated(self):
        voice = make_mock_voice()
        voice.service = 'TestService'
        ctx = make_mock_context()
        mock_service = mock.Mock()
        mock_service.name = 'TestService'
        mock_service.get_tts_audio.side_effect = requests.exceptions.Timeout('timed out')
        manager = self._make_service_manager_direct(mock_service)
        with self.assertRaises(errors.ServiceTimeoutError):
            manager.get_tts_audio_implementation('text', voice, {}, ctx)

    def test_connection_error_translated(self):
        voice = make_mock_voice()
        voice.service = 'TestService'
        ctx = make_mock_context()
        mock_service = mock.Mock()
        mock_service.name = 'TestService'
        mock_service.get_tts_audio.side_effect = requests.exceptions.ConnectionError('connection refused')
        manager = self._make_service_manager_direct(mock_service)
        with self.assertRaises(errors.ServiceConnectionError) as cm:
            manager.get_tts_audio_implementation('text', voice, {}, ctx)
        self.assertIn('connection refused', cm.exception.error_message)

    def test_generic_exception_translated_to_unknown(self):
        voice = make_mock_voice()
        voice.service = 'TestService'
        ctx = make_mock_context()
        mock_service = mock.Mock()
        mock_service.name = 'TestService'
        mock_service.get_tts_audio.side_effect = RuntimeError('unexpected')
        manager = self._make_service_manager_direct(mock_service)
        with self.assertRaises(errors.UnknownServiceError):
            manager.get_tts_audio_implementation('text', voice, {}, ctx)

    def test_hypertts_error_passed_through(self):
        voice = make_mock_voice()
        voice.service = 'TestService'
        ctx = make_mock_context()
        mock_service = mock.Mock()
        mock_service.name = 'TestService'
        mock_service.get_tts_audio.side_effect = errors.RequestError('text', voice, 'some error')
        manager = self._make_service_manager_direct(mock_service)
        with self.assertRaises(errors.RequestError):
            manager.get_tts_audio_implementation('text', voice, {}, ctx)

    def test_direct_service_success(self):
        voice = make_mock_voice()
        voice.service = 'TestService'
        ctx = make_mock_context()
        mock_service = mock.Mock()
        mock_service.name = 'TestService'
        mock_service.get_tts_audio.return_value = b'audio_data'
        manager = self._make_service_manager_direct(mock_service)
        result = manager.get_tts_audio_implementation('text', voice, {}, ctx)
        self.assertEqual(result, b'audio_data')

    def test_timeout_propagates_no_retry(self):
        """Timeout is translated to TimeoutError and propagates (no retry in servicemanager)."""
        voice = make_mock_voice()
        voice.service = 'TestService'
        ctx = make_mock_context()
        mock_service = mock.Mock()
        mock_service.name = 'TestService'
        mock_service.get_tts_audio.side_effect = requests.exceptions.Timeout('timed out')
        manager = self._make_service_manager_direct(mock_service)
        with self.assertRaises(errors.ServiceTimeoutError):
            manager.get_tts_audio_implementation('text', voice, {}, ctx)
        self.assertEqual(mock_service.get_tts_audio.call_count, 1)


class TestAudioRequestContext(unittest.TestCase):

    def test_default_retry_state(self):
        ctx = context.AudioRequestContext(constants.AudioRequestReason.batch)
        self.assertEqual(ctx.retry_count, 0)
        self.assertEqual(ctx.retry_max, 3)

    def test_increment_retry_count(self):
        ctx = context.AudioRequestContext(constants.AudioRequestReason.batch)
        ctx.increment_retry_count()
        self.assertEqual(ctx.retry_count, 1)
        ctx.increment_retry_count()
        self.assertEqual(ctx.retry_count, 2)


class MockBatchStatusListener():
    def __init__(self, anki_utils):
        self.anki_utils = anki_utils
    def batch_start(self):
        pass
    def batch_end(self, completed):
        pass
    def batch_change(self, note_id, row, total_count, start_time, current_time):
        pass


def _make_batch_fixtures():
    """Build HyperTTS instance, batch config, note list, and batch_status for retry tests."""
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')
    mock_collection = testing_utils.MockCollection()
    hypertts_instance.anki_utils.current_time = datetime.datetime.now()

    voice_list = hypertts_instance.service_manager.full_voice_list()
    voice_a_1 = [v for v in voice_list if v.name == 'voice_a_1'][0].voice_id

    single = config_models.VoiceSelectionSingle()
    single.set_voice(config_models.VoiceWithOptions(voice_a_1, {}))

    batch = config_models.BatchConfig(hypertts_instance.anki_utils)
    batch.set_source(config_models.BatchSource(mode=constants.BatchMode.simple, source_field='Chinese'))
    batch.set_target(config_models.BatchTarget('Sound', False, True))
    batch.set_voice_selection(single)
    batch.set_text_processing(config_models.TextProcessing())

    note_id_list = [config_gen.note_id_1]
    listener = MockBatchStatusListener(hypertts_instance.anki_utils)
    batch_status_obj = batch_status.BatchStatus(hypertts_instance.anki_utils, note_id_list, listener)

    return hypertts_instance, batch, note_id_list, batch_status_obj, mock_collection


def test_batch_retry_transient_then_success(qtbot):
    """Transient error on first attempt, success on second — note marked Done."""
    hypertts_instance, batch, note_id_list, batch_status_obj, mock_collection = _make_batch_fixtures()

    call_count = [0]
    original = hypertts_instance.process_note_audio

    def mock_process(batch_arg, note, add_mode, audio_request_context, text_override, anki_collection):
        call_count[0] += 1
        if call_count[0] == 1:
            raise errors.TransientError('老人家', make_mock_voice(), 'temp fail')
        return original(batch_arg, note, add_mode, audio_request_context, text_override, anki_collection)

    with mock.patch.object(hypertts_instance, 'process_note_audio', side_effect=mock_process):
        with mock.patch('time.sleep') as mock_sleep:
            hypertts_instance.process_batch_audio(note_id_list, batch, batch_status_obj, mock_collection)

    assert call_count[0] == 2
    assert batch_status_obj[0].status == constants.BatchNoteStatus.Done
    assert batch_status_obj[0].error is None
    mock_sleep.assert_called_once()


def test_batch_retry_exhausted(qtbot):
    """All retries exhausted — note marked Error."""
    hypertts_instance, batch, note_id_list, batch_status_obj, mock_collection = _make_batch_fixtures()

    voice = make_mock_voice()

    def mock_process(batch_arg, note, add_mode, audio_request_context, text_override, anki_collection):
        raise errors.TransientError('老人家', voice, 'always fails')

    with mock.patch.object(hypertts_instance, 'process_note_audio', side_effect=mock_process):
        with mock.patch('time.sleep'):
            hypertts_instance.process_batch_audio(note_id_list, batch, batch_status_obj, mock_collection)

    assert batch_status_obj[0].status == constants.BatchNoteStatus.Error
    assert batch_status_obj[0].error is not None


def test_batch_retry_rate_limit_uses_retry_after(qtbot):
    """RateLimitRetryAfterError uses retry_after value as sleep delay."""
    hypertts_instance, batch, note_id_list, batch_status_obj, mock_collection = _make_batch_fixtures()

    call_count = [0]
    original = hypertts_instance.process_note_audio

    def mock_process(batch_arg, note, add_mode, audio_request_context, text_override, anki_collection):
        call_count[0] += 1
        if call_count[0] == 1:
            raise errors.RateLimitRetryAfterError('老人家', make_mock_voice(), 'rate limited', 42)
        return original(batch_arg, note, add_mode, audio_request_context, text_override, anki_collection)

    with mock.patch.object(hypertts_instance, 'process_note_audio', side_effect=mock_process):
        with mock.patch('time.sleep') as mock_sleep:
            hypertts_instance.process_batch_audio(note_id_list, batch, batch_status_obj, mock_collection)

    assert call_count[0] == 2
    mock_sleep.assert_called_once_with(42)
    assert batch_status_obj[0].status == constants.BatchNoteStatus.Done


def test_batch_no_retry_on_permanent_error(qtbot):
    """PermanentError on first attempt — no retry, error propagates immediately."""
    hypertts_instance, batch, note_id_list, batch_status_obj, mock_collection = _make_batch_fixtures()

    call_count = [0]

    def mock_process(batch_arg, note, add_mode, audio_request_context, text_override, anki_collection):
        call_count[0] += 1
        raise errors.PermanentError('老人家', make_mock_voice(), 'permanent fail')

    with mock.patch.object(hypertts_instance, 'process_note_audio', side_effect=mock_process):
        with mock.patch('time.sleep') as mock_sleep:
            hypertts_instance.process_batch_audio(note_id_list, batch, batch_status_obj, mock_collection)

    assert call_count[0] == 1
    mock_sleep.assert_not_called()
    assert batch_status_obj[0].status == constants.BatchNoteStatus.Error


def test_batch_retry_increments_retry_count(qtbot):
    """retry_count on AudioRequestContext increments correctly across attempts."""
    hypertts_instance, batch, note_id_list, batch_status_obj, mock_collection = _make_batch_fixtures()

    observed_retry_counts = []
    original = hypertts_instance.process_note_audio

    def mock_process(batch_arg, note, add_mode, audio_request_context, text_override, anki_collection):
        observed_retry_counts.append(audio_request_context.retry_count)
        if len(observed_retry_counts) <= 2:
            raise errors.TransientError('老人家', make_mock_voice(), 'temp fail')
        return original(batch_arg, note, add_mode, audio_request_context, text_override, anki_collection)

    with mock.patch.object(hypertts_instance, 'process_note_audio', side_effect=mock_process):
        with mock.patch('time.sleep'):
            hypertts_instance.process_batch_audio(note_id_list, batch, batch_status_obj, mock_collection)

    assert observed_retry_counts == [0, 1, 2]
    assert batch_status_obj[0].status == constants.BatchNoteStatus.Done


if __name__ == '__main__':
    unittest.main()
