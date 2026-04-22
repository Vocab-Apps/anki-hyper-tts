#!/usr/bin/env python3
"""Test error handling in TTS services, particularly for rate limiting (429) errors."""

import unittest
import unittest.mock as mock
import logging
from hypertts_addon.services import service_azure
from hypertts_addon import logging_utils
from hypertts_addon import errors

logger = logging_utils.get_test_child_logger(__name__)


class TestServicesErrorHandling(unittest.TestCase):
    """Test error handling behaviors for TTS services."""

    def setUp(self):
        """Set up test fixtures."""
        self.azure_service = service_azure.Azure()
        # Mock the configuration
        self.azure_service._config = {
            'region': 'eastus',
            'api_key': 'fake_api_key'
        }
        # Mock the access token to avoid authentication
        with mock.patch.object(self.azure_service, 'token_refresh_required', return_value=False):
            self.azure_service.access_token = 'fake_token'
        
        # Create a mock voice
        self.mock_voice = mock.Mock()
        self.mock_voice.name = 'Test Voice'
        self.mock_voice.voice_key = {'name': 'test-voice'}
        self.mock_voice.options = {
            'rate': {'default': 1.0},
            'pitch': {'default': 0}
        }

    def test_azure_429_logged_as_warning(self):
        """Test that Azure 429 (Too Many Requests) errors are logged as warnings."""
        # Create a mock response for 429 error
        mock_response = mock.Mock()
        mock_response.status_code = 429
        mock_response.reason = 'Too Many Requests'
        
        with mock.patch.object(self.azure_service, 'token_refresh_required', return_value=False):
            with mock.patch('requests.post', return_value=mock_response):
                with self.assertLogs('hypertts.service_azure', level='WARNING') as log_context:
                    with self.assertRaises(errors.RequestError) as context:
                        self.azure_service.get_tts_audio('Test text', self.mock_voice, {})
                    
                    # Check that the error was raised with correct message
                    self.assertIn('429', str(context.exception))
                    self.assertIn('Too Many Requests', str(context.exception))
                    
                    # Check that it was logged as WARNING, not ERROR
                    self.assertEqual(len(log_context.output), 1)
                    self.assertIn('WARNING', log_context.output[0])
                    self.assertIn('status code 429', log_context.output[0])
                    self.assertIn('Too Many Requests', log_context.output[0])

if __name__ == '__main__':
    unittest.main()