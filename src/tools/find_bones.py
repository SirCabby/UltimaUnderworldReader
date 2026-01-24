#!/usr/bin/env python3
"""
Discovery script to find all bone objects in the game and identify
what makes the bones at (2, 15) on level 8 unique (Garamon's bones).

This script performs a thorough analysis to find intrinsic properties
that distinguish Garamon's bones from all other bones in the game,
so the identification works even if the bones are moved.

Usage:
    python -m src.tools.find_bones <data_path>

Example:
    python -m src.tools.find_bones Input/UW1/DATA
"""

import sys
from pathlib import Path
from collections import defaultdict

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.parsers.level_parser import LevelParser


# Bone-related object IDs
BONE_IDS = {
    0x0C4: "bones",
    0x0C5: "bones",
    0x0C6: "pile of bones",
    0x0DC: "pile of bones",
}


def find_all_bones(data_path: str):
    """Find all bone objects across all levels and analyze uniqueness."""
    parser = LevelParser(Path(data_path) / "LEV.ARK")
    parser.parse()
    
    print("=" * 120)
    print("All Bone Objects in Ultima Underworld - Thorough Analysis")
    print("=" * 120)
    print()
    
    # Collect all bones with ALL their raw data
    all_bones = []
    
    for level_num in range(9):
        level = parser.get_level(level_num)
        if not level:
            continue
        
        for idx, obj in level.objects.items():
            if obj.item_id in BONE_IDS:
                bone_info = {
                    'level': level_num,
                    'tile_x': obj.tile_x,
                    'tile_y': obj.tile_y,
                    'item_id': obj.item_id,
                    'item_name': BONE_IDS[obj.item_id],
                    'quality': obj.quality,
                    'owner': obj.owner,
                    'flags': obj.flags,
                    'quantity_or_link': obj.quantity_or_link,
                    'is_enchanted': obj.is_enchanted,
                    'is_quantity': obj.is_quantity,
                    'is_invisible': obj.is_invisible,
                    'index': idx,
                    'z_pos': obj.z_pos,
                    'x_pos': obj.x_pos,
                    'y_pos': obj.y_pos,
                    'heading': obj.heading,
                    'next_index': obj.next_index,
                    'door_dir': obj.door_dir,
                }
                all_bones.append(bone_info)
    
    # Print header with all fields
    print(f"{'Lvl':<4} {'TileX':<6} {'TileY':<6} {'ID':<6} {'Name':<16} {'Qual':<5} {'Own':<4} {'Flg':<4} {'Q/L':<5} {'Enc':<5} {'IsQ':<5} {'Inv':<5} {'Idx':<6}")
    print("-" * 120)
    
    # Sort by level, then tile_x, then tile_y
    all_bones.sort(key=lambda b: (b['level'], b['tile_x'], b['tile_y']))
    
    # Track target bones (level 7, tile 2, 15)
    target_bones = []
    
    for bone in all_bones:
        # Check if this is a potential target (level 7, tile 2, 15)
        is_target = (bone['level'] == 7 and bone['tile_x'] == 2 and bone['tile_y'] == 15)
        marker = ">>>" if is_target else "   "
        
        if is_target:
            target_bones.append(bone)
        
        print(f"{marker}{bone['level']:<4} {bone['tile_x']:<6} {bone['tile_y']:<6} 0x{bone['item_id']:03X} {bone['item_name']:<16} {bone['quality']:<5} {bone['owner']:<4} {bone['flags']:<4} {bone['quantity_or_link']:<5} {str(bone['is_enchanted']):<5} {str(bone['is_quantity']):<5} {str(bone['is_invisible']):<5} {bone['index']:<6}")
    
    print()
    print("=" * 120)
    print(f"Total bones found: {len(all_bones)}")
    print("=" * 120)
    
    # Detailed target analysis
    print()
    print("=" * 120)
    print("TARGET BONE DETAILS (Level 7, Tile 2,15 - Garamon's bones)")
    print("=" * 120)
    
    if not target_bones:
        print("ERROR: No bones found at (2, 15) on level 7!")
        return None
    
    target = target_bones[0]
    print(f"  Level: {target['level']} (display as 'Level {target['level'] + 1}')")
    print(f"  Position: tile ({target['tile_x']}, {target['tile_y']}), sub-pos ({target['x_pos']}, {target['y_pos']})")
    print(f"  Item ID: 0x{target['item_id']:03X} ({target['item_name']})")
    print(f"  Z position: {target['z_pos']}")
    print(f"  Heading: {target['heading']}")
    print(f"  Quality: {target['quality']}")
    print(f"  Owner: {target['owner']}")
    print(f"  Flags: {target['flags']}")
    print(f"  Quantity/Link: {target['quantity_or_link']}")
    print(f"  Is Enchanted: {target['is_enchanted']}")
    print(f"  Is Quantity: {target['is_quantity']}")
    print(f"  Is Invisible: {target['is_invisible']}")
    print(f"  Door Dir: {target['door_dir']}")
    print(f"  Next Index: {target['next_index']}")
    print(f"  Object Index: {target['index']}")
    
    # THOROUGH UNIQUENESS ANALYSIS
    print()
    print("=" * 120)
    print("THOROUGH UNIQUENESS ANALYSIS")
    print("=" * 120)
    
    # Exclude templates at (0,0) - they're not real placed items
    real_bones = [b for b in all_bones if not (b['tile_x'] == 0 and b['tile_y'] == 0)]
    print(f"\nAnalyzing {len(real_bones)} real bones (excluding {len(all_bones) - len(real_bones)} templates at 0,0)")
    
    # Check each field for uniqueness
    fields_to_check = ['item_id', 'quality', 'owner', 'flags', 'quantity_or_link', 
                       'is_enchanted', 'is_quantity', 'is_invisible']
    
    print("\n--- Single Field Analysis ---")
    unique_fields = []
    for field in fields_to_check:
        target_value = target[field]
        others_with_same = [b for b in real_bones if b[field] == target_value and b != target]
        if not others_with_same:
            print(f"  UNIQUE: {field}={target_value} - NO other bone has this value!")
            unique_fields.append(field)
        else:
            print(f"  {field}={target_value}: shared with {len(others_with_same)} other bones")
    
    # Check combinations of fields
    print("\n--- Field Combination Analysis ---")
    unique_combos = []
    
    # Try 2-field combinations
    from itertools import combinations
    for combo in combinations(fields_to_check, 2):
        target_values = tuple(target[f] for f in combo)
        others_with_same = [b for b in real_bones if tuple(b[f] for f in combo) == target_values and b != target]
        if not others_with_same:
            print(f"  UNIQUE 2-combo: {combo} = {target_values}")
            unique_combos.append((combo, target_values))
    
    # Try 3-field combinations if no 2-field unique combos found
    if not unique_combos:
        for combo in combinations(fields_to_check, 3):
            target_values = tuple(target[f] for f in combo)
            others_with_same = [b for b in real_bones if tuple(b[f] for f in combo) == target_values and b != target]
            if not others_with_same:
                print(f"  UNIQUE 3-combo: {combo} = {target_values}")
                unique_combos.append((combo, target_values))
    
    # Distribution analysis
    print("\n--- Value Distribution for Key Fields ---")
    for field in ['item_id', 'quality', 'owner']:
        distribution = defaultdict(list)
        for b in real_bones:
            distribution[b[field]].append(f"L{b['level']}({b['tile_x']},{b['tile_y']})")
        print(f"\n  {field} distribution:")
        for value in sorted(distribution.keys()):
            locs = distribution[value]
            if len(locs) <= 5:
                print(f"    {value}: {len(locs)} bones - {locs}")
            else:
                print(f"    {value}: {len(locs)} bones - {locs[:3]}... and {len(locs)-3} more")
    
    # RECOMMENDATION
    print()
    print("=" * 120)
    print("RECOMMENDATION FOR IDENTIFICATION")
    print("=" * 120)
    
    if unique_fields:
        print(f"\nBest option: Use single unique field")
        for field in unique_fields:
            print(f"  - {field}={target[field]}")
    elif unique_combos:
        # Find the simplest combo (fewest fields)
        simplest = min(unique_combos, key=lambda x: len(x[0]))
        print(f"\nBest option: Use field combination {simplest[0]} = {simplest[1]}")
    else:
        print("\nWARNING: No unique intrinsic property found!")
        print("The bones may only be identifiable by location.")
    
    return target


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m src.tools.find_bones <data_path>")
        print("Example: python -m src.tools.find_bones Input/UW1/DATA")
        sys.exit(1)
    
    data_path = sys.argv[1]
    
    if not Path(data_path).exists():
        print(f"Error: Data path does not exist: {data_path}")
        sys.exit(1)
    
    find_all_bones(data_path)
