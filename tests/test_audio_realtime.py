
from hypertts_addon import text_utils
from hypertts_addon import constants



def test_template_regexps(qtbot):
    """
    note: the tts tag may need to have style="display: none;visibility: hidden;"
    """

    template_output = """
{{Text}}
<hypertts-template-advanced setting="voice_a" version="v1" style="display: none;visibility: hidden;">
field1 = template_fields['Text']
field2 = template_fields['Extra']
result = f"{field1} {field2}"
</hypertts-template-advanced>
"""
    expected_content = """field1 = template_fields['Text']
field2 = template_fields['Extra']
result = f"{field1} {field2}"
""".strip()
    actual_setting, version, actual_content = text_utils.extract_advanced_template(template_output)
    assert actual_content == expected_content

    template_output = """
{{Text}}
<hypertts-template setting="voice_c" version="v1" style="display: none;visibility: hidden;">{Text} {Extra}</hypertts-template>
"""
    expected_content = """{Text} {Extra}"""
    actual_setting, version, actual_content = text_utils.extract_simple_template(template_output)
    assert actual_content == expected_content   
    assert version == constants.TemplateFormatVersion.v1


    template_output = """
{{Text}}
<hypertts-template setting="voice_a" version="v1">
{Text} {Extra}
</hypertts-template>
"""
    expected_content = """{Text} {Extra}"""
    actual_setting, version, actual_content = text_utils.extract_simple_template(template_output)
    assert actual_content == expected_content    
    assert version == constants.TemplateFormatVersion.v1


    # no template available

    template_output = """
{{Text}}
{Text} {Extra}
"""
    expected_content = """{Text} {Extra}"""
    actual_setting, version, actual_content = text_utils.extract_simple_template(template_output)
    assert actual_setting == None
    assert version == None
    assert actual_content == None
    # assert actual_content == expected_content    
    # assert version == constants.TemplateFormatVersion.v1    