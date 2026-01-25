"""Debug script to check item flags attribute access."""
import sys
sys.path.insert(0, '.')

from pathlib import Path
from src.extractors import ItemExtractor

data_path = Path("Input/UW1/DATA")
items = ItemExtractor(data_path)
items.extract()

# Find writings
print("Sample writings from ItemExtractor:")
print("=" * 70)
count = 0
for item in items.placed_items:
    if item.object_id == 0x166:  # Writing
        count += 1
        if count <= 10:
            print(f"Writing #{count}:")
            print(f"  object_id: 0x{item.object_id:X}")
            print(f"  flags (attr): {item.flags}")
            print(f"  flags (getattr): {getattr(item, 'flags', 'NOT FOUND')}")
            print(f"  quality: {item.quality}")
            print(f"  owner: {item.owner}")
            print(f"  quantity: {item.quantity}")
            print(f"  level: {item.level}")
            print()

print(f"Total writings: {count}")

# Check if there are different flags values
flags_set = set()
for item in items.placed_items:
    if item.object_id == 0x166:
        flags_set.add(item.flags)

print(f"\nUnique flags values for writings: {sorted(flags_set)}")
