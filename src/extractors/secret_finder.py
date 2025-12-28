"""
Secret Finder for Ultima Underworld

Analyzes game data to find:
- Hidden triggers and traps
- Secret doors
- Hidden objects (invisible items)
- Unreachable areas
- Easter eggs
"""

from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass

from ..parsers.strings_parser import StringsParser
from ..parsers.level_parser import LevelParser, TileType
from ..utils import parse_item_name


@dataclass
class Secret:
    """Information about a found secret."""
    secret_type: str      # "trigger", "trap", "hidden_door", "invisible", etc.
    level: int
    tile_x: int
    tile_y: int
    description: str
    object_id: int = 0
    details: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.secret_type,
            'level': self.level,
            'position': {'x': self.tile_x, 'y': self.tile_y},
            'description': self.description,
            'object_id': self.object_id,
            'details': self.details or {}
        }


class SecretFinder:
    """
    Finds secrets and hidden content in Ultima Underworld.
    
    Usage:
        finder = SecretFinder("path/to/DATA")
        finder.analyze()
        
        secrets = finder.get_all_secrets()
    """
    
    # Trap object ID ranges
    TRAP_IDS = range(0x180, 0x1A0)
    TRIGGER_IDS = range(0x1A0, 0x1C0)
    
    # Secret door ID
    SECRET_DOOR_ID = 0x147
    
    # Change terrain trap ID (used for illusory walls)
    CHANGE_TERRAIN_TRAP_ID = 0x185
    
    def __init__(self, data_path: str | Path):
        self.data_path = Path(data_path)
        
        # Initialize parsers
        self.strings = StringsParser(self.data_path / "STRINGS.PAK")
        self.levels = LevelParser(self.data_path / "LEV.ARK")
        
        # Found secrets
        self.secrets: List[Secret] = []
        
        self._analyzed = False
    
    def analyze(self) -> None:
        """Analyze all levels for secrets."""
        self.strings.parse()
        self.levels.parse()
        
        for level_num in range(9):
            level = self.levels.get_level(level_num)
            if not level:
                continue
            
            self._find_triggers(level_num, level)
            self._find_traps(level_num, level)
            self._find_secret_doors(level_num, level)
            self._find_illusory_walls(level_num, level)
            self._find_invisible_objects(level_num, level)
            self._find_interesting_tiles(level_num, level)
        
        self._analyzed = True
    
    def _find_triggers(self, level_num: int, level) -> None:
        """Find all trigger objects."""
        object_names = self.strings.get_block(StringsParser.BLOCK_OBJECT_NAMES) or []
        
        for idx, obj in level.objects.items():
            if obj.item_id in self.TRIGGER_IDS:
                name = ""
                if obj.item_id < len(object_names):
                    raw = object_names[obj.item_id]
                    name, _, _ = parse_item_name(raw)
                
                trigger_type = self._get_trigger_type(obj.item_id)
                
                self.secrets.append(Secret(
                    secret_type="trigger",
                    level=level_num,
                    tile_x=obj.tile_x,
                    tile_y=obj.tile_y,
                    description=f"{trigger_type}: {name}",
                    object_id=obj.item_id,
                    details={
                        'trigger_type': trigger_type,
                        'quality': obj.quality,
                        'owner': obj.owner,
                        'special_link': obj.quantity_or_link if not obj.is_quantity else 0
                    }
                ))
    
    def _find_traps(self, level_num: int, level) -> None:
        """Find all trap objects."""
        object_names = self.strings.get_block(StringsParser.BLOCK_OBJECT_NAMES) or []
        
        for idx, obj in level.objects.items():
            if obj.item_id in self.TRAP_IDS:
                name = ""
                if obj.item_id < len(object_names):
                    raw = object_names[obj.item_id]
                    name, _, _ = parse_item_name(raw)
                
                trap_type = self._get_trap_type(obj.item_id)
                
                self.secrets.append(Secret(
                    secret_type="trap",
                    level=level_num,
                    tile_x=obj.tile_x,
                    tile_y=obj.tile_y,
                    description=f"{trap_type}: {name}",
                    object_id=obj.item_id,
                    details={
                        'trap_type': trap_type,
                        'quality': obj.quality,
                        'owner': obj.owner,
                        'target_link': obj.quantity_or_link if not obj.is_quantity else 0
                    }
                ))
    
    def _find_secret_doors(self, level_num: int, level) -> None:
        """Find all secret doors."""
        for idx, obj in level.objects.items():
            if obj.item_id == self.SECRET_DOOR_ID:
                self.secrets.append(Secret(
                    secret_type="secret_door",
                    level=level_num,
                    tile_x=obj.tile_x,
                    tile_y=obj.tile_y,
                    description="Secret door",
                    object_id=obj.item_id,
                    details={
                        'quality': obj.quality,
                        'is_locked': obj.quantity_or_link != 0 if not obj.is_quantity else False
                    }
                ))
    
    def _find_illusory_walls(self, level_num: int, level) -> None:
        """
        Find illusory walls - solid tiles that can be revealed.
        
        These are implemented as change_terrain_trap (0x185) objects placed on
        SOLID tiles. When triggered (by Reveal spell or triggers), the tile
        changes from SOLID to OPEN (or another passable type), allowing passage.
        
        The trap's quality field encodes the new tile properties:
        - bits 0-3: new floor height
        - bits 4-7: new tile type (1 = OPEN, etc.)
        
        The trap's owner field typically contains the new wall texture (63 = unchanged).
        
        Note: Traps that keep tiles as SOLID (new_type=0) are included as
        "terrain_modifier" since they modify wall height/texture, not reveal passages.
        """
        tile_type_names = {
            0: "SOLID",
            1: "OPEN",
            2: "DIAG_SE",
            3: "DIAG_SW",
            4: "DIAG_NE",
            5: "DIAG_NW",
            6: "SLOPE_N",
            7: "SLOPE_S",
            8: "SLOPE_E",
            9: "SLOPE_W",
        }
        
        for idx, obj in level.objects.items():
            if obj.item_id == self.CHANGE_TERRAIN_TRAP_ID:
                # Skip placeholder objects at (0, 0)
                if obj.tile_x == 0 and obj.tile_y == 0:
                    continue
                    
                # Check if the trap is on a SOLID tile
                tile = level.get_tile(obj.tile_x, obj.tile_y)
                if tile and tile.tile_type == TileType.SOLID:
                    new_tile_type = (obj.quality >> 4) & 0xF
                    new_floor_height = obj.quality & 0xF
                    new_type_name = tile_type_names.get(new_tile_type, f"type_{new_tile_type}")
                    
                    # Determine what triggers this wall
                    trigger_info = self._find_trigger_for_trap(level, idx)
                    
                    # Classify based on whether it reveals a passage or just modifies terrain
                    if new_tile_type == 0:
                        # SOLID -> SOLID: terrain modifier (changes height/texture)
                        secret_type = "terrain_modifier"
                        description = f"Terrain modifier (height {tile.floor_height}->{new_floor_height})"
                    else:
                        # SOLID -> passable type: illusory wall
                        secret_type = "illusory_wall"
                        description = f"Illusory wall -> {new_type_name}"
                    
                    if trigger_info:
                        description += f" ({trigger_info})"
                    
                    self.secrets.append(Secret(
                        secret_type=secret_type,
                        level=level_num,
                        tile_x=obj.tile_x,
                        tile_y=obj.tile_y,
                        description=description,
                        object_id=obj.item_id,
                        details={
                            'current_type': 'SOLID',
                            'current_height': tile.floor_height,
                            'new_type': new_type_name,
                            'new_floor_height': new_floor_height,
                            'new_wall_texture': obj.owner,
                            'trap_index': idx,
                            'trigger': trigger_info,
                            'z_pos': obj.z_pos,
                            'special_link': obj.quantity_or_link if not obj.is_quantity else 0
                        }
                    ))
    
    def _find_trigger_for_trap(self, level, trap_index: int) -> str:
        """Find what trigger activates a trap and return a description."""
        trigger_types = {
            0x1A0: "move",
            0x1A1: "pick_up",
            0x1A2: "use",
            0x1A3: "look",
            0x1A4: "step_on",
            0x1A5: "open",
            0x1A6: "unlock",
            0x1A7: "timer",
            0x1A8: "scheduled",
        }
        
        # Look for triggers that link to this trap
        for idx, obj in level.objects.items():
            if obj.item_id in self.TRIGGER_IDS:
                # Check if this trigger links to our trap
                if not obj.is_quantity and obj.quantity_or_link == trap_index:
                    trigger_name = trigger_types.get(obj.item_id, f"trigger_0x{obj.item_id:03X}")
                    return f"{trigger_name} trigger at ({obj.tile_x}, {obj.tile_y})"
        
        # No direct trigger found - wall can likely be revealed by Reveal spell
        return "Reveal spell"
    
    def _find_invisible_objects(self, level_num: int, level) -> None:
        """Find all invisible objects."""
        object_names = self.strings.get_block(StringsParser.BLOCK_OBJECT_NAMES) or []
        
        for idx, obj in level.objects.items():
            if obj.is_invisible:
                name = ""
                if obj.item_id < len(object_names):
                    raw = object_names[obj.item_id]
                    name, _, _ = parse_item_name(raw)
                
                self.secrets.append(Secret(
                    secret_type="invisible",
                    level=level_num,
                    tile_x=obj.tile_x,
                    tile_y=obj.tile_y,
                    description=f"Invisible: {name}",
                    object_id=obj.item_id,
                    details={
                        'quality': obj.quality
                    }
                ))
    
    def _find_interesting_tiles(self, level_num: int, level) -> None:
        """Find tiles with interesting properties."""
        # Look for tiles marked as no-magic zones
        for y, row in enumerate(level.tiles):
            for x, tile in enumerate(row):
                if tile.no_magic and tile.tile_type != TileType.SOLID:
                    self.secrets.append(Secret(
                        secret_type="no_magic_zone",
                        level=level_num,
                        tile_x=x,
                        tile_y=y,
                        description="No-magic zone",
                        details={
                            'tile_type': tile.tile_type.name,
                            'floor_height': tile.floor_height
                        }
                    ))
    
    def _get_trigger_type(self, item_id: int) -> str:
        """Get the trigger type name."""
        trigger_types = {
            0x1A0: "move_trigger",
            0x1A1: "pick_up_trigger",
            0x1A2: "use_trigger",
            0x1A3: "look_trigger",
            0x1A4: "step_on_trigger",
            0x1A5: "open_trigger",
            0x1A6: "unlock_trigger",
            0x1A7: "timer_trigger",
            0x1A8: "scheduled_trigger",
        }
        return trigger_types.get(item_id, f"trigger_0x{item_id:03X}")
    
    def _get_trap_type(self, item_id: int) -> str:
        """Get the trap type name."""
        trap_types = {
            0x180: "damage_trap",
            0x181: "teleport_trap",
            0x182: "arrow_trap",
            0x183: "do_trap",
            0x184: "pit_trap",
            0x185: "change_terrain_trap",
            0x186: "spell_trap",
            0x187: "create_object_trap",
            0x188: "door_trap",
            0x189: "ward_trap",
            0x18A: "tell_trap",
            0x18B: "delete_object_trap",
            0x18C: "inventory_trap",
            0x18D: "set_variable_trap",
            0x18E: "check_variable_trap",
            0x18F: "combination_trap",
        }
        return trap_types.get(item_id, f"trap_0x{item_id:03X}")
    
    def get_all_secrets(self) -> List[Secret]:
        """Get all found secrets."""
        if not self._analyzed:
            self.analyze()
        return self.secrets
    
    def get_secrets_by_level(self, level: int) -> List[Secret]:
        """Get secrets on a specific level."""
        if not self._analyzed:
            self.analyze()
        return [s for s in self.secrets if s.level == level]
    
    def get_secrets_by_type(self, secret_type: str) -> List[Secret]:
        """Get secrets of a specific type."""
        if not self._analyzed:
            self.analyze()
        return [s for s in self.secrets if s.secret_type == secret_type]
    
    def get_illusory_walls(self) -> List[Secret]:
        """
        Get all illusory walls that can be revealed.
        
        Returns:
            List of Secret objects representing walls that can be removed
            with the Reveal spell or other triggers.
        """
        return self.get_secrets_by_type("illusory_wall")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of found secrets."""
        if not self._analyzed:
            self.analyze()
        
        by_type = {}
        by_level = {}
        
        for secret in self.secrets:
            by_type[secret.secret_type] = by_type.get(secret.secret_type, 0) + 1
            by_level[secret.level] = by_level.get(secret.level, 0) + 1
        
        return {
            'total': len(self.secrets),
            'by_type': by_type,
            'by_level': by_level
        }


def main():
    """Test the secret finder."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python secret_finder.py <path_to_DATA_folder>")
        sys.exit(1)
    
    finder = SecretFinder(sys.argv[1])
    finder.analyze()
    
    summary = finder.get_summary()
    
    print("Secrets Summary:")
    print("=" * 50)
    print(f"Total secrets found: {summary['total']}")
    
    print("\nBy Type:")
    for stype, count in sorted(summary['by_type'].items()):
        print(f"  {stype}: {count}")
    
    print("\nBy Level:")
    for level in range(9):
        count = summary['by_level'].get(level, 0)
        print(f"  Level {level}: {count}")
    
    # Show some interesting secrets
    print("\nSecret Doors:")
    secret_doors = finder.get_secrets_by_type("secret_door")
    for secret in secret_doors[:10]:
        print(f"  Level {secret.level} @ ({secret.tile_x},{secret.tile_y})")
    
    print("\nTeleport Traps:")
    teleports = [s for s in finder.get_secrets_by_type("trap") 
                 if 'teleport' in s.description.lower()]
    for secret in teleports[:10]:
        print(f"  Level {secret.level} @ ({secret.tile_x},{secret.tile_y})")
    
    print("\nIllusory Walls (Reveal spell targets):")
    illusory_walls = finder.get_illusory_walls()
    for secret in illusory_walls:
        # Display as 1-indexed level for user friendliness
        print(f"  Level {secret.level + 1} @ ({secret.tile_x},{secret.tile_y}): {secret.description}")


if __name__ == '__main__':
    main()
