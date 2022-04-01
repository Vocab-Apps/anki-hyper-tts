<script context="module">
    import { writable } from 'svelte/store';
    
    export const batchNameListStore = writable([]);
    export const defaultBatchName = writable("");

    export function configureEditorHyperTTS(batchConfigList, defaultBatch) {
        console.log('setLanguageToolsEditorSettings: ', batchConfigList);
        batchNameListStore.set(batchConfigList)
        if( defaultBatch != null) {
            defaultBatchName.set(defaultBatch);
        }
    }

</script>

<script>

    let selectedBatchName;
    defaultBatchName.subscribe(value => {
        if (value) {
            selectedBatchName = value;
        }
    })

	let batchNameList;
	batchNameListStore.subscribe(value => {
		batchNameList = value;
	});    

    function addAudio() {
        console.log("addAudio");
        const cmdString = 'hypertts:addaudio:' + selectedBatchName;
        bridgeCommand(cmdString);
    }

    function previewAudio() {
        const cmdString = 'hypertts:previewaudio:' + selectedBatchName;
        bridgeCommand(cmdString);
    }    

</script>

<style>
.rounded-corners {
    border-style: solid;
    border-width: 1px;
    border-color: #b6b6b6;
    border-radius: 3px;
}
.language-tools-block {
    display: inline-flex;
    flex-direction: row;
    flex-wrap: wrap;
    font-size: 12px;
    align-items: center;
    margin-bottom: 3px;
}
.hypertts-button {
}
div {
    padding-left: 5px;
    padding-right: 5px;
}
</style>


<div class="language-tools-block rounded-corners">
    <div>
        <b>HyperTTS</b>
    </div>
    <div>
        <select bind:value={selectedBatchName}>
            {#each batchNameList as batch}
                <option value={batch}>
                    {batch}
                </option>
            {/each}
        </select>        
    </div>

    <button on:click={addAudio} class="hypertts-button rounded-corners">Add Audio</button>
    <button on:click={previewAudio} class="hypertts-button rounded-corners">Preview Audio</button>
</div>