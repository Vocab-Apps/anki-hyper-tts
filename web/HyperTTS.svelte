<script context="module">
    import { writable, get } from 'svelte/store';
    
    export const batchNameListStore = writable([]);
    export const selectedBatchNameStore = writable("New Preset");

    export function configureEditorHyperTTS(batchConfigList, defaultBatch) {
        console.log('setLanguageToolsEditorSettings: ', batchConfigList);
        batchNameListStore.set(batchConfigList)
        selectedBatchNameStore.set(defaultBatch);
    }

    let selectedBatchNameStoreCopy = null;
    selectedBatchNameStore.subscribe( value => {
        console.log('selectedBatchNameStore: ', value);
        selectedBatchNameStoreCopy = value;
    })

    export function hyperTTSAddAudio() {
        console.log("addAudio");
        const cmdString = 'hypertts:addaudio:' + selectedBatchNameStoreCopy;
        bridgeCommand(cmdString);
    }

    export function hyperTTSPreviewAudio() {
        const cmdString = 'hypertts:previewaudio:' + selectedBatchNameStoreCopy;
        bridgeCommand(cmdString);
    }        

</script>

<script>

	let batchNameList;
	batchNameListStore.subscribe(value => {
		batchNameList = value;
	});    

    let enable_selection = 1;

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
        <select bind:value={$selectedBatchNameStore}>
            {#each batchNameList as batch}
                <option value={batch}>
                    {batch}
                </option>
            {/each}
        </select>        
    </div>

    <button on:click={hyperTTSAddAudio} class="hypertts-button rounded-corners">Add Audio</button>
    <button on:click={hyperTTSPreviewAudio} class="hypertts-button rounded-corners">Preview Audio</button>
    
    <span class="hypertts-button" title="Generate audio using the entire content of the field.">
        <input type=radio bind:group={enable_selection} name="scoops" value={1} >
        Full text
    </span>
    
    <span class="hypertts-button" title="Generate audio only using the selected portion of the field.">
        <input type=radio bind:group={enable_selection} name="scoops" value={2} >
        Selection
    </span>
    
</div>