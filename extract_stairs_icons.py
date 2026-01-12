#!/usr/bin/env python3
"""
Extract stairs up and down icons from the game screenshot.

Usage:
    # Interactive mode - shows image info
    python extract_stairs_icons.py
    
    # Extract with coordinates
    python extract_stairs_icons.py <stairs_down_x> <stairs_down_y> <stairs_up_x> <stairs_up_y> [tile_size]
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

IMAGE_PATH = Path("Input/hqdefault-1016113285.jpg")
OUTPUT_DIR = Path("web/images/stairs")
TILE_SIZE = 10  # Final output size

def extract_stairs(stairs_down_x, stairs_down_y, stairs_up_x, stairs_up_y, tile_size=10):
    """Extract stairs icons from the screenshot."""
    if not IMAGE_PATH.exists():
        print(f"Error: Image not found: {IMAGE_PATH}")
        return False
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    img = Image.open(IMAGE_PATH)
    width, height = img.size
    
    # Calculate scale factor if screenshot tiles are larger than 10px
    # We'll extract at original size first, then resize
    screenshot_tile_size = tile_size  # Assume tiles in screenshot are this size
    
    # Extract stairs down
    stairs_down_bbox = (
        stairs_down_x,
        stairs_down_y,
        stairs_down_x + screenshot_tile_size,
        stairs_down_y + screenshot_tile_size
    )
    stairs_down = img.crop(stairs_down_bbox)
    
    # Resize to 10x10 if needed
    if screenshot_tile_size != TILE_SIZE:
        stairs_down = stairs_down.resize((TILE_SIZE, TILE_SIZE), Image.Resampling.LANCZOS)
    
    stairs_down_path = OUTPUT_DIR / "stairs_down.png"
    stairs_down.save(stairs_down_path)
    print(f"✓ Extracted stairs down: {stairs_down_path}")
    
    # Extract stairs up
    stairs_up_bbox = (
        stairs_up_x,
        stairs_up_y,
        stairs_up_x + screenshot_tile_size,
        stairs_up_y + screenshot_tile_size
    )
    stairs_up = img.crop(stairs_up_bbox)
    
    # Resize to 10x10 if needed
    if screenshot_tile_size != TILE_SIZE:
        stairs_up = stairs_up.resize((TILE_SIZE, TILE_SIZE), Image.Resampling.LANCZOS)
    
    stairs_up_path = OUTPUT_DIR / "stairs_up.png"
    stairs_up.save(stairs_up_path)
    print(f"✓ Extracted stairs up: {stairs_up_path}")
    
    print(f"\nIcons saved to {OUTPUT_DIR}/")
    print(f"Both icons are {TILE_SIZE}x{TILE_SIZE} pixels (map tile size)")
    
    return True

if __name__ == "__main__":
    img = Image.open(IMAGE_PATH)
    width, height = img.size
    
    if len(sys.argv) >= 5:
        # Extract with provided coordinates
        stairs_down_x = int(sys.argv[1])
        stairs_down_y = int(sys.argv[2])
        stairs_up_x = int(sys.argv[3])
        stairs_up_y = int(sys.argv[4])
        tile_size = int(sys.argv[5]) if len(sys.argv) >= 6 else 10
        
        extract_stairs(stairs_down_x, stairs_down_y, stairs_up_x, stairs_up_y, tile_size)
    else:
        # Show instructions
        print(f"Image: {IMAGE_PATH}")
        print(f"Size: {width}x{height} pixels")
        print("\nTo extract the stairs icons, you need the pixel coordinates.")
        print("\nUsage:")
        print(f"  python extract_stairs_icons.py <down_x> <down_y> <up_x> <up_y> [tile_size]")
        print("\nExample:")
        print("  python extract_stairs_icons.py 150 180 300 180 10")
        print("\nTo find coordinates:")
        print("1. Open the image in an image viewer (Windows Photos, GIMP, etc.)")
        print("2. Hover over the top-left corner of the 'stairs down' tile")
        print("3. Note the X,Y coordinates shown in the status bar")
        print("4. Do the same for 'stairs up' tile")
        print("5. Run the script with those coordinates")
        print("\nThe tile_size parameter is the size of tiles in the screenshot.")
        print("If tiles are 10x10 in the screenshot, use 10 (default).")
        print("If they're larger (e.g., 20x20), specify that size.")
