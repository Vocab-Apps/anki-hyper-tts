import sys
if hasattr(sys, '_pytest_mode'):
    import errors
else:
    from . import errors

# represent a deck + notetype combination (DNT)
class DeckNoteType():
    def __init__(self, deck_id, deck_name, model_id, model_name):
        self.deck_id = deck_id
        self.deck_name = deck_name
        self.model_id = model_id 
        self.model_name = model_name
    def __str__(self):
        return f'{self.model_name} / {self.deck_name}'

    def __eq__(self, other):
        if type(other) is type(self):
            return self.deck_id == other.deck_id and self.model_id == other.model_id
        else:
            return False    

    def __hash__(self):
        return hash((self.deck_id, self.model_id))


# represent a deck + notetype + field combination (DNTF), which can be associated with a language
class DeckNoteTypeField():
    def __init__(self, deck_note_type, field_name):
        self.deck_note_type = deck_note_type
        self.field_name = field_name

    def get_model_name(self):
        return self.deck_note_type.model_name

    def get_deck_name(self):
        return self.deck_note_type.deck_name

    def __str__(self):
        return f'{self.get_model_name()} / {self.get_deck_name()} / {self.field_name}'

    def __eq__(self, other):
        if type(other) is type(self):
            return self.deck_note_type == other.deck_note_type and self.field_name == other.field_name
        else:
            return False    

    def __hash__(self):
        return hash((self.deck_note_type, self.field_name))

class Deck():
    def __init__(self):
        self.note_type_map = {}

    def add_deck_note_type_field(self, deck_note_type_field: DeckNoteTypeField):
        note_type = deck_note_type_field.get_model_name()
        if note_type not in self.note_type_map:
            self.note_type_map[note_type] = []
        self.note_type_map[note_type].append(deck_note_type_field)


class DeckUtils():
    def __init__(self, anki_utils):
        self.anki_utils = anki_utils

    # just build a new Deck object
    def new_deck(self):
        return Deck()

    # from a DNT + field name, return DNTF
    def build_dntf_from_dnt(self, deck_note_type, field_name):
        return DeckNoteTypeField(deck_note_type, field_name)

    # given a note and the card, build DNT (used within note editor)
    # note: anki.notes.Note
    # card: anki.cards.Card
    def build_deck_note_type_from_note_card(self, note, card) -> DeckNoteType:
        if card == None:
            raise errors.AnkiItemNotFoundError(f'card not found')
        model_id = note.mid
        deck_id = card.did
        deck_note_type = self.build_deck_note_type(deck_id, model_id)
        return deck_note_type

    # given a note being edited and the AddCards dialog, build DNT (used when adding a new note)
    # note: anki.notes.Note
    # add_cards: aqt.addcards.AddCards
    def build_deck_note_type_from_addcard(self, note, add_cards) -> DeckNoteType:
        model_id = note.mid
        deck_id = add_cards.deckChooser.selectedId()
        deck_note_type = self.build_deck_note_type(deck_id, model_id)
        return deck_note_type    

    def build_deck_note_type_from_editor(self, editor):
        note = editor.note
        if note == None:
            raise errors.AnkiNoteEditorError(f'editor.note not found')

        if editor.addMode:
            deck_note_type = self.build_deck_note_type_from_addcard(note, editor.parentWindow)
        else:
            deck_note_type = self.build_deck_note_type_from_note_card(note, editor.card)

        return deck_note_type

    # given an editor and field index, return DNTF
    def editor_get_dntf(self, editor, field_index):
        deck_note_type = self.build_deck_note_type_from_editor(editor)
        deck_note_type_field = self.get_dntf_from_fieldindex(deck_note_type, field_index)
        return deck_note_type_field

    # given deck id, model id, build DNT
    def build_deck_note_type(self, deck_id, model_id) -> DeckNoteType:
        model = self.anki_utils.get_model(model_id)
        if model == None:
            raise errors.AnkiItemNotFoundError(f'Note Type id {model_id} not found')
        model_name = model['name']
        deck = self.anki_utils.get_deck(deck_id)
        if deck == None:
            raise errors.AnkiItemNotFoundError(f'Deck id {deck_id} not found')
        deck_name = deck['name']
        deck_note_type = DeckNoteType(deck_id, deck_name, model_id, model_name)
        return deck_note_type

    # given a deck id, model id and field name, build DNTF
    def build_deck_note_type_field(self, deck_id, model_id, field_name) -> DeckNoteTypeField:
        deck_note_type = self.build_deck_note_type(deck_id, model_id)
        return DeckNoteTypeField(deck_note_type, field_name)

    # given a deck name, model name and field name, build the DNTF
    def build_deck_note_type_field_from_names(self, deck_name, model_name, field_name) -> DeckNoteTypeField:
        # get the deck_id from the deck_name
        # get the model_id from the model_name

        model_id = self.anki_utils.get_model_id(model_name)
        deck_id = self.anki_utils.get_deck_id(deck_name)

        if model_id == None:
            raise errors.AnkiItemNotFoundError(f'Note Type {model_name} not found')
        if deck_id == None:
            raise errors.AnkiItemNotFoundError(f'Deck {deck_name} not found')

        deck_note_type = self.build_deck_note_type(deck_id, model_id)
        return DeckNoteTypeField(deck_note_type, field_name)    

    # given a DNT, get field names
    def get_field_names(self, deck_note_type):
        model = self.anki_utils.get_model(deck_note_type.model_id)
        fields = model['flds']
        field_names = [x['name'] for x in fields]
        return field_names        

    # given a DNT and field index, return DNTF
    def get_dntf_from_fieldindex(self, deck_note_type: DeckNoteType, field_index) -> DeckNoteTypeField:
        model = self.anki_utils.get_model(deck_note_type.model_id)
        fields = model['flds']
        field_name = fields[field_index]['name']
        return self.build_dntf_from_dnt(deck_note_type, field_name)        

    def get_field_id(self, deck_note_type_field: DeckNoteTypeField):
        model = self.anki_utils.get_model(deck_note_type_field.deck_note_type.model_id)
        fields = model['flds']
        field_names = [x['name'] for x in fields]
        if deck_note_type_field.field_name not in field_names:
            raise errors.FieldNotFoundError(deck_note_type_field)
        field_index = field_names.index(deck_note_type_field.field_name)
        return field_index    