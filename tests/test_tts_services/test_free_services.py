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

    def test_googletranslate_chunked_encoding_error(self):
        # pytest tests/test_tts_services/ -k 'test_googletranslate_chunked_encoding_error'
        # Fixes ANKI-HYPER-TTS-K1Y: a ChunkedEncodingError wrapping a ConnectionResetError
        # (server closed the connection mid-response body) must surface as ServiceConnectionError,
        # not the UnknownServiceError catch-all. ChunkedEncodingError does not inherit from
        # requests.exceptions.ConnectionError so it needs its own branch.
        from unittest.mock import patch
        import requests
        from urllib3.exceptions import ProtocolError

        selected_voice = self._googletranslate_voice()
        reset = ConnectionResetError(54, 'Connection reset by peer')
        protocol_error = ProtocolError(f'Connection broken: {reset!r}', reset)
        underlying = requests.exceptions.ChunkedEncodingError(protocol_error)

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

    def test_googletranslate_regional_voices_listed(self):
        # pytest tests/test_tts_services/ -k 'test_googletranslate_regional_voices_listed'
        # Issue #297: Google Translate should expose regional English voices (UK, AU, etc.)
        # in addition to US.
        # Issue #346: pt-PT and pt-BR should be distinct voices, and fr-FR / fr-CA should
        # be distinct as well.
        service_name = 'GoogleTranslate'
        if self.manager.get_service(service_name).enabled == False:
            raise unittest.SkipTest(f'service {service_name} not enabled, skipping')

        voice_list = [v for v in self.manager.full_voice_list() if v.service == service_name]

        voice_keys = {v.voice_key for v in voice_list}
        # Backward compat: every voice_key the OLD voice_list() emitted must still appear
        # so that users with saved presets continue to resolve their voice via locate_voice.
        # gtts.lang.tts_langs() returns 'pt-PT' and 'fr-CA' alongside 'pt' and 'fr', and
        # the old code emitted all of them — preserve that.
        for legacy_key in ('en', 'fr', 'fr-CA', 'pt', 'pt-PT', 'es'):
            self.assertIn(legacy_key, voice_keys, f'legacy voice_key {legacy_key} missing')
        # new regional variants for #297 — full set from the gTTS localized-accents docs
        for expected in ('en-GB', 'en-AU', 'en-CA', 'en-IN', 'en-IE', 'en-ZA', 'en-NG'):
            self.assertIn(expected, voice_keys, f'missing regional voice {expected}')
        # new Brazilian voice for #346 plus Spanish (North America)
        self.assertIn('pt-BR', voice_keys)
        self.assertIn('es-US', voice_keys)

        # Each variant must advertise the right AudioLanguage so the GUI filter shows it
        # under the correct locale.
        by_key = {v.voice_key: v for v in voice_list}
        self.assertIn(AudioLanguage.en_GB, by_key['en-GB'].audio_languages)
        self.assertIn(AudioLanguage.en_AU, by_key['en-AU'].audio_languages)
        self.assertIn(AudioLanguage.pt_PT, by_key['pt'].audio_languages)
        self.assertIn(AudioLanguage.pt_PT, by_key['pt-PT'].audio_languages)
        self.assertIn(AudioLanguage.pt_BR, by_key['pt-BR'].audio_languages)
        self.assertIn(AudioLanguage.fr_FR, by_key['fr'].audio_languages)
        self.assertIn(AudioLanguage.fr_CA, by_key['fr-CA'].audio_languages)

    def test_googletranslate_voice_key_tld_routing(self):
        # pytest tests/test_tts_services/ -k 'test_googletranslate_voice_key_tld_routing'
        # Issues #297 and #346: the voice_key chosen by the user must drive the gTTS `tld`
        # parameter so that regional accents actually differ. Confirm by intercepting the
        # gTTS constructor and inspecting the kwargs.
        from unittest.mock import patch, MagicMock

        service_name = 'GoogleTranslate'
        if self.manager.get_service(service_name).enabled == False:
            raise unittest.SkipTest(f'service {service_name} not enabled, skipping')

        voice_list = self.manager.full_voice_list()
        by_key = {v.voice_key: v for v in voice_list if v.service == service_name}

        # (voice_key, expected_lang_kwarg, expected_tld_kwarg)
        # Verifies both new variants and backward compat for every legacy voice_key that
        # the OLD voice_list() emitted (from gtts.lang.tts_langs()). The (lang, tld) pairs
        # mirror the gTTS docs table at
        # https://gtts.readthedocs.io/en/latest/module.html#localized-accents
        # - 'pt' and 'pt-PT' must now route to tld='pt' (fixes #346: the voices labelled
        #   Portuguese (Portugal) were producing Brazilian audio).
        # - 'fr-CA' must now route to tld='ca' (was silently falling back to 'fr').
        # - 'fr' moves to tld='fr' so it remains distinct from fr-CA.
        # - 'en' moves to tld='us' and 'es' to tld='es' so each base voice matches the
        #   explicit accent listed in the docs rather than the geo-dependent 'com' default.
        cases = [
            # English: default + regional variants from the docs (issue #297)
            ('en', 'en', 'us'),
            ('en-GB', 'en', 'co.uk'),
            ('en-AU', 'en', 'com.au'),
            ('en-CA', 'en', 'ca'),
            ('en-IN', 'en', 'co.in'),
            ('en-IE', 'en', 'ie'),
            ('en-ZA', 'en', 'co.za'),
            ('en-NG', 'en', 'com.ng'),
            # French: legacy 'fr' and legacy 'fr-CA' both routed correctly
            ('fr', 'fr', 'fr'),
            ('fr-CA', 'fr', 'ca'),
            # Portuguese: legacy 'pt' AND legacy 'pt-PT' both produce Portugal audio (#346)
            ('pt', 'pt', 'pt'),
            ('pt-PT', 'pt', 'pt'),
            ('pt-BR', 'pt', 'com.br'),
            # Spanish
            ('es', 'es', 'es'),
            ('es-MX', 'es', 'com.mx'),
            ('es-US', 'es', 'us'),
        ]

        for voice_key, expected_lang, expected_tld in cases:
            with self.subTest(voice_key=voice_key):
                self.assertIn(voice_key, by_key, f'voice {voice_key} missing from voice_list')
                selected_voice = by_key[voice_key]
                fake_tts = MagicMock()
                # write_to_fp is what the service calls; make it write some bytes so the
                # service believes synthesis succeeded.
                fake_tts.write_to_fp.side_effect = lambda buf: buf.write(b'\x00')
                with patch('gtts.gTTS', return_value=fake_tts) as gtts_ctor:
                    self.manager.get_tts_audio(
                        'hello',
                        selected_voice,
                        {},
                        context.AudioRequestContext(constants.AudioRequestReason.batch))
                self.assertEqual(gtts_ctor.call_count, 1)
                kwargs = gtts_ctor.call_args.kwargs
                self.assertEqual(kwargs.get('lang'), expected_lang,
                                 f'lang for {voice_key}: expected {expected_lang}, got {kwargs.get("lang")}')
                self.assertEqual(kwargs.get('tld'), expected_tld,
                                 f'tld for {voice_key}: expected {expected_tld}, got {kwargs.get("tld")}')

    def test_googletranslate_dev_branch_voice_keys_still_emit(self):
        # pytest tests/test_tts_services/ -k 'test_googletranslate_dev_branch_voice_keys_still_emit'
        # Comprehensive backward-compat guard: reproduce the OLD voice_list() algorithm
        # (as it lived on the `dev` branch) and assert every voice_key it would have
        # emitted is also emitted by the current voice_list(). Without this guard,
        # adding a new key to GTTS_KEY_TO_EMITTED_VOICE_KEYS without listing the
        # corresponding legacy voice_key would silently break user presets.
        import gtts
        from hypertts_addon import voice as voice_module

        service_name = 'GoogleTranslate'
        service_obj = self.manager.get_service(service_name)
        if service_obj.enabled == False:
            raise unittest.SkipTest(f'service {service_name} not enabled, skipping')

        # Re-implement dev's voice_list() voice_key emission. Dev iterated
        # gtts.lang.tts_langs() and emitted voice_key=language_key whenever
        # get_language(language_key) returned non-None.
        dev_voice_keys = []
        for language_key in gtts.lang.tts_langs().keys():
            if service_obj.get_language(language_key) is not None:
                dev_voice_keys.append(language_key)

        # Current voice_list — collect every voice_key actually emitted today
        current_voice_keys = {
            v.voice_key for v in self.manager.full_voice_list()
            if v.service == service_name
        }

        missing = [k for k in dev_voice_keys if k not in current_voice_keys]
        self.assertEqual(missing, [],
            f'voice_keys emitted by dev are no longer emitted: {missing}. '
            'Saved presets pointing at these keys would fail locate_voice.')

        # Every dev voice_key must also resolve to a valid TtsVoice via locate_voice —
        # this is the exact path the addon uses when loading a serialized preset.
        for vk in dev_voice_keys:
            with self.subTest(voice_key=vk):
                located = self.manager.locate_voice(
                    voice_module.TtsVoiceId_v3(voice_key=vk, service=service_name))
                self.assertEqual(located.voice_key, vk)

    def test_googletranslate_legacy_voice_key_locates(self):
        # pytest tests/test_tts_services/ -k 'test_googletranslate_legacy_voice_key_locates'
        # Issues #297 and #346: simulate a saved preset built by an older version of the
        # addon. Such presets serialise a TtsVoiceId_v3(voice_key=..., service=...) and
        # rely on ServiceManager.locate_voice() to resolve it back to a TtsVoice_v3. If
        # the new voice_list() ever stops emitting one of the legacy voice_keys, those
        # presets break with VoiceIdNotFound — guard against that here.
        from hypertts_addon import voice as voice_module

        service_name = 'GoogleTranslate'
        if self.manager.get_service(service_name).enabled == False:
            raise unittest.SkipTest(f'service {service_name} not enabled, skipping')

        for legacy_voice_key in ('en', 'fr', 'fr-CA', 'pt', 'pt-PT', 'es',
                                 'de', 'ja', 'zh-CN', 'zh-TW'):
            with self.subTest(voice_key=legacy_voice_key):
                voice_id = voice_module.TtsVoiceId_v3(
                    voice_key=legacy_voice_key, service=service_name)
                located = self.manager.locate_voice(voice_id)
                self.assertEqual(located.voice_key, legacy_voice_key)
                self.assertEqual(located.service, service_name)

    def test_googletranslate_unknown_voice_key_default_tld(self):
        # pytest tests/test_tts_services/ -k 'test_googletranslate_unknown_voice_key_default_tld'
        # A voice_key that isn't in VOICE_KEY_TLD_MAP (e.g. 'de', 'ja', or any non-variant
        # language) must fall back to tld='com' so that synthesis for the long tail of
        # languages keeps working unchanged.
        from unittest.mock import patch, MagicMock

        service_name = 'GoogleTranslate'
        if self.manager.get_service(service_name).enabled == False:
            raise unittest.SkipTest(f'service {service_name} not enabled, skipping')

        voice_list = self.manager.full_voice_list()
        de_voice = next(v for v in voice_list if v.service == service_name and v.voice_key == 'de')

        fake_tts = MagicMock()
        fake_tts.write_to_fp.side_effect = lambda buf: buf.write(b'\x00')
        with patch('gtts.gTTS', return_value=fake_tts) as gtts_ctor:
            self.manager.get_tts_audio(
                'guten tag',
                de_voice,
                {},
                context.AudioRequestContext(constants.AudioRequestReason.batch))
        kwargs = gtts_ctor.call_args.kwargs
        self.assertEqual(kwargs.get('lang'), 'de')
        self.assertEqual(kwargs.get('tld'), 'com')

    def test_googletranslate_pt_pt_audio(self):
        # pytest tests/test_tts_services/ -k 'test_googletranslate_pt_pt_audio'
        # Issue #346: end-to-end check that the Portuguese (Portugal) voice produces audio
        # that transcribes back to the source text. (The audio is recognized via the
        # base-class verify_audio_output helper which uses Whisper / Azure.)
        service_name = 'GoogleTranslate'
        if self.manager.get_service(service_name).enabled == False:
            raise unittest.SkipTest(f'service {service_name} not enabled, skipping')

        voice_list = self.manager.full_voice_list()
        pt_pt_voice = next(v for v in voice_list
                           if v.service == service_name and v.voice_key == 'pt')
        # 'bom dia a todos' is the phrase suggested in the issue thread — distinct enough
        # between pt-PT and pt-BR pronunciation that a botched fix would fail recognition.
        self.verify_audio_output(pt_pt_voice, AudioLanguage.pt_PT, 'bom dia a todos')

    def test_googletranslate_pt_br_audio(self):
        # pytest tests/test_tts_services/ -k 'test_googletranslate_pt_br_audio'
        # Issue #346: end-to-end check for the new Brazilian voice.
        service_name = 'GoogleTranslate'
        if self.manager.get_service(service_name).enabled == False:
            raise unittest.SkipTest(f'service {service_name} not enabled, skipping')

        voice_list = self.manager.full_voice_list()
        pt_br_voice = next(v for v in voice_list
                           if v.service == service_name and v.voice_key == 'pt-BR')
        self.verify_audio_output(pt_br_voice, AudioLanguage.pt_BR, 'bom dia a todos')

    def test_googletranslate_en_gb_audio(self):
        # pytest tests/test_tts_services/ -k 'test_googletranslate_en_gb_audio'
        # Issue #297: end-to-end check for the new UK English voice.
        service_name = 'GoogleTranslate'
        if self.manager.get_service(service_name).enabled == False:
            raise unittest.SkipTest(f'service {service_name} not enabled, skipping')

        voice_list = self.manager.full_voice_list()
        en_gb_voice = next(v for v in voice_list
                           if v.service == service_name and v.voice_key == 'en-GB')
        self.verify_audio_output(en_gb_voice, AudioLanguage.en_GB, 'This is the first sentence')

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
