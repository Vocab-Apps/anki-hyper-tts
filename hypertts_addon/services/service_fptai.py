import sys
import os
import json
import tempfile
import requests
import aqt.sound

from hypertts_addon import voice
from hypertts_addon import service
from hypertts_addon import errors
from hypertts_addon import constants
from hypertts_addon import languages
from hypertts_addon import logging_utils
logger = logging_utils.get_child_logger(__name__)

class FptAi(service.ServiceBase):
    CONFIG_API_KEY = 'api_key'

    def __init__(self):
        service.ServiceBase.__init__(self)
        self.access_token = None

    def cloudlanguagetools_enabled(self):
        return True

    @property
    def service_type(self) -> constants.ServiceType:
        return constants.ServiceType.tts

    @property
    def service_fee(self) -> constants.ServiceFee:
        return constants.ServiceFee.paid

    def configuration_options(self):
        return {
            self.CONFIG_API_KEY: str,
        }

    def voice_list(self):
        return self.basic_voice_list()

    def get_tts_audio(self, source_text, voice: voice.VoiceBase, options):
        api_key = self.get_configuration_value_mandatory(self.CONFIG_API_KEY)

        api_url = "https://mkp-api.fptcloud.com/v1/audio/speech"
        
        # Prepare request data
        data = {
            'model': 'FPT.AI-VITs',
            'input': source_text,
            'voice': voice.voice_key['voice_id']
        }
        
        # Add optional speed parameter if provided
        if 'speed' in options:
            speed = float(options.get('speed', 1.0))
            # Clamp speed to valid range (0.5 to 2.0)
            speed = max(0.5, min(2.0, speed))
            data['speed'] = speed
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }
        
        logger.debug(f'Sending request to FPT.AI API with data: {data}')
        
        response = requests.post(
            api_url, 
            headers=headers, 
            json=data,
            timeout=constants.RequestTimeout
        )

        if response.status_code == 200:
            # The new API returns WAV audio directly
            wav_audio = response.content
            
            # Convert WAV to MP3 using Anki's built-in converter
            # Create temporary files for conversion
            fh_wav, wav_temp_file = tempfile.mkstemp(prefix='hypertts_fptai_', suffix='.wav')
            fh_mp3, mp3_temp_file = tempfile.mkstemp(prefix='hypertts_fptai_', suffix='.mp3')
            
            try:
                # Write WAV data to temp file
                os.write(fh_wav, wav_audio)
                os.close(fh_wav)
                os.close(fh_mp3)
                
                # Convert WAV to MP3
                aqt.sound._encode_mp3(wav_temp_file, mp3_temp_file)
                
                # Read the MP3 data
                with open(mp3_temp_file, 'rb') as f:
                    mp3_audio = f.read()
                
                return mp3_audio
            finally:
                # Clean up temp files
                if os.path.exists(wav_temp_file):
                    os.remove(wav_temp_file)
                if os.path.exists(mp3_temp_file):
                    os.remove(mp3_temp_file)
        
        # Handle error responses
        error_message = f'FPT.AI API error (status {response.status_code}): {response.text}'
        logger.error(error_message)
        raise errors.RequestError(source_text, voice, error_message)