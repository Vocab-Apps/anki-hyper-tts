import sys
import os

from test_utils import testing_utils
from hypertts_addon import errors
from hypertts_addon import logging_utils
from hypertts_addon import constants

logger = logging_utils.get_test_child_logger(__name__)

def test_exceptions(qtbot):
    try:
        raise errors.FieldEmptyError('field2')
    except Exception as e:
        error_message = str(e)
        assert error_message == 'Field <b>field2</b> is empty'

    # FieldNotFoundError

    try:
        raise errors.FieldNotFoundError('field1')
    except Exception as e:
        error_message = str(e)
        assert error_message == f'Field <b>field1</b> not found'


def test_error_manager(qtbot):
    # pytest test_errors.py -s -rPP -k test_error_manager

    config_gen = testing_utils.TestConfigGenerator()
    mock_hypertts = config_gen.build_hypertts_instance('default')
    error_manager = errors.ErrorManager(mock_hypertts.anki_utils)

    # single actions
    # ==============

    with error_manager.get_single_action_context('single action 1'):
        logger.info('single action 1')
        raise errors.FieldEmptyError('field1')


    assert isinstance(mock_hypertts.anki_utils.last_exception, errors.FieldEmptyError)
    assert mock_hypertts.anki_utils.last_action == 'single action 1'
    mock_hypertts.anki_utils.reset_exceptions()

    with error_manager.get_single_action_context('single action 2'):
        logger.info('single action 2')
        logger.info('successful')

    assert mock_hypertts.anki_utils.last_exception == None
    mock_hypertts.anki_utils.reset_exceptions()

    # unhandled exception
    with error_manager.get_single_action_context('single action 3'):
        logger.info('single action 3')
        raise Exception('this is unhandled')
    
    assert isinstance(mock_hypertts.anki_utils.last_exception, Exception)
    assert mock_hypertts.anki_utils.last_action == 'single action 3'
    mock_hypertts.anki_utils.reset_exceptions()

    # single actions, configurable
    # ============================

    # dialog
    with error_manager.get_single_action_context_configurable('single action 4', constants.ErrorDialogType.Dialog):
        logger.info('single action 4')
        raise errors.FieldEmptyError('field1')

    assert isinstance(mock_hypertts.anki_utils.last_exception, errors.FieldEmptyError)
    assert mock_hypertts.anki_utils.last_action == 'single action 4'
    assert mock_hypertts.anki_utils.last_exception_dialog_type == 'dialog'
    mock_hypertts.anki_utils.reset_exceptions()

    # tooltip
    with error_manager.get_single_action_context_configurable('single action 5', constants.ErrorDialogType.Tooltip):
        logger.info('single action 5')
        raise errors.FieldEmptyError('field1')

    assert isinstance(mock_hypertts.anki_utils.last_exception, errors.FieldEmptyError)
    assert mock_hypertts.anki_utils.last_action == 'single action 5'
    assert mock_hypertts.anki_utils.last_exception_dialog_type == 'tooltip'
    mock_hypertts.anki_utils.reset_exceptions()    

    # nothing
    with error_manager.get_single_action_context_configurable('single action 6', constants.ErrorDialogType.Nothing):
        logger.info('single action 6')
        raise errors.FieldEmptyError('field1')

    assert mock_hypertts.anki_utils.last_action == None
    assert mock_hypertts.anki_utils.last_exception_dialog_type == None
    mock_hypertts.anki_utils.reset_exceptions()        

    # batch actions
    # =============

    batch_error_manager = error_manager.get_batch_error_manager('batch test 1')

    with batch_error_manager.get_batch_action_context(42):
        logger.info('batch iteration 1')
        raise errors.FieldEmptyError('field 3')

    with batch_error_manager.get_batch_action_context(43):
        logger.info('batch iteration 2')
        logger.info('ok')

    with batch_error_manager.get_batch_action_context(44):
        logger.info('batch iteration 3')
        raise errors.FieldNotFoundError('field 4')

    expected_action_stats = {
        'success': 1,
        'error': {
            'Field <b>field 3</b> is empty': 1,
            'Field <b>field 4</b> not found': 1
        }
    }
    actual_action_stats = batch_error_manager.action_stats
    assert expected_action_stats == actual_action_stats

    # batch_error_manager.display_stats()

    # batch actions with unhandled exceptions
    # =======================================

    batch_error_manager = error_manager.get_batch_error_manager('batch test 2')

    with batch_error_manager.get_batch_action_context(45):
        logger.info('batch iteration 1')
        logger.info('ok')

    with batch_error_manager.get_batch_action_context(46):
        logger.info('batch iteration 2')
        raise Exception('this is unhandled')

    expected_action_stats = {
        'success': 1,        
        'error': {'Unknown Error: this is unhandled': 1}
    }
    actual_action_stats = batch_error_manager.action_stats
    assert expected_action_stats == actual_action_stats    