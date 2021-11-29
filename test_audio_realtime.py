import testing_utils
import re

def test_template_regexps(qtbot):
    template_output = """
<hypertts-template-advanced>
field1 = template_fields['Text']
field2 = template_fields['Extra']
result = f"{field1} {field2}"
</hypertts-template-advanced>
"""
    expected_content = """field1 = template_fields['Text']
field2 = template_fields['Extra']
result = f"{field1} {field2}"
"""
    match_result = re.match('.*<hypertts-template-advanced>\n(.*)</hypertts-template-advanced>.*', template_output, re.DOTALL)
    assert match_result != None
    actual_content = match_result.group(1)
    assert actual_content == expected_content
