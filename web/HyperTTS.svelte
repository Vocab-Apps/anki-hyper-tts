<script context="module">
    import { writable } from 'svelte/store';
    
    export const batchNameListStore = writable([]);

    export function configureEditorHyperTTS(batchConfigList) {
        console.log('setLanguageToolsEditorSettings: ', batchConfigList);
        batchNameListStore.set(batchConfigList)
    }

</script>

<script>

    let selectedBatchName;

	let batchNameList;
	batchNameListStore.subscribe(value => {
		batchNameList = value;
	});    

    function addAudio() {
        console.log("addAudio");
        let fieldData = {}
        forEditorField([], (field, _data) => {
            const field_id = field.editingArea.ord;
            const field_value = field.editingArea.fieldHTML;
            fieldData[field_id] = field_value;
        });            

        console.log('fieldData: ', fieldData);
        let addAudioData = {
            batch_name: selectedBatchName,
            field_data: fieldData
        }
        const cmdString = 'hypertts:addaudio:' + JSON.stringify(addAudioData);
        bridgeCommand(cmdString);
    }

</script>

<style>
.language-tools-block {
    display: inline-flex;
    flex-direction: row;
    flex-wrap: wrap;
    font-size: 12px;
    align-items: center;
    border-style: solid;
    border-width: 1px;
    border-color: #b6b6b6;
    border-radius: 3px;
  margin-top: 3px;    
}
div {
    padding-left: 5px;
    padding-right: 5px;
}
</style>


<div class="language-tools-block">
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

    <button on:click={addAudio} class="lt-field-button">Add Audio</button>
</div>