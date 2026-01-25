import json
import os
from PIL import Image

# Check if tmobj 0-9 exist
tmobj_dir = 'web/images/extracted/tmobj'
print("TMOBJ file status:")
for i in range(38):
    path = f'{tmobj_dir}/tmobj_{i}.png'
    if os.path.exists(path):
        img = Image.open(path)
        print(f'  tmobj_{i:02d}.png: {img.size[0]:2d}x{img.size[1]:2d}')
    else:
        print(f'  tmobj_{i:02d}.png: MISSING')

print()

# Load the web map data and look at writings
with open('web/data/web_map_data.json', 'r') as f:
    data = json.load(f)

writings = []
gravestones = []
for level in data.get('levels', []):
    for obj in level.get('objects', []):
        obj_id = obj.get('object_id', 0)
        if obj_id == 0x166:  # Writing
            writings.append({
                'level': level.get('level_num'),
                'name': obj.get('name'),
                'flags': obj.get('flags'),
                'image_path': obj.get('image_path'),
                'description': (obj.get('description', '') or '')[:50]
            })
        elif obj_id == 0x165:  # Gravestone
            gravestones.append({
                'level': level.get('level_num'),
                'name': obj.get('name'),
                'flags': obj.get('flags'),
                'image_path': obj.get('image_path'),
                'description': (obj.get('description', '') or '')[:50]
            })

# Show writings sorted by flags
writings_sorted = sorted(writings, key=lambda x: (x.get('flags') or 0))
print(f"Writings (total: {len(writings)}) sorted by flags:")
print(f"{'Lv':>2} {'Flags':>5} {'Image':<20} Description")
print("-" * 80)
for w in writings_sorted[:25]:
    lv = w.get('level')
    lv_str = str(lv) if lv is not None else '?'
    flags = w.get('flags') or 0
    img = w.get('image_path', '(none)')
    img_short = img.split('/')[-1] if img else '(none)'
    desc = w.get('description', '')[:35]
    print(f"{lv_str:>2} {flags:>5} {img_short:<20} {desc}")

# Count unique flags values for writings
flags_counts = {}
for w in writings:
    f = w.get('flags') or 0
    flags_counts[f] = flags_counts.get(f, 0) + 1

print()
print("Flags value distribution for writings:")
for f in sorted(flags_counts.keys()):
    tmobj_idx = (f & 0xFF) + 20
    print(f"  flags={f:2d} -> tmobj_{tmobj_idx:02d}.png: {flags_counts[f]} writings")

print()
print(f"Gravestones (total: {len(gravestones)}) sorted by flags:")
print(f"{'Lv':>2} {'Flags':>5} {'Image':<20} Description")
print("-" * 80)
gravestones_sorted = sorted(gravestones, key=lambda x: (x.get('flags') or 0))
for g in gravestones_sorted[:15]:
    lv = g.get('level')
    lv_str = str(lv) if lv is not None else '?'
    flags = g.get('flags') or 0
    img = g.get('image_path', '(none)')
    img_short = img.split('/')[-1] if img else '(none)'
    desc = g.get('description', '')[:35]
    print(f"{lv_str:>2} {flags:>5} {img_short:<20} {desc}")

# Count unique flags values for gravestones
gs_flags_counts = {}
for g in gravestones:
    f = g.get('flags') or 0
    gs_flags_counts[f] = gs_flags_counts.get(f, 0) + 1

print()
print("Flags value distribution for gravestones:")
for f in sorted(gs_flags_counts.keys()):
    tmobj_idx = (f & 0xFF) + 28
    print(f"  flags={f:2d} -> tmobj_{tmobj_idx:02d}.png: {gs_flags_counts[f]} gravestones")
