#!/usr/bin/env python3
"""
LEV.ARK Structure Analyzer

Analyzes the structure of LEV.ARK to investigate difficulty settings
and document the complete block layout.

Usage:
    python -m src.tools.analyze_lev_ark [path_to_LEV.ARK]
"""

import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.parsers.ark_parser import LevArkParser


def analyze_lev_ark(filepath: Path):
    """Analyze LEV.ARK structure in detail."""
    
    print("=" * 70)
    print("LEV.ARK Structure Analysis")
    print("=" * 70)
    print(f"File: {filepath}")
    print(f"Size: {filepath.stat().st_size:,} bytes")
    print()
    
    parser = LevArkParser(filepath)
    parser.parse()
    
    # Basic statistics
    print(f"Total block slots declared: {parser.num_blocks}")
    print(f"Non-empty blocks found: {len(parser.blocks)}")
    print(f"Empty block slots: {parser.num_blocks - len(parser.blocks)}")
    print()
    
    # Expected structure
    print("Expected Structure (135 blocks):")
    print("  Blocks 0-8:   Level data (9 levels)")
    print("  Blocks 9-17:  Animation overlay (9 levels)")
    print("  Blocks 18-26: Texture mapping (9 levels)")
    print("  Blocks 27-35: Automap data (9 levels)")
    print("  Blocks 36-44: Map notes (9 levels)")
    print("  Blocks 45+:   Unused")
    print()
    
    # Check if we have exactly 135 blocks or more
    if parser.num_blocks > 135:
        print(f"WARNING: File declares {parser.num_blocks} blocks, expected 135!")
        print("   This could indicate difficulty-specific blocks.")
    elif parser.num_blocks == 135:
        print("OK: Block count matches expected 135 blocks")
    else:
        print(f"WARNING: File declares {parser.num_blocks} blocks, expected 135")
    print()
    
    # Analyze block organization
    level_blocks = [i for i in range(9) if i in parser.blocks]
    anim_blocks = [i for i in range(9, 18) if i in parser.blocks]
    texture_blocks = [i for i in range(18, 27) if i in parser.blocks]
    automap_blocks = [i for i in range(27, 36) if i in parser.blocks]
    map_note_blocks = [i for i in range(36, 45) if i in parser.blocks]
    other_blocks = [i for i in parser.blocks.keys() if i >= 45]
    
    print("Block Organization:")
    print(f"  Level data blocks (0-8):     {len(level_blocks)} blocks")
    print(f"  Animation blocks (9-17):     {len(anim_blocks)} blocks")
    print(f"  Texture blocks (18-26):      {len(texture_blocks)} blocks")
    print(f"  Automap blocks (27-35):      {len(automap_blocks)} blocks")
    print(f"  Map note blocks (36-44):     {len(map_note_blocks)} blocks")
    if other_blocks:
        print(f"  WARNING: Additional blocks (45+):   {len(other_blocks)} blocks")
        print(f"      Block indices: {sorted(other_blocks)[:20]}{'...' if len(other_blocks) > 20 else ''}")
    print()
    
    # Detailed block listing
    print("Block Details:")
    print("-" * 70)
    print(f"{'Index':<8} {'Offset':<12} {'Size':<10} {'Category':<20}")
    print("-" * 70)
    
    for idx in sorted(parser.blocks.keys()):
        block = parser.blocks[idx]
        
        # Categorize block
        if 0 <= idx <= 8:
            category = f"Level {idx}"
        elif 9 <= idx <= 17:
            category = f"Anim {idx-9}"
        elif 18 <= idx <= 26:
            category = f"Texture {idx-18}"
        elif 27 <= idx <= 35:
            category = f"Automap {idx-27}"
        elif 36 <= idx <= 44:
            category = f"MapNote {idx-36}"
        else:
            category = "OTHER"
        
        print(f"{idx:<8} 0x{block.offset:08X}  {block.size:>8}   {category}")
    
    print()
    
    # Look for patterns in block sizes
    if level_blocks:
        level_sizes = [parser.blocks[i].size for i in level_blocks]
        print("Level Data Block Sizes:")
        print(f"  Min: {min(level_sizes):,} bytes")
        print(f"  Max: {max(level_sizes):,} bytes")
        print(f"  Expected: 31,752 bytes (0x7C08)")
        if len(set(level_sizes)) == 1:
            print(f"  OK: All level blocks are same size: {level_sizes[0]:,} bytes")
        else:
            print(f"  WARNING: Size variation detected!")
            for i, size in zip(level_blocks, level_sizes):
                if size != 31752:
                    print(f"    Block {i}: {size:,} bytes (expected 31,752)")
        print()
    
    # Check for duplicate or alternate blocks (potential difficulty data)
    if other_blocks:
        print("=" * 70)
        print("ANALYSIS: Additional Blocks Found")
        print("=" * 70)
        print("The file contains blocks beyond the expected 135.")
        print("These could potentially be difficulty-specific level data.")
        print()
        print("Investigating additional blocks...")
        for idx in sorted(other_blocks)[:10]:  # Show first 10
            block = parser.blocks[idx]
            print(f"\nBlock {idx}:")
            print(f"  Offset: 0x{block.offset:08X}")
            print(f"  Size: {block.size:,} bytes")
            
            # Check if size matches level data blocks
            if block.size == 31752:
                print(f"  WARNING: Size matches level data block (31,752 bytes)")
                print(f"      This could be a difficulty-specific level data block!")
            elif block.size in level_sizes:
                print(f"  WARNING: Size matches other level data blocks")
            
            # Show first few bytes as hex
            if len(block.data) >= 16:
                hex_preview = ' '.join(f'{b:02X}' for b in block.data[:16])
                print(f"  First 16 bytes: {hex_preview}")
        
        if len(other_blocks) > 10:
            print(f"\n... and {len(other_blocks) - 10} more additional blocks")
        print()
    
    # Summary and recommendations
    print("=" * 70)
    print("Summary and Recommendations")
    print("=" * 70)
    
    if parser.num_blocks == 135 and len(parser.blocks) == 135:
        print("OK: File structure matches expected format (135 blocks, all present)")
        print("  Current export likely represents ONE difficulty setting.")
        print("  Difficulty differences may be:")
        print("   1. Applied at runtime by game engine")
        print("   2. Stored in separate files")
        print("   3. Encoded within level data blocks (requires byte-level analysis)")
    elif other_blocks:
        print("WARNING: Additional blocks found beyond expected 135")
        print("  Recommend: Inspect additional blocks for difficulty-specific data")
        print("  Action: Compare block contents to level data blocks")
    else:
        print("INFO: File structure analysis complete")
        print("  Next step: Byte-level analysis of level data blocks")
    
    print()
    return parser


if __name__ == '__main__':
    if len(sys.argv) < 2:
        # Default path
        default_path = Path("Input/UW1/DATA/LEV.ARK")
        if default_path.exists():
            filepath = default_path
        else:
            print("Usage: python -m src.tools.analyze_lev_ark <path_to_LEV.ARK>")
            print(f"   or place LEV.ARK at: {default_path}")
            sys.exit(1)
    else:
        filepath = Path(sys.argv[1])
    
    if not filepath.exists():
        print(f"Error: File not found: {filepath}")
        sys.exit(1)
    
    try:
        parser = analyze_lev_ark(filepath)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
