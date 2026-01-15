"""
Save Game Parser for Ultima Underworld

Parses save game directories (SaveN folders) to extract level data from lev.ark files.
Save game lev.ark files use the same format as the base game LEV.ARK.
"""

from pathlib import Path
from typing import Dict, List, Optional
import tempfile
import shutil

from .level_parser import LevelParser, Level, GameObject
from .strings_parser import StringsParser
from .objects_parser import ObjectsParser, CommonObjectsParser
from ..extractors.item_extractor import ItemExtractor
from ..utils import parse_item_name


class SaveGameParser:
    """
    Parser for Ultima Underworld save game directories.
    
    Usage:
        parser = SaveGameParser("path/to/Save0")
        parser.parse()
        save_data = parser.get_save_data()
    """
    
    def __init__(self, save_directory: str | Path):
        """
        Initialize parser with save game directory path.
        
        Args:
            save_directory: Path to SaveN directory (e.g., "Save0", "Save1")
        """
        self.save_directory = Path(save_directory)
        self.lev_ark_path: Optional[Path] = None
        self.levels: Dict[int, Level] = {}
        self._parsed = False
        
    def find_lev_ark(self) -> Optional[Path]:
        """
        Find lev.ark file in the save directory.
        
        Returns:
            Path to lev.ark file, or None if not found
        """
        # If save_directory is actually a file (lev.ark), return it
        if self.save_directory.is_file() and self.save_directory.name.lower() == 'lev.ark':
            return self.save_directory
        
        # Check for lev.ark (case-insensitive) in directory
        if self.save_directory.is_dir():
            for file_path in self.save_directory.iterdir():
                if file_path.is_file() and file_path.name.lower() == 'lev.ark':
                    return file_path
        
        return None
    
    def parse(self, base_data_path: Optional[str | Path] = None) -> None:
        """
        Parse the save game's lev.ark file.
        
        Args:
            base_data_path: Optional path to base game DATA directory for item names/strings
        """
        # Find lev.ark
        self.lev_ark_path = self.find_lev_ark()
        if not self.lev_ark_path:
            raise FileNotFoundError(
                f"lev.ark not found in save directory: {self.save_directory}"
            )
        
        # Parse level data using existing LevelParser
        level_parser = LevelParser(self.lev_ark_path)
        level_parser.parse()
        self.levels = level_parser.get_all_levels()
        
        self._parsed = True
    
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
    
    def get_save_data_for_web(self, base_data_path: str | Path) -> Dict:
        """
        Convert save game data to web map data format.
        
        This extracts objects in the same format as web_map_data.json,
        but from the save game's lev.ark instead of the base game.
        
        Args:
            base_data_path: Path to base game DATA directory for item names/strings
            
        Returns:
            Dictionary with save game data in web map format
        """
        if not self._parsed:
            self.parse(base_data_path)
        
        # We need item names and properties from base game
        base_data_path = Path(base_data_path)
        strings = StringsParser(base_data_path / "STRINGS.PAK")
        strings.parse()
        object_names = strings.get_block(StringsParser.BLOCK_OBJECT_NAMES) or []
        
        # Load full item type data from base game so we can reuse
        # the same category logic as the main extractor / web exporter.
        # This ensures categories (weapons, armor, keys, stairs, etc.)
        # match the base-game web_map_data.json instead of falling back to "misc".
        item_extractor = ItemExtractor(base_data_path)
        item_extractor.extract()
        item_types = item_extractor.item_types
        
        # Extract objects similar to ItemExtractor
        objects_by_level = {i: [] for i in range(9)}
        npcs_by_level = {i: [] for i in range(9)}
        
        for level_num in range(9):
            level = self.levels.get(level_num)
            if not level:
                continue
            
            # Build set of objects that are actually linked to tiles (excluding tile 0,0)
            # Objects not in tile chains are likely uninitialized/free list entries
            # Also exclude tile (0,0) as it's typically used for templates
            linked_object_indices = set()
            for y, row in enumerate(level.tiles):
                for x, tile in enumerate(row):
                    # Skip tile (0,0) - typically contains templates
                    if x == 0 and y == 0:
                        continue
                    if tile.first_object_index == 0:
                        continue
                    idx = tile.first_object_index
                    visited = set()
                    while idx != 0 and idx not in visited:
                        visited.add(idx)
                        linked_object_indices.add(idx)
                        if idx in level.objects:
                            idx = level.objects[idx].next_index
                        else:
                            break
            
            # Process all objects in the level
            for idx, obj in level.objects.items():
                # Skip empty objects
                if obj.item_id == 0:
                    continue
                
                # Skip objects at origin (0,0) - these are usually templates
                # This matches the behavior of the base game extractor
                if obj.tile_x == 0 and obj.tile_y == 0:
                    continue
                
                # Skip static objects not linked to any tile (uninitialized/free list entries)
                # Mobile objects (NPCs) can be valid even if not explicitly linked to a tile
                # because they can move around, but we already filtered (0,0) above
                if not obj.is_mobile and idx not in linked_object_indices:
                    continue
                
                # Get name
                name = ""
                if obj.item_id < len(object_names):
                    raw_name = object_names[obj.item_id]
                    name, _, _ = parse_item_name(raw_name)
                
                # Override name for dial
                if obj.item_id == 0x161:
                    name = "dial"
                
                # Determine if this is an NPC
                is_npc = obj.is_npc and obj.is_mobile
                
                if is_npc:
                    # Process as NPC
                    npc_data = {
                        'id': idx,
                        'object_id': obj.item_id,
                        'name': name,
                        'creature_type': name,
                        'tile_x': obj.tile_x,
                        'tile_y': obj.tile_y,
                        'z': obj.z_pos,
                        'hp': obj.npc_hp,
                        'level': obj.npc_level,
                        'attitude': 'unknown',  # Would need to decode attitude
                        'has_conversation': obj.npc_whoami > 0,
                        'conversation_slot': obj.npc_whoami,
                    }
                    npcs_by_level[level_num].append(npc_data)
                else:
                    # Process as regular object
                    # Determine quantity
                    quantity = 0
                    if obj.is_quantity:
                        quantity = obj.quantity_or_link
                    
                    # Get category using the same logic as the main extractor.
                    # This keeps save-game categories consistent with the base-game data.
                    item_info = item_types.get(obj.item_id)
                    if item_info:
                        category = item_info.category or "misc"
                    else:
                        category = "misc"
                    
                    obj_data = {
                        'id': idx,
                        'object_id': obj.item_id,
                        'name': name,
                        'tile_x': obj.tile_x,
                        'tile_y': obj.tile_y,
                        'z': obj.z_pos,
                        'category': category,
                        'is_enchanted': obj.is_enchanted,
                        'quality': obj.quality,
                        'owner': obj.owner,
                    }
                    
                    if quantity > 0:
                        obj_data['quantity'] = quantity
                    
                    objects_by_level[level_num].append(obj_data)
        
        # Build web data structure
        return {
            'levels': [
                {
                    'level': i,
                    'name': f"Level {i + 1}",
                    'objects': objects_by_level.get(i, []),
                    'npcs': npcs_by_level.get(i, []),
                }
                for i in range(9)
            ]
        }


def parse_save_directory(save_dir: str | Path, base_data_path: str | Path) -> Dict:
    """
    Convenience function to parse a save directory and return web-formatted data.
    
    Args:
        save_dir: Path to SaveN directory
        base_data_path: Path to base game DATA directory
        
    Returns:
        Dictionary with save game data in web map format
    """
    parser = SaveGameParser(save_dir)
    parser.parse(base_data_path)
    return parser.get_save_data_for_web(base_data_path)
