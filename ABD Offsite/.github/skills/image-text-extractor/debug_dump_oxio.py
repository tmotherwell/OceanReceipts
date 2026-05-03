from pathlib import Path
from run_extractor import process_pdf, find_amounts, find_two_decimal_amounts, find_amounts_near_phrases

p = Path('input') / 'OXIO-11581354_2026-02-07.pdf'
text, meta = process_pdf(p)
print('----RAW OCR TEXT----')
print(text)
print('\n----LINES----')
lines = text.splitlines()
for i, line in enumerate(lines):
    print(f'{i}: {line}')
print('\n----AMOUNTS----')
print('find_amounts:', find_amounts(text))
print('two_decimal:', find_two_decimal_amounts(text))
print('near_phrases:', find_amounts_near_phrases(text, phrases=['amount due','total','balance due','amount','invoice total','amount due:']))
