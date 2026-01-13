#!/usr/bin/env python3
"""
Script to check a specific item's raw data.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from parsers.level_parser import LevelParser

def check_item(data_path, level, tile_x, tile_y, item_id):
    """Check raw data for a specific item."""
    parser = LevelParser(Path(data_path) / "LEV.ARK")
    parser.parse()
    
    level_data = parser.get_level(level)
    if not level_data:
        print(f"Level {level} not found")
        return
    
    # Find items at the specified location
    items_at_location = []
    for idx, obj in level_data.objects.items():
        if obj.item_id == item_id and obj.tile_x == tile_x and obj.tile_y == tile_y:
            items_at_location.append((idx, obj))
    
    if not items_at_location:
        print(f"Item 0x{item_id:03X} not found at level {level}, tile ({tile_x}, {tile_y})")
        return
    
    for idx, obj in items_at_location:
        print(f"\nFound item at index {idx}:")
        print(f"  Item ID: 0x{obj.item_id:03X} ({obj.item_id})")
        print(f"  Position: tile ({obj.tile_x}, {obj.tile_y}), pos ({obj.x_pos}, {obj.y_pos}, {obj.z_pos})")
        print(f"  is_enchanted: {obj.is_enchanted}")
        print(f"  is_quantity: {obj.is_quantity}")
        print(f"  quantity_or_link: {obj.quantity_or_link}")
        print(f"  quality: {obj.quality}")
        print(f"  owner: {obj.owner}")
        print(f"  flags: {obj.flags}")
        
        # Check for potential enchantment data
        link_value = obj.quantity_or_link
        if link_value >= 512:
            ench_property = link_value - 512
            print(f"\n  Potential enchantment data:")
            print(f"    link_value: {link_value}")
            print(f"    ench_property: {ench_property}")
            if 0x20 <= obj.item_id < 0x40:  # Armor
                if 192 <= ench_property <= 199:
                    print(f"    Type: Protection +{ench_property - 191}")
                elif 200 <= ench_property <= 207:
                    print(f"    Type: Toughness +{ench_property - 199}")
                elif ench_property < 64:
                    print(f"    Type: Spell enchantment (index {256 + ench_property})")
                else:
                    print(f"    Type: Unknown enchantment #{ench_property}")

if __name__ == "__main__":
    if len(sys.argv) < 6:
        print("Usage: python check_item.py <data_path> <level> <tile_x> <tile_y> <item_id_hex>")
        print("Example: python check_item.py Input/UW1/DATA 4 29 25 0x021")
        sys.exit(1)
    
    data_path = sys.argv[1]
    level = int(sys.argv[2])
    tile_x = int(sys.argv[3])
    tile_y = int(sys.argv[4])
    item_id = int(sys.argv[5], 16) if sys.argv[5].startswith('0x') else int(sys.argv[5])
    
    check_item(data_path, level, tile_x, tile_y, item_id)
