"""
Secret Finder for Ultima Underworld

Analyzes game data to find:
- Hidden triggers and traps
- Secret doors
- Hidden objects (invisible items)
- Unreachable areas
- Easter eggs

Trap/Trigger System Overview:
- TRIGGERS (0x1A0-0x1BF) detect player actions and link to traps
- TRAPS (0x180-0x19F) execute game effects

Key trap types:
- damage_trap (0x180): Deals damage, quality = damage amount
- teleport_trap (0x181): Teleports player, quality=dest_x, owner=dest_y
- change_terrain_trap (0x185): Modifies terrain (illusory walls)

Key trigger types:
- move_trigger (0x1A0): Activates when player enters tile
- use_trigger (0x1A2): Activates when object is used
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from ..parsers.strings_parser import StringsParser
from ..parsers.level_parser import LevelParser, TileType
from ..utils import parse_item_name
from ..constants.traps import (
    is_trap, is_trigger,
    get_trap_name, get_trigger_name,
    get_trap_info, get_trigger_info,
    get_trap_purpose, TrapPurpose,
    describe_teleport, describe_damage, describe_change_terrain,
    describe_trap_effect,
    is_level_transition_teleport,
    TRAP_ID_MIN, TRAP_ID_MAX,
    TRIGGER_ID_MIN, TRIGGER_ID_MAX,
)


@dataclass
class Secret:
    """Information about a found secret."""
    secret_type: str      # "trigger", "trap", "hidden_door", "invisible", etc.
    level: int
    tile_x: int
    tile_y: int
    description: str
    object_id: int = 0
    details: Dict[str, Any] = field(default_factory=dict)
    
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
    
    # Trap object ID ranges (using constants module)
    TRAP_IDS = range(TRAP_ID_MIN, TRAP_ID_MAX + 1)
    TRIGGER_IDS = range(TRIGGER_ID_MIN, TRIGGER_ID_MAX + 1)
    
    # Secret door ID
    SECRET_DOOR_ID = 0x147
    
    # Specific trap types for special handling
    DAMAGE_TRAP_ID = 0x180
    TELEPORT_TRAP_ID = 0x181
    CHANGE_TERRAIN_TRAP_ID = 0x185
    
    # Move trigger ID for level transitions
    MOVE_TRIGGER_ID = 0x1A0
    
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
        """Find all trigger objects with detailed effect analysis."""
        object_names = self.strings.get_block(StringsParser.BLOCK_OBJECT_NAMES) or []
        
        for idx, obj in level.objects.items():
            if not is_trigger(obj.item_id):
                continue
                
            name = ""
            if obj.item_id < len(object_names):
                raw = object_names[obj.item_id]
                name, _, _ = parse_item_name(raw)
            
            trigger_type = get_trigger_name(obj.item_id)
            trigger_info = get_trigger_info(obj.item_id)
            
            # Get the link target to understand what this trigger does
            # For triggers, quantity_or_link ALWAYS contains the trap link,
            # regardless of the is_quantity flag
            special_link = obj.quantity_or_link
            target_obj = level.objects.get(special_link) if special_link > 0 else None
            
            # Determine the effect of this trigger
            effect_description = ""
            effect_type = "unknown"
            linked_trap_name = ""
            
            if target_obj and is_trap(target_obj.item_id):
                # Trigger links to a trap - describe the trap and its effect
                trap_purpose = get_trap_purpose(target_obj.item_id)
                linked_trap_name = get_trap_name(target_obj.item_id)
                
                # Get the detailed effect description
                effect_description = describe_trap_effect(
                    target_obj.item_id,
                    target_obj.quality,
                    target_obj.owner,
                    target_obj.z_pos,
                    target_obj.tile_x,
                    target_obj.tile_y,
                    level_num
                )
                effect_type = trap_purpose
                
                # Special case for teleport - check if level transition
                if target_obj.item_id == self.TELEPORT_TRAP_ID:
                    trap_x = target_obj.tile_x if target_obj.tile_x > 0 else obj.tile_x
                    trap_y = target_obj.tile_y if target_obj.tile_y > 0 else obj.tile_y
                    if is_level_transition_teleport(
                        target_obj.quality, target_obj.owner,
                        trap_x, trap_y,
                        target_obj.z_pos, level_num
                    ):
                        effect_type = "level_transition"
                    else:
                        effect_type = "teleport"
                        
            elif special_link == 0:
                # Link is 0 - for move_trigger, quality/owner may encode destination
                if obj.item_id == self.MOVE_TRIGGER_ID:
                    effect_description = f"Move to ({obj.quality}, {obj.owner})"
                    effect_type = "movement"
            
            # Build description - show trigger type, linked trap, and effect
            full_description = f"{trigger_type}"
            if linked_trap_name and effect_description:
                # Show: "move_trigger -> damage_trap: Deals 20 damage"
                full_description += f" -> {linked_trap_name}: {effect_description}"
            elif effect_description:
                full_description += f": {effect_description}"
            elif name:
                full_description += f": {name}"
            
            self.secrets.append(Secret(
                secret_type="trigger",
                level=level_num,
                tile_x=obj.tile_x,
                tile_y=obj.tile_y,
                description=full_description,
                object_id=obj.item_id,
                details={
                    'trigger_type': trigger_type,
                    'linked_trap': linked_trap_name,
                    'effect_type': effect_type,
                    'quality': obj.quality,
                    'owner': obj.owner,
                    'special_link': special_link,
                    'effect_description': effect_description,
                    'target_trap_id': target_obj.item_id if target_obj else None,
                }
            ))
    
    def _find_traps(self, level_num: int, level) -> None:
        """Find all trap objects with detailed effect descriptions."""
        object_names = self.strings.get_block(StringsParser.BLOCK_OBJECT_NAMES) or []
        
        for idx, obj in level.objects.items():
            if not is_trap(obj.item_id):
                continue
                
            name = ""
            if obj.item_id < len(object_names):
                raw = object_names[obj.item_id]
                name, _, _ = parse_item_name(raw)
            
            trap_type = get_trap_name(obj.item_id)
            trap_info = get_trap_info(obj.item_id)
            trap_purpose = get_trap_purpose(obj.item_id)
            
            # Use comprehensive effect description
            effect_description = describe_trap_effect(
                obj.item_id,
                obj.quality,
                obj.owner,
                obj.z_pos,
                obj.tile_x,
                obj.tile_y,
                level_num
            )
            
            # Special handling for teleport traps to classify level transitions vs warps
            if obj.item_id == self.TELEPORT_TRAP_ID:
                if is_level_transition_teleport(
                    obj.quality, obj.owner, obj.tile_x, obj.tile_y,
                    obj.z_pos, level_num
                ):
                    trap_purpose = "level_transition"
                else:
                    trap_purpose = "teleport"
            
            # Build full description
            full_description = trap_type
            if effect_description:
                full_description += f": {effect_description}"
            elif name:
                full_description += f": {name}"
            
            # Determine if this is a direct trap (stepped on) or activated by trigger
            is_direct = self._is_direct_trap(level, idx)
            
            self.secrets.append(Secret(
                secret_type="trap",
                level=level_num,
                tile_x=obj.tile_x,
                tile_y=obj.tile_y,
                description=full_description,
                object_id=obj.item_id,
                details={
                    'trap_type': trap_type,
                    'trap_purpose': trap_purpose,
                    'effect_description': effect_description,
                    'quality': obj.quality,
                    'owner': obj.owner,
                    'z_pos': obj.z_pos,
                    'target_link': obj.quantity_or_link if not obj.is_quantity else 0,
                    'is_direct': is_direct,
                }
            ))
    
    def _is_direct_trap(self, level, trap_index: int) -> bool:
        """Check if a trap is stepped on directly vs activated by a trigger."""
        # Look for any trigger that links to this trap
        for idx, obj in level.objects.items():
            if is_trigger(obj.item_id):
                # For triggers, quantity_or_link ALWAYS contains the trap link
                link = obj.quantity_or_link
                if link == trap_index:
                    return False  # Activated by trigger
        return True  # Direct trap
    
    def _find_secret_doors(self, level_num: int, level) -> None:
        """Find all secret doors."""
        for idx, obj in level.objects.items():
            if obj.item_id == self.SECRET_DOOR_ID:
                # Extract lock information similar to item_extractor
                # A door is locked if:
                # 1. It has a non-zero special_link (pointing to a lock object 0x10F), OR
                # 2. It has a non-zero owner (for template doors at 0,0)
                special_link = obj.quantity_or_link if not obj.is_quantity else 0
                is_locked = special_link != 0 or obj.owner != 0
                
                details = {
                    'quality': obj.quality,
                    'is_locked': is_locked
                }
                
                if is_locked:
                    # The real lock ID is stored in the lock object's quantity field
                    # lock.quantity - 512 = lock_id that matches key.owner
                    lock_id = None
                    lock_quality = None
                    if special_link != 0:
                        lock_obj = level.objects.get(special_link)
                        if lock_obj and lock_obj.item_id == 0x10F:  # Lock object
                            # Lock ID is stored as quantity - 512
                            lock_quantity = lock_obj.quantity_or_link if lock_obj.is_quantity else 0
                            if lock_quantity >= 512:
                                lock_id = lock_quantity - 512
                            lock_quality = lock_obj.quality
                    
                    # Fallback to owner for template doors at (0,0)
                    if lock_id is None and obj.owner != 0:
                        lock_id = obj.owner
                    
                    if lock_id is not None:
                        details['lock_id'] = lock_id
                        details['lock_type'] = 'keyed'  # Needs key with owner=lock_id
                    else:
                        # No lock ID found - might be trigger-opened
                        details['lock_type'] = 'special'
                    
                    # Check if lock is pickable based on lock quality
                    # Quality 40 = pickable, Quality 63 = special/not pickable
                    if lock_quality is not None:
                        details['is_pickable'] = lock_quality == 40
                    else:
                        details['is_pickable'] = False
                
                # Extract door health (secret doors can be broken down)
                # Secret doors use the same health system as regular doors
                raw_quality = int(getattr(obj, "quality", 0))
                # Secret doors are never massive (0x145), so they're always breakable
                door_max = 40
                door_health = max(0, min(door_max, raw_quality))
                details['door_health'] = door_health
                details['door_max_health'] = door_max
                
                # Determine condition based on health
                if door_health <= 0:
                    details['door_condition'] = 'broken'
                elif door_health <= 13:
                    details['door_condition'] = 'badly damaged'
                elif door_health <= 26:
                    details['door_condition'] = 'damaged'
                elif door_health == door_max:
                    details['door_condition'] = 'sturdy'
                else:
                    details['door_condition'] = 'undamaged'
                
                self.secrets.append(Secret(
                    secret_type="secret_door",
                    level=level_num,
                    tile_x=obj.tile_x,
                    tile_y=obj.tile_y,
                    description="Secret door",
                    object_id=obj.item_id,
                    details=details
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
                # For triggers, quantity_or_link ALWAYS contains the trap link
                if obj.quantity_or_link == trap_index:
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
        return get_trigger_name(item_id)
    
    def _get_trap_type(self, item_id: int) -> str:
        """Get the trap type name."""
        return get_trap_name(item_id)
    
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
