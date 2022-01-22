// build using:
// npm run build

import HyperTTS, {setLanguageToolsEditorSettings} from "./HyperTTS.svelte";

$editorToolbar.then((editorToolbar) => {
    console.log(setLanguageToolsEditorSettings);
    editorToolbar.toolbar.insertGroup({component: LanguageTools, id: "languagetools"});
});
