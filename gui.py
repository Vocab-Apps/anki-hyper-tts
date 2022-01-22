import sys

# pyqt
import PyQt5
import logging

# anki imports
import aqt.qt
import aqt.editor
import aqt.gui_hooks
import aqt.sound
import aqt.utils
import anki.hooks

# addon imports
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_base)
component_batch = __import__('component_batch', globals(), locals(), [], sys._addon_import_level_base)


class BatchDialog(PyQt5.QtWidgets.QDialog):
    def __init__(self, hypertts, note_id_list):
        super(PyQt5.QtWidgets.QDialog, self).__init__()
        self.hypertts = hypertts
        self.note_id_list = note_id_list
        self.batch_component = component_batch.ComponentBatch(self.hypertts, self.note_id_list)

    def setupUi(self):
        self.main_layout = PyQt5.QtWidgets.QVBoxLayout(self)
        self.batch_component.draw(self.main_layout)

def launch_batch_dialog(hypertts, note_id_list):
    logging.info('launch_batch_dialog')
    dialog = BatchDialog(hypertts, note_id_list)
    dialog.setupUi()
    dialog.exec_()


def init(hypertts):

    def browerMenusInit(browser: aqt.browser.Browser):
        menu = aqt.qt.QMenu(constants.ADDON_NAME, browser.form.menubar)
        browser.form.menubar.addMenu(menu)

        action = aqt.qt.QAction(f'HyperTTS Batch...', browser)
        action.triggered.connect(lambda: launch_batch_dialog(hypertts, browser.selectedNotes()))
        menu.addAction(action)

    def shortcut_test(cuts, editor):
        logging.info('editor shortcuts setup')
        cuts.append(("Ctrl+l", lambda: aqt.utils.tooltip("test")))

        
    # browser menus
    aqt.gui_hooks.browser_menus_did_init.append(browerMenusInit)
    # shortcuts
    aqt.gui_hooks.editor_did_init_shortcuts.append(shortcut_test)