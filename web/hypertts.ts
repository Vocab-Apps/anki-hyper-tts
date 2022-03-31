// build using:
// npm run build

import * as NoteEditor from "anki/NoteEditor";
import HyperTTS, {configureEditorHyperTTS} from "./HyperTTS.svelte";

NoteEditor.lifecycle.onMount(({ toolbar }) => {
    console.log(configureEditorHyperTTS);
    toolbar.toolbar.append({component: HyperTTS, id: "hypertts"});
});
