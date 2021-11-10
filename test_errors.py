import unittest
import pytest
import pprint
import logging
import PyQt5

import constants
import dialogs
import errors
import deck_utils
import testing_utils

def test_exceptions(qtbot):
    try:
        raise errors.LanguageToolsValidationFieldEmpty()
    except Exception as e:
        error_message = str(e)
        assert error_message == 'Field is empty'

    # FieldNotFoundError

    try:
        dnt = deck_utils.DeckNoteType(1, 'Deck', 1, 'NoteType')
        dntf = deck_utils.DeckNoteTypeField(dnt, 'field1')
        raise errors.FieldNotFoundError(dntf)
    except Exception as e:
        error_message = str(e)
        assert error_message == f'Field not found: <b>NoteType / Deck / field1</b>. {constants.DOCUMENTATION_EDIT_RULES}'

def test_exception_operators(qtbot):
    dnt = deck_utils.DeckNoteType(1, 'Deck', 1, 'NoteType')
    dntf = deck_utils.DeckNoteTypeField(dnt, 'field1')

    exception1 = errors.FieldNotFoundError(dntf)
    exception2 = errors.FieldNotFoundError(dntf)

    assert str(exception1) == str(exception2)


def test_error_manager(qtbot):
    # pytest test_errors.py -s -rPP -k test_error_manager

    config_gen = testing_utils.TestConfigGenerator()
    mock_language_tools = config_gen.build_languagetools_instance('default')
    error_manager = errors.ErrorManager(mock_language_tools.anki_utils)

    dnt = deck_utils.DeckNoteType(1, 'Deck', 1, 'NoteType')
    dntf = deck_utils.DeckNoteTypeField(dnt, 'field1')


    # single actions
    # ==============

    with error_manager.get_single_action_context('single action 1'):
        logging.info('single action 1')
        raise errors.LanguageToolsValidationFieldEmpty()


    assert isinstance(mock_language_tools.anki_utils.last_exception, errors.LanguageToolsValidationFieldEmpty)
    assert mock_language_tools.anki_utils.last_action == 'single action 1'
    mock_language_tools.anki_utils.reset_exceptions()

    with error_manager.get_single_action_context('single action 2'):
        logging.info('single action 2')
        logging.info('successful')

    assert mock_language_tools.anki_utils.last_exception == None
    mock_language_tools.anki_utils.reset_exceptions()

    # unhandled exception
    with error_manager.get_single_action_context('single action 3'):
        logging.info('single action 3')
        raise Exception('this is unhandled')
    
    assert isinstance(mock_language_tools.anki_utils.last_exception, Exception)
    assert mock_language_tools.anki_utils.last_action == 'single action 3'
    mock_language_tools.anki_utils.reset_exceptions()


    # batch actions
    # =============

    batch_error_manager = error_manager.get_batch_error_manager('batch test 1')

    with batch_error_manager.get_batch_action_context('batch iteration 1'):
        logging.info('batch iteration 1')
        raise errors.LanguageToolsValidationFieldEmpty()

    with batch_error_manager.get_batch_action_context('batch iteration 2'):
        logging.info('batch iteration 2')
        logging.info('ok')

    with batch_error_manager.get_batch_action_context('batch iteration 3'):
        logging.info('batch iteration 3')
        raise errors.FieldLanguageMappingError(dntf)

    expected_action_stats = {
        'batch iteration 1': {
            'success': 0,
            'error': {
                'Field is empty': 1
            }
        },
        'batch iteration 2': {
            'success': 1,
            'error': {}
        },
        'batch iteration 3': {
            'success': 0,
            'error': {
                'No language set for NoteType / Deck / field1. Please setup Language Mappings, from the Anki main screen: <b>Tools -> Language Tools: Language Mapping</b>': 1
            }
        }        
    }
    actual_action_stats = batch_error_manager.action_stats
    assert expected_action_stats == actual_action_stats

    # batch_error_manager.display_stats()

    # batch actions with unhandled exceptions
    # =======================================

    batch_error_manager = error_manager.get_batch_error_manager('batch test 2')

    with batch_error_manager.get_batch_action_context('batch iteration 1'):
        logging.info('batch iteration 1')
        logging.info('ok')

    with batch_error_manager.get_batch_action_context('batch iteration 2'):
        logging.info('batch iteration 2')
        raise Exception('this is unhandled')

    expected_action_stats = {
        'batch iteration 1': {
            'success': 1,
            'error': {}
        },
        'batch iteration 2': {
            'success': 0,
            'error': {'Unknown Error: this is unhandled': 1}
        }        
    }