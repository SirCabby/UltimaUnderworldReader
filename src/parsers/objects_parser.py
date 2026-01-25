"""
Object Properties Parsers for Ultima Underworld

OBJECTS.DAT - Object class-specific properties
Contains tables for different object types:
- Melee weapons (16 entries, 8 bytes each)
- Ranged weapons (16 entries, 3 bytes each)
- Armour/wearables (32 entries, 4 bytes each)
- Critters (64 entries, 48 bytes each)
- Containers (16 entries, 3 bytes each)
- Light sources (16 entries, 2 bytes each)
- Animation objects (16 entries, 4 bytes each)

COMOBJ.DAT - Common object properties for all 512 object types
Contains weight, value, and various flags for each object.
"""

import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from enum import IntEnum, IntFlag


class ObjectClass(IntEnum):
    """Object class categories based on object ID ranges."""
    WEAPONS_MELEE = 0      # 0x00-0x0F
    WEAPONS_RANGED = 1     # 0x10-0x1F
    ARMOUR = 2             # 0x20-0x3F
    MONSTERS = 3           # 0x40-0x7F
    CONTAINERS = 4         # 0x80-0x8F
    LIGHT_SOURCES = 5      # 0x90-0x97
    WANDS = 6              # 0x98-0x9F
    TREASURE = 7           # 0xA0-0xAF
    COMESTIBLES = 8        # 0xB0-0xBF
    SCENERY = 9            # 0xC0-0xDF
    RUNES = 10             # 0xE0-0xFF
    KEYS = 11              # 0x100-0x10F
    QUEST_ITEMS = 12       # 0x110-0x11F
    INVENTORY = 13         # 0x120-0x12F
    BOOKS = 14             # 0x130-0x13F
    DOORS = 15             # 0x140-0x14F
    FURNITURE = 16         # 0x150-0x15F
    PILLARS = 17           # 0x160-0x16F
    SWITCHES = 18          # 0x170-0x17F
    TRAPS = 19             # 0x180-0x19F
    TRIGGERS = 20          # 0x1A0-0x1BF
    ANIMATIONS = 21        # 0x1C0-0x1CF


class WeaponSkillType(IntEnum):
    """Weapon skill types."""
    SWORD = 3
    AXE = 4
    MACE = 5
    UNARMED = 6


class ArmourCategory(IntEnum):
    """Armour category types."""
    SHIELD = 0
    BODY = 1
    LEGGINGS = 3
    GLOVES = 4
    BOOTS = 5
    HAT = 8
    RING = 9


@dataclass
class MeleeWeaponProperties:
    """Properties for a melee weapon."""
    object_id: int
    slash_damage: int
    bash_damage: int
    stab_damage: int
    unknown1: int
    unknown2: int
    unknown3: int
    skill_type: WeaponSkillType
    durability: int


@dataclass
class RangedWeaponProperties:
    """Properties for a ranged weapon."""
    object_id: int
    unknown_flags: int  # bits 9-15: ammo type + 0x10
    durability: int
    
    @property
    def ammo_type(self) -> int:
        """Get the ammunition object ID needed."""
        return ((self.unknown_flags >> 9) & 0x7F) + 0x10


@dataclass
class ArmourProperties:
    """Properties for armour and wearables."""
    object_id: int
    protection: int
    durability: int
    unknown: int
    category: ArmourCategory


@dataclass
class CritterProperties:
    """Properties for a creature/NPC type."""
    object_id: int
    raw_data: bytes  # 48 bytes of creature data
    power: int
    animation_index: int  # Animation index at byte offset 0 (maps to CrXXPAGE.NYY files)
    
    # More fields can be parsed from raw_data as needed


@dataclass
class ContainerProperties:
    """Properties for containers."""
    object_id: int
    capacity: int  # In 0.1 stones
    accepted_type: int  # 0=runes, 1=arrows, 2=scrolls, 3=edibles, 0xFF=any
    num_slots: int
    
    @property
    def capacity_stones(self) -> float:
        """Get capacity in stones."""
        return self.capacity / 10.0
    
    @property
    def accepted_type_name(self) -> str:
        """Get human-readable accepted type."""
        types = {0: 'runes', 1: 'arrows', 2: 'scrolls', 3: 'edibles', 0xFF: 'any'}
        return types.get(self.accepted_type, f'unknown({self.accepted_type})')


@dataclass
class LightSourceProperties:
    """Properties for light sources."""
    object_id: int
    brightness: int  # 0-4, 0 = unlit
    duration: int    # 0 = eternal (e.g., taper of sacrifice)


@dataclass
class AnimationProperties:
    """Properties for animated objects."""
    object_id: int
    unknown1: int
    unknown2: int
    start_frame: int
    num_frames: int


class ObjectsParser:
    """
    Parser for OBJECTS.DAT - class-specific object properties.
    
    Usage:
        parser = ObjectsParser("path/to/OBJECTS.DAT")
        parser.parse()
        
        # Get weapon properties
        sword = parser.get_melee_weapon(5)  # longsword
        
        # Get all containers
        containers = parser.get_all_containers()
    """
    
    # File layout offsets
    OFFSET_HEADER = 0x0000
    OFFSET_MELEE = 0x0002
    OFFSET_RANGED = 0x0082
    OFFSET_ARMOUR = 0x00B2
    OFFSET_CRITTERS = 0x0132
    OFFSET_CONTAINERS = 0x0D32
    OFFSET_LIGHTS = 0x0D62
    OFFSET_UNKNOWN = 0x0D82  # Maybe jewelry?
    OFFSET_ANIMATIONS = 0x0DA2
    
    # Entry counts and sizes
    NUM_MELEE = 16
    NUM_RANGED = 16
    NUM_ARMOUR = 32
    NUM_CRITTERS = 64
    NUM_CONTAINERS = 16
    NUM_LIGHTS = 16
    NUM_ANIMATIONS = 16
    
    SIZE_MELEE = 8
    SIZE_RANGED = 3
    SIZE_ARMOUR = 4
    SIZE_CRITTER = 48
    SIZE_CONTAINER = 3
    SIZE_LIGHT = 2
    SIZE_ANIMATION = 4
    
    def __init__(self, filepath: str | Path):
        self.filepath = Path(filepath)
        self._data: bytes = b''
        self._parsed = False
        
        self.melee_weapons: Dict[int, MeleeWeaponProperties] = {}
        self.ranged_weapons: Dict[int, RangedWeaponProperties] = {}
        self.armour: Dict[int, ArmourProperties] = {}
        self.critters: Dict[int, CritterProperties] = {}
        self.containers: Dict[int, ContainerProperties] = {}
        self.light_sources: Dict[int, LightSourceProperties] = {}
        self.animations: Dict[int, AnimationProperties] = {}
    
    def parse(self) -> None:
        """Parse the OBJECTS.DAT file."""
        with open(self.filepath, 'rb') as f:
            self._data = f.read()
        
        # Parse header (always 0x010F)
        header = struct.unpack_from('<H', self._data, self.OFFSET_HEADER)[0]
        
        # Parse melee weapons
        for i in range(self.NUM_MELEE):
            offset = self.OFFSET_MELEE + i * self.SIZE_MELEE
            data = struct.unpack_from('8B', self._data, offset)
            self.melee_weapons[i] = MeleeWeaponProperties(
                object_id=i,
                slash_damage=data[0],
                bash_damage=data[1],
                stab_damage=data[2],
                unknown1=data[3],
                unknown2=data[4],
                unknown3=data[5],
                skill_type=WeaponSkillType(data[6]) if data[6] in (3, 4, 5, 6) else data[6],
                durability=data[7]
            )
        
        # Parse ranged weapons
        for i in range(self.NUM_RANGED):
            offset = self.OFFSET_RANGED + i * self.SIZE_RANGED
            data = struct.unpack_from('<HB', self._data, offset)
            self.ranged_weapons[i + 0x10] = RangedWeaponProperties(
                object_id=i + 0x10,
                unknown_flags=data[0],
                durability=data[1]
            )
        
        # Parse armour
        for i in range(self.NUM_ARMOUR):
            offset = self.OFFSET_ARMOUR + i * self.SIZE_ARMOUR
            data = struct.unpack_from('4B', self._data, offset)
            cat = data[3]
            self.armour[i + 0x20] = ArmourProperties(
                object_id=i + 0x20,
                protection=data[0],
                durability=data[1],
                unknown=data[2],
                category=ArmourCategory(cat) if cat in (0, 1, 3, 4, 5, 8, 9) else cat
            )
        
        # Parse critters
        for i in range(self.NUM_CRITTERS):
            offset = self.OFFSET_CRITTERS + i * self.SIZE_CRITTER
            raw = self._data[offset:offset + self.SIZE_CRITTER]
            animation_index = raw[0] if len(raw) > 0 else 0  # Byte 0 = animation index
            power = raw[5] if len(raw) > 5 else 0
            self.critters[i + 0x40] = CritterProperties(
                object_id=i + 0x40,
                raw_data=raw,
                power=power,
                animation_index=animation_index
            )
        
        # Parse containers
        for i in range(self.NUM_CONTAINERS):
            offset = self.OFFSET_CONTAINERS + i * self.SIZE_CONTAINER
            data = struct.unpack_from('3B', self._data, offset)
            self.containers[i + 0x80] = ContainerProperties(
                object_id=i + 0x80,
                capacity=data[0],
                accepted_type=data[1],
                num_slots=data[2]
            )
        
        # Parse light sources
        for i in range(self.NUM_LIGHTS):
            offset = self.OFFSET_LIGHTS + i * self.SIZE_LIGHT
            data = struct.unpack_from('2B', self._data, offset)
            self.light_sources[i + 0x90] = LightSourceProperties(
                object_id=i + 0x90,
                brightness=data[0],
                duration=data[1]
            )
        
        # Parse animations
        for i in range(self.NUM_ANIMATIONS):
            offset = self.OFFSET_ANIMATIONS + i * self.SIZE_ANIMATION
            data = struct.unpack_from('4B', self._data, offset)
            self.animations[i + 0x1C0] = AnimationProperties(
                object_id=i + 0x1C0,
                unknown1=data[0],
                unknown2=data[1],
                start_frame=data[2],
                num_frames=data[3]
            )
        
        self._parsed = True
    
    def get_melee_weapon(self, object_id: int) -> Optional[MeleeWeaponProperties]:
        """Get melee weapon properties by object ID."""
        if not self._parsed:
            self.parse()
        return self.melee_weapons.get(object_id)
    
    def get_ranged_weapon(self, object_id: int) -> Optional[RangedWeaponProperties]:
        """Get ranged weapon properties by object ID."""
        if not self._parsed:
            self.parse()
        return self.ranged_weapons.get(object_id)
    
    def get_armour(self, object_id: int) -> Optional[ArmourProperties]:
        """Get armour properties by object ID."""
        if not self._parsed:
            self.parse()
        return self.armour.get(object_id)
    
    def get_critter(self, object_id: int) -> Optional[CritterProperties]:
        """Get critter properties by object ID."""
        if not self._parsed:
            self.parse()
        return self.critters.get(object_id)
    
    def get_container(self, object_id: int) -> Optional[ContainerProperties]:
        """Get container properties by object ID."""
        if not self._parsed:
            self.parse()
        return self.containers.get(object_id)
    
    def get_light_source(self, object_id: int) -> Optional[LightSourceProperties]:
        """Get light source properties by object ID."""
        if not self._parsed:
            self.parse()
        return self.light_sources.get(object_id)
    
    def get_all_melee_weapons(self) -> Dict[int, MeleeWeaponProperties]:
        if not self._parsed:
            self.parse()
        return self.melee_weapons
    
    def get_all_containers(self) -> Dict[int, ContainerProperties]:
        if not self._parsed:
            self.parse()
        return self.containers


# Re-export CommonObjectsParser for backward compatibility
from .common_objects_parser import CommonObjectsParser, CommonObjectProperties, CommonObjectFlags


def main():
    """Test the objects parsers."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python objects_parser.py <OBJECTS.DAT> [COMOBJ.DAT]")
        sys.exit(1)
    
    # Parse OBJECTS.DAT
    parser = ObjectsParser(sys.argv[1])
    parser.parse()
    
    print("OBJECTS.DAT Contents")
    print("=" * 60)
    
    print("\nMelee Weapons:")
    print("-" * 60)
    for obj_id, weapon in parser.melee_weapons.items():
        skill = weapon.skill_type.name if isinstance(weapon.skill_type, WeaponSkillType) else f"Type{weapon.skill_type}"
        print(f"  {obj_id:3d} (0x{obj_id:02X}): Slash={weapon.slash_damage:2d} Bash={weapon.bash_damage:2d} "
              f"Stab={weapon.stab_damage:2d} Skill={skill:8s} Dur={weapon.durability}")
    
    print("\nContainers:")
    print("-" * 60)
    for obj_id, cont in parser.containers.items():
        print(f"  {obj_id:3d} (0x{obj_id:02X}): Capacity={cont.capacity_stones:.1f} stones, "
              f"Accepts={cont.accepted_type_name}, Slots={cont.num_slots}")
    
    print("\nLight Sources:")
    print("-" * 60)
    for obj_id, light in parser.light_sources.items():
        dur = "eternal" if light.duration == 0 else f"{light.duration}"
        print(f"  {obj_id:3d} (0x{obj_id:02X}): Brightness={light.brightness}, Duration={dur}")
    
    # Parse COMOBJ.DAT if provided
    if len(sys.argv) >= 3:
        print("\n" + "=" * 60)
        print("COMOBJ.DAT Contents (first 32 entries)")
        print("=" * 60)
        
        common = CommonObjectsParser(sys.argv[2])
        common.parse()
        
        for obj_id in range(32):
            obj = common.objects.get(obj_id)
            if obj:
                hex_data = ' '.join(f'{b:02X}' for b in obj.raw_data)
                print(f"  {obj_id:3d} (0x{obj_id:02X}): {hex_data}")


if __name__ == '__main__':
    main()


