We want to address the configuration loss issue described in github issue #360
Look at the recommendations in @20260817_CONFIGURATION_ISSUE_CHATGPT.md and @20260817_CONFIGURATION_ISSUE_CLAUDE.md and implement the ones that make sense.

Implement configuration backup that writes a configuration backup json file into `user_files/config_backup/` everytime we save the configuration.
This should come with a GUI change, the "HyperTTS: Preferences" screen should have another tab which offers restoring configuration files. The screen
should show when a config was saved and whether it seems correct (and not empty).

Raise a sentry error if we detect the config has been truncated, or if it became unusual for whatever reason.

Overall the goal is to guarantee we either eliminate this configuration loss bug, or at least have the instrumentation that lets us get to the bottom of it,
and failing that, the user should be able to restore their configuration.

Make sure changes have sufficient regression test coverage, and that changes are tested live with `anki-gui-automation`.

