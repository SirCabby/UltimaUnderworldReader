#!/usr/bin/env python3
"""
Level Data Byte-Level Inspector

Inspects unknown data regions and object placement patterns in level data blocks
to investigate difficulty-related encoding.
"""

import sys
import struct
from pathlib import Path
from src.parsers.ark_parser import LevArkParser
from src.parsers.level_parser import LevelParser


def hex_dump(data: bytes, offset: int = 0, width: int = 16) -> str:
    """Create a hex dump of binary data."""
    lines = []
    for i in range(0, len(data), width):
        chunk = data[i:i+width]
        hex_part = ' '.join(f'{b:02X}' for b in chunk)
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        lines.append(f"{offset + i:08X}  {hex_part:<48}  {ascii_part}")
    return '\n'.join(lines)


def analyze_unknown_region(level_data: bytes, level_num: int):
    """Analyze the unknown data region (0x7AFC-0x7BFF, 260 bytes)."""
    
    print(f"\n{'='*70}")
    print(f"Level {level_num}: Unknown Data Region (0x7AFC-0x7BFF, 260 bytes)")
    print(f"{'='*70}")
    
    if len(level_data) < 0x7C08:
        print(f"WARNING: Level data too short ({len(level_data)} bytes, expected 31,752)")
        return
    
    # Extract unknown region
    unknown_offset = 0x7AFC
    unknown_data = level_data[unknown_offset:unknown_offset + 260]
    
    print(f"\nHex Dump:")
    print(hex_dump(unknown_data, unknown_offset))
    
    # Analyze patterns
    print(f"\nPattern Analysis:")
    
    # Check if all zeros or all same value
    if all(b == 0 for b in unknown_data):
        print("  All zeros - likely unused padding")
    elif len(set(unknown_data)) == 1:
        print(f"  All bytes are 0x{unknown_data[0]:02X}")
    else:
        # Look for repeated patterns
        unique_bytes = len(set(unknown_data))
        print(f"  Contains {unique_bytes} unique byte values")
        
        # Check for common values
        byte_counts = {}
        for b in unknown_data:
            byte_counts[b] = byte_counts.get(b, 0) + 1
        
        # Show most common bytes
        common_bytes = sorted(byte_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        print(f"  Most common bytes:")
        for byte_val, count in common_bytes:
            print(f"    0x{byte_val:02X} ({byte_val:3d}): {count} occurrences ({count*100//len(unknown_data)}%)")
        
        # Check for patterns in first/last bytes
        if unknown_data[:4] != b'\x00\x00\x00\x00':
            word = struct.unpack_from('<I', unknown_data, 0)[0]
            print(f"  First 4 bytes (little-endian word): 0x{word:08X} ({word})")
        
        if unknown_data[-4:] != b'\x00\x00\x00\x00':
            word = struct.unpack_from('<I', unknown_data, len(unknown_data) - 4)[0]
            print(f"  Last 4 bytes (little-endian word): 0x{word:08X} ({word})")
    
    # Check magic marker
    magic_offset = 0x7C06
    if len(level_data) >= magic_offset + 2:
        magic = struct.unpack_from('<H', level_data, magic_offset)[0]
        if magic == 0x7775:  # 'uw' in little-endian
            print(f"\n  Magic marker at 0x7C06: 0x{magic:04X} ('uw') - OK")
        else:
            print(f"\n  Magic marker at 0x7C06: 0x{magic:04X} (expected 0x7775)")


def analyze_object_placement(level_parser: LevelParser, level_num: int):
    """Analyze object placement patterns for difficulty indicators."""
    
    print(f"\n{'='*70}")
    print(f"Level {level_num}: Object Placement Analysis")
    print(f"{'='*70}")
    
    level = level_parser.get_level(level_num)
    if not level:
        print("  Level not found")
        return
    
    print(f"\nObject Statistics:")
    print(f"  Total objects: {len(level.objects)}")
    print(f"  Mobile objects: {len(level.mobile_objects)}")
    print(f"  Static objects: {len(level.static_objects)}")
    
    # Check for objects at specific locations (e.g., (0,0) which are often templates)
    objects_at_origin = [obj for obj in level.objects.values() 
                        if obj.tile_x == 0 and obj.tile_y == 0]
    if objects_at_origin:
        print(f"\n  Objects at tile (0,0): {len(objects_at_origin)}")
        print(f"    (These are often templates, not actually placed)")
    
    # Check for objects with unusual flags
    # Objects might have difficulty flags in their flag bits
    objects_with_flags = [obj for obj in level.objects.values() if obj.flags != 0]
    if objects_with_flags:
        print(f"\n  Objects with non-zero flags: {len(objects_with_flags)}")
        # Show some examples
        for obj in list(objects_with_flags)[:5]:
            print(f"    Object {obj.index}: ID=0x{obj.item_id:03X}, flags=0x{obj.flags:X}, "
                  f"tile=({obj.tile_x},{obj.tile_y})")


def inspect_level_data(filepath: Path, level_num: int = None):
    """Inspect level data at byte level."""
    
    print("="*70)
    print("Level Data Byte-Level Inspection")
    print("="*70)
    print(f"File: {filepath}")
    print()
    
    # Parse ARK to get raw level data
    ark_parser = LevArkParser(filepath)
    ark_parser.parse()
    
    # Also parse with LevelParser for object analysis
    level_parser = LevelParser(filepath)
    level_parser.parse()
    
    # Inspect specified level or all levels
    levels_to_inspect = [level_num] if level_num is not None else list(range(9))
    
    for lev_num in levels_to_inspect:
        level_data = ark_parser.get_level_data(lev_num)
        if not level_data:
            print(f"\nLevel {lev_num}: No data found")
            continue
        
        # Analyze unknown region
        analyze_unknown_region(level_data, lev_num)
        
        # Analyze object placement
        analyze_object_placement(level_parser, lev_num)
        
        print()
    
    # Compare unknown regions across levels
    if len(levels_to_inspect) > 1:
        print("="*70)
        print("Cross-Level Comparison: Unknown Regions")
        print("="*70)
        
        unknown_regions = {}
        for lev_num in levels_to_inspect:
            level_data = ark_parser.get_level_data(lev_num)
            if level_data and len(level_data) >= 0x7C08:
                unknown_offset = 0x7AFC
                unknown_regions[lev_num] = level_data[unknown_offset:unknown_offset + 260]
        
        if len(unknown_regions) > 1:
            # Check if all unknown regions are identical
            first_region = unknown_regions[levels_to_inspect[0]]
            all_same = all(reg == first_region for reg in unknown_regions.values())
            
            if all_same:
                print("\nAll unknown regions are identical across levels")
                print("(Likely padding or unused data)")
            else:
                print("\nUnknown regions differ between levels:")
                for lev_num, region in unknown_regions.items():
                    unique_bytes = len(set(region))
                    print(f"  Level {lev_num}: {unique_bytes} unique byte values")
                
                # Find differences
                print("\nByte-by-byte differences (first 32 bytes):")
                first_key = levels_to_inspect[0]
                first_data = unknown_regions[first_key]
                for i in range(min(32, len(first_data))):
                    different_levels = [lev for lev, data in unknown_regions.items() 
                                       if i < len(data) and data[i] != first_data[i]]
                    if different_levels:
                        print(f"  Offset +{i:3d}: Level {first_key}=0x{first_data[i]:02X}, "
                              f"differs in levels {different_levels}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Inspect level data blocks at byte level"
    )
    parser.add_argument(
        '--file', '-f',
        type=Path,
        default=Path("Input/UW1/DATA/LEV.ARK"),
        help="Path to LEV.ARK file"
    )
    parser.add_argument(
        '--level', '-l',
        type=int,
        choices=range(9),
        metavar='0-8',
        help="Specific level to inspect (0-8), or all levels if omitted"
    )
    
    args = parser.parse_args()
    
    if not args.file.exists():
        print(f"Error: File not found: {args.file}")
        sys.exit(1)
    
    try:
        inspect_level_data(args.file, args.level)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
