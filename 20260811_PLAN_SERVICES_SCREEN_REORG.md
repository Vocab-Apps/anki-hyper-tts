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
- service name (like Alibaba), in bold
- free or paid
- dictionary (dict) or TTS
- 
there should be a header above that grid layout explaining what the different items are

## Extensions
we want to move the "Extensions" tab which is currently in "HyperTTS: Preferences" to the services configuration screen.



