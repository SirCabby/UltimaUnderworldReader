"""
Level Parser for Ultima Underworld LEV.ARK

Parses the tilemap and master object list for each level.

Level data block layout (31752 bytes = 0x7C08):
- 0x0000-0x3FFF: Tilemap (64x64 tiles, 4 bytes each)
- 0x4000-0x5AFF: Mobile objects (256 entries, 27 bytes each)
- 0x5B00-0x72FF: Static objects (768 entries, 8 bytes each)
- 0x7300-0x74FB: Mobile free list (254 entries, 2 bytes each)
- 0x74FC-0x7AFB: Static free list (768 entries, 2 bytes each)
- 0x7AFC-0x7BFF: Unknown (260 bytes)
- 0x7C00-0x7C01: Unknown word
- 0x7C02-0x7C03: Mobile free list count - 1
- 0x7C04-0x7C05: Static free list count - 1
- 0x7C06-0x7C07: Magic marker 'uw' (0x7775)

Tile format (4 bytes, 2 Int16):
Word 0 (tile properties):
  bits 0-3: Tile type (0-9)
  bits 4-7: Floor height
  bit 8: Unknown (lighting?)
  bit 9: Unused
  bits 10-13: Floor texture index
  bit 14: No magic flag
  bit 15: Door present flag

Word 1 (wall/object):
  bits 0-5: Wall texture index
  bits 6-15: First object index in tile

Object format (8 bytes for static, 27 bytes for mobile):
General object info (8 bytes, 4 Int16):
Word 0 (item_id/flags):
  bits 0-8: Object ID (item_id)
  bits 9-12: Flags
  bit 12: Enchant flag
  bit 13: Door direction
  bit 14: Invisible flag
  bit 15: is_quant flag

Word 1 (position):
  bits 0-6: Z position
  bits 7-9: Heading
  bits 10-12: Y position (0-7 within tile)
  bits 13-15: X position (0-7 within tile)

Word 2 (quality/chain):
  bits 0-5: Quality
  bits 6-15: Next object index

Word 3 (link/special):
  bits 0-5: Owner
  bits 6-15: Quantity/special link

Mobile object extra info (19 bytes after general info):
  - NPC HP, goals, attitudes, home position, etc.
"""

import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from enum import IntEnum

try:
    from .ark_parser import LevArkParser
except ImportError:
    from ark_parser import LevArkParser


class TileType(IntEnum):
    """Tile types in the level map."""
    SOLID = 0           # Wall tile
    OPEN = 1            # Open square tile
    DIAG_SE = 2         # Diagonal, open SE
    DIAG_SW = 3         # Diagonal, open SW
    DIAG_NE = 4         # Diagonal, open NE
    DIAG_NW = 5         # Diagonal, open NW
    SLOPE_N = 6         # Sloping up north
    SLOPE_S = 7         # Sloping up south
    SLOPE_E = 8         # Sloping up east
    SLOPE_W = 9         # Sloping up west


@dataclass
class Tile:
    """A single tile in the level map."""
    x: int
    y: int
    tile_type: TileType
    floor_height: int
    floor_texture: int
    wall_texture: int
    no_magic: bool
    has_door: bool
    first_object_index: int
    
    # Unknown flag (bit 8) - possibly lighting related
    unknown_flag: bool = False


@dataclass 
class GameObject:
    """An object placed in a level."""
    # Object list index
    index: int
    
    # From word 0
    item_id: int           # Object type ID (0-511)
    flags: int             # 4-bit flags
    is_enchanted: bool
    door_dir: bool         # Door direction flag
    is_invisible: bool
    is_quantity: bool      # True if link field is quantity, not link
    
    # From word 1
    z_pos: int             # Height position (0-127)
    heading: int           # Direction (0-7, *45 degrees)
    y_pos: int             # Y position within tile (0-7)
    x_pos: int             # X position within tile (0-7)
    
    # From word 2
    quality: int           # Quality value (0-63)
    next_index: int        # Next object in chain (0-1023)
    
    # From word 3
    owner: int             # Owner/special (0-63)
    quantity_or_link: int  # Quantity (if is_quantity) or special link (0-1023)
    
    # Fields with defaults must come last
    tile_x: int = 0        # Tile X coordinate
    tile_y: int = 0        # Tile Y coordinate
    
    # For mobile objects only (NPCs)
    is_mobile: bool = False
    npc_hp: int = 0
    npc_goal: int = 0
    npc_gtarg: int = 0
    npc_level: int = 0
    npc_talkedto: bool = False
    npc_attitude: int = 0
    npc_xhome: int = 0
    npc_yhome: int = 0
    npc_hunger: int = 0
    npc_whoami: int = 0    # Conversation slot
    mobile_raw: bytes = field(default_factory=bytes)
    
    @property
    def object_class(self) -> int:
        """Get the object class (bits 6-8 of item_id)."""
        return (self.item_id >> 6) & 0x7
    
    @property
    def object_subclass(self) -> int:
        """Get the object subclass (bits 4-5 of item_id)."""
        return (self.item_id >> 4) & 0x3
    
    @property
    def is_npc(self) -> bool:
        """Check if this is an NPC (object IDs 0x40-0x7F)."""
        return 0x40 <= self.item_id <= 0x7F
    
    @property
    def is_container(self) -> bool:
        """Check if this is a container."""
        return 0x80 <= self.item_id <= 0x8F
    
    @property
    def is_door(self) -> bool:
        """Check if this is a door."""
        return 0x140 <= self.item_id <= 0x14F
    
    @property
    def is_trigger(self) -> bool:
        """Check if this is a trigger."""
        return 0x1A0 <= self.item_id <= 0x1BF
    
    @property
    def is_trap(self) -> bool:
        """Check if this is a trap."""
        return 0x180 <= self.item_id <= 0x19F


@dataclass
class Level:
    """A complete level with tilemap and objects."""
    level_num: int
    tiles: List[List[Tile]]          # 64x64 grid
    objects: Dict[int, GameObject]   # Index -> object
    
    @property
    def mobile_objects(self) -> Dict[int, GameObject]:
        """Get only mobile (NPC) objects."""
        return {idx: obj for idx, obj in self.objects.items() 
                if obj.is_mobile}
    
    @property
    def static_objects(self) -> Dict[int, GameObject]:
        """Get only static objects."""
        return {idx: obj for idx, obj in self.objects.items() 
                if not obj.is_mobile}
    
    def get_tile(self, x: int, y: int) -> Optional[Tile]:
        """Get tile at coordinates."""
        if 0 <= x < 64 and 0 <= y < 64:
            return self.tiles[y][x]
        return None
    
    def get_objects_at(self, x: int, y: int) -> List[GameObject]:
        """Get all objects at a tile coordinate."""
        tile = self.get_tile(x, y)
        if not tile or tile.first_object_index == 0:
            return []
        
        result = []
        idx = tile.first_object_index
        visited = set()
        
        while idx != 0 and idx not in visited:
            visited.add(idx)
            if idx in self.objects:
                result.append(self.objects[idx])
                idx = self.objects[idx].next_index
            else:
                break
        
        return result
    
    def get_all_npcs(self) -> List[GameObject]:
        """Get all NPC objects in the level."""
        return [obj for obj in self.objects.values() 
                if obj.is_npc and obj.is_mobile]


class LevelParser:
    """
    Parser for level data from LEV.ARK.
    
    Usage:
        parser = LevelParser("path/to/LEV.ARK")
        parser.parse()
        
        # Get level 0
        level = parser.get_level(0)
        
        # Get all objects in a tile
        objects = level.get_objects_at(32, 32)
        
        # Get all NPCs
        npcs = level.get_all_npcs()
    """
    
    NUM_LEVELS = 9
    TILEMAP_SIZE = 64
    TILEMAP_BYTES = 64 * 64 * 4  # 0x4000
    
    MOBILE_OBJECT_COUNT = 256
    MOBILE_OBJECT_SIZE = 27  # 8 + 19 bytes
    
    STATIC_OBJECT_COUNT = 768
    STATIC_OBJECT_SIZE = 8
    
    # Offsets within level data block
    OFFSET_TILEMAP = 0x0000
    OFFSET_MOBILE = 0x4000
    OFFSET_STATIC = 0x5B00
    
    def __init__(self, filepath: str | Path):
        self.filepath = Path(filepath)
        self.ark_parser = LevArkParser(filepath)
        self.levels: Dict[int, Level] = {}
        self._parsed = False
    
    def parse(self) -> None:
        """Parse all levels from LEV.ARK."""
        self.ark_parser.parse()
        
        for level_num in range(self.NUM_LEVELS):
            data = self.ark_parser.get_level_data(level_num)
            if data:
                self.levels[level_num] = self._parse_level(level_num, data)
        
        self._parsed = True
    
    def _parse_level(self, level_num: int, data: bytes) -> Level:
        """Parse a single level's data block."""
        # Parse tilemap
        tiles = self._parse_tilemap(data)
        
        # Parse objects
        objects = {}
        
        # Parse mobile objects (indices 0-255)
        for i in range(self.MOBILE_OBJECT_COUNT):
            offset = self.OFFSET_MOBILE + i * self.MOBILE_OBJECT_SIZE
            # Check if slot is completely empty (all zeros) before parsing
            words = struct.unpack_from('<4H', data, offset)
            if not all(w == 0 for w in words):  # Only parse non-empty slots
                obj = self._parse_object(i, data, offset, is_mobile=True)
                objects[i] = obj
        
        # Parse static objects (indices 256-1023)
        for i in range(self.STATIC_OBJECT_COUNT):
            idx = i + 256
            offset = self.OFFSET_STATIC + i * self.STATIC_OBJECT_SIZE
            # Check if slot is completely empty (all zeros) before parsing
            words = struct.unpack_from('<4H', data, offset)
            if not all(w == 0 for w in words):  # Only parse non-empty slots
                obj = self._parse_object(idx, data, offset, is_mobile=False)
                objects[idx] = obj
        
        # Set tile coordinates for objects based on their position in tile chains
        self._assign_tile_coords(tiles, objects)
        
        return Level(level_num, tiles, objects)
    
    def _parse_tilemap(self, data: bytes) -> List[List[Tile]]:
        """Parse the 64x64 tilemap."""
        tiles = []
        
        for y in range(self.TILEMAP_SIZE):
            row = []
            for x in range(self.TILEMAP_SIZE):
                offset = self.OFFSET_TILEMAP + (y * self.TILEMAP_SIZE + x) * 4
                word0, word1 = struct.unpack_from('<HH', data, offset)
                
                tile = Tile(
                    x=x,
                    y=y,
                    tile_type=TileType(word0 & 0xF),
                    floor_height=(word0 >> 4) & 0xF,
                    floor_texture=(word0 >> 10) & 0xF,
                    wall_texture=word1 & 0x3F,
                    no_magic=bool(word0 & 0x4000),
                    has_door=bool(word0 & 0x8000),
                    first_object_index=(word1 >> 6) & 0x3FF,
                    unknown_flag=bool(word0 & 0x100)
                )
                row.append(tile)
            tiles.append(row)
        
        return tiles
    
    def _parse_object(self, index: int, data: bytes, offset: int, 
                      is_mobile: bool) -> GameObject:
        """Parse a single object entry."""
        # Read the 4 words of general object info
        words = struct.unpack_from('<4H', data, offset)
        
        word0, word1, word2, word3 = words
        
        obj = GameObject(
            index=index,
            item_id=word0 & 0x1FF,
            flags=(word0 >> 9) & 0xF,
            is_enchanted=bool(word0 & 0x1000),
            door_dir=bool(word0 & 0x2000),
            is_invisible=bool(word0 & 0x4000),
            is_quantity=bool(word0 & 0x8000),
            z_pos=word1 & 0x7F,
            heading=(word1 >> 7) & 0x7,
            y_pos=(word1 >> 10) & 0x7,
            x_pos=(word1 >> 13) & 0x7,
            quality=word2 & 0x3F,
            next_index=(word2 >> 6) & 0x3FF,
            owner=word3 & 0x3F,
            quantity_or_link=(word3 >> 6) & 0x3FF,
            is_mobile=is_mobile
        )
        
        # Parse mobile object extra info if present
        if is_mobile:
            extra_offset = offset + 8
            extra_data = data[extra_offset:extra_offset + 19]
            obj.mobile_raw = extra_data
            
            if len(extra_data) >= 19:
                obj.npc_hp = extra_data[0]
                
                # Word at offset 3-4: goal and gtarg
                goal_word = struct.unpack_from('<H', extra_data, 3)[0]
                obj.npc_goal = goal_word & 0xF
                obj.npc_gtarg = (goal_word >> 4) & 0xFF
                
                # Word at offset 5-6: level, talkedto, attitude
                level_word = struct.unpack_from('<H', extra_data, 5)[0]
                obj.npc_level = level_word & 0xF
                obj.npc_talkedto = bool(level_word & 0x2000)
                obj.npc_attitude = (level_word >> 14) & 0x3
                
                # Word at offset 14-15: home coordinates
                home_word = struct.unpack_from('<H', extra_data, 14)[0]
                obj.npc_yhome = (home_word >> 4) & 0x3F
                obj.npc_xhome = (home_word >> 10) & 0x3F
                
                # Byte at offset 17: hunger
                obj.npc_hunger = extra_data[17] & 0x7F
                
                # Byte at offset 18: npc_whoami (conversation slot)
                obj.npc_whoami = extra_data[18]
        
        return obj
    
    def _assign_tile_coords(self, tiles: List[List[Tile]], 
                           objects: Dict[int, GameObject]) -> None:
        """Walk tile chains to assign tile coordinates to objects."""
        for y, row in enumerate(tiles):
            for x, tile in enumerate(row):
                if tile.first_object_index == 0:
                    continue
                
                idx = tile.first_object_index
                visited = set()
                
                while idx != 0 and idx not in visited:
                    visited.add(idx)
                    if idx in objects:
                        objects[idx].tile_x = x
                        objects[idx].tile_y = y
                        idx = objects[idx].next_index
                    else:
                        break
    
    def get_level(self, level_num: int) -> Optional[Level]:
        """Get a parsed level."""
        if not self._parsed:
            self.parse()
        return self.levels.get(level_num)
    
    def get_all_levels(self) -> Dict[int, Level]:
        """Get all parsed levels."""
        if not self._parsed:
            self.parse()
        return self.levels
    
    def get_all_objects(self) -> List[Tuple[int, GameObject]]:
        """Get all objects from all levels as (level_num, object) pairs."""
        if not self._parsed:
            self.parse()
        
        result = []
        for level_num, level in self.levels.items():
            for obj in level.objects.values():
                result.append((level_num, obj))
        return result
    
    def get_all_npcs(self) -> List[Tuple[int, GameObject]]:
        """Get all NPCs from all levels."""
        return [(lvl, obj) for lvl, obj in self.get_all_objects() 
                if obj.is_npc and obj.is_mobile]
    
    def dump_level_summary(self, level_num: int) -> str:
        """Return a summary of a level."""
        level = self.get_level(level_num)
        if not level:
            return f"Level {level_num} not found"
        
        lines = [
            f"Level {level_num} Summary",
            "=" * 50,
            f"Total objects: {len(level.objects)}",
            f"Mobile objects: {len(level.mobile_objects)}",
            f"Static objects: {len(level.static_objects)}",
            f"NPCs: {len(level.get_all_npcs())}",
            "",
            "Open tile count by type:",
        ]
        
        type_counts = {}
        for row in level.tiles:
            for tile in row:
                tt = tile.tile_type
                type_counts[tt] = type_counts.get(tt, 0) + 1
        
        for tt in TileType:
            lines.append(f"  {tt.name}: {type_counts.get(tt, 0)}")
        
        return '\n'.join(lines)


def main():
    """Test the level parser."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python level_parser.py <path_to_LEV.ARK>")
        sys.exit(1)
    
    parser = LevelParser(sys.argv[1])
    parser.parse()
    
    print(f"Parsed {len(parser.levels)} levels\n")
    
    for level_num in range(9):
        level = parser.get_level(level_num)
        if level:
            print(parser.dump_level_summary(level_num))
            
            # Show first 10 objects
            print("\nFirst 10 objects:")
            for idx, obj in list(level.objects.items())[:10]:
                print(f"  [{idx:4d}] ID=0x{obj.item_id:03X} @ ({obj.tile_x},{obj.tile_y}) "
                      f"z={obj.z_pos} next={obj.next_index}")
            
            # Show NPCs
            npcs = level.get_all_npcs()
            if npcs:
                print(f"\nNPCs ({len(npcs)}):")
                for npc in npcs[:5]:
                    print(f"  [{npc.index:4d}] ID=0x{npc.item_id:02X} HP={npc.npc_hp} "
                          f"conv={npc.npc_whoami} @ ({npc.tile_x},{npc.tile_y})")
            
            print()


if __name__ == '__main__':
    main()

