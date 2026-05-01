import unittest

from .base import TTSTests, logger
from hypertts_addon import constants
from hypertts_addon import context
from hypertts_addon import errors
from hypertts_addon import languages
from hypertts_addon.languages import AudioLanguage


class TestFreeServices(TTSTests):

    def test_googletranslate(self):
        # pytest tests/test_tts_services/ -k 'TestFreeServices and test_googletranslate'
        service_name = 'GoogleTranslate'
        if self.manager.get_service(service_name).enabled == False:
            logger.warning(f'service {service_name} not enabled, skipping')
            raise unittest.SkipTest(f'service {service_name} not enabled, skipping')

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service == service_name]
        assert len(service_voices) >= 2

        # English test
        self.random_voice_test(service_name, languages.AudioLanguage.en_US, 'This is the first sentence')

        # French test
        self.random_voice_test(service_name, languages.AudioLanguage.fr_FR, 'Je ne suis pas disponible.')

        # Hebrew test
        self.random_voice_test(service_name, languages.AudioLanguage.he_IL, '.בבקשה')

    def test_naverpapago(self):
        service_name = 'NaverPapago'
        if self.manager.get_service(service_name).enabled == False:
            logger.warning(f'service {service_name} not enabled, skipping')
            raise unittest.SkipTest(f'service {service_name} not enabled, skipping')

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service == service_name]

        logger.info(f'found {len(service_voices)} voices for {service_name} services')
        assert len(service_voices) >= 2

        # pick a random ko_KR voice
        self.random_voice_test(service_name, languages.AudioLanguage.ko_KR, '여보세요')

        self.random_voice_test(service_name, languages.AudioLanguage.ja_JP, 'おはようございます')

        self.random_voice_test(service_name, languages.AudioLanguage.th_TH, 'สวัสดีค่ะ')

    def test_oxford(self):
        service_name = 'Oxford'
        if self.manager.get_service(service_name).enabled == False:
            logger.warning(f'service {service_name} not enabled, skipping')
            raise unittest.SkipTest(f'service {service_name} not enabled, skipping')

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service == service_name]

        logger.info(f'found {len(service_voices)} voices for {service_name} services')
        assert len(service_voices) >= 2

        # pick a random en_GB voice
        self.random_voice_test(service_name, languages.AudioLanguage.en_GB, 'successful')

        # pick a random en_GB voice
        self.random_voice_test(service_name, languages.AudioLanguage.en_GB, 'House')

        # pick a random en_GB voice
        self.random_voice_test(service_name, languages.AudioLanguage.en_US, 'successful')


        # error handling
        # ==============

        # ensure that a non-existent word raises AudioNotFoundError
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.en_GB)
        self.assertRaises(errors.AudioNotFoundError,
                          self.manager.get_tts_audio,
                          'xxoanetuhsoae', # non-existent word
                          selected_voice,
                          {},
                          context.AudioRequestContext(constants.AudioRequestReason.batch))

    def test_dwds(self):
        # pytest tests/test_tts_services/ -k test_dwds
        service_name = 'DigitalesWorterbuchDeutschenSprache'
        if self.manager.get_service(service_name).enabled == False:
            logger.warning(f'service {service_name} not enabled, skipping')
            raise unittest.SkipTest(f'service {service_name} not enabled, skipping')

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service == service_name]

        logger.info(f'found {len(service_voices)} voices for {service_name} services')
        assert len(service_voices) >= 1

        # test german voice
        selected_voice = self.pick_random_voice(voice_list, service_name, AudioLanguage.de_DE)
        self.verify_audio_output(selected_voice, AudioLanguage.de_DE, 'Gesundheit', 'die Gesundheit')
        self.verify_audio_output(selected_voice, AudioLanguage.de_DE, 'Entschuldigung', 'die Entschuldigung')

        # test error handling
        self.assertRaises(errors.AudioNotFoundError,
                          self.manager.get_tts_audio,
                          'xxoanetuhsoae', # non-existent word
                          selected_voice,
                          {},
                          context.AudioRequestContext(constants.AudioRequestReason.batch))

    def test_duden(self):
        # pytest tests/test_tts_services/ -k test_duden
        service_name = 'Duden'
        if self.manager.get_service(service_name).enabled == False:
            logger.warning(f'service {service_name} not enabled, skipping')
            raise unittest.SkipTest(f'service {service_name} not enabled, skipping')

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service == service_name]

        logger.info(f'found {len(service_voices)} voices for {service_name} services')
        assert len(service_voices) >= 1

        # test german voice
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.de_DE)
        self.verify_audio_output(selected_voice, AudioLanguage.de_DE, 'Gesundheit')
        self.verify_audio_output(selected_voice, AudioLanguage.de_DE, 'Entschuldigung')

        # test error handling
        self.assertRaises(errors.AudioNotFoundError,
                          self.manager.get_tts_audio,
                          'xxoanetuhsoae', # non-existent word
                          selected_voice,
                          {},
                          context.AudioRequestContext(constants.AudioRequestReason.batch))

    def test_duden_umlauts(self):
        # pytest tests/test_tts_services/ -k test_duden_umlauts
        # Test for issue https://github.com/Vocab-Apps/anki-hyper-tts/issues/216
        service_name = 'Duden'
        if self.manager.get_service(service_name).enabled == False:
            logger.warning(f'service {service_name} not enabled, skipping')
            raise unittest.SkipTest(f'service {service_name} not enabled, skipping')

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service == service_name]

        logger.info(f'found {len(service_voices)} voices for {service_name} services')
        assert len(service_voices) >= 1

        # test german voice with umlauts
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.de_DE)

        # Test words with umlauts from the issue - these should work with the fix
        self.verify_audio_output(selected_voice, AudioLanguage.de_DE, 'schälen')
        self.verify_audio_output(selected_voice, AudioLanguage.de_DE, 'dünsten')
        self.verify_audio_output(selected_voice, AudioLanguage.de_DE, 'dämpfen')

        # Additional umlaut test cases that should work
        self.verify_audio_output(selected_voice, AudioLanguage.de_DE, 'müde')
        self.verify_audio_output(selected_voice, AudioLanguage.de_DE, 'ärgern')
        self.verify_audio_output(selected_voice, AudioLanguage.de_DE, 'öffnen')
        self.verify_audio_output(selected_voice, AudioLanguage.de_DE, 'führen')
        self.verify_audio_output(selected_voice, AudioLanguage.de_DE, 'hören')
        self.verify_audio_output(selected_voice, AudioLanguage.de_DE, 'Tür')

        # Test words that might not have audio (not all words have pronunciations on Duden)
        words_that_might_not_have_audio = [
            'übersetzen', 'Größe', 'üblich', 'Äpfel', 'Öl', 'Über',
            'Frühstück', 'Glückwunsch', 'Bürogebäude'
        ]

        for word in words_that_might_not_have_audio:
            try:
                self.verify_audio_output(selected_voice, AudioLanguage.de_DE, word)
                logger.info(f'Audio found for "{word}"')
            except errors.AudioNotFoundError:
                logger.info(f'No audio available for "{word}" on Duden (expected for some words)')

    def test_youdao(self):
        # pytest tests/test_tts_services/ -k test_youdao
        service_name = 'Youdao'
        if self.manager.get_service(service_name).enabled == False:
            logger.warning(f'service {service_name} not enabled, skipping')
            raise unittest.SkipTest(f'service {service_name} not enabled, skipping')

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service == service_name]

        logger.info(f'found {len(service_voices)} voices for {service_name} services')
        assert len(service_voices) >= 2  # UK and US English

        # Test UK English voice
        uk_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.en_GB)
        self.verify_audio_output(uk_voice, AudioLanguage.en_GB, 'hello')
        self.verify_audio_output(uk_voice, AudioLanguage.en_GB, 'vehicle')
        self.verify_audio_output(uk_voice, AudioLanguage.en_GB, 'computer')

        # Test US English voice
        us_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.en_US)
        self.verify_audio_output(us_voice, AudioLanguage.en_US, 'hello')
        self.verify_audio_output(us_voice, AudioLanguage.en_US, 'vehicle')
        self.verify_audio_output(us_voice, AudioLanguage.en_US, 'technology')

        # Test error handling - very long word that likely doesn't exist
        self.assertRaises(errors.AudioNotFoundError,
                          self.manager.get_tts_audio,
                          'pneumonoultramicroscopicsilicovolcanoconiosisxxxyyy',
                          us_voice,
                          {},
                          context.AudioRequestContext(constants.AudioRequestReason.batch))

    def test_cambridge(self):
        service_name = 'Cambridge'
        if self.manager.get_service(service_name).enabled == False:
            logger.warning(f'service {service_name} not enabled, skipping')
            raise unittest.SkipTest(f'service {service_name} not enabled, skipping')

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service == service_name]

        logger.info(f'found {len(service_voices)} voices for {service_name} services')
        assert len(service_voices) >= 2 # british and american

        # test british voice
        self.random_voice_test(service_name, languages.AudioLanguage.en_GB, 'vehicle')
        # test american voice
        self.random_voice_test(service_name, languages.AudioLanguage.en_US, 'vehicle')

        # regression test for "dynamic" - first UK pronunciation span lacks audio source tag
        # Fixes ANKI-HYPER-TTS-HFJ
        self.random_voice_test(service_name, languages.AudioLanguage.en_GB, 'dynamic')
        self.random_voice_test(service_name, languages.AudioLanguage.en_US, 'dynamic')

        # test error handling
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.en_GB)
        self.assertRaises(errors.AudioNotFoundError,
                          self.manager.get_tts_audio,
                          'xxoanetuhsoae', # non-existent word
                          selected_voice,
                          {},
                          context.AudioRequestContext(constants.AudioRequestReason.batch))

    def test_spanishdict(self):
        service_name = 'SpanishDict'
        if self.manager.get_service(service_name).enabled == False:
            logger.warning(f'service {service_name} not enabled, skipping')
            raise unittest.SkipTest(f'service {service_name} not enabled, skipping')

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service == service_name]

        logger.info(f'found {len(service_voices)} voices for {service_name} services')
        assert len(service_voices) >= 2 # spanish and english

        # test spanish voice
        self.random_voice_test(service_name, languages.AudioLanguage.es_ES, 'furgoneta')
        # test english voice
        self.random_voice_test(service_name, languages.AudioLanguage.en_US, 'vehicle')


    def test_googletranslate_rate_limit(self):
        # pytest tests/test_tts_services/ -k 'test_googletranslate_rate_limit'
        # Fixes ANKI-HYPER-TTS-HGZ
        from unittest.mock import patch, MagicMock
        import gtts

        service_name = 'GoogleTranslate'
        if self.manager.get_service(service_name).enabled == False:
            logger.warning(f'service {service_name} not enabled, skipping')
            raise unittest.SkipTest(f'service {service_name} not enabled, skipping')

        voice_list = self.manager.full_voice_list()
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.en_US)

        # Create a mock 429 response
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.reason = 'Too Many Requests'
        mock_response.headers = {'Retry-After': '60'}

        mock_tts = MagicMock()
        gtts_error = gtts.gTTSError(response=mock_response, tts=mock_tts)

        with patch('gtts.gTTS.write_to_fp', side_effect=gtts_error):
            with self.assertRaises(errors.RateLimitRetryAfterError) as cm:
                self.manager.get_tts_audio(
                    'test',
                    selected_voice,
                    {},
                    context.AudioRequestContext(constants.AudioRequestReason.batch))
            self.assertEqual(cm.exception.retry_after, 60)
            self.assertTrue(cm.exception.retryable)

    def test_googletranslate_no_text(self):
        # pytest tests/test_tts_services/ -k 'test_googletranslate_no_text'
        # Fixes ANKI-HYPER-TTS-J00
        # gTTS raises AssertionError("No text to send to TTS API") when the
        # tokenizer reduces the input to nothing (e.g. ",,,"). Verify we
        # surface that as a non-retryable ServiceInputError.
        from unittest.mock import patch

        service_name = 'GoogleTranslate'
        if self.manager.get_service(service_name).enabled == False:
            logger.warning(f'service {service_name} not enabled, skipping')
            raise unittest.SkipTest(f'service {service_name} not enabled, skipping')

        voice_list = self.manager.full_voice_list()
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.en_US)

        assertion_error = AssertionError('No text to send to TTS API')

        with patch('gtts.gTTS.write_to_fp', side_effect=assertion_error):
            with self.assertRaises(errors.ServiceInputError) as cm:
                self.manager.get_tts_audio(
                    ',,,',
                    selected_voice,
                    {},
                    context.AudioRequestContext(constants.AudioRequestReason.batch))
            self.assertFalse(cm.exception.retryable)
            self.assertIn('No text to send to TTS API', cm.exception.error_message)

    def _googletranslate_voice(self):
        service_name = 'GoogleTranslate'
        if self.manager.get_service(service_name).enabled == False:
            logger.warning(f'service {service_name} not enabled, skipping')
            raise unittest.SkipTest(f'service {service_name} not enabled, skipping')
        voice_list = self.manager.full_voice_list()
        return self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.en_US)

    def _raise_gtts_error_from(self, underlying):
        # Mimic how gtts raises gTTSError inside an `except requests.exceptions.RequestException`
        # block, so the underlying exception ends up in __context__.
        from unittest.mock import MagicMock
        import gtts
        try:
            raise underlying
        except Exception:
            raise gtts.gTTSError(tts=MagicMock())

    def test_googletranslate_read_timeout(self):
        # pytest tests/test_tts_services/ -k 'test_googletranslate_read_timeout'
        # Fixes ANKI-HYPER-TTS-J9B: ReadTimeout in gtts must surface as ServiceTimeoutError, not the
        # legacy RequestError catch-all.
        from unittest.mock import patch
        import requests

        selected_voice = self._googletranslate_voice()
        underlying = requests.exceptions.ReadTimeout('Read timed out. (read timeout=20)')

        with patch('gtts.gTTS.write_to_fp', side_effect=lambda *a, **kw: self._raise_gtts_error_from(underlying)):
            with self.assertRaises(errors.ServiceTimeoutError) as cm:
                self.manager.get_tts_audio(
                    'test',
                    selected_voice,
                    {},
                    context.AudioRequestContext(constants.AudioRequestReason.batch))
            self.assertTrue(cm.exception.retryable)

    def test_googletranslate_connect_timeout(self):
        # pytest tests/test_tts_services/ -k 'test_googletranslate_connect_timeout'
        # Fixes ANKI-HYPER-TTS-J90: ConnectTimeout (subclass of both Timeout and ConnectionError)
        # should be classified as ServiceTimeoutError, since Timeout is the more specific signal.
        from unittest.mock import patch
        import requests

        selected_voice = self._googletranslate_voice()
        underlying = requests.exceptions.ConnectTimeout('Connection to translate.google.com timed out.')

        with patch('gtts.gTTS.write_to_fp', side_effect=lambda *a, **kw: self._raise_gtts_error_from(underlying)):
            with self.assertRaises(errors.ServiceTimeoutError) as cm:
                self.manager.get_tts_audio(
                    'test',
                    selected_voice,
                    {},
                    context.AudioRequestContext(constants.AudioRequestReason.batch))
            self.assertTrue(cm.exception.retryable)

    def test_googletranslate_connection_error(self):
        # pytest tests/test_tts_services/ -k 'test_googletranslate_connection_error'
        # Fixes ANKI-HYPER-TTS-J04: a "Network is unreachable" ConnectionError must surface as
        # ServiceConnectionError, not the legacy RequestError catch-all.
        from unittest.mock import patch
        import requests

        selected_voice = self._googletranslate_voice()
        underlying = requests.exceptions.ConnectionError(
            'HTTPSConnectionPool(host=\'translate.google.com\', port=443): '
            'Failed to establish a new connection: [Errno 101] Network is unreachable'
        )

        with patch('gtts.gTTS.write_to_fp', side_effect=lambda *a, **kw: self._raise_gtts_error_from(underlying)):
            with self.assertRaises(errors.ServiceConnectionError) as cm:
                self.manager.get_tts_audio(
                    'test',
                    selected_voice,
                    {},
                    context.AudioRequestContext(constants.AudioRequestReason.batch))
            self.assertTrue(cm.exception.retryable)

    def test_googletranslate_gateway_error(self):
        # pytest tests/test_tts_services/ -k 'test_googletranslate_gateway_error'
        # 5xx upstream gateway responses (no Retry-After) should be ServiceGatewayError.
        from unittest.mock import patch, MagicMock
        import gtts

        selected_voice = self._googletranslate_voice()
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.reason = 'Service Unavailable'
        mock_response.headers = {}

        gtts_error = gtts.gTTSError(response=mock_response, tts=MagicMock())

        with patch('gtts.gTTS.write_to_fp', side_effect=gtts_error):
            with self.assertRaises(errors.ServiceGatewayError) as cm:
                self.manager.get_tts_audio(
                    'test',
                    selected_voice,
                    {},
                    context.AudioRequestContext(constants.AudioRequestReason.batch))
            self.assertTrue(cm.exception.retryable)

    def test_googletranslate_unknown_error(self):
        # pytest tests/test_tts_services/ -k 'test_googletranslate_unknown_error'
        # gTTSError without an HTTP response and without a recognizable underlying requests
        # exception should fall through to UnknownServiceError (transient catch-all), not the
        # legacy RequestError.
        from unittest.mock import patch, MagicMock
        import gtts

        selected_voice = self._googletranslate_voice()
        gtts_error = gtts.gTTSError(tts=MagicMock())

        with patch('gtts.gTTS.write_to_fp', side_effect=gtts_error):
            with self.assertRaises(errors.UnknownServiceError) as cm:
                self.manager.get_tts_audio(
                    'test',
                    selected_voice,
                    {},
                    context.AudioRequestContext(constants.AudioRequestReason.batch))
            self.assertTrue(cm.exception.retryable)


class TestFreeServicesCLT(TestFreeServices):
    CONFIG_MODE = 'clt'
