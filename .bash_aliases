alias run_tests_all='pytest tests'
alias run_tests_gui='pytest tests --ignore=tests/test_tts_services.py'
alias run_test_debug_logging='pytest --log-cli-level=DEBUG tests/test_components.py -k test_batch_source_1'
alias run_test_audio='pytest --log-cli-level=DEBUG tests/test_tts_services.py -k test_azure'
alias package='./package.sh'
alias coverage_run='coverage run -m pytest' # run tests with coverage
alias coverage_run_gui='coverage run -m pytest --ignore=tests/test_tts_services.py' # run tests with coverage (GUI tests only)
alias coverage_html='coverage html' # generate html report
alias coverage_erase='coverage erase' # erase coverage data
alias coverage_http_server='cd htmlcov && python -m http.server --bind :: 8000' # serve html pages
alias activate_pyenv='source ~/python-env/anki-hyper-tts/bin/activate'