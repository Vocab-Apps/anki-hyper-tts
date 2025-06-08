from typing import Dict
import requests
import base64
from hypertts_addon import service, voice, constants, logging_utils

logger = logging_utils.get_child_logger(__name__)

class ResembleAI(service.ServiceBase):
    # https://docs.app.resemble.ai/docs/text_to_speech/
    API_ENDPOINT = "https://f.cluster.resemble.ai/synthesize"
    CONFIG_API_KEY = 'resemble_api_key'

    # --- Service Properties ---
    def __init__(self):
        service.ServiceBase.__init__(self)

    @property
    def service_name(self) -> str:
        return "ResembleAI"

    @property
    def service_type(self) -> constants.ServiceType:
        return constants.ServiceType.tts

    @property
    def service_fee(self) -> constants.ServiceFee:
        return constants.ServiceFee.paid

    def configuration_options(self):
        return {
            self.CONFIG_API_KEY: str
        }

    def configure(self, config):
        self._config = config
        self.api_key = self.get_configuration_value_mandatory(self.CONFIG_API_KEY)

    def voice_list(self):
        return self.basic_voice_list()

    # --- TTS Core Logic ---
    def get_tts_audio(self, source_text: str, voice_info: voice.VoiceBase, voice_options_override: Dict):
        voice_uuid = voice_info.voice_key['uuid']

        output_format = voice_options_override.get('output_format', 'mp3')
        sample_rate = voice_options_override.get('sample_rate')
        precision = voice_options_override.get('precision')

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "voice_uuid": voice_uuid,
            "data": source_text,
            "output_format": output_format
        }

        if sample_rate:
            payload["sample_rate"] = int(sample_rate)
        if output_format == 'wav' and precision:
            payload["precision"] = precision

        logger.debug(f"ResembleAI synthesis with {payload}")
        response = requests.post(self.API_ENDPOINT, json=payload, headers=headers)
        response_data = response.json()

        # https://docs.app.resemble.ai/docs/getting_started/errors
        if not response_data.get("success"):
            raise RuntimeError(f"ResembleAI synthesis failed: {response_data.get('message')}")

        audio_bytes = base64.b64decode(response_data["audio_content"])
        return audio_bytes