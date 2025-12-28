#!/usr/bin/env python3
"""
Generate clean map images from Ultima Underworld level data.
These maps will have no annotations or text overlays.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image, ImageDraw
from src.parsers.level_parser import LevelParser, TileType

# Configuration
TILE_SIZE = 10  # Pixels per tile
MAP_SIZE = 64   # 64x64 tiles
IMAGE_SIZE = TILE_SIZE * MAP_SIZE  # 640x640 pixels

# Color scheme - dungeon theme
COLORS = {
    # Walls and solid areas
    TileType.SOLID: (40, 35, 30),        # Dark brown/gray for walls
    
    # Open/walkable areas  
    TileType.OPEN: (120, 100, 80),       # Tan/brown for floors
    
    # Diagonal walls (half-open tiles)
    TileType.DIAG_SE: (90, 75, 60),      # Slightly darker
    TileType.DIAG_SW: (90, 75, 60),
    TileType.DIAG_NE: (90, 75, 60),
    TileType.DIAG_NW: (90, 75, 60),
    
    # Slopes
    TileType.SLOPE_N: (100, 85, 70),
    TileType.SLOPE_S: (100, 85, 70),
    TileType.SLOPE_E: (100, 85, 70),
    TileType.SLOPE_W: (100, 85, 70),
    
    # Special colors for features
    'water': (60, 80, 140),              # Blue for water
    'lava': (180, 60, 40),               # Red/orange for lava
    'door': (100, 70, 50),               # Brown for doors
}

# Water texture indices (common ones)
WATER_TEXTURES = {8, 9, 10}  # Typical water floor textures
LAVA_TEXTURES = {14, 15}     # Typical lava floor textures


def get_tile_color(tile, level_num):
    """Determine the color for a tile based on its properties."""
    base_color = COLORS.get(tile.tile_type, COLORS[TileType.SOLID])
    
    # Only apply floor textures to non-solid tiles
    if tile.tile_type != TileType.SOLID:
        # Check for water
        if tile.floor_texture in WATER_TEXTURES:
            return COLORS['water']
        
        # Check for lava (more common in deeper levels)
        if tile.floor_texture in LAVA_TEXTURES or (level_num >= 6 and tile.floor_texture in {11, 12, 13, 14, 15}):
            return COLORS['lava']
        
        # Adjust brightness based on floor height
        height_factor = 1.0 + (tile.floor_height - 8) * 0.02
        base_color = tuple(min(255, max(0, int(c * height_factor))) for c in base_color)
    
    return base_color


def draw_diagonal_tile(draw, x, y, tile_type, color, wall_color):
    """Draw a diagonal tile with the open portion filled."""
    px = x * TILE_SIZE
    py = y * TILE_SIZE
    
    # Fill base with wall color
    draw.rectangle([px, py, px + TILE_SIZE - 1, py + TILE_SIZE - 1], fill=wall_color)
    
    # Draw the open (walkable) portion
    if tile_type == TileType.DIAG_SE:
        # Open in south-east: triangle with vertices at (0,0), (SIZE,0), (SIZE,SIZE)
        points = [(px + TILE_SIZE, py), (px + TILE_SIZE, py + TILE_SIZE), (px, py + TILE_SIZE)]
        draw.polygon(points, fill=color)
    elif tile_type == TileType.DIAG_SW:
        # Open in south-west: triangle with vertices at (SIZE,0), (0,0), (0,SIZE)
        points = [(px, py), (px, py + TILE_SIZE), (px + TILE_SIZE, py + TILE_SIZE)]
        draw.polygon(points, fill=color)
    elif tile_type == TileType.DIAG_NE:
        # Open in north-east
        points = [(px, py), (px + TILE_SIZE, py), (px + TILE_SIZE, py + TILE_SIZE)]
        draw.polygon(points, fill=color)
    elif tile_type == TileType.DIAG_NW:
        # Open in north-west
        points = [(px, py), (px + TILE_SIZE, py), (px, py + TILE_SIZE)]
        draw.polygon(points, fill=color)


def generate_level_map(level, level_num):
    """Generate a map image for a single level."""
    # Create image with wall color background
    img = Image.new('RGB', (IMAGE_SIZE, IMAGE_SIZE), COLORS[TileType.SOLID])
    draw = ImageDraw.Draw(img)
    
    # Draw each tile
    # Note: Game coordinates have Y=0 at south (bottom), but image Y=0 is top
    # So we flip Y: image_y = (MAP_SIZE - 1 - game_y)
    for game_y in range(MAP_SIZE):
        for game_x in range(MAP_SIZE):
            tile = level.tiles[game_y][game_x]
            image_y = MAP_SIZE - 1 - game_y  # Flip Y for image coordinates
            
            color = get_tile_color(tile, level_num)
            
            if tile.tile_type == TileType.SOLID:
                # Wall - already filled with background color
                continue
            elif tile.tile_type in {TileType.DIAG_SE, TileType.DIAG_SW, 
                                    TileType.DIAG_NE, TileType.DIAG_NW}:
                # Diagonal tile
                draw_diagonal_tile(draw, game_x, image_y, tile.tile_type, 
                                  color, COLORS[TileType.SOLID])
            else:
                # Regular open or slope tile
                px = game_x * TILE_SIZE
                py = image_y * TILE_SIZE
                draw.rectangle([px, py, px + TILE_SIZE - 1, py + TILE_SIZE - 1], fill=color)
            
            # Add subtle door indicator if present
            if tile.has_door:
                px = game_x * TILE_SIZE
                py = image_y * TILE_SIZE
                # Draw a small marker
                draw.rectangle([px + 3, py + 3, px + TILE_SIZE - 4, py + TILE_SIZE - 4], 
                              outline=COLORS['door'], width=1)
    
    return img


def main():
    """Generate all level maps."""
    # Find the data path
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    data_path = project_root / "Input" / "UW1" / "DATA" / "LEV.ARK"
    
    if not data_path.exists():
        print(f"Error: LEV.ARK not found at {data_path}")
        print("Please ensure the game data is in Input/UW1/DATA/")
        sys.exit(1)
    
    # Create output directory
    output_dir = script_dir / "maps"
    output_dir.mkdir(exist_ok=True)
    
    print(f"Parsing level data from {data_path}...")
    parser = LevelParser(data_path)
    parser.parse()
    
    print(f"Generating maps for {len(parser.levels)} levels...")
    
    for level_num in range(9):
        level = parser.get_level(level_num)
        if level:
            print(f"  Level {level_num + 1}...", end=" ")
            img = generate_level_map(level, level_num)
            
            # Save as PNG for better quality
            output_path = output_dir / f"level{level_num + 1}.png"
            img.save(output_path, 'PNG')
            print(f"saved to {output_path}")
    
    print("\nDone! Clean maps generated.")
    print("Note: These maps use the following color scheme:")
    print("  - Dark brown/gray: Walls")
    print("  - Tan/brown: Walkable floors")
    print("  - Blue: Water")
    print("  - Red/orange: Lava")


if __name__ == '__main__':
    main()

