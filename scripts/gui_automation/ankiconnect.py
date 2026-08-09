#!/usr/bin/env python3
"""
Command line client for AnkiConnect running inside the automation Anki instance,
plus a `seed` command which injects a deck / note type / notes that HyperTTS can
operate on.

Examples:
    ankiconnect.py version
    ankiconnect.py seed
    ankiconnect.py invoke deckNames
    ankiconnect.py invoke findNotes --params '{"query": "tag:hypertts_automation"}'
    ankiconnect.py notes
    ankiconnect.py browse

Only depends on the standard library.
"""

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_PORT = int(os.environ.get('HYPERTTS_GUI_ANKICONNECT_PORT', 8766))

DECK_NAME = 'HyperTTS Automation'
MODEL_NAME = 'HyperTTS Automation Note'
# anki search syntax: the quotes have to wrap the whole term, not just the value
DECK_QUERY = f'"deck:{DECK_NAME}"'
FIELDS = ['Chinese', 'English', 'Sound', 'Sound English']

# audio filenames: hypertts- prefixed files are the ones HyperTTS itself
# generates, the others simulate audio the user added some other way
HYPERTTS_AUDIO_FILES = [
    'hypertts-automation-0001.mp3',
    'hypertts-automation-0002.mp3',
    'hypertts-automation-0003.mp3',
]
FOREIGN_AUDIO_FILES = [
    'external-recording.mp3',
]


def invoke(action, port=DEFAULT_PORT, timeout=60, **params):
    payload = json.dumps({'action': action, 'version': 6, 'params': params}).encode('utf-8')
    request = urllib.request.Request(
        f'http://127.0.0.1:{port}/',
        data=payload,
        headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read())
    except urllib.error.URLError as exception:
        raise SystemExit(
            f'could not reach AnkiConnect on port {port}: {exception}\n'
            f'is anki running ? scripts/gui_automation/status.sh') from exception
    if body.get('error'):
        raise SystemExit(f"ankiconnect error on {action}: {body['error']}")
    return body['result']


def print_json(value):
    print(json.dumps(value, indent=2, ensure_ascii=False))


# seeding
# =======

def ensure_deck(port):
    if DECK_NAME not in invoke('deckNames', port=port):
        invoke('createDeck', port=port, deck=DECK_NAME)
        print(f'created deck [{DECK_NAME}]')


def ensure_model(port):
    if MODEL_NAME in invoke('modelNames', port=port):
        return
    invoke('createModel', port=port,
           modelName=MODEL_NAME,
           inOrderFields=FIELDS,
           cardTemplates=[{
               'Name': 'Card 1',
               'Front': '{{Chinese}}{{Sound}}',
               'Back': '{{FrontSide}}<hr id=answer>{{English}}{{Sound English}}',
           }])
    print(f'created note type [{MODEL_NAME}]')


def store_media(port):
    """store small dummy audio files so the sound tags reference real media"""
    for filename in HYPERTTS_AUDIO_FILES + FOREIGN_AUDIO_FILES:
        # not valid mp3 audio, but enough for tags to reference existing media
        data = base64.b64encode(f'dummy audio for {filename}'.encode('utf-8')).decode('ascii')
        invoke('storeMediaFile', port=port, filename=filename, data=data)
    print(f'stored {len(HYPERTTS_AUDIO_FILES + FOREIGN_AUDIO_FILES)} media files')


def seed_notes(port):
    """
    notes covering the cases the Remove Audio dialog has to handle:
      1. a single hypertts sound tag, nothing else in the field
      2. text followed by a hypertts sound tag
      3. audio which HyperTTS did not generate
      4. hypertts audio in two different fields
      5. no audio at all
    """
    notes = [
        {
            'Chinese': '老人家', 'English': 'old people',
            'Sound': f'[sound:{HYPERTTS_AUDIO_FILES[0]}]', 'Sound English': '',
        },
        {
            'Chinese': '你好', 'English': 'hello',
            'Sound': f'你好 [sound:{HYPERTTS_AUDIO_FILES[1]}]', 'Sound English': '',
        },
        {
            'Chinese': '赚钱', 'English': 'to earn money',
            'Sound': f'[sound:{FOREIGN_AUDIO_FILES[0]}]', 'Sound English': '',
        },
        {
            'Chinese': '大使馆', 'English': 'embassy',
            'Sound': f'[sound:{HYPERTTS_AUDIO_FILES[2]}]',
            'Sound English': f'[sound:{HYPERTTS_AUDIO_FILES[0]}]',
        },
        {
            'Chinese': '猫', 'English': 'cat',
            'Sound': '', 'Sound English': '',
        },
    ]
    payload = [{
        'deckName': DECK_NAME,
        'modelName': MODEL_NAME,
        'fields': fields,
        'options': {'allowDuplicate': True},
        'tags': ['hypertts_automation'],
    } for fields in notes]
    note_ids = invoke('addNotes', port=port, notes=payload)
    added = [note_id for note_id in note_ids if note_id]
    print(f'added {len(added)} notes: {note_ids}')
    # AnkiConnect's addNote still assigns the deck the legacy way (through the
    # note type dict), which modern Anki ignores, so the cards land in Default.
    # move them explicitly.
    card_ids = invoke('findCards', port=port, query='tag:hypertts_automation')
    if card_ids:
        invoke('changeDeck', port=port, cards=card_ids, deck=DECK_NAME)
        print(f'moved {len(card_ids)} cards into [{DECK_NAME}]')
    return note_ids


def command_seed(args):
    port = args.port
    ensure_deck(port)
    ensure_model(port)
    store_media(port)
    if args.reset:
        existing = invoke('findNotes', port=port, query='tag:hypertts_automation')
        if existing:
            invoke('deleteNotes', port=port, notes=existing)
            print(f'deleted {len(existing)} pre-existing notes')
    note_ids = seed_notes(port)
    print_json({'deck': DECK_NAME, 'model': MODEL_NAME, 'note_ids': note_ids})


def command_notes(args):
    note_ids = invoke('findNotes', port=args.port, query=args.query)
    info = invoke('notesInfo', port=args.port, notes=note_ids)
    for note in info:
        fields = {name: value['value'] for name, value in note['fields'].items()}
        print(f"{note['noteId']}: {fields}")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--port', type=int, default=DEFAULT_PORT)
    subparsers = parser.add_subparsers(dest='command', required=True)

    subparsers.add_parser('version')

    seed_parser = subparsers.add_parser('seed', help='inject deck / note type / notes')
    seed_parser.add_argument('--reset', action='store_true',
                             help='delete existing notes in the automation deck first')

    notes_parser = subparsers.add_parser('notes', help='dump note fields')
    notes_parser.add_argument('--query', default=DECK_QUERY)

    browse_parser = subparsers.add_parser('browse', help='open the browser on a query')
    browse_parser.add_argument('--query', default=DECK_QUERY)

    invoke_parser = subparsers.add_parser('invoke', help='call any ankiconnect action')
    invoke_parser.add_argument('action')
    invoke_parser.add_argument('--params', default='{}')

    args = parser.parse_args()

    if args.command == 'version':
        print_json(invoke('version', port=args.port))
    elif args.command == 'seed':
        command_seed(args)
    elif args.command == 'notes':
        command_notes(args)
    elif args.command == 'browse':
        print_json(invoke('guiBrowse', port=args.port, query=args.query))
    elif args.command == 'invoke':
        print_json(invoke(args.action, port=args.port, **json.loads(args.params)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
