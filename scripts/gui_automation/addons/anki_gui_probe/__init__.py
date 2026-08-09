"""
anki_gui_probe - a development-only Anki add-on which exposes the live Qt widget
tree over HTTP so an AI agent (or a human) can inspect and drive dialogs as text
instead of pixels.

It is installed only into the throwaway automation profile created by
scripts/gui_automation/setup_profile.py and is never shipped with HyperTTS.

Protocol: POST / with a JSON body {"action": "...", ...}, mirroring AnkiConnect's
style. Every response is JSON: {"result": ..., "error": null}.

All Qt access happens on the main thread via aqt.mw.taskman.run_on_main. Actions
which open a modal dialog block the main thread; those return
{"status": "pending"} rather than failing, since the modal is the expected state.
"""

import json
import os
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import aqt
import aqt.qt

try:
    from PyQt6.QtTest import QTest
except ImportError:  # pragma: no cover - only on a qt5 build
    QTest = None

DEFAULT_PORT = 8767
MAIN_THREAD_TIMEOUT = 15.0


class ProbeError(Exception):
    pass


# main thread dispatch
# ====================

def run_on_main_sync(function, timeout=MAIN_THREAD_TIMEOUT):
    """run function on the Qt main thread and return its result"""
    outcome = {}
    done = threading.Event()

    def wrapper():
        try:
            outcome['value'] = function()
        except Exception as exception:  # noqa: BLE001 - reported back to the caller
            outcome['error'] = f'{type(exception).__name__}: {exception}'
            outcome['traceback'] = traceback.format_exc()
        finally:
            done.set()

    aqt.mw.taskman.run_on_main(wrapper)
    if not done.wait(timeout):
        return {
            'status': 'pending',
            'note': 'the qt main thread is busy, a modal dialog is most likely open. '
                    'query action=windows to see it.',
        }
    if 'error' in outcome:
        raise ProbeError(f"{outcome['error']}\n{outcome.get('traceback', '')}")
    return outcome['value']


def run_on_main_async(function):
    """schedule function on the Qt main thread without waiting for it"""
    def wrapper():
        try:
            function()
        except Exception:  # noqa: BLE001 - nothing to report the error to
            traceback.print_exc()

    aqt.mw.taskman.run_on_main(wrapper)
    return {'status': 'scheduled'}


# widget introspection
# ===================

def unwrap_variant(value):
    """anki/hypertts table models return QVariant, which is not json serializable"""
    if isinstance(value, aqt.qt.QVariant):
        if value.isNull():
            return None
        return value.value()
    return value


def widget_text(widget):
    """the most useful piece of user visible state for this widget"""
    for getter in ('text', 'currentText', 'title', 'plainText', 'windowTitle'):
        if hasattr(widget, getter):
            try:
                value = getattr(widget, getter)()
            except Exception:  # noqa: BLE001
                continue
            if isinstance(value, str) and value != '':
                return value
    return None


def widget_extra(widget):
    extra = {}
    if isinstance(widget, aqt.qt.QAbstractButton):
        if widget.isCheckable():
            extra['checked'] = widget.isChecked()
    if isinstance(widget, aqt.qt.QComboBox):
        extra['items'] = [widget.itemText(i) for i in range(widget.count())]
        extra['current_index'] = widget.currentIndex()
    if isinstance(widget, aqt.qt.QTabWidget):
        extra['tabs'] = [widget.tabText(i) for i in range(widget.count())]
        extra['current_index'] = widget.currentIndex()
    if isinstance(widget, aqt.qt.QStackedWidget):
        extra['current_index'] = widget.currentIndex()
    if isinstance(widget, aqt.qt.QProgressBar):
        extra['value'] = widget.value()
        extra['maximum'] = widget.maximum()
    return extra


def describe_widget(widget, path):
    geometry = widget.geometry()
    return {
        'path': path,
        'class': widget.metaObject().className(),
        'object_name': widget.objectName(),
        'text': widget_text(widget),
        'visible': widget.isVisible(),
        'enabled': widget.isEnabled(),
        'geometry': [geometry.x(), geometry.y(), geometry.width(), geometry.height()],
        **widget_extra(widget),
    }


def child_widgets(widget):
    return [child for child in widget.children() if isinstance(child, aqt.qt.QWidget)]


def build_path(parent_path, widget, siblings):
    """stable-ish address: object name when available, otherwise class + index"""
    class_name = widget.metaObject().className()
    if widget.objectName():
        return f'{parent_path}/{widget.objectName()}'
    index = 0
    for sibling in siblings:
        if sibling is widget:
            break
        if sibling.metaObject().className() == class_name:
            index += 1
    return f'{parent_path}/{class_name}[{index}]'


def walk_widgets(widget, path, depth, max_depth, visible_only):
    """yield (widget, path, depth) depth first"""
    yield widget, path, depth
    if depth >= max_depth:
        return
    children = child_widgets(widget)
    for child in children:
        if visible_only and not child.isVisible():
            continue
        yield from walk_widgets(child, build_path(path, child, children), depth + 1,
                                max_depth, visible_only)


def top_level_windows():
    windows = []
    for widget in aqt.qt.QApplication.topLevelWidgets():
        if not widget.isWindow():
            continue
        windows.append(widget)
    return windows


def window_path(widget):
    if widget.objectName():
        return widget.objectName()
    return widget.metaObject().className()


ADDRESSING_KEYS = ('object_name', 'path', 'class', 'window', 'visible_only')


def widget_spec(params, include_text=False):
    """
    extract the widget addressing keys from an action's params, so that a param
    like text= (the value to type into a combo box) is not mistaken for a widget
    matcher. Actions which have no value of their own can address by text.
    """
    spec = {key: params[key] for key in ADDRESSING_KEYS if key in params}
    if include_text and params.get('text') is not None:
        spec['text'] = params['text']
    return spec


def find_widget(spec):
    """
    locate a single widget. spec keys (any combination):
      object_name, path, class, text, window
    raises when zero or more than one widget matches
    """
    object_name = spec.get('object_name')
    path = spec.get('path')
    class_name = spec.get('class')
    text = spec.get('text')
    window_filter = spec.get('window')
    visible_only = spec.get('visible_only', True)

    if not any([object_name, path, class_name, text]):
        raise ProbeError('specify at least one of object_name, path, class, text')

    matches = []
    for window in top_level_windows():
        root_path = window_path(window)
        if window_filter is not None and window_filter not in (
                root_path, window.windowTitle(), window.objectName()):
            continue
        if visible_only and not window.isVisible():
            continue
        for widget, widget_path, _depth in walk_widgets(window, root_path, 0, 40, visible_only):
            if object_name is not None and widget.objectName() != object_name:
                continue
            if path is not None and widget_path != path:
                continue
            if class_name is not None and widget.metaObject().className() != class_name:
                continue
            if text is not None and (widget_text(widget) or '') != text:
                continue
            matches.append((widget, widget_path))

    if not matches:
        raise ProbeError(f'no widget matched {spec}')
    if len(matches) > 1:
        paths = [widget_path for _widget, widget_path in matches[:10]]
        raise ProbeError(f'{len(matches)} widgets matched {spec}, be more specific: {paths}')
    return matches[0][0]


def all_actions():
    actions = []
    for window in top_level_windows():
        for action in window.findChildren(aqt.qt.QAction):
            actions.append((window, action))
    return actions


# actions
# =======

def action_ping(_params):
    return {'status': 'ok', 'profile': aqt.mw.pm.name if aqt.mw.pm else None}


def action_windows(params):
    visible_only = params.get('visible_only', True)

    def op():
        windows = []
        for window in top_level_windows():
            if visible_only and not window.isVisible():
                continue
            geometry = window.geometry()
            windows.append({
                'path': window_path(window),
                'class': window.metaObject().className(),
                'object_name': window.objectName(),
                'title': window.windowTitle(),
                'visible': window.isVisible(),
                'modal': window.isModal(),
                'active': window.isActiveWindow(),
                'geometry': [geometry.x(), geometry.y(), geometry.width(), geometry.height()],
            })
        return windows

    return run_on_main_sync(op)


def action_widget_tree(params):
    window_filter = params.get('window')
    max_depth = params.get('max_depth', 40)
    visible_only = params.get('visible_only', True)
    named_only = params.get('named_only', False)
    # widgets which are pure layout scaffolding and only add noise
    skip_classes = set(params.get('skip_classes', []))

    def op():
        result = []
        for window in top_level_windows():
            root_path = window_path(window)
            if window_filter is not None and window_filter not in (
                    root_path, window.windowTitle(), window.objectName()):
                continue
            if visible_only and not window.isVisible():
                continue
            for widget, widget_path, depth in walk_widgets(
                    window, root_path, 0, max_depth, visible_only):
                if named_only and not widget.objectName() and depth > 0:
                    continue
                if widget.metaObject().className() in skip_classes:
                    continue
                entry = describe_widget(widget, widget_path)
                entry['depth'] = depth
                result.append(entry)
        if not result:
            raise ProbeError(f'no window matched {window_filter}')
        return result

    return run_on_main_sync(op)


def action_widget_info(params):
    def op():
        widget = find_widget(widget_spec(params, include_text=True))
        return describe_widget(widget, params.get('path') or params.get('object_name') or '?')

    return run_on_main_sync(op)


def action_table(params):
    """dump the contents of a QTableView / QTreeView / QListView as rows"""
    max_rows = params.get('max_rows', 200)

    def op():
        widget = find_widget(widget_spec(params, include_text=True))
        if not isinstance(widget, aqt.qt.QAbstractItemView):
            raise ProbeError(f'{widget.metaObject().className()} is not an item view')
        model = widget.model()
        if model is None:
            return {'headers': [], 'rows': []}
        row_count = model.rowCount(aqt.qt.QModelIndex())
        column_count = model.columnCount(aqt.qt.QModelIndex())
        headers = []
        for column in range(column_count):
            header = unwrap_variant(model.headerData(
                column, aqt.qt.Qt.Orientation.Horizontal,
                aqt.qt.Qt.ItemDataRole.DisplayRole))
            headers.append(str(header) if header is not None else '')
        rows = []
        for row in range(min(row_count, max_rows)):
            values = []
            for column in range(column_count):
                value = unwrap_variant(model.data(model.index(row, column),
                                                  aqt.qt.Qt.ItemDataRole.DisplayRole))
                values.append('' if value is None else str(value))
            rows.append(values)
        return {
            'headers': headers,
            'row_count': row_count,
            'truncated': row_count > max_rows,
            'rows': rows,
        }

    return run_on_main_sync(op)


def action_click(params):
    """click a button. buttons which open a modal dialog need wait=false"""
    wait = params.get('wait', True)

    def op():
        widget = find_widget(widget_spec(params, include_text=True))
        if not widget.isEnabled():
            raise ProbeError(f'widget {widget.objectName()} is disabled')
        if isinstance(widget, aqt.qt.QAbstractButton):
            # HyperTTS wires most buttons to the pressed signal, click() emits
            # pressed + released + clicked so it covers both conventions
            widget.click()
            return {'clicked': widget.objectName() or widget.metaObject().className()}
        if QTest is not None:
            QTest.mouseClick(widget, aqt.qt.Qt.MouseButton.LeftButton)
            return {'clicked': widget.objectName() or widget.metaObject().className()}
        raise ProbeError(f'{widget.metaObject().className()} is not clickable')

    if wait:
        return run_on_main_sync(op)
    return run_on_main_async(op)


def action_set_text(params):
    text = params.get('text', '')

    def op():
        widget = find_widget(widget_spec(params))
        if isinstance(widget, aqt.qt.QLineEdit):
            widget.setText(text)
        elif isinstance(widget, aqt.qt.QPlainTextEdit):
            widget.setPlainText(text)
        elif isinstance(widget, aqt.qt.QTextEdit):
            widget.setPlainText(text)
        elif isinstance(widget, aqt.qt.QComboBox):
            widget.setCurrentText(text)
        else:
            raise ProbeError(f'cannot set text on {widget.metaObject().className()}')
        return {'text': text}

    return run_on_main_sync(op)


def action_set_combo(params):
    text = params.get('text')
    index = params.get('index')

    def op():
        widget = find_widget(widget_spec(params))
        if not isinstance(widget, aqt.qt.QComboBox):
            raise ProbeError(f'{widget.metaObject().className()} is not a combo box')
        if index is not None:
            widget.setCurrentIndex(index)
        elif text is not None:
            items = [widget.itemText(i) for i in range(widget.count())]
            if text not in items:
                raise ProbeError(f'[{text}] not among combo box items: {items}')
            widget.setCurrentIndex(items.index(text))
        else:
            raise ProbeError('specify text or index')
        return {'current_text': widget.currentText(), 'current_index': widget.currentIndex()}

    return run_on_main_sync(op)


def action_set_checked(params):
    checked = params.get('checked', True)

    def op():
        widget = find_widget(widget_spec(params))
        if not isinstance(widget, aqt.qt.QAbstractButton) or not widget.isCheckable():
            raise ProbeError(f'{widget.metaObject().className()} is not checkable')
        if widget.isChecked() != checked:
            # click so that the toggled/stateChanged signals fire
            widget.click()
        return {'checked': widget.isChecked()}

    return run_on_main_sync(op)


def action_select_row(params):
    """select a row in an item view, which is how HyperTTS previews a note"""
    row = params.get('row', 0)

    def op():
        widget = find_widget(widget_spec(params))
        if not isinstance(widget, aqt.qt.QAbstractItemView):
            raise ProbeError(f'{widget.metaObject().className()} is not an item view')
        widget.selectRow(row)
        return {'row': row}

    return run_on_main_sync(op)


def action_list_actions(params):
    filter_text = params.get('text')

    def op():
        result = []
        for window, action in all_actions():
            text = action.text()
            if filter_text is not None and filter_text not in text:
                continue
            result.append({
                'text': text,
                'enabled': action.isEnabled(),
                'window': window_path(window),
                'window_title': window.windowTitle(),
            })
        return result

    return run_on_main_sync(op)


def action_trigger_action(params):
    """
    trigger a QAction by its menu text. Most HyperTTS entry points open a modal
    dialog, so this does not wait for the main thread by default.
    """
    text = params.get('text')
    window_filter = params.get('window')
    wait = params.get('wait', False)
    if text is None:
        raise ProbeError('text is required')

    def op():
        matches = []
        for window, action in all_actions():
            if window_filter is not None and window_filter not in (
                    window_path(window), window.windowTitle(), window.objectName()):
                continue
            if action.text() == text:
                matches.append((window, action))
        if not matches:
            partial = [(window, action) for window, action in all_actions()
                       if text in action.text()]
            if len(partial) == 1:
                matches = partial
        if not matches:
            raise ProbeError(f'no action matched [{text}]')
        if len(matches) > 1:
            raise ProbeError(f'{len(matches)} actions matched [{text}], pass window=')
        window, action = matches[0]
        action.trigger()
        return {'triggered': action.text()}

    if wait:
        return run_on_main_sync(op)
    return run_on_main_async(op)


def action_close_window(params):
    def op():
        matches = []
        for window in top_level_windows():
            if not window.isVisible():
                continue
            if params.get('title') is not None and window.windowTitle() != params['title']:
                continue
            if params.get('class') is not None \
                    and window.metaObject().className() != params['class']:
                continue
            if params.get('title') is None and params.get('class') is None:
                continue
            matches.append(window)
        if not matches:
            raise ProbeError(f'no window matched {params}')
        for window in matches:
            window.close()
        return {'closed': [window_path(window) for window in matches]}

    return run_on_main_async(op) if not params.get('wait', True) else run_on_main_sync(op)


def action_screenshot(params):
    """
    grab a window with QWidget.grab(). Pass window= to pick one, otherwise the
    active window is used. Use scripts/gui_automation/screenshot.sh for a full
    screen grab (which also captures window decorations).
    """
    path = params.get('path')
    if not path:
        raise ProbeError('path is required')
    window_filter = params.get('window')

    def op():
        target = None
        if window_filter is None:
            target = aqt.qt.QApplication.activeWindow()
            if target is None:
                visible = [window for window in top_level_windows() if window.isVisible()]
                if not visible:
                    raise ProbeError('no visible window')
                target = visible[-1]
        else:
            for window in top_level_windows():
                if window_filter in (window_path(window), window.windowTitle(),
                                     window.objectName()):
                    target = window
                    break
            if target is None:
                raise ProbeError(f'no window matched {window_filter}')
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        if not target.grab().save(path):
            raise ProbeError(f'could not save screenshot to {path}')
        return {'path': path, 'window': window_path(target)}

    return run_on_main_sync(op)


def find_browser():
    for window in top_level_windows():
        if window.metaObject().className() == 'Browser':
            return window
    raise ProbeError('the anki browser is not open, use ankiconnect guiBrowse first')


def action_browser_select_all(_params):
    """select every row in the browser, which is what HyperTTS operates on"""
    def op():
        browser = find_browser()
        browser.table.select_all()
        return {'selected_notes': len(browser.selectedNotes())}

    return run_on_main_sync(op)


def action_browser_search(params):
    query = params.get('query', '')

    def op():
        browser = find_browser()
        browser.form.searchEdit.lineEdit().setText(query)
        browser.onSearchActivated()
        return {'query': query, 'row_count': browser.table.len()}

    return run_on_main_sync(op)


def action_undo_status(_params):
    """the label of the next undoable operation, used to verify undo support"""
    def op():
        status = aqt.mw.col.undo_status()
        return {'undo': status.undo, 'redo': status.redo}

    return run_on_main_sync(op)


def action_undo(_params):
    def op():
        before = aqt.mw.col.undo_status().undo
        aqt.mw.undo()
        return {'undone': before}

    return run_on_main_sync(op)


def action_note_fields(params):
    """read the fields of a note straight from the collection"""
    note_id = params.get('note_id')
    if note_id is None:
        raise ProbeError('note_id is required')

    def op():
        note = aqt.mw.col.get_note(int(note_id))
        return {key: note[key] for key in note.keys()}

    return run_on_main_sync(op)


def action_eval(params):
    """
    last resort escape hatch: evaluate a python expression on the main thread with
    aqt, aqt.qt and mw in scope. Keep automation on the structured actions where
    possible, this exists for one-off debugging.
    """
    expression = params.get('expression')
    if expression is None:
        raise ProbeError('expression is required')

    def op():
        scope = {'aqt': aqt, 'qt': aqt.qt, 'mw': aqt.mw, 'probe': globals()}
        return repr(eval(expression, scope))  # noqa: S307 - development tool

    return run_on_main_sync(op)


ACTION_MAP = {
    'ping': action_ping,
    'windows': action_windows,
    'widget_tree': action_widget_tree,
    'widget_info': action_widget_info,
    'table': action_table,
    'click': action_click,
    'set_text': action_set_text,
    'set_combo': action_set_combo,
    'set_checked': action_set_checked,
    'select_row': action_select_row,
    'list_actions': action_list_actions,
    'trigger_action': action_trigger_action,
    'close_window': action_close_window,
    'screenshot': action_screenshot,
    'browser_select_all': action_browser_select_all,
    'browser_search': action_browser_search,
    'undo_status': action_undo_status,
    'undo': action_undo,
    'note_fields': action_note_fields,
    'eval': action_eval,
}


# http server
# ===========

class ProbeRequestHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, format, *args):  # noqa: A002 - signature from stdlib
        # keep anki's stdout readable
        pass

    def _respond(self, payload, status=200):
        body = json.dumps(payload).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._respond({'result': {'status': 'ok', 'actions': sorted(ACTION_MAP)}, 'error': None})

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            request = json.loads(self.rfile.read(length) or b'{}')
        except Exception as exception:  # noqa: BLE001
            self._respond({'result': None, 'error': f'bad request: {exception}'}, status=400)
            return

        action_name = request.get('action')
        params = request.get('params', {}) or {}
        handler = ACTION_MAP.get(action_name)
        if handler is None:
            self._respond({
                'result': None,
                'error': f'unknown action [{action_name}], available: {sorted(ACTION_MAP)}',
            }, status=400)
            return
        try:
            self._respond({'result': handler(params), 'error': None})
        except ProbeError as exception:
            self._respond({'result': None, 'error': str(exception)}, status=200)
        except Exception as exception:  # noqa: BLE001
            self._respond({
                'result': None,
                'error': f'{type(exception).__name__}: {exception}',
                'traceback': traceback.format_exc(),
            }, status=200)


def start_server():
    port = int(os.environ.get('HYPERTTS_GUI_PROBE_PORT', DEFAULT_PORT))
    server = ThreadingHTTPServer(('127.0.0.1', port), ProbeRequestHandler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, name='anki_gui_probe',
                              daemon=True)
    thread.start()
    print(f'[anki_gui_probe] listening on http://127.0.0.1:{port}')
    return server


_server = start_server()
