import sys
import os
import logging

addon_dir = os.path.dirname(os.path.realpath(__file__))
external_dir = os.path.join(addon_dir, 'external')
sys.path.insert(0, external_dir)

import testing_utils
import gui_testing_utils
import component_batch

logger = logging.getLogger(__name__)


def test_batch_dialog_editor_manual(qtbot):
    # HYPERTTS_BATCH_DIALOG_DEBUG=yes pytest --log-cli-level=DEBUG test_components.py -k test_batch_dialog_editor_manual -s -rPP

    logger.info('test_batch_dialog_editor_manual')

    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    note_id_list = [config_gen.note_id_1, config_gen.note_id_2]    

    # test saving of config
    # =====================

    dialog = gui_testing_utils.build_empty_dialog()
    note = hypertts_instance.anki_utils.get_note_by_id(config_gen.note_id_1)
    mock_editor = testing_utils.MockEditor()
    dialog = gui_testing_utils.build_empty_dialog()
    batch = component_batch.create_component_batch_editor_new_preset(
        hypertts_instance, dialog, note, mock_editor, False, 'preset 1')
    
    if os.environ.get('HYPERTTS_BATCH_DIALOG_DEBUG', 'no') == 'yes':
        dialog.exec()
