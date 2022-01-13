

class NoteStatus():
    def __init__(self, note_id):
        self.note_id = note_id
        self.source_text = None
        self.processed_text = None
        self.sound_file = None
        self.error = None

class BatchStatus():
    def __init__(self, note_id_list, change_listener_fn):
        self.note_id_list = note_id_list
        self.change_listener_fn = change_listener_fn
        self.note_status_array = []
        self.note_status_map = {}
        self.note_id_map = {}
        i = 0
        for note_id in self.note_id_list:
            note_status = NoteStatus(note_id)
            self.note_status_array.append(note_status)
            self.note_status_map[note_id] = note_status
            self.note_id_map[note_id] = i
            i += 1
    
    def __getitem__(self, array_index):
        return self.note_status_array[array_index]

    def set_source_text_blank_error(self, note_id, source_text):
        self.note_status_map[note_id].source_text = source_text
        self.note_status_map[note_id].error = None
        self.notify_change(note_id)

    def set_processed_text(self, note_id, processed_text):
        self.note_status_map[note_id].processed_text = processed_text
        self.notify_change(note_id)

    def set_error_blank_source_text(self, note_id, error):
        self.note_status_map[note_id].error = error
        self.note_status_map[note_id].source_text = None
        self.notify_change(note_id)


    def set_sound(self, note_id, sound):
        self.note_status_map[note_id].sound = sound
        self.notify_change(note_id)

    def notify_change(self, note_id):
        row = self.note_id_map[note_id]
        self.change_listener_fn(note_id, row)