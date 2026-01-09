#!/usr/bin/env python3
"""
Ultima Underworld Data Extraction Toolkit

A comprehensive toolkit to extract and analyze game data from
Ultima Underworld I: The Stygian Abyss.

Usage:
    python main.py <path_to_DATA_folder> [output_folder]
    python main.py Input/UW1/DATA Output --xlsx

Example:
    python main.py Input/UW1/DATA Output
    python main.py Input/UW1/DATA Output --xlsx  # Also generate Excel file
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

from src.parsers import StringsParser, ObjectsParser, CommonObjectsParser, LevelParser, ConversationParser
from src.extractors import ItemExtractor, NPCExtractor, SpellExtractor, SecretFinder
from src.exporters import JsonExporter, XLSX_AVAILABLE

if XLSX_AVAILABLE:
    from src.exporters import XlsxExporter


def print_header():
    """Print application header."""
    print("=" * 60)
    print("  Ultima Underworld Data Extraction Toolkit")
    print("  Extracts comprehensive game data from UW1")
    print("=" * 60)
    print()


def validate_data_path(data_path: Path) -> bool:
    """Validate that required data files exist."""
    required_files = [
        "STRINGS.PAK",
        "LEV.ARK", 
        "CNV.ARK",
        "OBJECTS.DAT",
        "COMOBJ.DAT"
    ]
    
    missing = []
    for filename in required_files:
        if not (data_path / filename).exists():
            missing.append(filename)
    
    if missing:
        print(f"Error: Missing required files in {data_path}:")
        for f in missing:
            print(f"  - {f}")
        return False
    
    return True


def extract_all(data_path: Path, output_path: Path, export_xlsx: bool = False) -> None:
    """Extract all game data and export to JSON (and optionally XLSX)."""
    
    print(f"Data folder: {data_path}")
    print(f"Output folder: {output_path}")
    print()
    
    # Initialize exporter
    exporter = JsonExporter(output_path)
    
    # Storage for xlsx export
    extracted_data = {}
    
    # 1. Extract strings
    print("[1/8] Extracting game strings...")
    strings = StringsParser(data_path / "STRINGS.PAK")
    strings.parse()
    exporter.export_all_strings(strings)
    extracted_data['strings'] = strings
    print(f"       Extracted {len(strings.blocks)} string blocks")
    
    # 2. Extract items
    print("[2/8] Extracting items...")
    items = ItemExtractor(data_path)
    items.extract()
    exporter.export_items(items.item_types, items.placed_items)
    extracted_data['items'] = items
    print(f"       Found {len(items.item_types)} item types")
    print(f"       Found {len(items.placed_items)} placed objects")
    
    # 3. Extract NPCs
    print("[3/8] Extracting NPCs...")
    npcs = NPCExtractor(data_path)
    npcs.extract()
    exporter.export_npcs(npcs.npcs, npcs.npc_names)
    extracted_data['npcs'] = npcs
    print(f"       Found {len(npcs.npcs)} NPCs")
    
    # 4. Extract spells and mantras
    print("[4/8] Extracting spells and mantras...")
    spells = SpellExtractor(data_path)
    spells.extract()
    exporter.export_spells(
        spells.spells, 
        spells.mantras, 
        spells.get_rune_names(),
        spells.get_spell_runes()
    )
    extracted_data['spells'] = spells
    print(f"       Found {len(spells.spells)} spells")
    print(f"       Found {len(spells.mantras)} mantras")
    
    # 5. Extract conversations
    print("[5/8] Extracting conversations...")
    convs = ConversationParser(data_path / "CNV.ARK")
    convs.parse()
    exporter.export_conversations(convs.conversations, strings)
    extracted_data['conversations'] = convs
    print(f"       Found {len(convs.conversations)} conversations")
    
    # 6. Extract secrets
    print("[6/8] Finding secrets and traps...")
    secrets = SecretFinder(data_path)
    secrets.analyze()
    exporter.export_secrets(secrets.secrets)
    extracted_data['secrets'] = secrets
    summary = secrets.get_summary()
    print(f"       Found {summary['total']} secrets/traps")
    
    # 7. Export map data
    print("[7/8] Exporting map data...")
    levels = LevelParser(data_path / "LEV.ARK")
    levels.parse()
    exporter.export_map_data(levels.levels)
    extracted_data['levels'] = levels
    print(f"       Exported data for {len(levels.levels)} levels")
    
    # 8. Export web map viewer data
    print("[8/8] Exporting web map viewer data...")
    # Try to load image paths if they exist (from make web)
    image_paths = {}
    web_images_dir = Path("web/images/objects")
    if web_images_dir.exists():
        # Scan for existing images and build path mapping
        for img_file in web_images_dir.glob("object_*.png"):
            # Extract object ID from filename (object_XXX.png)
            try:
                obj_id_str = img_file.stem.replace("object_", "")
                obj_id = int(obj_id_str, 10)
                image_paths[obj_id] = f"images/objects/{img_file.name}"
            except ValueError:
                continue
    
    web_map_path = exporter.export_web_map_data(
        items.placed_items, 
        npcs.npcs, 
        npcs.npc_names,
        items.item_types,
        levels.levels,  # Pass levels for container content extraction
        strings,  # Pass strings for rich descriptions (books, scrolls, keys, spells)
        secrets.secrets,  # Pass secrets (illusory walls, secret doors)
        convs.conversations,  # Pass conversations to verify dialogue scripts exist
        image_paths  # Pass image paths for object images
    )
    print(f"       Exported web map data to {web_map_path.name}")
    
    # Export to xlsx if requested
    if export_xlsx:
        print()
        print("Generating Excel workbook...")
        export_to_xlsx(data_path, output_path, extracted_data)
    
    print()
    print("=" * 60)
    print("  Extraction Complete!")
    print("=" * 60)
    print()
    print("Generated files:")
    for f in sorted(output_path.glob("*.json")):
        size = f.stat().st_size
        print(f"  {f.name}: {size:,} bytes")
    
    if export_xlsx:
        for f in sorted(output_path.glob("*.xlsx")):
            size = f.stat().st_size
            print(f"  {f.name}: {size:,} bytes")
    
    print()
    print("Summary:")
    print(f"  - {len(items.item_types)} unique item types")
    print(f"  - {len(items.placed_items)} placed objects across 9 levels")
    print(f"  - {len(npcs.npcs)} NPCs with {len([n for n in npcs.npcs if n.conversation_slot > 0])} having conversations")
    print(f"  - {len(spells.spells)} spells in 8 circles")
    print(f"  - {len(convs.conversations)} conversation scripts")
    print(f"  - {summary['total']} triggers, traps, and secrets")


def export_to_xlsx(data_path: Path, output_path: Path, extracted_data: dict) -> None:
    """Export all extracted data to an Excel workbook."""
    if not XLSX_AVAILABLE:
        print("  Warning: openpyxl not installed, skipping xlsx export")
        print("  Install with: pip install openpyxl")
        return
    
    xlsx = XlsxExporter(output_path)
    
    items = extracted_data['items']
    npcs = extracted_data['npcs']
    spells = extracted_data['spells']
    secrets = extracted_data['secrets']
    convs = extracted_data['conversations']
    strings = extracted_data['strings']
    levels = extracted_data['levels']
    
    # Load parsers for detailed item info
    objects_parser = ObjectsParser(data_path / "OBJECTS.DAT")
    objects_parser.parse()
    
    common_parser = CommonObjectsParser(data_path / "COMOBJ.DAT")
    common_parser.parse()
    
    # Export all sheets
    print("  - Items sheet (with weights)...")
    xlsx.export_items(items.item_types, items.placed_items)
    
    print("  - Weapons sheet...")
    xlsx.export_weapons(items.item_types, objects_parser)
    
    print("  - Armor sheet...")
    xlsx.export_armor(items.item_types, objects_parser)
    
    print("  - Containers sheet (carryable only)...")
    xlsx.export_containers(items.item_types, objects_parser, common_parser)
    
    print("  - Food sheet (with nutrition values)...")
    xlsx.export_food(items.item_types, strings)
    
    print("  - Light Sources sheet (with spells)...")
    xlsx.export_light_sources(items.item_types, objects_parser, strings)
    
    print("  - NPCs sheet (with inventory)...")
    xlsx.export_npcs(npcs.npcs, npcs.npc_names, strings, levels)
    
    print("  - NPC Names sheet (filtered)...")
    xlsx.export_npc_names(npcs.npc_names, strings)
    
    print("  - Spells sheet (with descriptions and mana costs)...")
    xlsx.export_spells(spells.spells, spells.get_spell_runes())
    
    print("  - Runes sheet...")
    xlsx.export_runes(spells.get_rune_names())
    
    print("  - Mantras sheet (with point increases)...")
    xlsx.export_mantras()
    
    print("  - Conversations sheet (structured with NPC/Player distinction)...")
    xlsx.export_conversations_structured(convs.conversations, strings, npcs.npc_names)
    
    print("  - Placed Objects sheet (with descriptions and enchantments)...")
    xlsx.export_placed_objects(items.placed_items, items.item_types, strings, levels)
    
    print("  - Unused Items sheet...")
    xlsx.export_unused_items(items.item_types, items.placed_items, strings)
    
    filepath = xlsx.save()
    print(f"  Saved: {filepath}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Extract game data from Ultima Underworld I"
    )
    parser.add_argument(
        "data_path",
        help="Path to the DATA folder containing game files"
    )
    parser.add_argument(
        "output_path",
        nargs="?",
        default="Output",
        help="Output folder for extracted data (default: Output)"
    )
    parser.add_argument(
        "--xlsx", "-x",
        action="store_true",
        help="Also generate Excel workbook (.xlsx) with all data"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    print_header()
    
    data_path = Path(args.data_path)
    output_path = Path(args.output_path)
    
    if not data_path.exists():
        print(f"Error: Data path does not exist: {data_path}")
        sys.exit(1)
    
    if not validate_data_path(data_path):
        sys.exit(1)
    
    if args.xlsx and not XLSX_AVAILABLE:
        print("Warning: --xlsx specified but openpyxl not installed")
        print("Install with: pip install openpyxl")
        print()
    
    try:
        extract_all(data_path, output_path, export_xlsx=args.xlsx)
    except Exception as e:
        print(f"\nError during extraction: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
