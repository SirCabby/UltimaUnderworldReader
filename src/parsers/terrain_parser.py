"""
Terrain Parser for Ultima Underworld TERRAIN.DAT

TERRAIN.DAT contains terrain type flags for floor and wall textures.

Format (UW1):
- File size: 0x0400 bytes (1024 bytes)
- First 256 entries (0x000-0x1FF): Wall texture terrain types
- Next 256 entries (0x200-0x3FF): Floor texture terrain types
- Each entry is a 16-bit word (Int16)

Terrain type flags:
- 0x0000 = Normal (solid) wall or floor
- 0x0002 = Ankh mural (shrines)
- 0x0003 = Stairs up
- 0x0004 = Stairs down
- 0x0005 = Pipe
- 0x0006 = Grating
- 0x0007 = Drain
- 0x0008 = Chained-up princess
- 0x0009 = Window
- 0x000a = Tapestry
- 0x000b = Textured door
- 0x0010 = Water (not waterfall)
- 0x0020 = Lava (not lavafall)
"""

import struct
from dataclasses import dataclass
from enum import IntFlag
from pathlib import Path
from typing import Dict, Optional


class TerrainType(IntFlag):
    """Terrain type flags from TERRAIN.DAT."""
    NORMAL = 0x0000
    ANKH_MURAL = 0x0002
    STAIRS_UP = 0x0003
    STAIRS_DOWN = 0x0004
    PIPE = 0x0005
    GRATING = 0x0006
    DRAIN = 0x0007
    CHAINED_PRINCESS = 0x0008
    WINDOW = 0x0009
    TAPESTRY = 0x000A
    TEXTURED_DOOR = 0x000B
    WATER = 0x0010
    LAVA = 0x0020
    WATERFALL = 0x0040  # Wall texture
    LAVAFALL = 0x0080   # Wall texture


@dataclass
class TerrainData:
    """Terrain data for a single texture."""
    texture_index: int
    raw_value: int
    
    @property
    def is_water(self) -> bool:
        """Check if this terrain is water (bit 0x0010 set)."""
        return bool(self.raw_value & TerrainType.WATER)
    
    @property
    def is_lava(self) -> bool:
        """Check if this terrain is lava (bit 0x0020 set)."""
        return bool(self.raw_value & TerrainType.LAVA)
    
    @property
    def is_waterfall(self) -> bool:
        """Check if this terrain is a waterfall (bit 0x0040 set)."""
        return bool(self.raw_value & TerrainType.WATERFALL)
    
    @property
    def is_lavafall(self) -> bool:
        """Check if this terrain is a lavafall (bit 0x0080 set)."""
        return bool(self.raw_value & TerrainType.LAVAFALL)
    
    @property
    def is_liquid(self) -> bool:
        """Check if this terrain is any liquid (water, lava, or falls)."""
        return self.is_water or self.is_lava or self.is_waterfall or self.is_lavafall
    
    @property
    def terrain_name(self) -> str:
        """Get a human-readable name for this terrain type."""
        if self.is_lava or self.is_lavafall:
            return "lava"
        if self.is_water or self.is_waterfall:
            return "water"
        # Check for special terrain types
        special_types = {
            0x0002: "ankh_mural",
            0x0003: "stairs_up",
            0x0004: "stairs_down",
            0x0005: "pipe",
            0x0006: "grating",
            0x0007: "drain",
            0x0008: "chained_princess",
            0x0009: "window",
            0x000A: "tapestry",
            0x000B: "textured_door",
        }
        return special_types.get(self.raw_value, "normal")


class TerrainParser:
    """
    Parser for TERRAIN.DAT terrain type data.
    
    Usage:
        parser = TerrainParser("path/to/TERRAIN.DAT")
        parser.parse()
        
        # Check if floor texture 8 is water
        if parser.is_floor_water(8):
            print("Texture 8 is water")
        
        # Check if floor texture 14 is lava
        if parser.is_floor_lava(14):
            print("Texture 14 is lava")
        
        # Get terrain type for a floor texture
        terrain = parser.get_floor_terrain(5)
        print(f"Texture 5: {terrain.terrain_name}")
    """
    
    NUM_WALL_TEXTURES = 256
    NUM_FLOOR_TEXTURES = 256
    FLOOR_OFFSET = 0x200  # Floor data starts at offset 512
    
    def __init__(self, filepath: str | Path):
        self.filepath = Path(filepath)
        self.wall_terrain: Dict[int, TerrainData] = {}
        self.floor_terrain: Dict[int, TerrainData] = {}
        self._parsed = False
    
    def parse(self) -> None:
        """Parse the TERRAIN.DAT file."""
        with open(self.filepath, 'rb') as f:
            data = f.read()
        
        # Parse wall textures (first 256 entries)
        for i in range(self.NUM_WALL_TEXTURES):
            offset = i * 2
            if offset + 2 <= len(data):
                value = struct.unpack_from('<H', data, offset)[0]
                self.wall_terrain[i] = TerrainData(
                    texture_index=i,
                    raw_value=value
                )
        
        # Parse floor textures (next 256 entries, starting at offset 0x200)
        for i in range(self.NUM_FLOOR_TEXTURES):
            offset = self.FLOOR_OFFSET + i * 2
            if offset + 2 <= len(data):
                value = struct.unpack_from('<H', data, offset)[0]
                self.floor_terrain[i] = TerrainData(
                    texture_index=i,
                    raw_value=value
                )
        
        self._parsed = True
    
    def get_floor_terrain(self, texture_index: int) -> Optional[TerrainData]:
        """Get terrain data for a floor texture index."""
        if not self._parsed:
            self.parse()
        return self.floor_terrain.get(texture_index)
    
    def get_wall_terrain(self, texture_index: int) -> Optional[TerrainData]:
        """Get terrain data for a wall texture index."""
        if not self._parsed:
            self.parse()
        return self.wall_terrain.get(texture_index)
    
    def is_floor_water(self, texture_index: int) -> bool:
        """Check if a floor texture is water."""
        terrain = self.get_floor_terrain(texture_index)
        return terrain.is_water if terrain else False
    
    def is_floor_lava(self, texture_index: int) -> bool:
        """Check if a floor texture is lava."""
        terrain = self.get_floor_terrain(texture_index)
        return terrain.is_lava if terrain else False
    
    def get_water_floor_textures(self) -> set:
        """Get all floor texture indices that are water."""
        if not self._parsed:
            self.parse()
        return {idx for idx, terrain in self.floor_terrain.items() 
                if terrain.is_water}
    
    def get_lava_floor_textures(self) -> set:
        """Get all floor texture indices that are lava."""
        if not self._parsed:
            self.parse()
        return {idx for idx, terrain in self.floor_terrain.items() 
                if terrain.is_lava}
    
    def dump_terrain_info(self) -> str:
        """Return a summary of terrain types found."""
        if not self._parsed:
            self.parse()
        
        lines = [
            "TERRAIN.DAT Summary",
            "=" * 50,
            "",
            "Floor textures with special terrain:",
        ]
        
        for idx, terrain in sorted(self.floor_terrain.items()):
            if terrain.raw_value != 0:
                lines.append(f"  Floor {idx:3d}: 0x{terrain.raw_value:04X} ({terrain.terrain_name})")
        
        lines.append("")
        lines.append("Wall textures with special terrain:")
        
        for idx, terrain in sorted(self.wall_terrain.items()):
            if terrain.raw_value != 0:
                lines.append(f"  Wall  {idx:3d}: 0x{terrain.raw_value:04X} ({terrain.terrain_name})")
        
        return '\n'.join(lines)


def main():
    """Test the terrain parser."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python terrain_parser.py <path_to_TERRAIN.DAT>")
        sys.exit(1)
    
    parser = TerrainParser(sys.argv[1])
    parser.parse()
    
    print(parser.dump_terrain_info())
    
    print("\n" + "=" * 50)
    print("Water floor textures:", sorted(parser.get_water_floor_textures()))
    print("Lava floor textures:", sorted(parser.get_lava_floor_textures()))


if __name__ == '__main__':
    main()

