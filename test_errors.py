import unittest
import pytest
import pprint
import logging

import errors
import testing_utils

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
        logging.info('single action 1')
        raise errors.FieldEmptyError('field1')


    assert isinstance(mock_hypertts.anki_utils.last_exception, errors.FieldEmptyError)
    assert mock_hypertts.anki_utils.last_action == 'single action 1'
    mock_hypertts.anki_utils.reset_exceptions()

    with error_manager.get_single_action_context('single action 2'):
        logging.info('single action 2')
        logging.info('successful')

    assert mock_hypertts.anki_utils.last_exception == None
    mock_hypertts.anki_utils.reset_exceptions()

    # unhandled exception
    with error_manager.get_single_action_context('single action 3'):
        logging.info('single action 3')
        raise Exception('this is unhandled')
    
    assert isinstance(mock_hypertts.anki_utils.last_exception, Exception)
    assert mock_hypertts.anki_utils.last_action == 'single action 3'
    mock_hypertts.anki_utils.reset_exceptions()


    # batch actions
    # =============

    batch_error_manager = error_manager.get_batch_error_manager('batch test 1')

    with batch_error_manager.get_batch_action_context(42):
        logging.info('batch iteration 1')
        raise errors.FieldEmptyError('field 3')

    with batch_error_manager.get_batch_action_context(43):
        logging.info('batch iteration 2')
        logging.info('ok')

    with batch_error_manager.get_batch_action_context(44):
        logging.info('batch iteration 3')
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
        logging.info('batch iteration 1')
        logging.info('ok')

    with batch_error_manager.get_batch_action_context(46):
        logging.info('batch iteration 2')
        raise Exception('this is unhandled')

    expected_action_stats = {
        'success': 1,        
        'error': {'Unknown Error: this is unhandled': 1}
    }
    actual_action_stats = batch_error_manager.action_stats
    assert expected_action_stats == actual_action_stats    