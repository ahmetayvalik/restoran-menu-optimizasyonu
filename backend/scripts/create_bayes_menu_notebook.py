# -*- coding: utf-8 -*-
import json
from pathlib import Path

NOTEBOOK_PATH = Path('BAYES_MENU.ipynb')

def write_notebook(notebook, path=NOTEBOOK_PATH):
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(notebook, f, ensure_ascii=False, indent=1)

if __name__ == '__main__':
    with open(NOTEBOOK_PATH, 'r', encoding='utf-8') as f:
        notebook = json.load(f)
    write_notebook(notebook)
    print('Notebook ensure_ascii=False ile kaydedildi.')
