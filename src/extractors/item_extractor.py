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
    
    def _get_identified_name(self, item_id: int, base_name: str) -> tuple[str, str, str]:
        """
        Get the identified name for an item from game files.
        
        For most quest items and talismans, Block 4 contains the identified name.
        Some quest items have their identified names in Block 1 (dynamically searched).
        For enchanted items, we check Block 5 for identified names.
        
        Checks multiple possible locations:
        1. Block 1 - dynamically search for quest item identified names
        2. Block 4 at object ID (most quest items/talismans have identified names here)
        3. Block 5 at object ID index (object look descriptions may contain identified names)
        4. Block 4 at object ID + 512 (if Block 4 has extended entries)
        5. Block 5 at object ID + 512 (if Block 5 has extended entries)
        
        Returns:
            Tuple of (name, article, plural)
        """
        block1 = self.strings.get_block(StringsParser.BLOCK_UI) or []
        block4 = self.strings.get_block(StringsParser.BLOCK_OBJECT_NAMES) or []
        block5 = self.strings.get_block(StringsParser.BLOCK_OBJECT_LOOK) or []
        
        # For quest items and talismans, check if Block 4 has a generic name
        # that might need to be replaced with an identified name from Block 1
        is_quest_or_talisman = (
            (0x110 <= item_id <= 0x11F or item_id == 0x1CA) or
            (0xE1 <= item_id <= 0xE7 or item_id == 0xBF)
        )
        
        if is_quest_or_talisman:
            # First, get the Block 4 name to see if it's generic/unidentified
            if item_id < len(block4) and block4[item_id]:
                block4_name = block4[item_id]
                parsed_name, parsed_article, parsed_plural = parse_item_name(block4_name)
                block4_base = parsed_name.lower()
                
                # Check if Block 4 has a generic name that might have an identified version in Block 1
                # Generic names to check: "standard", "wine", etc.
                generic_names = ['standard', 'wine', 'taper', 'silver tree']
                is_generic = any(generic in block4_base for generic in generic_names)
                
                # Search Block 1 for a more specific identified name if Block 4 is generic
                if is_generic:
                    # Search Block 1 for quest item names that might match
                    for idx, block1_text in enumerate(block1):
                        if not block1_text:
                            continue
                        
                        # Strip whitespace and newlines first
                        block1_text = block1_text.strip()
                        if not block1_text:
                            continue
                        
                        block1_lower = block1_text.lower()
                        # Look for patterns like "the [Item Name]." where Item Name contains the base name
                        # or is a known quest item name
                        if block1_lower.startswith(('the ', 'a ', 'an ')) and (block1_lower.endswith('.') or block1_lower.endswith('.\n')):
                            # Extract the item name
                            text = block1_text
                            for prefix in ['the ', 'a ', 'an ']:
                                if text.lower().startswith(prefix):
                                    text = text[len(prefix):]
                            # Remove trailing period and any whitespace
                            text = text.rstrip('.\n').strip()
                            
                            text_lower = text.lower()
                            
                            # Check if this Block 1 entry contains the base name or is a known quest item
                            # For "standard" -> look for "Standard of Honor"
                            # For "wine" or "bottle of wine" -> look for "Wine of Compassion"
                            if block4_base == 'standard' and 'standard of honor' in text_lower:
                                return text, "", ""
                            elif ('wine' in block4_base or block4_base == 'bottle of wine') and 'wine of compassion' in text_lower:
                                return text, "", ""
                            elif 'taper of sacrifice' in text_lower and block4_base in ['taper', 'candle']:
                                return text, "", ""
                            elif 'silver tree' in text_lower and block4_base in ['silver tree', 'tree']:
                                return text, "", ""
                
                # Use Block 4 name (either specific or as fallback if Block 1 search didn't find a match)
                return parsed_name, parsed_article, parsed_plural
        
        # Try Block 5 at object ID index for enchanted items
        if item_id < len(block5) and block5[item_id]:
            identified_text = block5[item_id].strip()
            # Skip quality descriptions that are commonly used in Block 5
            quality_descriptions = {'massive', 'sturdy', 'new', 'smooth', 'old', 'worn', 'broken', 'fine', 'excellent', 'poor', 'good', 'bad', 'undamaged', 'damaged', 'slightly damaged', 'tattered'}
            identified_lower = identified_text.lower()
            # Check if it looks like a name (not a description starting with common phrases, and not a quality description)
            if identified_text and not identified_lower.startswith(('it is', 'it looks', 'this is', 'you see', 'a ', 'an ', 'some ')) and identified_lower not in quality_descriptions:
                # Try to parse as name format
                parsed_name, parsed_article, parsed_plural = parse_item_name(identified_text)
                if parsed_name and parsed_name != base_name:
                    return parsed_name, parsed_article, parsed_plural
        
        # Try Block 4 at object ID + 512 (if Block 4 has extended entries)
        extended_idx = item_id + 512
        if extended_idx < len(block4) and block4[extended_idx]:
            raw_name = block4[extended_idx]
            parsed_name, parsed_article, parsed_plural = parse_item_name(raw_name)
            if parsed_name and parsed_name != base_name:
                return parsed_name, parsed_article, parsed_plural
        
        # Try Block 5 at object ID + 512 (if Block 5 has extended entries)
        if extended_idx < len(block5) and block5[extended_idx]:
            identified_text = block5[extended_idx].strip()
            # Skip quality descriptions that are commonly used in Block 5
            quality_descriptions = {'massive', 'sturdy', 'new', 'smooth', 'old', 'worn', 'broken', 'fine', 'excellent', 'poor', 'good', 'bad', 'undamaged', 'damaged', 'slightly damaged', 'tattered'}
            identified_lower = identified_text.lower()
            if identified_text and not identified_lower.startswith(('it is', 'it looks', 'this is', 'you see', 'a ', 'an ', 'some ')) and identified_lower not in quality_descriptions:
                parsed_name, parsed_article, parsed_plural = parse_item_name(identified_text)
                if parsed_name and parsed_name != base_name:
                    return parsed_name, parsed_article, parsed_plural
        
        # Fall back to base name from Block 4
        return base_name, "a", ""
    
    def _extract_item_types(self) -> None:
        """Extract all item type definitions."""
        object_names = self.strings.get_block(StringsParser.BLOCK_OBJECT_NAMES) or []
        object_look = self.strings.get_block(StringsParser.BLOCK_OBJECT_LOOK) or []
        
        for item_id in range(self.NUM_ITEM_TYPES):
            # Get base name from strings
            raw_name = object_names[item_id] if item_id < len(object_names) else ""
            base_name, base_article, base_plural = parse_item_name(raw_name)
            
            # Override name for dial (0x161) - game strings call it "lever" but it's actually a dial
            if item_id == 0x161:
                name = "dial"
                article = "a"
                plural = "dials"
            else:
                # For quest items and talismans, get the identified name
                # Quest items (0x110-0x11F, 0x1CA), talismans (0xE1-0xE7, 0xBF)
                is_quest_or_talisman = (
                    (0x110 <= item_id <= 0x11F or item_id == 0x1CA) or
                    (0xE1 <= item_id <= 0xE7 or item_id == 0xBF)
                )
                
                if is_quest_or_talisman:
                    # Get identified name from game files (Block 4 for most, Block 1[264] for 0xBF)
                    name, article, plural = self._get_identified_name(item_id, base_name)
                else:
                    name, article, plural = base_name, base_article, base_plural
            
            # Get common properties
            common_props = self.common.get_object(item_id)
            
            # Get class-specific properties
            properties = self._get_class_properties(item_id, object_look)
            
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
    
    def _normalize_door_object_id(self, item_id: int) -> int:
        """Normalize open/closed variants to a stable 'base' door id."""
        # Closed doors (0x140-0x145) <-> open doors (0x148-0x14D)
        if 0x148 <= item_id <= 0x14D:
            return item_id - 8
        # Open portcullis -> portcullis
        if item_id == 0x14E:
            return 0x146
        # Open secret door -> secret door
        if item_id == 0x14F:
            return 0x147
        return item_id

    def _get_door_type_info(self, item_id: int, object_look: list[str]) -> Dict[str, Any]:
        """
        Return door metadata for this door object type.

        Door massiveness is determined per-instance:
        - object_id 0x145 (door_style_5) => always massive (unbreakable)
        - quality==63 on any door type => also massive
        - else => breakable, with quality representing health (0-40)

        For type tables (`object_types`), we provide variant info only.
        Actual massive/sturdy determination happens per-instance in _get_extra_info.
        """
        base_id = self._normalize_door_object_id(item_id)
        # Provide a stable variant identity even when we can't name the material.
        if 0x140 <= base_id <= 0x145:
            door_variant = f"door_style_{base_id - 0x140}"
        elif base_id == 0x146:
            door_variant = "portcullis"
        elif base_id == 0x147:
            door_variant = "secret_door"
        else:
            door_variant = f"door_0x{base_id:03X}"

        return {
            "type": "door",
            "door_variant": door_variant,
            "door_variant_id": base_id,
            "door_variant_id_hex": f"0x{base_id:03X}",
        }

    @staticmethod
    def _door_condition_from_health(health: int) -> str:
        """
        Convert door health (0-63) to a UI-friendly condition label.

        We intentionally keep these broad buckets; UW uses many per-item quality semantics.
        """
        # Doors use a different vocabulary than cloth/armor condition; avoid "tattered".
        # Health is treated as 0..40 for breakable doors.
        if health <= 0:
            return "broken"
        if health <= 13:
            return "badly damaged"
        if health <= 26:
            return "damaged"
        return "undamaged"

    def _get_class_properties(self, item_id: int, object_look: list[str]) -> Dict[str, Any]:
        """Get class-specific properties for an item."""
        props = {}

        # Doors (including portcullis and secret doors)
        if is_door(item_id):
            return self._get_door_type_info(item_id, object_look)
        
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
                else:
                    # For quest items, talismans, and enchanted items, get the identified name
                    # Quest items (0x110-0x11F, 0x1CA), talismans (0xE1-0xE7, 0xBF)
                    is_quest_or_talisman = (
                        (0x110 <= obj.item_id <= 0x11F or obj.item_id == 0x1CA) or
                        (0xE1 <= obj.item_id <= 0xE7 or obj.item_id == 0xBF)
                    )
                    
                    if is_quest_or_talisman or obj.is_enchanted:
                        # Get identified name from game files
                        identified_name, _, _ = self._get_identified_name(obj.item_id, name)
                        if identified_name and identified_name != name:
                            name = identified_name
                
                # Determine quantity vs special_link
                # For triggers (0x1A0-0x1BF), quantity_or_link ALWAYS contains
                # the link to the trap, regardless of is_quantity flag
                is_trigger = 0x1A0 <= obj.item_id <= 0x1BF
                
                # Items that can have quantity: emeralds, rubies, sapphires, tiny blue gems, red gems
                # For these items, if is_quantity is True but quantity_or_link is 0, it means quantity is 1
                quantity_capable_items = [
                    0x0A2,  # Ruby
                    0x0A3,  # Red gem
                    0x0A4,  # Small blue gem (tiny blue gem)
                    0x0A6,  # Sapphire
                    0x0A7,  # Emerald
                    # Add resilient spear object ID here when found
                ]
                can_have_quantity = obj.item_id in quantity_capable_items
                
                if is_trigger:
                    # Triggers always use quantity_or_link as a link
                    quantity = 0
                    special_link = obj.quantity_or_link
                else:
                    # Normal items follow is_quantity flag
                    if obj.is_quantity:
                        # If is_quantity is True, quantity_or_link contains the quantity
                        quantity = obj.quantity_or_link
                        special_link = 0
                    else:
                        # If is_quantity is False, quantity_or_link contains a special link
                        quantity = 0
                        special_link = obj.quantity_or_link
                        
                        # For quantity-capable items, if is_quantity is False and quantity_or_link is 0,
                        # it means there's no link and the item has quantity 1 (default single item)
                        if can_have_quantity and obj.quantity_or_link == 0:
                            quantity = 1
                            special_link = 0
                    
                    # For quantity-capable items, if quantity is 0 after processing, it means quantity is 1
                    # This handles the case where is_quantity is True but quantity_or_link is 0
                    if can_have_quantity and quantity == 0:
                        quantity = 1
                
                # For armor items, check if enchantment data is present even if is_enchanted flag is not set
                # Some armor items may have enchantment data in the link field without the flag set
                is_enchanted = obj.is_enchanted
                if 0x20 <= obj.item_id < 0x40 and not is_enchanted:
                    # Check if link field contains enchantment data (>= 512)
                    # Use quantity_or_link directly since we've already determined quantity/special_link
                    if obj.quantity_or_link >= 512:
                        is_enchanted = True
                
                # Get base and detailed categories
                base_category = get_category(obj.item_id)
                # Look up can_be_picked_up from item type if available
                can_be_picked_up = False
                if obj.item_id in self.item_types:
                    can_be_picked_up = self.item_types[obj.item_id].can_be_picked_up
                detailed_cat = get_detailed_category(
                    obj.item_id,
                    is_enchanted=is_enchanted,
                    owner=obj.owner,
                    special_link=special_link,
                    can_be_picked_up=can_be_picked_up
                )
                
                # Apply location-based category overrides
                from ..constants import get_location_category_override
                location_override = get_location_category_override(
                    level_num, obj.tile_x, obj.tile_y, obj.item_id
                )
                if location_override:
                    detailed_cat = location_override
                
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
                    is_enchanted=is_enchanted,
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
            extra['is_open'] = (0x148 <= obj.item_id <= 0x14E) or (obj.item_id == 0x14F)
            
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

            # Door health/type/status
            raw_quality = int(getattr(obj, "quality", 0))
            
            # Determine if this door is massive (unbreakable):
            # - object_id 0x145 (door_style_5) is inherently massive regardless of quality
            # - object_id 0x146 (portcullis) is inherently massive regardless of quality
            # - quality==63 on any door type also indicates massive
            is_massive_door = (obj.item_id == 0x145) or (obj.item_id == 0x146) or (raw_quality == 63)
            
            # Door health is max 40 for breakable doors
            door_max = 40
            if is_massive_door:
                door_health = door_max  # Massive doors show full health
            else:
                door_health = max(0, min(door_max, raw_quality))
            extra['door_health'] = door_health
            extra['door_max_health'] = door_max
            extra['door_condition'] = self._door_condition_from_health(door_health)

            # Merge door variant metadata from item_types when available
            item_info = self.item_types.get(obj.item_id)
            door_props = (item_info.properties if item_info and item_info.properties else {}) if item_info else {}
            if door_props:
                for k in ('door_variant', 'door_variant_id', 'door_variant_id_hex'):
                    if k in door_props:
                        extra[k] = door_props.get(k)

            # Override condition based on massive determination
            if is_massive_door:
                extra['door_condition'] = "massive"
            elif door_health == door_max:
                extra['door_condition'] = "sturdy"

            # Friendly combined status string for UI/search
            status_parts: list[str] = []
            status_parts.append(str(extra.get('door_condition')))
            status_parts.append('open' if extra.get('is_open') else 'closed')
            if extra.get('is_locked'):
                status_parts.append('locked')
            if extra.get('is_secret'):
                status_parts.append('secret')
            extra['door_status'] = ", ".join(status_parts)
        
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
