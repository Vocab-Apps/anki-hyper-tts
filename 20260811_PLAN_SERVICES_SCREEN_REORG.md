# Overview
We want to re-organize the services screen (HyperTTS: Services Configuration).
there should be three tabs at the top:
- HyperTTS Pro
- Services
- Extensions

# Design
## HyperTTS Pro tab
should just be the current "HyperTTS Pro" pane which already exists.

## Services
move the current Services pane to this Services tab. We also want to make additional changes:
we want a more compact Qt grid layout which contains the following items:
- a checkbox to enable the service. when checked, the whole service row appears in black instead of gray.
- HyperTTS Pro (checkmark if it's included in HyperTTS Pro)
- service name (like Alibaba), in bold
- free or paid
- dictionary (dict) or TTS
- a configure button (only show if the service is enabled)

there should be a header above that grid layout explaining what the different items are.

When the user enables a service by clicking the checkbox, there should be a panel that opens immediately below the service row and shows the configuration
options. The user can then click OK to retain the configuration options, or cancel to cancel and close the panell. That panel should also appear if the
user clicks configure.

## Extensions
we want to move the "Extensions" tab which is currently in "HyperTTS: Preferences" to the services configuration screen.

## Alert at the bottom
at the bottom of the screen (not inside the 3 tabs), there should be an alert if the user doesn't have any services configured.
explain that they either have to use the HyperTTS Pro service, or enable individual services in the Services tab. Once the user enables
services, that alert can go away.

# Goal
Redesign the screen, use the `anki-gui-automation` skill to make sure the screen works properly, and update regression tests, add regression tests if required.
make sure the trial flow is still working.



