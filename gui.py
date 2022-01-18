import sys

# pyqt
import PyQt5
import logging

# anki imports
import aqt.qt
import aqt.editor
import aqt.gui_hooks
import aqt.sound
import anki.hooks

import_level = 0
if hasattr(sys, '_pytest_mode'):
    import_level = 0
else:
    # import running from within Anki
    import_level = 1

# addon imports
constants = __import__('constants', globals(), locals(), [], import_level)
component_batch = __import__('component_batch', globals(), locals(), [], import_level)


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

        
    # browser menus
    aqt.gui_hooks.browser_menus_did_init.append(browerMenusInit)