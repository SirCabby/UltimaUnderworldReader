#!/usr/bin/env python3
"""
Extract object images from Ultima Underworld .GR files for the web viewer.

This script extracts sprite images from OBJECTS.GR or TMOBJ.GR files
and saves them as PNG files to web/images/objects/.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.extractors import ImageExtractor

# Default paths
DATA_PATH = Path("Input/UW1/DATA")
WEB_IMAGES_DIR = Path("web/images/objects")
WEB_NPC_IMAGES_DIR = Path("web/images/npcs")


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
        image_extractor = ImageExtractor(DATA_PATH)
        
        # Extract object images
        if image_extractor.extract():
            image_paths = image_extractor.save_images(WEB_IMAGES_DIR)
            print()
            print(f"Successfully extracted {len(image_paths)} object images")
            print(f"  Images saved to: {WEB_IMAGES_DIR}")
        else:
            print()
            print("No object images extracted (extraction failed)")
            print("  This may be normal if the .GR file format is not fully supported")
        
        # Extract NPC images
        print()
        print("=" * 60)
        print("  Extracting NPC Images for Web Viewer")
        print("=" * 60)
        print()
        
        # Clean existing NPC images before extracting new ones
        if WEB_NPC_IMAGES_DIR.exists():
            existing_npcs = list(WEB_NPC_IMAGES_DIR.glob("npc_*.png"))
            if existing_npcs:
                print(f"  Cleaning {len(existing_npcs)} existing NPC images...")
                for old_file in existing_npcs:
                    try:
                        old_file.unlink()
                    except Exception:
                        pass
        
        if image_extractor.extract_npc_images():
            npc_image_paths = image_extractor.save_npc_images(WEB_NPC_IMAGES_DIR)
            print()
            print(f"Successfully extracted {len(npc_image_paths)} NPC images")
            total_frames = sum(len(frames) for frames in image_extractor.extracted_npc_frames.values()) if hasattr(image_extractor, 'extracted_npc_frames') else len(npc_image_paths)
            frame_files = list(WEB_NPC_IMAGES_DIR.glob("npc_*_frame_*.png")) if WEB_NPC_IMAGES_DIR.exists() else []
            print(f"  Total NPC images saved: {len(npc_image_paths)} main images + {len(frame_files)} additional frames = {len(npc_image_paths) + len(frame_files)} total")
            print(f"  Images saved to: {WEB_NPC_IMAGES_DIR}")
        else:
            print()
            print("No NPC images extracted (extraction failed)")
            print("  This may be normal if animation files are not available or parsing failed")
        
    except Exception as e:
        print()
        print(f"Error during image extraction: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print()


if __name__ == "__main__":
    main()
