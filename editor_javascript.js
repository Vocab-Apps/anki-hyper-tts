

function configure_languagetools_fields(options) {
    // console.log(options);
    forEditorField(options, (field, field_type) => {
        const field_id = field.editingArea.ord
         
        // console.log('configuring field: ', field, field_id, field_type, field.hasAttribute("languagetools-common"));

        // the common set only needs to be added once, and doesn't need to be removed
        if (!field.hasAttribute("languagetools-common")) {
            // alter the class on the field header
            const fieldHeaderDiv = $(field).find("div.justify-content-between")[0];
            fieldHeaderDiv.classList.remove("justify-content-between");
            fieldHeaderDiv.classList.add("justify-content-start");

            // add loading indicator
            const loadingIndicator = document.createElement('span');
            loadingIndicator.id = 'loading_indicator' + field_id;
            loadingIndicator.classList.add('field-label-element');
            loadingIndicator.classList.add('loading-indicator');
            loadingIndicator.classList.add('loading-indicator-hidden');
            loadingIndicator.innerText = 'loading...';
            field.labelContainer.appendChild(loadingIndicator);

            // add generated for 
            const generatedForIndicator = document.createElement('span');
            generatedForIndicator.id = 'generatedfor_indicator' + field_id;
            generatedForIndicator.classList.add('field-label-element');
            generatedForIndicator.classList.add('generated-for');
            generatedForIndicator.classList.add('generated-for-hidden');
            field.labelContainer.appendChild(generatedForIndicator);

            field.setAttribute("languagetools-common", "")
        } else {
            // hide out loading / generated for indicators
            $('#loading_indicator' + field_id).hide();
            $('#generatedfor_indicator' + field_id).hide();            
        }

        var old_field_type = "";
        if (field.hasAttribute("languagetools-type")) {
            old_field_type = field.getAttribute("languagetools-type");
        }

        if( old_field_type != field_type ) {
            // need to clean up old elements
            if(old_field_type == 'language') {
                var elements = field.getElementsByClassName("class-language-field");
                elements[0].remove();
            }

            if(old_field_type == "translation") {
                var elements = field.getElementsByClassName("class-language-field");
                elements[0].remove();
                elements = field.getElementsByClassName("class-translation-field");
                elements[0].remove();                
            }

            if(old_field_type == "sound") {
                var elements = field.getElementsByClassName("class-sound-field");
                elements[0].remove();
            }

            // do we need to add some audio buttons ?
            // add the speak button
            if( field_type == 'language') {
                const speakButton = document.createElement('button');
                speakButton.classList.add('field-label-element');
                speakButton.classList.add('class-language-field');
                speakButton.classList.add('lt-field-button');
                speakButton.innerText = 'Speak';
                speakButton.addEventListener(
                    'click',
                    (() => {
                        pycmd('ttsspeak:' + field_id)
                    }),
                );
                field.labelContainer.appendChild(speakButton);
            }

            // add breakdown button
            if( field_type == 'language') {
                const breakdownButton = document.createElement('button');
                breakdownButton.classList.add('field-label-element');
                breakdownButton.classList.add('class-language-field');
                breakdownButton.classList.add('lt-field-button');
                breakdownButton.innerText = 'Breakdown';
                breakdownButton.addEventListener(
                    'click',
                    (() => {
                        pycmd('languagetools:breakdown:' + field_id + ':' + getEditorField(field_id).editingArea.fieldHTML)
                    }),
                );
                field.labelContainer.appendChild(breakdownButton);
            }            

            if( field_type == 'translation') {
                // speak button
                const speakButton = document.createElement('button');
                speakButton.classList.add('field-label-element');
                speakButton.classList.add('class-language-field');
                speakButton.classList.add('lt-field-button');
                speakButton.innerText = 'Speak';
                speakButton.addEventListener(
                    'click',
                    (() => {
                        pycmd('ttsspeak:' + field_id)
                    }),
                );
                field.labelContainer.appendChild(speakButton);

                // choose translation button
                const translationButton = document.createElement('button');
                translationButton.classList.add('field-label-element');
                translationButton.classList.add('class-translation-field');
                translationButton.classList.add('lt-field-button');
                translationButton.innerText = 'Choose Translation';
                translationButton.addEventListener(
                    'click',
                    (() => {
                        pycmd('choosetranslation:' + field_id)
                    }),
                );
                field.labelContainer.appendChild(translationButton);
            }            

            if( field_type == 'sound') {
                const speakButton = document.createElement('button');
                speakButton.classList.add('field-label-element');
                speakButton.classList.add('class-sound-field');
                speakButton.classList.add('lt-field-button');
                speakButton.innerText = 'Play';
                speakButton.addEventListener(
                    'click',
                    (() => {
                        pycmd('playsoundcollection:' + field_id)
                    }),
                );
                field.labelContainer.appendChild(speakButton);
            }
        }
        field.setAttribute("languagetools-type", field_type);
    


    })    
}

function hide_loading_indicator(field_id, original_field_value) {
    $('#loading_indicator' + field_id).hide();
    $('#generatedfor_indicator' + field_id).text('generated from: ' + original_field_value);
    $('#generatedfor_indicator' + field_id).show();
}

function show_loading_indicator(field_id) {
    $('#loading_indicator' + field_id).show();
    $('#generatedfor_indicator' + field_id).hide();
}

function set_field_value(field_id, value) {
    var decoded_value = decodeURI(value);

    var field = getEditorField(field_id);
    field.editingArea.fieldHTML = decoded_value;
}
