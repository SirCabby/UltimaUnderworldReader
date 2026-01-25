#!/usr/bin/env python3
"""
Analyze writings and gravestones from extracted game data.

Inspects writing objects (0x166) and gravestones (0x165), showing their
flags values, image paths, and descriptions. Useful for debugging TMOBJ
texture mapping.

Usage:
    python -m src.tools.analyze_writings [--source web|json|extractor] [--data-path PATH]

Examples:
    python -m src.tools.analyze_writings
    python -m src.tools.analyze_writings --source json --output Output
    python -m src.tools.analyze_writings --source extractor --data-path Input/UW1/DATA
"""

import sys
import json
import argparse
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def analyze_from_web_json(web_data_path: Path) -> None:
    """Analyze writings from web_map_data.json."""
    json_file = web_data_path / "web_map_data.json"
    
    if not json_file.exists():
        print(f"Error: {json_file} not found")
        print("Run 'make web' to generate web viewer data first.")
        sys.exit(1)
    
    with open(json_file, 'r') as f:
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
    
    _print_analysis(writings, gravestones)


def analyze_from_placed_objects(output_path: Path) -> None:
    """Analyze writings from placed_objects.json."""
    json_file = output_path / "placed_objects.json"
    
    if not json_file.exists():
        print(f"Error: {json_file} not found")
        print("Run 'python main.py Input/UW1/DATA Output' first.")
        sys.exit(1)
    
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    objects = data.get('objects', data)  # Handle both formats
    
    writings = []
    gravestones = []
    
    for item in objects:
        obj_id = item.get('object_id', 0)
        if obj_id == 0x166:  # Writing (358 decimal)
            writings.append({
                'level': item.get('level'),
                'name': item.get('name', ''),
                'flags': item.get('flags'),
                'quality': item.get('quality'),
                'owner': item.get('owner'),
                'quantity': item.get('quantity'),
                'special_link': item.get('special_link'),
                'is_quantity': item.get('is_quantity'),
                'description': ''
            })
        elif obj_id == 0x165:  # Gravestone (357 decimal)
            gravestones.append({
                'level': item.get('level'),
                'name': item.get('name', ''),
                'flags': item.get('flags'),
                'quality': item.get('quality'),
                'owner': item.get('owner'),
                'quantity': item.get('quantity'),
                'description': ''
            })
    
    _print_detailed_analysis(writings, gravestones)


def analyze_from_extractor(data_path: Path) -> None:
    """Analyze writings directly from ItemExtractor."""
    from src.extractors import ItemExtractor
    
    if not data_path.exists():
        print(f"Error: Data path not found: {data_path}")
        sys.exit(1)
    
    items = ItemExtractor(data_path)
    items.extract()
    
    writings = []
    gravestones = []
    
    for item in items.placed_items:
        if item.object_id == 0x166:  # Writing
            writings.append({
                'level': item.level,
                'name': item.name,
                'flags': item.flags,
                'quality': item.quality,
                'owner': item.owner,
                'quantity': item.quantity,
                'description': item.description or ''
            })
        elif item.object_id == 0x165:  # Gravestone
            gravestones.append({
                'level': item.level,
                'name': item.name,
                'flags': item.flags,
                'quality': item.quality,
                'owner': item.owner,
                'quantity': item.quantity,
                'description': item.description or ''
            })
    
    _print_detailed_analysis(writings, gravestones)


def _print_analysis(writings: list, gravestones: list) -> None:
    """Print basic analysis of writings and gravestones."""
    # Sort by flags
    writings_sorted = sorted(writings, key=lambda x: (x.get('flags') or 0))
    
    print(f"Writings (total: {len(writings)}) sorted by flags:")
    print(f"{'Lv':>2} {'Flags':>5} {'Image':<25} Description")
    print("-" * 80)
    
    for w in writings_sorted[:25]:
        lv = w.get('level')
        lv_str = str(lv) if lv is not None else '?'
        flags = w.get('flags') or 0
        img = w.get('image_path', '(none)')
        img_short = img.split('/')[-1] if img else '(none)'
        desc = w.get('description', '')[:35]
        print(f"{lv_str:>2} {flags:>5} {img_short:<25} {desc}")
    
    # Flags distribution for writings
    flags_counts = {}
    for w in writings:
        f = w.get('flags') or 0
        flags_counts[f] = flags_counts.get(f, 0) + 1
    
    print()
    print("Flags value distribution for writings:")
    for f in sorted(flags_counts.keys()):
        tmobj_idx = (f & 0xFF) + 20
        print(f"  flags={f:2d} -> tmobj_{tmobj_idx:02d}.png: {flags_counts[f]} writings")
    
    # Gravestones
    print()
    print(f"Gravestones (total: {len(gravestones)}) sorted by flags:")
    print(f"{'Lv':>2} {'Flags':>5} {'Image':<25} Description")
    print("-" * 80)
    
    gravestones_sorted = sorted(gravestones, key=lambda x: (x.get('flags') or 0))
    for g in gravestones_sorted[:15]:
        lv = g.get('level')
        lv_str = str(lv) if lv is not None else '?'
        flags = g.get('flags') or 0
        img = g.get('image_path', '(none)')
        img_short = img.split('/')[-1] if img else '(none)'
        desc = g.get('description', '')[:35]
        print(f"{lv_str:>2} {flags:>5} {img_short:<25} {desc}")
    
    # Flags distribution for gravestones
    gs_flags_counts = {}
    for g in gravestones:
        f = g.get('flags') or 0
        gs_flags_counts[f] = gs_flags_counts.get(f, 0) + 1
    
    print()
    print("Flags value distribution for gravestones:")
    for f in sorted(gs_flags_counts.keys()):
        tmobj_idx = (f & 0xFF) + 28
        print(f"  flags={f:2d} -> tmobj_{tmobj_idx:02d}.png: {gs_flags_counts[f]} gravestones")


def _print_detailed_analysis(writings: list, gravestones: list) -> None:
    """Print detailed analysis including all object fields."""
    print("Sample writings:")
    print("=" * 70)
    
    for i, w in enumerate(writings[:15], 1):
        print(f"Writing #{i}:")
        print(f"  level: {w.get('level')}")
        print(f"  flags: {w.get('flags')}")
        print(f"  quality: {w.get('quality')}")
        print(f"  owner: {w.get('owner')}")
        if 'quantity' in w:
            print(f"  quantity: {w.get('quantity')}")
        if 'special_link' in w:
            print(f"  special_link: {w.get('special_link')}")
        if 'is_quantity' in w:
            print(f"  is_quantity: {w.get('is_quantity')}")
        print()
    
    print(f"Total writings: {len(writings)}")
    
    # Check unique flags values
    flags_set = set(w.get('flags', 0) for w in writings)
    print(f"\nUnique flags values for writings: {sorted(flags_set)}")
    
    print()
    print("Sample gravestones:")
    print("=" * 70)
    
    for i, g in enumerate(gravestones[:5], 1):
        print(f"Gravestone #{i}:")
        print(f"  level: {g.get('level')}")
        print(f"  flags: {g.get('flags')}")
        print(f"  quality: {g.get('quality')}")
        print(f"  owner: {g.get('owner')}")
        if 'quantity' in g:
            print(f"  quantity: {g.get('quantity')}")
        print()
    
    print(f"Total gravestones: {len(gravestones)}")
    
    # Check unique flags values
    gs_flags_set = set(g.get('flags', 0) for g in gravestones)
    print(f"\nUnique flags values for gravestones: {sorted(gs_flags_set)}")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze writings and gravestones from extracted game data"
    )
    parser.add_argument(
        '--source', '-s',
        choices=['web', 'json', 'extractor'],
        default='web',
        help="Data source: 'web' (web_map_data.json), 'json' (placed_objects.json), "
             "or 'extractor' (directly from game files). Default: web"
    )
    parser.add_argument(
        '--data-path', '-d',
        type=Path,
        default=Path("Input/UW1/DATA"),
        help="Path to DATA folder (for extractor source). Default: Input/UW1/DATA"
    )
    parser.add_argument(
        '--output', '-o',
        type=Path,
        default=Path("Output"),
        help="Output folder (for json source). Default: Output"
    )
    parser.add_argument(
        '--web-data', '-w',
        type=Path,
        default=Path("web/data"),
        help="Web data folder (for web source). Default: web/data"
    )
    
    args = parser.parse_args()
    
    if args.source == 'web':
        analyze_from_web_json(args.web_data)
    elif args.source == 'json':
        analyze_from_placed_objects(args.output)
    elif args.source == 'extractor':
        analyze_from_extractor(args.data_path)


if __name__ == "__main__":
    main()
