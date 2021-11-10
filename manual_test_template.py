

template_str = """
word = template_fields['word']
word = word.replace('Hund', 'chien')
if template_fields['article'] == 'das':
    result = f"Das {word}"
else:
    result = f"{template_fields['article']} {word}"
"""

def main():
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


if __name__ == '__main__':
    main()