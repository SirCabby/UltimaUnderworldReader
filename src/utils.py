"""
Shared utility functions for Ultima Underworld data extraction.

These functions are used across multiple extractors and exporters.
"""

from typing import Tuple, Optional, Dict, Any, List


def parse_item_name(raw_name: str) -> Tuple[str, str, str]:
    """
    Parse item name format from STRINGS.PAK block 4.
    
    Format: 'article_name&plural'
    Examples:
        'a_sword&swords' -> ('sword', 'a', 'swords')
        'an_apple&apples' -> ('apple', 'an', 'apples')
        'some_gold&gold' -> ('gold', 'some', 'gold')
    
    Args:
        raw_name: Raw string from STRINGS.PAK block 4
        
    Returns:
        Tuple of (name, article, plural)
    """
    article = "a"
    name = raw_name
    plural = ""
    
    if '_' in raw_name:
        parts = raw_name.split('_', 1)
        article = parts[0]
        name = parts[1]
    
    if '&' in name:
        parts = name.split('&', 1)
        name = parts[0]
        plural = parts[1]
    
    return name, article, plural


def extract_name_only(raw_name: str) -> str:
    """
    Extract just the name portion from a raw object name string.
    
    Args:
        raw_name: Raw string from STRINGS.PAK block 4
        
    Returns:
        The name without article or plural suffix
    """
    name, _, _ = parse_item_name(raw_name)
    return name


def format_hex_id(value: int, width: int = 3) -> str:
    """
    Format an integer as a hex string with leading zeros.
    
    Args:
        value: Integer value to format
        width: Number of hex digits (default 3 for object IDs)
        
    Returns:
        Hex string like '0x00F' or '0x1A0'
    """
    return f"0x{value:0{width}X}"


def clamp(value: int, min_val: int, max_val: int) -> int:
    """
    Clamp a value to a range.
    
    Args:
        value: Value to clamp
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        
    Returns:
        Value clamped to [min_val, max_val]
    """
    return max(min_val, min(max_val, value))


def quality_to_offset(quality: int) -> int:
    """
    Convert quality value (0-63) to description offset (0-5).
    
    Quality descriptions in STRINGS.PAK block 5 are organized in groups of 6.
    This converts the raw quality value to an offset within a description group.
    
    Mapping:
        0-9   -> 0
        10-19 -> 1
        20-29 -> 2
        30-39 -> 3
        40-49 -> 4
        50-63 -> 5
    
    Args:
        quality: Quality value from object data (0-63)
        
    Returns:
        Offset into description group (0-5)
    """
    return min(5, quality // 10)


# Quality description base indices in STRINGS.PAK block 5
# Each category has 6 quality levels (offset 0-5)
QUALITY_DESCRIPTION_BASES = {
    'melee_weapon': 6,      # 0x00-0x0F
    'ranged_weapon': 6,     # 0x10-0x1F (except ammo)
    'armor': 6,             # 0x20-0x3F (most armor)
    'armor_leather': 78,    # 0x24-0x27 (leather armor variants)
    'light_source': 60,     # 0x90-0x97
    'treasure_gem': 42,     # 0xA2-0xA7 (gems)
    'treasure_other': 36,   # 0xA8-0xAF (other treasure)
    'food': 18,             # 0xB0-0xB7
    'drink': 24,            # 0xB8-0xBF
    'container': 72,        # 0x80-0x8F
}

# Skip these quality descriptions as they're not meaningful
SKIP_QUALITY_DESCRIPTIONS = {'massive', 'sturdy', 'new', 'smooth'}


def get_quality_description(
    object_id: int,
    quality: int,
    block5: List[str]
) -> str:
    """
    Get the quality description for an item based on its type and quality value.
    
    Quality descriptions are stored in STRINGS.PAK block 5, organized by
    item category. Each category has a base index, and quality maps to
    an offset (0-5) within that group.
    
    Args:
        object_id: The object type ID
        quality: Quality value from object data (0-63)
        block5: List of strings from STRINGS.PAK block 5
    
    Returns:
        Quality description string, or empty string if not applicable
    """
    offset = quality_to_offset(quality)
    base = None
    
    # Melee weapons (0x00-0x0F)
    if 0x00 <= object_id <= 0x0F:
        base = QUALITY_DESCRIPTION_BASES['melee_weapon']
    
    # Ranged weapons (0x10-0x1F), except ammo
    elif 0x10 <= object_id <= 0x1F:
        if object_id in (0x10, 0x11, 0x12):  # Ammo: sling stone, bolt, arrow
            return ""
        base = QUALITY_DESCRIPTION_BASES['ranged_weapon']
    
    # Armor (0x20-0x3F)
    elif 0x20 <= object_id <= 0x3F:
        if 0x3C <= object_id <= 0x3F:  # Rings and amulets
            base = QUALITY_DESCRIPTION_BASES['armor']
        elif object_id in (0x24, 0x25, 0x26, 0x27):  # Leather armor
            base = QUALITY_DESCRIPTION_BASES['armor_leather']
        else:
            base = QUALITY_DESCRIPTION_BASES['armor']
    
    # Light sources (0x90-0x97)
    elif 0x90 <= object_id <= 0x97:
        base = QUALITY_DESCRIPTION_BASES['light_source']
    
    # Wands (0x98-0x9B) - no quality description
    elif 0x98 <= object_id <= 0x9B:
        return ""
    
    # Treasure (0xA0-0xAF)
    elif 0xA0 <= object_id <= 0xAF:
        if object_id == 0xA0:  # Coins
            return ""
        elif object_id in (0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7):  # Gems
            base = QUALITY_DESCRIPTION_BASES['treasure_gem']
        else:
            base = QUALITY_DESCRIPTION_BASES['treasure_other']
    
    # Food and drinks (0xB0-0xBF)
    elif 0xB0 <= object_id <= 0xBF:
        if 0xB0 <= object_id <= 0xB7:  # Food
            base = QUALITY_DESCRIPTION_BASES['food']
        else:  # Drinks
            base = QUALITY_DESCRIPTION_BASES['drink']
    
    # Containers (0x80-0x8F)
    elif 0x80 <= object_id <= 0x8F:
        if quality >= 40:  # High quality containers don't show condition
            return ""
        base = QUALITY_DESCRIPTION_BASES['container']
    
    # Books and scrolls (0x130-0x13F) - no quality description
    elif 0x130 <= object_id <= 0x13F:
        return ""
    
    # Quest items and misc (0x110-0x12F) - no quality description
    elif 0x110 <= object_id <= 0x12F:
        return ""
    
    # Keys (0x100-0x10F) - no quality description
    elif 0x100 <= object_id <= 0x10F:
        return ""
    
    # Scenery (0xC0-0xDF) - no quality description
    elif 0xC0 <= object_id <= 0xDF:
        return ""
    
    # No base found for this item type
    if base is None:
        return ""
    
    # Get the description from block 5
    desc_idx = base + offset
    if desc_idx < len(block5) and block5[desc_idx]:
        desc = block5[desc_idx]
        # Skip generic descriptions
        if desc.lower() in SKIP_QUALITY_DESCRIPTIONS:
            return ""
        return desc
    
    return ""


def get_door_condition(health: int, max_health: int = 40) -> str:
    """
    Get door condition description based on health value.
    
    Args:
        health: Current door health (0-40)
        max_health: Maximum door health (default 40)
    
    Returns:
        Condition string: 'broken', 'badly damaged', 'damaged', 
        'undamaged', or 'sturdy'
    """
    if health <= 0:
        return 'broken'
    elif health <= max_health // 3:
        return 'badly damaged'
    elif health <= 2 * max_health // 3:
        return 'damaged'
    elif health == max_health:
        return 'sturdy'
    else:
        return 'undamaged'


def is_massive_door(item_id: int, quality: int) -> bool:
    """
    Check if a door is massive (unbreakable).
    
    Massive doors include:
    - Door style 5 (0x145) and its open version (0x14D)
    - Portcullis (0x146) and open portcullis (0x14E)
    - Any door with quality=63
    
    Args:
        item_id: The door object type ID
        quality: The door's quality value
    
    Returns:
        True if the door is massive/unbreakable
    """
    massive_door_ids = {0x145, 0x14D, 0x146, 0x14E}
    return item_id in massive_door_ids or quality == 63

