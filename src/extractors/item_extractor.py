"""
Item Extractor for Ultima Underworld

Extracts complete item database from game files, including:
- All item types with their properties
- All placed items in all levels
"""

from pathlib import Path
from typing import Dict, List, Any

from ..parsers.strings_parser import StringsParser
from ..parsers.objects_parser import ObjectsParser, CommonObjectsParser
from ..parsers.level_parser import LevelParser
from ..models.game_object import ItemInfo, GameObjectInfo
from ..constants import (
    get_category, 
    get_detailed_category,
    get_potion_effect,
    is_special_tmap,
    get_tmap_info,
    is_door,
    is_secret_door,
    is_container,
    STATIC_CONTAINERS,
    CARRYABLE_CONTAINERS,
)
from ..utils import parse_item_name


class ItemExtractor:
    """
    Extracts all item data from Ultima Underworld.
    
    Usage:
        extractor = ItemExtractor("path/to/DATA")
        extractor.extract()
        
        items = extractor.get_all_item_types()
        placed = extractor.get_all_placed_items()
    """
    
    NUM_ITEM_TYPES = 512  # 0x000 - 0x1FF
    
    def __init__(self, data_path: str | Path):
        self.data_path = Path(data_path)
        
        # Initialize parsers
        self.strings = StringsParser(self.data_path / "STRINGS.PAK")
        self.objects = ObjectsParser(self.data_path / "OBJECTS.DAT")
        self.common = CommonObjectsParser(self.data_path / "COMOBJ.DAT")
        self.levels = LevelParser(self.data_path / "LEV.ARK")
        
        # Extracted data
        self.item_types: Dict[int, ItemInfo] = {}
        self.placed_items: List[GameObjectInfo] = []
        
        self._extracted = False
    
    def extract(self) -> None:
        """Extract all item data."""
        # Parse all source files
        self.strings.parse()
        self.objects.parse()
        self.common.parse()
        self.levels.parse()
        
        # Extract item types
        self._extract_item_types()
        
        # Extract placed items from all levels
        self._extract_placed_items()
        
        self._extracted = True
    
    def _extract_item_types(self) -> None:
        """Extract all item type definitions."""
        object_names = self.strings.get_block(StringsParser.BLOCK_OBJECT_NAMES) or []
        
        for item_id in range(self.NUM_ITEM_TYPES):
            # Get name from strings
            raw_name = object_names[item_id] if item_id < len(object_names) else ""
            name, article, plural = parse_item_name(raw_name)
            
            # Override name for dial (0x161) - game strings call it "lever" but it's actually a dial
            if item_id == 0x161:
                name = "dial"
                article = "a"
                plural = "dials"
            
            # Get common properties
            common_props = self.common.get_object(item_id)
            
            # Get class-specific properties
            properties = self._get_class_properties(item_id)
            
            # Get category using detailed category to handle scenery -> useless_item split
            can_be_picked_up = common_props.can_be_picked_up if common_props else False
            category = get_detailed_category(item_id, can_be_picked_up=can_be_picked_up)
            
            info = ItemInfo(
                item_id=item_id,
                name=name,
                name_plural=plural,
                article=article,
                object_class=(item_id >> 6) & 0x7,
                object_subclass=(item_id >> 4) & 0x3,
                category=category,
                properties=properties,
                height=common_props.height if common_props else 0,
                mass=common_props.mass if common_props else 0,  # Mass in 0.1 stones (tenths)
                value=common_props.value if common_props else 0,  # Value in gold pieces (whole)
                flags=common_props.flags if common_props else 0,
                can_be_owned=bool(common_props.raw_data[4] & 0x10) if common_props else False,
                is_enchantable=bool(common_props.flags & 0x02) if common_props else False,
                can_be_picked_up=common_props.can_be_picked_up if common_props else False
            )
            
            self.item_types[item_id] = info
    
    def _get_class_properties(self, item_id: int) -> Dict[str, Any]:
        """Get class-specific properties for an item."""
        props = {}
        
        # Melee weapons
        if item_id <= 0x0F:
            weapon = self.objects.get_melee_weapon(item_id)
            if weapon:
                props = {
                    'type': 'melee_weapon',
                    'slash_damage': weapon.slash_damage,
                    'bash_damage': weapon.bash_damage,
                    'stab_damage': weapon.stab_damage,
                    'skill_type': weapon.skill_type.name if hasattr(weapon.skill_type, 'name') else str(weapon.skill_type),
                    'durability': weapon.durability
                }
        
        # Ranged weapons
        elif 0x10 <= item_id <= 0x1F:
            weapon = self.objects.get_ranged_weapon(item_id)
            if weapon:
                props = {
                    'type': 'ranged_weapon',
                    'durability': weapon.durability,
                    'ammo_type': weapon.ammo_type
                }
        
        # Armor
        elif 0x20 <= item_id <= 0x3F:
            armor = self.objects.get_armour(item_id)
            if armor:
                props = {
                    'type': 'armor',
                    'protection': armor.protection,
                    'durability': armor.durability,
                    'category': armor.category.name if hasattr(armor.category, 'name') else str(armor.category)
                }
        
        # Containers
        elif 0x80 <= item_id <= 0x8F:
            container = self.objects.get_container(item_id)
            if container:
                props = {
                    'type': 'container',
                    'capacity': container.capacity_stones,
                    'accepts': container.accepted_type_name,
                    'slots': container.num_slots
                }
        
        # Light sources
        elif 0x90 <= item_id <= 0x9F:
            light = self.objects.get_light_source(item_id)
            if light:
                props = {
                    'type': 'light_source',
                    'brightness': light.brightness,
                    'duration': 'eternal' if light.duration == 0 else light.duration
                }
        
        return props
    
    def _extract_placed_items(self) -> None:
        """Extract all placed items from all levels."""
        object_names = self.strings.get_block(StringsParser.BLOCK_OBJECT_NAMES) or []
        
        for level_num in range(9):
            level = self.levels.get_level(level_num)
            if not level:
                continue
            
            for idx, obj in level.objects.items():
                # Get name
                name = ""
                if obj.item_id < len(object_names):
                    raw_name = object_names[obj.item_id]
                    name, _, _ = parse_item_name(raw_name)
                
                # Override name for dial (0x161) - game strings call it "lever" but it's actually a dial
                if obj.item_id == 0x161:
                    name = "dial"
                
                # Determine quantity vs special_link
                # For triggers (0x1A0-0x1BF), quantity_or_link ALWAYS contains
                # the link to the trap, regardless of is_quantity flag
                is_trigger = 0x1A0 <= obj.item_id <= 0x1BF
                
                if is_trigger:
                    # Triggers always use quantity_or_link as a link
                    quantity = 0
                    special_link = obj.quantity_or_link
                else:
                    # Normal items follow is_quantity flag
                    quantity = obj.quantity_or_link if obj.is_quantity else 0
                    special_link = obj.quantity_or_link if not obj.is_quantity else 0
                
                # Get base and detailed categories
                base_category = get_category(obj.item_id)
                # Look up can_be_picked_up from item type if available
                can_be_picked_up = False
                if obj.item_id in self.item_types:
                    can_be_picked_up = self.item_types[obj.item_id].can_be_picked_up
                detailed_cat = get_detailed_category(
                    obj.item_id,
                    is_enchanted=obj.is_enchanted,
                    owner=obj.owner,
                    special_link=special_link,
                    can_be_picked_up=can_be_picked_up
                )
                
                # Build extra info for special object types
                extra_info = self._get_extra_info(obj, special_link, level.objects)
                
                # Create object info
                info = GameObjectInfo(
                    object_id=obj.item_id,
                    index=idx,
                    level=level_num,
                    name=name,
                    tile_x=obj.tile_x,
                    tile_y=obj.tile_y,
                    x_pos=obj.x_pos,
                    y_pos=obj.y_pos,
                    z_pos=obj.z_pos,
                    heading=obj.heading,
                    quality=obj.quality,
                    owner=obj.owner,
                    quantity=quantity,
                    flags=obj.flags,
                    is_enchanted=obj.is_enchanted,
                    is_invisible=obj.is_invisible,
                    is_quantity=obj.is_quantity,
                    object_class=base_category,
                    detailed_category=detailed_cat,
                    next_index=obj.next_index,
                    special_link=special_link,
                    extra_info=extra_info
                )
                
                self.placed_items.append(info)
    
    def _get_extra_info(self, obj, special_link: int, level_objects: dict = None) -> dict:
        """
        Get extra information for special object types.
        
        This adds metadata for:
        - Potions: effect type (mana/health)
        - Doors: lock status and lock ID
        - Special tmap objects: texture/level transition info
        - Spell scrolls: spell information
        
        Args:
            obj: The game object
            special_link: The special_link value for this object
            level_objects: Dictionary of all objects on this level (for following links)
        """
        extra = {}
        
        # Potions
        potion_effect = get_potion_effect(obj.item_id)
        if potion_effect:
            extra['effect'] = potion_effect
        
        # Doors
        if is_door(obj.item_id):
            extra['is_secret'] = is_secret_door(obj.item_id)
            # Check if door is open (IDs 0x148-0x14E are open versions)
            extra['is_open'] = 0x148 <= obj.item_id <= 0x14E
            
            # A door is locked if:
            # 1. It has a non-zero special_link (pointing to a lock object 0x10F), OR
            # 2. It has a non-zero owner (for template doors at 0,0)
            if special_link != 0 or obj.owner != 0:
                extra['is_locked'] = True
                
                # The real lock ID is stored in the lock object's quantity field
                # lock.quantity - 512 = lock_id that matches key.owner
                lock_id = None
                lock_quality = None
                if special_link != 0 and level_objects:
                    lock_obj = level_objects.get(special_link)
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
                    extra['lock_id'] = lock_id
                    extra['lock_type'] = 'keyed'  # Needs key with owner=lock_id
                else:
                    # No lock ID found - might be trigger-opened
                    extra['lock_type'] = 'special'
                
                # Check if lock is pickable based on lock quality
                # Quality 40 = pickable, Quality 63 = special/not pickable
                if lock_quality is not None:
                    extra['is_pickable'] = lock_quality == 40
                else:
                    extra['is_pickable'] = False
            else:
                extra['is_locked'] = False
        
        # Containers (chests, barrels, etc.) - check for locks
        # Containers use the same lock mechanism as doors
        if is_container(obj.item_id):
            # A container is locked if it has a non-zero special_link pointing to a lock object (0x10F)
            if special_link != 0 and level_objects:
                lock_obj = level_objects.get(special_link)
                if lock_obj and lock_obj.item_id == 0x10F:  # Lock object
                    extra['is_locked'] = True
                    
                    # The lock ID is stored in the lock object's quantity field
                    # lock.quantity - 512 = lock_id that matches key.owner
                    lock_id = None
                    lock_quality = lock_obj.quality
                    lock_quantity = lock_obj.quantity_or_link if lock_obj.is_quantity else 0
                    
                    if lock_quantity >= 512:
                        lock_id = lock_quantity - 512
                    
                    if lock_id is not None and lock_id > 0:
                        extra['lock_id'] = lock_id
                        extra['lock_type'] = 'keyed'  # Needs key with owner=lock_id
                    else:
                        # No lock ID found - might be trigger-opened or special
                        extra['lock_type'] = 'special'
                    
                    # Check if lock is pickable based on lock quality
                    # Quality 40 = pickable, Quality 63 = special/not pickable
                    extra['is_pickable'] = lock_quality == 40
                else:
                    # special_link points to something else (probably contents), not locked
                    extra['is_locked'] = False
            else:
                # No special_link, container is unlocked
                extra['is_locked'] = False
        
        # Special tmap objects
        if is_special_tmap(obj.item_id):
            tmap_info = get_tmap_info(obj.quality, obj.owner)
            extra.update(tmap_info)
            # Add any link info that might indicate level transitions
            if special_link != 0:
                extra['linked_object'] = special_link
        
        # Spell scrolls (enchanted books/scrolls)
        if obj.is_enchanted and 0x130 <= obj.item_id <= 0x13F:
            # For enchanted scrolls, quantity contains spell info
            # Spell index is quantity - 512 when is_quantity is True
            if obj.is_quantity and obj.quantity_or_link >= 512:
                spell_index = obj.quantity_or_link - 512
                extra['spell_index'] = spell_index
            elif obj.quantity_or_link >= 256 and obj.quantity_or_link < 512:
                # Direct spell reference (256-319 range)
                extra['spell_index'] = obj.quantity_or_link - 256
        
        # Wands - they link to spell objects
        if 0x098 <= obj.item_id <= 0x09B:
            if special_link != 0:
                extra['spell_link'] = special_link
        
        return extra
    
    def get_all_item_types(self) -> Dict[int, ItemInfo]:
        """Get all item type definitions."""
        if not self._extracted:
            self.extract()
        return self.item_types
    
    def get_all_placed_items(self) -> List[GameObjectInfo]:
        """Get all placed items from all levels."""
        if not self._extracted:
            self.extract()
        return self.placed_items
    
    def get_items_by_category(self, category: str) -> List[ItemInfo]:
        """Get all item types of a specific category."""
        if not self._extracted:
            self.extract()
        return [item for item in self.item_types.values() 
                if item.category == category]
    
    def get_placed_items_by_level(self, level: int) -> List[GameObjectInfo]:
        """Get all placed items on a specific level."""
        if not self._extracted:
            self.extract()
        return [item for item in self.placed_items if item.level == level]
    
    def get_items_summary(self) -> Dict[str, int]:
        """Get a summary of item counts by category."""
        if not self._extracted:
            self.extract()
        
        summary = {}
        for item in self.item_types.values():
            cat = item.category
            summary[cat] = summary.get(cat, 0) + 1
        
        return summary


def main():
    """Test the item extractor."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python item_extractor.py <path_to_DATA_folder>")
        sys.exit(1)
    
    extractor = ItemExtractor(sys.argv[1])
    extractor.extract()
    
    print("Item Types Summary:")
    print("=" * 50)
    for category, count in sorted(extractor.get_items_summary().items()):
        print(f"  {category}: {count}")
    
    print(f"\nTotal item types: {len(extractor.item_types)}")
    print(f"Total placed items: {len(extractor.placed_items)}")
    
    # Show some examples
    print("\nFirst 10 item types:")
    for item_id in range(10):
        item = extractor.item_types.get(item_id)
        if item:
            print(f"  {item_id:3d}: {item.article} {item.name}")
    
    # Show placed items per level
    print("\nPlaced items per level:")
    for level in range(9):
        items = extractor.get_placed_items_by_level(level)
        print(f"  Level {level}: {len(items)} items")


if __name__ == '__main__':
    main()
