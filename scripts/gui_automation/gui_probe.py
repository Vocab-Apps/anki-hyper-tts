#!/usr/bin/env python3
"""
Command line client for the anki_gui_probe add-on: inspect and drive the live
Anki/HyperTTS GUI as text.

Examples:
    gui_probe.py windows
    gui_probe.py tree --window 'HyperTTS: Remove Audio'
    gui_probe.py tree --named-only
    gui_probe.py table --object-name hypertts_remove_audio_preview_table
    gui_probe.py click --object-name hypertts_remove_audio_remove_button --no-wait
    gui_probe.py combo --object-name hypertts_remove_audio_field --text Sound
    gui_probe.py trigger --text 'Remove Audio...'
    gui_probe.py undo-status
    gui_probe.py raw '{"action": "eval", "params": {"expression": "mw.pm.name"}}'

Only depends on the standard library so it runs with any python3.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_PORT = int(os.environ.get('HYPERTTS_GUI_PROBE_PORT', 8767))


def invoke(action, params=None, port=DEFAULT_PORT, timeout=60):
    payload = json.dumps({'action': action, 'params': params or {}}).encode('utf-8')
    request = urllib.request.Request(
        f'http://127.0.0.1:{port}/',
        data=payload,
        headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read())
    except urllib.error.URLError as exception:
        raise SystemExit(
            f'could not reach anki_gui_probe on port {port}: {exception}\n'
            f'is anki running ? scripts/gui_automation/status.sh') from exception
    if body.get('error'):
        message = body['error']
        if body.get('traceback'):
            message = f"{message}\n{body['traceback']}"
        raise SystemExit(f'probe error: {message}')
    return body['result']


# output formatting
# =================

def format_widget(entry):
    parts = [entry['class']]
    if entry['object_name']:
        parts.append(f"#{entry['object_name']}")
    if entry.get('text'):
        text = entry['text']
        if len(text) > 60:
            text = text[:57] + '...'
        parts.append(f'"{text}"')
    flags = []
    if not entry['visible']:
        flags.append('hidden')
    if not entry['enabled']:
        flags.append('disabled')
    if 'checked' in entry:
        flags.append('checked' if entry['checked'] else 'unchecked')
    if 'current_index' in entry:
        flags.append(f"index={entry['current_index']}")
    if flags:
        parts.append(f"[{','.join(flags)}]")
    line = ' '.join(parts)
    if entry.get('items'):
        line += f"\n{'  ' * (entry['depth'] + 1)}items: {entry['items']}"
    if entry.get('tabs'):
        line += f"\n{'  ' * (entry['depth'] + 1)}tabs: {entry['tabs']}"
    return line


def print_tree(entries):
    for entry in entries:
        print('  ' * entry['depth'] + format_widget(entry))


def print_table(result):
    print(' | '.join(result['headers']))
    print('-' * 60)
    for row in result['rows']:
        print(' | '.join(row))
    print(f"({result['row_count']} rows"
          + (', truncated' if result.get('truncated') else '') + ')')


def print_json(value):
    print(json.dumps(value, indent=2, ensure_ascii=False))


# subcommands
# ===========

def add_target_arguments(parser):
    parser.add_argument('--object-name', help='widget objectName')
    parser.add_argument('--path', help='widget path from the tree output')
    parser.add_argument('--class', dest='class_name', help='widget class name')
    parser.add_argument('--text', help='widget text')
    parser.add_argument('--window', help='restrict to this window (path or title)')


def target_params(args):
    params = {}
    for source, key in (('object_name', 'object_name'), ('path', 'path'),
                        ('class_name', 'class'), ('window', 'window')):
        value = getattr(args, source, None)
        if value is not None:
            params[key] = value
    return params


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--port', type=int, default=DEFAULT_PORT)
    subparsers = parser.add_subparsers(dest='command', required=True)

    subparsers.add_parser('ping')
    subparsers.add_parser('windows')

    tree_parser = subparsers.add_parser('tree', help='dump the widget tree as text')
    tree_parser.add_argument('--window', help='window path or title')
    tree_parser.add_argument('--named-only', action='store_true',
                             help='only widgets which have an objectName')
    tree_parser.add_argument('--all', action='store_true',
                             help='include hidden widgets and windows')
    tree_parser.add_argument('--max-depth', type=int, default=40)

    info_parser = subparsers.add_parser('info', help='details for one widget')
    add_target_arguments(info_parser)

    table_parser = subparsers.add_parser('table', help='dump an item view as rows')
    add_target_arguments(table_parser)
    table_parser.add_argument('--max-rows', type=int, default=200)

    click_parser = subparsers.add_parser('click')
    add_target_arguments(click_parser)
    click_parser.add_argument('--no-wait', action='store_true',
                              help='do not wait for the main thread (use when the '
                                   'click opens a modal dialog)')

    set_text_parser = subparsers.add_parser('set-text')
    add_target_arguments(set_text_parser)
    set_text_parser.add_argument('--value', required=True)

    combo_parser = subparsers.add_parser('combo', help='select a combo box entry')
    add_target_arguments(combo_parser)
    combo_parser.add_argument('--index', type=int)

    check_parser = subparsers.add_parser('check', help='check/uncheck a checkbox')
    add_target_arguments(check_parser)
    check_parser.add_argument('--off', action='store_true')

    row_parser = subparsers.add_parser('select-row')
    add_target_arguments(row_parser)
    row_parser.add_argument('--row', type=int, default=0)

    actions_parser = subparsers.add_parser('actions', help='list menu actions')
    actions_parser.add_argument('--text', help='substring filter')

    trigger_parser = subparsers.add_parser('trigger', help='trigger a menu action')
    trigger_parser.add_argument('--text', required=True)
    trigger_parser.add_argument('--window')
    trigger_parser.add_argument('--wait', action='store_true')

    close_parser = subparsers.add_parser('close', help='close a window')
    close_parser.add_argument('--title')
    close_parser.add_argument('--class', dest='class_name')

    screenshot_parser = subparsers.add_parser('screenshot',
                                              help='grab one window with QWidget.grab()')
    screenshot_parser.add_argument('--path', required=True)
    screenshot_parser.add_argument('--window')

    subparsers.add_parser('undo-status')
    subparsers.add_parser('undo')
    subparsers.add_parser('browser-select-all')

    search_parser = subparsers.add_parser('browser-search')
    search_parser.add_argument('--query', required=True)

    note_parser = subparsers.add_parser('note-fields')
    note_parser.add_argument('--note-id', required=True)

    raw_parser = subparsers.add_parser('raw', help='send a raw json request')
    raw_parser.add_argument('json')

    args = parser.parse_args()
    port = args.port

    if args.command == 'ping':
        print_json(invoke('ping', port=port))
    elif args.command == 'windows':
        print_json(invoke('windows', port=port))
    elif args.command == 'tree':
        print_tree(invoke('widget_tree', {
            'window': args.window,
            'named_only': args.named_only,
            'visible_only': not args.all,
            'max_depth': args.max_depth,
        }, port=port))
    elif args.command == 'info':
        print_json(invoke('widget_info', target_params(args), port=port))
    elif args.command == 'table':
        params = target_params(args)
        params['max_rows'] = args.max_rows
        print_table(invoke('table', params, port=port))
    elif args.command == 'click':
        params = target_params(args)
        if args.text is not None:
            params['text'] = args.text
        params['wait'] = not args.no_wait
        print_json(invoke('click', params, port=port))
    elif args.command == 'set-text':
        params = target_params(args)
        params['text'] = args.value
        print_json(invoke('set_text', params, port=port))
    elif args.command == 'combo':
        params = target_params(args)
        if args.index is not None:
            params['index'] = args.index
        elif args.text is not None:
            params['text'] = args.text
        else:
            raise SystemExit('pass --text or --index')
        print_json(invoke('set_combo', params, port=port))
    elif args.command == 'check':
        params = target_params(args)
        params['checked'] = not args.off
        print_json(invoke('set_checked', params, port=port))
    elif args.command == 'select-row':
        params = target_params(args)
        params['row'] = args.row
        print_json(invoke('select_row', params, port=port))
    elif args.command == 'actions':
        for entry in invoke('list_actions', {'text': args.text}, port=port):
            state = '' if entry['enabled'] else ' [disabled]'
            print(f"{entry['window']}: {entry['text']}{state}")
    elif args.command == 'trigger':
        print_json(invoke('trigger_action', {
            'text': args.text, 'window': args.window, 'wait': args.wait,
        }, port=port))
    elif args.command == 'close':
        print_json(invoke('close_window', {
            'title': args.title, 'class': args.class_name,
        }, port=port))
    elif args.command == 'screenshot':
        print_json(invoke('screenshot', {
            'path': args.path, 'window': args.window,
        }, port=port))
    elif args.command == 'undo-status':
        print_json(invoke('undo_status', port=port))
    elif args.command == 'undo':
        print_json(invoke('undo', port=port))
    elif args.command == 'browser-select-all':
        print_json(invoke('browser_select_all', port=port))
    elif args.command == 'browser-search':
        print_json(invoke('browser_search', {'query': args.query}, port=port))
    elif args.command == 'note-fields':
        print_json(invoke('note_fields', {'note_id': args.note_id}, port=port))
    elif args.command == 'raw':
        request = json.loads(args.json)
        print_json(invoke(request['action'], request.get('params'), port=port))
    return 0


if __name__ == '__main__':
    sys.exit(main())
