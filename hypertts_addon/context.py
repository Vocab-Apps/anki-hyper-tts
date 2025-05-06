import sys
import uuid

from . import constants

class AudioRequestContext():
    def __init__(self, audio_request_reason: constants.AudioRequestReason):
        self.audio_request_reason = audio_request_reason
        self.batch_uuid = uuid.uuid4()

    def get_request_mode(self) -> constants.RequestMode:
        request_mode_map = {
            constants.AudioRequestReason.preview: constants.RequestMode.batch,
            constants.AudioRequestReason.batch: constants.RequestMode.batch,
            constants.AudioRequestReason.realtime: constants.RequestMode.dynamic,
            constants.AudioRequestReason.editor_browser: constants.RequestMode.edit,
            constants.AudioRequestReason.editor_add: constants.RequestMode.edit,
        }
        return request_mode_map.get(self.audio_request_reason, constants.RequestMode.batch)

    def get_audio_request_reason_tag(self):
        return self.audio_request_reason.name

    def get_batch_uuid_str(self):
        return self.batch_uuid.hex