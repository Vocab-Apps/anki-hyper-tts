We want claude code to be able to automously create GUI screens for hypertts.
you may use the techniques in @20260809_ANKI_ADDON_AUTOMATION.md . You can install software packages using sudo and dnf.
Create a skill (or multiple) which describe how to test a live running Anki session and debug the GUI.

The guidelines are the following
- use a standalone GUI mechanism to start a full Anki instance
- we should use a separate Anki profile to avoid interfering with the existing one
- use AnkiConnect to inject data (notes / cards) into Anki: https://github.com/amikey/anki-connect
- Claude Code should be able to start up an Anki instance with HyperTTS, navigate its GUI, make sure that HyperTTS dialogs (for the feature being implemented) are correct
- Adding a new feature should still include pytest-qt tests as is already the case.
- the API key for the vocab backend is available in `/home/luc/code/secrets/hypertts/clt_tts_vocabai_qa.sh`
- if you had to install software packages, document it clearly (those packages will later be added to ansible). If you had to install python packages, add them to `requirements.txt`.
- if there are initalization/shutdown steps for the Xvfb or similar, put scripts in `scripts/`.
- after an agentic loop has finished, should shutdown leftover processes / xvfb or other.

The outcome of this project are the following
- we should have a fully re-usable skill or procedure to agentically develop GUI screens for HyperTTS
- the following issue should be implement: https://github.com/Vocab-Apps/anki-hyper-tts/issues/40 using the above created skill. This feature should be implemented in a standalone HyperTTS dialog, should operate on a collection of notes from the browser, should have undo support.