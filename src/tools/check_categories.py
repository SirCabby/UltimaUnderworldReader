#!/usr/bin/env python3
"""
Quick JSON category checker for web_map_data.json.

Usage:
    python -m src.tools.check_categories
"""

import json

d = json.load(open('web/data/web_map_data.json'))

print('Categories in data:')
for cat in d['categories']:
    print(f'  {cat["id"]}: {cat["name"]} ({cat["color"]})')

print()
print('Secrets category details:')
secrets_cat = next((c for c in d['categories'] if c['id'] == 'secrets'), None)
if secrets_cat:
    print(f'  Found: {secrets_cat}')
else:
    print('  NOT FOUND!')
