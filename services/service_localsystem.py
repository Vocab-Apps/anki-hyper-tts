import sys
import logging
import io
import pyttsx3
import pprint

voice = __import__('voice', globals(), locals(), [], sys._addon_import_level_services)
service = __import__('service', globals(), locals(), [], sys._addon_import_level_services)
errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_services)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_services)
languages = __import__('languages', globals(), locals(), [], sys._addon_import_level_services)


class LocalSystem(service.ServiceBase):

    def __init__(self):
        service.ServiceBase.__init__(self)

    @property
    def service_type(self) -> constants.ServiceType:
        return constants.ServiceType.tts

    @property
    def service_fee(self) -> constants.ServiceFee:
        return constants.ServiceFee.Free

    def voice_list(self):
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        for voice in voices:
            pprint.pprint(voice)
            logging.info(f'voice name: {voice.name} gender: {voice.gender}')
        raise Exception('not implemented')


    def get_tts_audio(self, source_text, voice: voice.VoiceBase, options):
        # configuration options
        throttle_seconds = self.get_configuration_value_optional(self.CONFIG_THROTTLE_SECONDS, 0)

        if throttle_seconds > 0:
            time.sleep(throttle_seconds)

        tts = gtts.gTTS(text=source_text, lang=voice.voice_key)
        buffer = io.BytesIO()
        tts.write_to_fp(buffer)

        return buffer.getbuffer()

