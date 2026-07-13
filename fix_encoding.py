
txt = open(r'd:\IEEE\pipeline.py', encoding='utf-8').read()

# Map all known unicode to ascii
table = str.maketrans({
    '\u2550': '=', '\u2551': '|', '\u2554': '+', '\u2557': '+',
    '\u255a': '+', '\u255d': '+', '\u2560': '+', '\u2563': '+',
    '\u2524': '|', '\u251c': '|', '\u2500': '-', '\u2502': '|',
    '\u252c': '+', '\u2534': '+', '\u253c': '+',
    '\u00d7': 'x', '\u2014': '-', '\u2013': '-',
    '\u2019': "'", '\u2018': "'", '\u201c': '"', '\u201d': '"',
    '\u2022': '*', '\u25ba': '>', '\u2605': '*',
    '\u00b2': '2', '\u00b3': '3',
    '\u2588': '#', '\u2593': '#', '\u2592': '#', '\u2591': ' ',
})
txt = txt.translate(table)
# Catch anything remaining
cleaned = txt.encode('ascii', 'replace').decode('ascii')
open(r'd:\IEEE\pipeline.py', 'w', encoding='ascii').write(cleaned)
print('Done — non-ASCII chars removed')
