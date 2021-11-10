

template_str = """
if article == 'das':
    result = f'Das {word}'
else:
    result = f'{das} {word}'
"""

def main():
    local_variables = {
        'article': 'das',
        'word': 'Hund'
    }
    expanded_template = exec(template_str, {}, local_variables)
    result = local_variables['result']
    print(result)


if __name__ == '__main__':
    main()