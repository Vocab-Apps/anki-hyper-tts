import os
import sys
import imp
import service

template_str = """
word = template_fields['word']
word = word.replace('Hund', 'chien')
if template_fields['article'] == 'das':
    result = f"Das {word}"
else:
    result = f"{template_fields['article']} {word}"
"""

def test_template():
    local_variables = {
        'template_deck_name': 'German',
        'template_note_type': 'German-Words',
        'template_fields': {
            'article': 'das',
            'word': 'Hund'
        }
    }
    expanded_template = exec(template_str, {}, local_variables)
    result = local_variables['result']
    print(result)

def all_service_files(directory):
    for path, dirs, files in os.walk(directory):
        for filename in files:
            if filename.startswith('service_') and filename.endswith('.py'):
                module_name = filename.replace('.py', '')
                #yield os.path.join(path, filename)
                yield module_name

def test_discover_services():
    current_script_path = os.path.realpath(__file__)
    current_script_dir = os.path.dirname(current_script_path)
    print(current_script_dir)
    #import_from_absolute_path(current_script_dir)
    all_service_module_names = all_service_files(current_script_dir)
    #print(list(all_service_module_names))
    for module_name in all_service_module_names:
        print(module_name)
        fp, pathname, description = imp.find_module(module_name)
        imp.load_module(module_name, fp, pathname, description)
    # find subclasses of ServiceBase
    for subclass in service.ServiceBase.__subclasses__():
        subclass_instance = subclass()
        print(subclass_instance)
        voices = subclass_instance.voice_list()
        print(voices)


if __name__ == '__main__':
    test_discover_services()