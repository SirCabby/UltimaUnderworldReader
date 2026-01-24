import sys
sys.path.insert(0, r'c:\Users\Joshua\workspace\GitHub\UltimaUnderworldReader')
from pathlib import Path

# Simulate what main.py does to build tmobj_image_paths
tmobj_image_paths = {}
web_tmobj_dir = Path("web/images/extracted/tmobj")
if web_tmobj_dir.exists():
    for img_file in web_tmobj_dir.glob("tmobj_*.png"):
        try:
            idx_str = img_file.stem.replace("tmobj_", "")
            idx = int(idx_str, 10)
            tmobj_image_paths[idx] = f"images/extracted/tmobj/{img_file.name}"
        except ValueError:
            continue

print(f"tmobj_image_paths has {len(tmobj_image_paths)} entries")
print(f"Keys: {sorted(tmobj_image_paths.keys())}")

# Check what indices would be needed for writings
# flags + 20 for writings
# flags is typically 0-7
print("\nWriting TMOBJ indices (flags + 20):")
for flags in range(8):
    idx = flags + 20
    exists = idx in tmobj_image_paths
    print(f"  flags={flags} -> idx={idx} -> exists={exists} -> {tmobj_image_paths.get(idx, 'N/A')}")

# Now check what the actual item.flags values are
from src.parsers.level_parser import LevelParser
levels = LevelParser(Path("Input/UW1/DATA/LEV.ARK"))
levels.parse()

print("\nActual writing objects and their flags:")
for level_num, level in levels.levels.items():
    writings = [obj for obj in level.objects.values() if obj.item_id == 0x166]
    if writings:
        print(f"Level {level_num}: {len(writings)} writings")
        for w in writings[:3]:
            print(f"  idx={w.index}, flags={w.flags}, owner={w.owner}, quality={w.quality}")
