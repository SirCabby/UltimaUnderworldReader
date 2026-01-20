#!/usr/bin/env python3
"""
Extract object images from Ultima Underworld .GR files for the web viewer.

This script extracts sprite images from OBJECTS.GR or TMOBJ.GR files
and saves them as PNG files to web/images/extracted/objects/.

Only images for objects that are actually used in the web viewer are
extracted, to avoid generating unused images. This is determined by
reading web_map_data.json to find which object IDs appear in the
objects array (excluding NPCs which have their own array).

Note: NPC image extraction was previously supported but has been removed.
The ImageExtractor class still has extract_npc_images() and save_npc_images()
methods available if NPC images are needed in the future.

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
WEB_DATA_PATH = Path("web/data/web_map_data.json")


def get_placed_object_ids() -> set:
    """
    Get the set of object IDs that are actually used in the web viewer.
    
    Reads from web_map_data.json to get only the object IDs that appear
    in the objects array (not NPCs, which have their own array).
    
    This excludes:
    - NPC object IDs (64-127) since they're in a separate npcs array
    - Objects that are filtered out by the json exporter (templates, etc.)
    
    Returns:
        Set of object IDs that need images, or None if web_map_data.json not found.
    """
    if not WEB_DATA_PATH.exists():
        print(f"  Warning: {WEB_DATA_PATH} not found")
        print("  Run 'make extract' first to generate web_map_data.json")
        return None
    
    print("Reading web_map_data.json for object IDs used in web viewer...")
    
    with open(WEB_DATA_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    placed_object_ids = set()
    
    # Collect object IDs from the objects array (not NPCs)
    for level in data.get('levels', []):
        for obj in level.get('objects', []):
            placed_object_ids.add(obj.get('object_id', 0))
            # Include container contents
            for content in obj.get('contents', []):
                placed_object_ids.add(content.get('object_id', 0))
    
    print(f"  Found {len(placed_object_ids)} unique object IDs used in web viewer")
    return placed_object_ids


def main():
    """Extract object images for web viewer."""
    print("=" * 60)
    print("  Extracting Object Images for Web Viewer")
    print("=" * 60)
    print()
    
    if not DATA_PATH.exists():
        print(f"Error: Data path does not exist: {DATA_PATH}")
        print("Please ensure game files are in Input/UW1/DATA/")
        sys.exit(1)
    
    # Check for .GR files
    objects_gr = DATA_PATH / "OBJECTS.GR"
    tmobj_gr = DATA_PATH / "TMOBJ.GR"
    
    if not objects_gr.exists() and not tmobj_gr.exists():
        print("Warning: No .GR image files found (OBJECTS.GR or TMOBJ.GR)")
        print("Image extraction will be skipped.")
        print()
        return
    
    print(f"Data folder: {DATA_PATH}")
    print(f"Output folder: {WEB_IMAGES_DIR}")
    print()
    
    try:
        # Pre-scan level data to get placed object IDs
        placed_object_ids = get_placed_object_ids()
        print()
        
        # Clean existing object images before extracting new ones
        if WEB_IMAGES_DIR.exists():
            existing_objects = list(WEB_IMAGES_DIR.glob("object_*.png"))
            if existing_objects:
                print(f"  Cleaning {len(existing_objects)} existing object images...")
                for old_file in existing_objects:
                    try:
                        old_file.unlink()
                    except Exception:
                        pass
        
        image_extractor = ImageExtractor(DATA_PATH)
        
        # Extract object images (filtered to only placed objects)
        if image_extractor.extract():
            image_paths = image_extractor.save_images(WEB_IMAGES_DIR, object_ids_filter=placed_object_ids)
            print()
            print(f"Successfully extracted {len(image_paths)} object images")
            print(f"  Images saved to: {WEB_IMAGES_DIR}")
        else:
            print()
            print("No object images extracted (extraction failed)")
            print("  This may be normal if the .GR file format is not fully supported")
        
    except Exception as e:
        print()
        print(f"Error during image extraction: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print()


if __name__ == "__main__":
    main()
