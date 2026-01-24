#!/usr/bin/env python3
"""
Extract object images from Ultima Underworld game files for the web viewer.

This script extracts sprite images from multiple sources:
- OBJECTS.GR: General object sprites (461 sprites)
- TMOBJ.GR: Wall decal textures (writings, gravestones, levers, etc.)
- W64.TR: Wall textures (for special tmap objects)
- CRIT folder: NPC/critter animation frames

Each source is extracted to a separate folder, and the JSON exporter maps
each object instance to the correct image based on its properties (flags, owner).

IMPORTANT: Run 'make extract' before 'make images' to generate web_map_data.json.
"""

import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.extractors import ImageExtractor

# Default paths
DATA_PATH = Path("Input/UW1/DATA")
WEB_IMAGES_DIR = Path("web/images/extracted/objects")
WEB_TMOBJ_DIR = Path("web/images/extracted/tmobj")
WEB_WALLS_DIR = Path("web/images/extracted/walls")
WEB_NPC_DIR = Path("web/images/extracted/npcs")
WEB_DATA_PATH = Path("web/data/web_map_data.json")


def get_placed_object_ids() -> set:
    """
    Get the set of object IDs that are actually used in the web viewer.
    """
    if not WEB_DATA_PATH.exists():
        print(f"  Warning: {WEB_DATA_PATH} not found")
        print("  Run 'make extract' first to generate web_map_data.json")
        return None
    
    print("Reading web_map_data.json for object IDs used in web viewer...")
    
    with open(WEB_DATA_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    placed_object_ids = set()
    
    for level in data.get('levels', []):
        for obj in level.get('objects', []):
            placed_object_ids.add(obj.get('object_id', 0))
            for content in obj.get('contents', []):
                placed_object_ids.add(content.get('object_id', 0))
        
        for npc in level.get('npcs', []):
            placed_object_ids.add(npc.get('object_id', 0))
    
    print(f"  Found {len(placed_object_ids)} unique object IDs used in web viewer")
    return placed_object_ids


def clean_directory(directory: Path, pattern: str):
    """Clean files matching pattern from directory."""
    if directory.exists():
        files = list(directory.glob(pattern))
        if files:
            print(f"  Cleaning {len(files)} existing files from {directory.name}/...")
            for f in files:
                try:
                    f.unlink()
                except Exception:
                    pass


def main():
    """Extract object images for web viewer."""
    print("=" * 60)
    print("  Extracting Game Images for Web Viewer")
    print("=" * 60)
    print()
    
    if not DATA_PATH.exists():
        print(f"Error: Data path does not exist: {DATA_PATH}")
        print("Please ensure game files are in Input/UW1/DATA/")
        sys.exit(1)
    
    print(f"Data folder: {DATA_PATH}")
    print()
    
    try:
        # Pre-scan level data to get placed object IDs
        placed_object_ids = get_placed_object_ids()
        print()
        
        image_extractor = ImageExtractor(DATA_PATH)
        
        # ========================================
        # 1. Extract OBJECTS.GR sprites
        # ========================================
        print("-" * 40)
        print("1. Extracting OBJECTS.GR sprites")
        print("-" * 40)
        
        clean_directory(WEB_IMAGES_DIR, "object_*.png")
        
        if image_extractor.extract():
            image_paths = image_extractor.save_images(WEB_IMAGES_DIR, object_ids_filter=placed_object_ids)
            print(f"  Extracted {len(image_paths)} object images")
        else:
            print("  Failed to extract OBJECTS.GR")
        print()
        
        # ========================================
        # 2. Extract TMOBJ.GR sprites
        # ========================================
        print("-" * 40)
        print("2. Extracting TMOBJ.GR textures")
        print("   (writings, gravestones, levers, etc.)")
        print("-" * 40)
        
        clean_directory(WEB_TMOBJ_DIR, "tmobj_*.png")
        
        if image_extractor.extract_tmobj_images():
            tmobj_paths = image_extractor.save_tmobj_images(WEB_TMOBJ_DIR)
            print(f"  Extracted {len(tmobj_paths)} TMOBJ textures")
        else:
            print("  Failed to extract TMOBJ.GR")
        print()
        
        # ========================================
        # 3. Extract W64.TR wall textures
        # ========================================
        print("-" * 40)
        print("3. Extracting W64.TR wall textures")
        print("   (for special tmap objects)")
        print("-" * 40)
        
        clean_directory(WEB_WALLS_DIR, "wall_*.png")
        
        if image_extractor.extract_wall_textures():
            wall_paths = image_extractor.save_wall_textures(WEB_WALLS_DIR)
            print(f"  Extracted {len(wall_paths)} wall textures")
        else:
            print("  Failed to extract W64.TR")
        print()
        
        # ========================================
        # 4. Extract CRIT NPC animation frames
        # ========================================
        print("-" * 40)
        print("4. Extracting CRIT NPC animations")
        print("   (critter/monster sprites)")
        print("-" * 40)
        
        clean_directory(WEB_NPC_DIR, "npc_*.png")
        
        if image_extractor.extract_npc_images():
            npc_paths = image_extractor.save_npc_images(WEB_NPC_DIR)
            print(f"  Extracted {len(npc_paths)} NPC images")
        else:
            print("  Failed to extract NPC images from CRIT folder")
        print()
        
        # ========================================
        # Summary
        # ========================================
        print("=" * 60)
        print("  Image Extraction Complete")
        print("=" * 60)
        print(f"  Objects: {WEB_IMAGES_DIR}")
        print(f"  TMOBJ:   {WEB_TMOBJ_DIR}")
        print(f"  Walls:   {WEB_WALLS_DIR}")
        print(f"  NPCs:    {WEB_NPC_DIR}")
        
    except Exception as e:
        print()
        print(f"Error during image extraction: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print()


if __name__ == "__main__":
    main()
