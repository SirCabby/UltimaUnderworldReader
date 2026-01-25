#!/usr/bin/env python3
"""
Debug script to check item flags attribute access.

Extracts items using ItemExtractor and displays their flags values.
Useful for debugging item property extraction.

Usage:
    python -m src.tools.debug_item_flags [--data-path PATH] [--item-id HEX]

Examples:
    python -m src.tools.debug_item_flags
    python -m src.tools.debug_item_flags --item-id 0x166
    python -m src.tools.debug_item_flags --data-path Input/UW1/DATA --item-id 0x165
"""

import sys
import argparse
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def debug_flags(data_path: Path, item_id: int = None) -> None:
    """Debug item flags for a specific item type or all items."""
    from src.extractors import ItemExtractor
    
    if not data_path.exists():
        print(f"Error: Data path not found: {data_path}")
        sys.exit(1)
    
    print("Loading items from ItemExtractor...")
    items = ItemExtractor(data_path)
    items.extract()
    
    if item_id is not None:
        # Show specific item type
        print(f"\nItems with object_id 0x{item_id:03X}:")
        print("=" * 70)
        
        matching = [item for item in items.placed_items if item.object_id == item_id]
        
        for i, item in enumerate(matching[:15], 1):
            print(f"Item #{i}:")
            print(f"  object_id: 0x{item.object_id:X}")
            print(f"  level: {item.level}")
            print(f"  tile: ({item.tile_x}, {item.tile_y})")
            print(f"  flags: {item.flags}")
            print(f"  quality: {item.quality}")
            print(f"  owner: {item.owner}")
            print(f"  quantity: {item.quantity}")
            print()
        
        print(f"Total matching items: {len(matching)}")
        
        # Show unique flags values
        flags_set = set(item.flags for item in matching)
        print(f"Unique flags values: {sorted(flags_set)}")
    else:
        # Show summary of all items with non-zero flags
        print("\nItems with non-zero flags:")
        print("=" * 70)
        
        flags_by_type = {}
        for item in items.placed_items:
            if item.flags != 0:
                if item.object_id not in flags_by_type:
                    flags_by_type[item.object_id] = set()
                flags_by_type[item.object_id].add(item.flags)
        
        print(f"{'Object ID':<12} {'Count':<8} Unique Flags Values")
        print("-" * 70)
        
        for obj_id in sorted(flags_by_type.keys()):
            matching = [item for item in items.placed_items 
                       if item.object_id == obj_id and item.flags != 0]
            flags_str = ', '.join(str(f) for f in sorted(flags_by_type[obj_id]))
            print(f"0x{obj_id:03X}        {len(matching):<8} {flags_str}")
        
        print()
        print(f"Total object types with non-zero flags: {len(flags_by_type)}")


def main():
    parser = argparse.ArgumentParser(
        description="Debug item flags attribute access"
    )
    parser.add_argument(
        '--data-path', '-d',
        type=Path,
        default=Path("Input/UW1/DATA"),
        help="Path to DATA folder. Default: Input/UW1/DATA"
    )
    parser.add_argument(
        '--item-id', '-i',
        type=lambda x: int(x, 0),  # Accepts both decimal and hex (0x...)
        default=None,
        help="Object ID to inspect (hex, e.g., 0x166). If omitted, shows summary."
    )
    
    args = parser.parse_args()
    
    try:
        debug_flags(args.data_path, args.item_id)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
