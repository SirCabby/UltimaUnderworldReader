#!/usr/bin/env python3
"""
Generate clean map images from Ultima Underworld level data.
These maps will have no annotations or text overlays.

Uses TERRAIN.DAT to properly classify water and lava textures
instead of hardcoded texture indices.
"""

import struct
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image, ImageDraw
from src.parsers.level_parser import LevelParser, TileType
from src.parsers.ark_parser import LevArkParser
from src.parsers.terrain_parser import TerrainParser

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

# Ethereal Void (Level 9) color scheme - for the final dimension
# The Ethereal Void has three distinct colored paths leading from the center:
# - Green path: leads to Britannia/victory (textures 43, 44, 45)
# - Red path: wrong way, leads back to start (textures 46, 48)
# - Blue path: third path (texture 49)
# - Main void area uses texture 26
ETHEREAL_COLORS = {
    TileType.SOLID: (15, 10, 25),        # Deep void black
    TileType.OPEN: (35, 30, 50),         # Dark void base
    TileType.DIAG_SE: (30, 25, 45),
    TileType.DIAG_SW: (30, 25, 45),
    TileType.DIAG_NE: (30, 25, 45),
    TileType.DIAG_NW: (30, 25, 45),
    TileType.SLOPE_N: (40, 35, 55),      # Slightly lighter for slopes
    TileType.SLOPE_S: (40, 35, 55),
    TileType.SLOPE_E: (40, 35, 55),
    TileType.SLOPE_W: (40, 35, 55),
    'water': (60, 150, 200),             # Cyan/blue water
    'lava': (200, 80, 180),              # Magenta/purple magic
    'door': (100, 80, 140),
    'edge': (50, 45, 70),                # Edge highlight color
    # Path colors for the three distinct paths
    'path_green': (50, 180, 80),         # Green path (victory)
    'path_red': (180, 60, 60),           # Red path (wrong way)
    'path_blue': (70, 100, 200),         # Blue path
    'void_floor': (35, 30, 50),          # Main void ground
}

# Texture to path mapping for Ethereal Void (Level 9)
# These are the actual F32.TR texture indices used in the level
ETHEREAL_PATH_TEXTURES = {
    # Green path - eastern region, leads to victory
    43: 'path_green',
    44: 'path_green', 
    45: 'path_green',
    # Red path - western region, wrong way
    46: 'path_red',
    48: 'path_red',
    # Blue path - southern region
    49: 'path_blue',
    # Main void floor
    26: 'void_floor',
}


def parse_texture_mapping(data: bytes) -> Dict[str, List[int]]:
    """
    Parse texture mapping data from LEV.ARK.
    
    Format (0x007A bytes):
    - 0x0000: 48 x Int16 wall texture numbers (from W64.TR)
    - 0x0060: 10 x Int16 floor texture numbers (from F32.TR)
    - 0x0074: 6 x Int8 door texture numbers (from DOORS.GR)
    """
    result = {
        'wall': [],
        'floor': [],
        'door': []
    }
    
    if not data or len(data) < 0x7A:
        return result
    
    # Read wall textures (48 entries at offset 0x0000)
    for i in range(48):
        offset = i * 2
        tex_idx = struct.unpack_from('<H', data, offset)[0]
        result['wall'].append(tex_idx)
    
    # Read floor textures (10 entries at offset 0x0060)
    for i in range(10):
        offset = 0x60 + i * 2
        tex_idx = struct.unpack_from('<H', data, offset)[0]
        result['floor'].append(tex_idx)
    
    # Read door textures (6 entries at offset 0x0074)
    for i in range(6):
        offset = 0x74 + i
        tex_idx = data[offset]
        result['door'].append(tex_idx)
    
    return result


class TerrainClassifier:
    """
    Classifies floor tiles as water, lava, or normal based on TERRAIN.DAT.
    """
    
    def __init__(self, terrain_parser: TerrainParser):
        self.terrain_parser = terrain_parser
        # Cache the water and lava texture indices
        self.water_textures = terrain_parser.get_water_floor_textures()
        self.lava_textures = terrain_parser.get_lava_floor_textures()
    
    def get_terrain_type(self, actual_texture_index: int) -> str:
        """
        Get terrain type for an actual F32.TR texture index.
        Returns: 'water', 'lava', or 'normal'
        """
        if actual_texture_index in self.lava_textures:
            return 'lava'
        if actual_texture_index in self.water_textures:
            return 'water'
        return 'normal'


def get_tile_color(tile, texture_mapping: Dict[str, List[int]], 
                   terrain_classifier: TerrainClassifier,
                   is_ethereal: bool = False) -> tuple:
    """Determine the color for a tile based on its properties."""
    color_scheme = ETHEREAL_COLORS if is_ethereal else COLORS
    base_color = color_scheme.get(tile.tile_type, color_scheme[TileType.SOLID])
    
    # Only apply floor textures to non-solid tiles
    if tile.tile_type != TileType.SOLID:
        # Get the actual texture index from the texture mapping
        floor_textures = texture_mapping.get('floor', [])
        tile_tex_idx = tile.floor_texture
        
        # Look up actual texture index (tile_tex_idx is an index into floor_textures)
        if 0 <= tile_tex_idx < len(floor_textures):
            actual_tex_idx = floor_textures[tile_tex_idx]
            
            # For Ethereal Void, check for special path textures first
            if is_ethereal and actual_tex_idx in ETHEREAL_PATH_TEXTURES:
                path_key = ETHEREAL_PATH_TEXTURES[actual_tex_idx]
                base_color = color_scheme[path_key]
                # Apply height-based brightness adjustment to paths
                height_factor = 1.0 + (tile.floor_height - 8) * 0.04
                return tuple(min(255, max(0, int(c * height_factor))) for c in base_color)
            
            # Check for water/lava terrain
            terrain_type = terrain_classifier.get_terrain_type(actual_tex_idx)
            
            if terrain_type == 'water':
                return color_scheme['water']
            elif terrain_type == 'lava':
                return color_scheme['lava']
        
        # Adjust brightness based on floor height for normal floors
        if is_ethereal:
            # Stronger height contrast for ethereal realm
            height_factor = 1.0 + (tile.floor_height - 8) * 0.06
        else:
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


def generate_level_map(level, texture_mapping: Dict[str, List[int]], 
                       terrain_classifier: TerrainClassifier,
                       is_ethereal: bool = False):
    """Generate a map image for a single level."""
    color_scheme = ETHEREAL_COLORS if is_ethereal else COLORS
    
    # Create image with wall color background
    img = Image.new('RGB', (IMAGE_SIZE, IMAGE_SIZE), color_scheme[TileType.SOLID])
    draw = ImageDraw.Draw(img)
    
    # Draw each tile
    # Note: Game coordinates have Y=0 at south (bottom), but image Y=0 is top
    # So we flip Y: image_y = (MAP_SIZE - 1 - game_y)
    for game_y in range(MAP_SIZE):
        for game_x in range(MAP_SIZE):
            tile = level.tiles[game_y][game_x]
            image_y = MAP_SIZE - 1 - game_y  # Flip Y for image coordinates
            
            color = get_tile_color(tile, texture_mapping, terrain_classifier, is_ethereal)
            
            if tile.tile_type == TileType.SOLID:
                # Wall - already filled with background color
                continue
            elif tile.tile_type in {TileType.DIAG_SE, TileType.DIAG_SW, 
                                    TileType.DIAG_NE, TileType.DIAG_NW}:
                # Diagonal tile
                draw_diagonal_tile(draw, game_x, image_y, tile.tile_type, 
                                  color, color_scheme[TileType.SOLID])
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
                              outline=color_scheme['door'], width=1)
    
    # For ethereal realm, add edge highlighting to show elevation changes
    if is_ethereal:
        add_ethereal_edges(draw, level, color_scheme)
    
    return img


def add_ethereal_edges(draw, level, color_scheme):
    """
    Add edge highlighting to the ethereal realm map to show elevation changes.
    This makes the vast open spaces more readable by showing where heights differ.
    """
    edge_color = color_scheme['edge']
    
    for game_y in range(MAP_SIZE):
        for game_x in range(MAP_SIZE):
            tile = level.tiles[game_y][game_x]
            if tile.tile_type == TileType.SOLID:
                continue
            
            image_y = MAP_SIZE - 1 - game_y
            px = game_x * TILE_SIZE
            py = image_y * TILE_SIZE
            
            # Check for height differences with neighbors
            current_height = tile.floor_height
            
            # Check right neighbor
            if game_x < MAP_SIZE - 1:
                right_tile = level.tiles[game_y][game_x + 1]
                if right_tile.tile_type != TileType.SOLID:
                    height_diff = abs(current_height - right_tile.floor_height)
                    if height_diff >= 2:  # Significant height difference
                        draw.line([(px + TILE_SIZE - 1, py), (px + TILE_SIZE - 1, py + TILE_SIZE - 1)], 
                                 fill=edge_color, width=1)
            
            # Check bottom neighbor (remember Y is flipped)
            if game_y > 0:
                bottom_tile = level.tiles[game_y - 1][game_x]
                if bottom_tile.tile_type != TileType.SOLID:
                    height_diff = abs(current_height - bottom_tile.floor_height)
                    if height_diff >= 2:
                        draw.line([(px, py + TILE_SIZE - 1), (px + TILE_SIZE - 1, py + TILE_SIZE - 1)], 
                                 fill=edge_color, width=1)
            
            # Check for transition to solid (walls)
            # Right wall edge
            if game_x < MAP_SIZE - 1:
                right_tile = level.tiles[game_y][game_x + 1]
                if right_tile.tile_type == TileType.SOLID:
                    draw.line([(px + TILE_SIZE - 1, py), (px + TILE_SIZE - 1, py + TILE_SIZE - 1)], 
                             fill=edge_color, width=2)
            
            # Top wall edge (in game coords)
            if game_y < MAP_SIZE - 1:
                top_tile = level.tiles[game_y + 1][game_x]
                if top_tile.tile_type == TileType.SOLID:
                    draw.line([(px, py), (px + TILE_SIZE - 1, py)], 
                             fill=edge_color, width=2)


def main():
    """Generate all level maps."""
    # Find the data path
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    data_dir = project_root / "Input" / "UW1" / "DATA"
    lev_ark_path = data_dir / "LEV.ARK"
    terrain_path = data_dir / "TERRAIN.DAT"
    
    if not lev_ark_path.exists():
        print(f"Error: LEV.ARK not found at {lev_ark_path}")
        print("Please ensure the game data is in Input/UW1/DATA/")
        sys.exit(1)
    
    if not terrain_path.exists():
        print(f"Error: TERRAIN.DAT not found at {terrain_path}")
        print("Please ensure the game data is in Input/UW1/DATA/")
        sys.exit(1)
    
    # Create output directory
    output_dir = script_dir / "maps"
    output_dir.mkdir(exist_ok=True)
    
    # Parse terrain data for water/lava classification
    print(f"Parsing terrain data from {terrain_path}...")
    terrain_parser = TerrainParser(terrain_path)
    terrain_parser.parse()
    terrain_classifier = TerrainClassifier(terrain_parser)
    
    print(f"  Water textures: {sorted(terrain_classifier.water_textures)}")
    print(f"  Lava textures: {sorted(terrain_classifier.lava_textures)}")
    
    # Parse level data
    print(f"Parsing level data from {lev_ark_path}...")
    level_parser = LevelParser(lev_ark_path)
    level_parser.parse()
    
    # Also parse ARK for texture mappings
    ark_parser = LevArkParser(lev_ark_path)
    ark_parser.parse()
    
    print(f"Generating maps for {len(level_parser.levels)} levels...")
    
    for level_num in range(9):
        level = level_parser.get_level(level_num)
        if level:
            # Level 9 (index 8) is the Ethereal Void - use special rendering
            is_ethereal = (level_num == 8)
            level_name = "Ethereal Void" if is_ethereal else f"Level {level_num + 1}"
            print(f"  {level_name}...", end=" ")
            
            # Get texture mapping for this level
            tex_mapping_data = ark_parser.get_texture_mapping(level_num)
            texture_mapping = parse_texture_mapping(tex_mapping_data) if tex_mapping_data else {'floor': [], 'wall': [], 'door': []}
            
            # Debug: show floor texture mapping for this level
            if texture_mapping['floor']:
                print(f"(floor textures: {texture_mapping['floor'][:5]}...)", end=" ")
            
            img = generate_level_map(level, texture_mapping, terrain_classifier, is_ethereal)
            
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
    print("  - Level 9 (Ethereal Void) uses a special ethereal blue theme")


if __name__ == '__main__':
    main()
