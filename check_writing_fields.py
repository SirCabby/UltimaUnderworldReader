import json

# Load raw placed_objects.json to see actual item data
with open('Output/placed_objects.json', 'r') as f:
    data = json.load(f)

objects = data.get('objects', data)  # Handle both formats

# Find writings (object_id 358 = 0x166)
print("Sample writings from placed_objects.json:")
print("=" * 70)
count = 0
for item in objects:
    if item.get('object_id') == 358:  # 0x166
        count += 1
        if count <= 15:
            print(f"Writing #{count}:")
            print(f"  object_id: {item.get('object_id')} (0x{item.get('object_id'):X})")
            print(f"  flags: {item.get('flags')}")
            print(f"  quality: {item.get('quality')}")
            print(f"  owner: {item.get('owner')}")
            print(f"  quantity: {item.get('quantity')}")
            print(f"  special_link: {item.get('special_link')}")
            print(f"  is_quantity: {item.get('is_quantity')}")
            print(f"  level: {item.get('level')}")
            print()

print(f"Total writings: {count}")

# Also check gravestones
print()
print("Sample gravestones from placed_objects.json:")
print("=" * 70)
count = 0
for item in objects:
    if item.get('object_id') == 357:  # 0x165
        count += 1
        if count <= 5:
            print(f"Gravestone #{count}:")
            print(f"  object_id: {item.get('object_id')} (0x{item.get('object_id'):X})")
            print(f"  flags: {item.get('flags')}")
            print(f"  quality: {item.get('quality')}")
            print(f"  owner: {item.get('owner')}")
            print(f"  quantity: {item.get('quantity')}")
            print()

print(f"Total gravestones: {count}")
