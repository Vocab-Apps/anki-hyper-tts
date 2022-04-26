// build using:
// npm run build

import HyperTTS, {configureEditorHyperTTS, hyperTTSAddAudio, hyperTTSPreviewAudio} from "./HyperTTS.svelte";

$editorToolbar.then((editorToolbar) => {
    console.log(configureEditorHyperTTS);
    editorToolbar.toolbar.insertGroup({component: HyperTTS, id: "hypertts"});
});

window.hyperTTSAddAudio = hyperTTSAddAudio;
window.hyperTTSPreviewAudio = hyperTTSPreviewAudio;
