#!/usr/bin/env python3
"""
Check TMOBJ image path mapping for writings and gravestones.

Verifies that TMOBJ texture images exist and shows the mapping between
object flags values and TMOBJ indices.

Usage:
    python -m src.tools.check_tmobj_mapping [--data-path PATH] [--tmobj-dir PATH]

Examples:
    python -m src.tools.check_tmobj_mapping
    python -m src.tools.check_tmobj_mapping --data-path Input/UW1/DATA
"""

import sys
import argparse
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def check_tmobj_files(tmobj_dir: Path) -> dict:
    """Check which TMOBJ files exist and return a mapping."""
    tmobj_image_paths = {}
    
    if not tmobj_dir.exists():
        print(f"Warning: TMOBJ directory not found: {tmobj_dir}")
        return tmobj_image_paths
    
    for img_file in tmobj_dir.glob("tmobj_*.png"):
        try:
            idx_str = img_file.stem.replace("tmobj_", "")
            idx = int(idx_str, 10)
            tmobj_image_paths[idx] = f"images/extracted/tmobj/{img_file.name}"
        except ValueError:
            continue
    
    return tmobj_image_paths


def check_mapping(data_path: Path, tmobj_dir: Path) -> None:
    """Check TMOBJ mapping against actual game data."""
    from src.parsers.level_parser import LevelParser
    
    # Check TMOBJ files
    print("=" * 70)
    print("TMOBJ Image File Status")
    print("=" * 70)
    
    tmobj_image_paths = check_tmobj_files(tmobj_dir)
    print(f"Found {len(tmobj_image_paths)} TMOBJ images")
    print(f"Indices: {sorted(tmobj_image_paths.keys())}")
    
    # Check writing indices (flags + 20)
    print("\n" + "=" * 70)
    print("Writing TMOBJ Index Mapping (flags + 20)")
    print("=" * 70)
    
    for flags in range(8):
        idx = flags + 20
        exists = idx in tmobj_image_paths
        status = "OK" if exists else "MISSING"
        path = tmobj_image_paths.get(idx, 'N/A')
        print(f"  flags={flags} -> tmobj_{idx:02d} -> {status} ({path})")
    
    # Check gravestone indices (flags + 28)
    print("\n" + "=" * 70)
    print("Gravestone TMOBJ Index Mapping (flags + 28)")
    print("=" * 70)
    
    for flags in range(8):
        idx = flags + 28
        exists = idx in tmobj_image_paths
        status = "OK" if exists else "MISSING"
        path = tmobj_image_paths.get(idx, 'N/A')
        print(f"  flags={flags} -> tmobj_{idx:02d} -> {status} ({path})")
    
    # Parse level data to see actual flags values used
    if not data_path.exists():
        print(f"\nWarning: Data path not found: {data_path}")
        print("Cannot analyze actual game objects.")
        return
    
    print("\n" + "=" * 70)
    print("Actual Writing Objects from Game Data")
    print("=" * 70)
    
    levels = LevelParser(data_path / "LEV.ARK")
    levels.parse()
    
    writing_flags = set()
    gravestone_flags = set()
    
    for level_num, level in levels.levels.items():
        writings = [obj for obj in level.objects.values() if obj.item_id == 0x166]
        gravestones = [obj for obj in level.objects.values() if obj.item_id == 0x165]
        
        for w in writings:
            writing_flags.add(w.flags)
        
        for g in gravestones:
            gravestone_flags.add(g.flags)
        
        if writings:
            print(f"\nLevel {level_num}: {len(writings)} writings")
            for w in writings[:3]:
                tmobj_idx = w.flags + 20
                exists = tmobj_idx in tmobj_image_paths
                status = "OK" if exists else "MISSING"
                print(f"  idx={w.index}, flags={w.flags} -> tmobj_{tmobj_idx:02d} ({status})")
            if len(writings) > 3:
                print(f"  ... and {len(writings) - 3} more")
    
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"Unique writing flags values: {sorted(writing_flags)}")
    print(f"Unique gravestone flags values: {sorted(gravestone_flags)}")
    
    # Check coverage
    missing_writing_tmobj = []
    for f in writing_flags:
        idx = f + 20
        if idx not in tmobj_image_paths:
            missing_writing_tmobj.append((f, idx))
    
    missing_gravestone_tmobj = []
    for f in gravestone_flags:
        idx = f + 28
        if idx not in tmobj_image_paths:
            missing_gravestone_tmobj.append((f, idx))
    
    if missing_writing_tmobj:
        print(f"\nMissing TMOBJ for writings:")
        for f, idx in missing_writing_tmobj:
            print(f"  flags={f} -> tmobj_{idx:02d}.png")
    else:
        print("\nAll writing TMOBJ images present.")
    
    if missing_gravestone_tmobj:
        print(f"\nMissing TMOBJ for gravestones:")
        for f, idx in missing_gravestone_tmobj:
            print(f"  flags={f} -> tmobj_{idx:02d}.png")
    else:
        print("\nAll gravestone TMOBJ images present.")


def main():
    parser = argparse.ArgumentParser(
        description="Check TMOBJ image path mapping for writings and gravestones"
    )
    parser.add_argument(
        '--data-path', '-d',
        type=Path,
        default=Path("Input/UW1/DATA"),
        help="Path to DATA folder containing LEV.ARK. Default: Input/UW1/DATA"
    )
    parser.add_argument(
        '--tmobj-dir', '-t',
        type=Path,
        default=Path("web/images/extracted/tmobj"),
        help="Path to TMOBJ images directory. Default: web/images/extracted/tmobj"
    )
    
    args = parser.parse_args()
    
    try:
        check_mapping(args.data_path, args.tmobj_dir)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
