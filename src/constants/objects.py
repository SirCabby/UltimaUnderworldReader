"""
Object constants for Ultima Underworld.

The game has 512 object types (IDs 0x000-0x1FF).
Objects are organized into categories based on ID ranges.
"""

from typing import Dict, Set, Tuple, Any, Optional

# Object category names by ID range
# Each tuple is (start_id, end_id): category_name
OBJECT_CATEGORIES: Dict[Tuple[int, int], str] = {
    (0x000, 0x00F): "melee_weapon",
    (0x010, 0x01F): "ranged_weapon",
    (0x020, 0x03F): "armor",
    (0x040, 0x07F): "npc",
    (0x080, 0x08F): "container",
    (0x090, 0x097): "light_source",
    (0x098, 0x09B): "wand",
    (0x09C, 0x09F): "broken_wand",
    (0x0A0, 0x0AF): "treasure",
    (0x0B0, 0x0B9): "food",           # Actual food items
    (0x0BA, 0x0BA): "food",           # Bottle of ale (alcoholic, causes intoxication)
    (0x0BB, 0x0BC): "potion",         # Red/green potions
    (0x0BD, 0x0BD): "food",           # Water - no effect (UW1 has no thirst system)
    (0x0BE, 0x0BE): "food",           # Flask of port (alcoholic, causes intoxication)
    (0x0BF, 0x0BF): "talisman",       # Wine of Compassion - quest item (Talisman of Sir Cabirus)
    (0x0C0, 0x0DF): "scenery",
    (0x0E0, 0x0E0): "rune",             # Generic runestone
    (0x0E1, 0x0E7): "talisman",         # Virtue keys and two-part keys
    (0x0E8, 0x0FF): "rune",             # Spell runestones (An through Ylem)
    (0x100, 0x10F): "key",
    (0x110, 0x11F): "quest_item",
    (0x120, 0x120): "spell",          # Spell object (used by wands)
    (0x121, 0x12F): "misc_item",      # Bedroll, mandolin, etc.
    (0x130, 0x137): "book",           # Books (may be readable or enchanted)
    (0x138, 0x13A): "scroll",         # Scrolls (may be readable or enchanted)
    (0x13B, 0x13B): "map",            # Map
    (0x13C, 0x13F): "scroll",         # More scrolls
    (0x140, 0x145): "door",           # Closed doors
    (0x146, 0x146): "portcullis",     # Closed portcullis
    (0x147, 0x147): "secret_door",    # Secret door
    (0x148, 0x14D): "open_door",      # Open doors
    (0x14E, 0x14E): "open_portcullis",
    (0x14F, 0x14F): "secret_door",    # Open secret door
    (0x150, 0x15F): "furniture",
    (0x160, 0x16D): "decal",
    (0x16E, 0x16F): "special_tmap",   # Special texture map objects
    (0x170, 0x17F): "switch",
    (0x180, 0x19F): "trap",
    (0x1A0, 0x1BF): "trigger",
    (0x1C0, 0x1CF): "animation",
}

# Specific item IDs for easy reference
ITEM_IDS = {
    # Potions
    'RED_POTION': 0x0BB,      # Mana potion
    'GREEN_POTION': 0x0BC,    # Health potion
    
    # Doors
    'SECRET_DOOR': 0x147,
    'SECRET_DOOR_OPEN': 0x14F,
    'PORTCULLIS': 0x146,
    'OPEN_PORTCULLIS': 0x14E,
    
    # Special objects
    'SPELL_OBJECT': 0x120,
    'MOONGATE': 0x15A,
    'SPECIAL_TMAP_1': 0x16E,
    'SPECIAL_TMAP_2': 0x16F,
}

# Text indices (from STRINGS.PAK block 3) that indicate quest books
# These books are important to the game's main quest and should be categorized as quest items
# Text index is calculated as: (quantity - 512) when is_quantity flag is set
QUEST_BOOK_TEXT_INDICES: Set[int] = {
    # Book of Honesty - contains philosophical text about the virtue of Honesty
    # Required for the Abyss quest completion
    22,  # "Honesty is scrupulous respect for truth..."
}


def is_quest_book(text_idx: int) -> bool:
    """Check if a book's text index indicates it's a quest item."""
    return text_idx in QUEST_BOOK_TEXT_INDICES

# Scenery items (0x0C0-0x0DF) that can be picked up by the player
# The can_be_picked_up flag in COMOBJ.DAT is not reliable for scenery items,
# so we use a manual list based on gameplay knowledge
SCENERY_PICKUPABLE_ITEMS: Set[int] = {
    0x0C2, 0x0C3,  # skulls
    0x0C4, 0x0C5,  # bones
    0x0C6, 0x0DC,  # pile of bones
    0x0C8, 0x0C9, 0x0CA, 0x0CB,  # broken items (axe, sword, mace, shield)
    0x0D5, 0x0D6,  # pile of debris
    # Note: 0x0DB (pile of wood chips) is handled separately as misc_item
}

# Items that use quantity for stacking (coins, arrows, etc.)
# For these, the quantity field holds the actual count, not a link
STACKABLE_ITEMS: Dict[int, str] = {
    0x10: "sling stone",
    0x11: "crossbow bolt",
    0x12: "arrow",
    0xA0: "coin",
}

# Categories of items that can be carried by the player
CARRYABLE_CATEGORIES: Set[str] = {
    "melee_weapon",
    "ranged_weapon",
    "armor",
    "container",
    "light_source",
    "wand",
    "treasure",
    "food",
    "drink",
    "potion",
    "rune",
    "talisman",
    "key",
    "quest_item",
    "misc_item",
    "book",
    "scroll",
    "map",
}

# Carryable container IDs (portable bags/packs the player can pick up)
# Odd IDs (0x81, 0x83, etc.) are "open" versions - skip them
# Note: urn (0x8C) is NOT carryable despite being in container range
CARRYABLE_CONTAINERS: Dict[int, str] = {
    0x80: "sack",
    0x82: "pack",
    0x84: "box",
    0x86: "pouch",
    0x88: "map case",
    0x8A: "gold coffer",
    0x8D: "quiver",
    0x8E: "bowl",
    0x8F: "rune bag",
}

# Static containers (non-carryable storage that can hold items)
# Includes urn from container range and furniture items that store things
# Note: nightstand (0x15E) is NOT a container - it's just furniture
# Note: cauldron (0x12F) is NOT a container - it's just furniture (no items found in game data)
STATIC_CONTAINERS: Dict[int, str] = {
    0x8C: "urn",        # In container range but not carryable
    0x158: "table",     # Tables can sometimes hold items
    0x15B: "barrel",
    0x15D: "chest",
    # 0x12F: "cauldron",  # Not a container - just furniture (no items found in game)
    # 0x15E: "nightstand",  # Not a container - just furniture
}

# All container-like item IDs (both carryable and static)
def is_container(item_id: int) -> bool:
    """Check if an item ID is any type of container (can hold other items)."""
    # Carryable containers (0x80-0x8F except urn 0x8C)
    if 0x80 <= item_id <= 0x8F and item_id != 0x8C:
        return True
    # Static containers (urn, barrels, chests, etc.)
    if item_id in STATIC_CONTAINERS:
        return True
    return False

def is_static_container(item_id: int) -> bool:
    """Check if an item ID is a static (non-carryable) container."""
    return item_id in STATIC_CONTAINERS

def is_carryable_container(item_id: int) -> bool:
    """Check if an item ID is a carryable container."""
    return item_id in CARRYABLE_CONTAINERS

# Category display names for UI
CATEGORY_DISPLAY_NAMES: Dict[str, str] = {
    "melee_weapon": "Melee Weapon",
    "ranged_weapon": "Ranged Weapon",
    "armor": "Armor",
    "npc": "NPC",
    "container": "Containers",      # Portable bags/packs
    "storage": "Storage",           # Static containers (barrels, chests, urns)
    "light_source": "Light Source",
    "wand": "Wand",
    "broken_wand": "Broken Wand",
    "treasure": "Treasure",
    "food": "Food",
    "drink": "Drink",
    "potion": "Potion",
    "scenery": "Scenery",
    "useless_item": "Useless Item",
    "rune": "Runestone",
    "talisman": "Talisman",
    "key": "Key",
    "quest_item": "Quest Item",
    "spell": "Spell",
    "misc_item": "Misc Item",
    "book": "Book",
    "scroll": "Scroll",
    "map": "Map",
    "readable_book": "Readable Book",
    "readable_scroll": "Readable Scroll",
    "spell_scroll": "Spell Scroll",
    "door": "Door",
    "door_locked": "Locked Door",
    "door_unlocked": "Unlocked Door",
    "portcullis": "Portcullis",
    "portcullis_locked": "Locked Portcullis",
    "open_door": "Open Door",
    "open_portcullis": "Open Portcullis",
    "secret_door": "Secret Door",
    "furniture": "Furniture",       # Non-container furniture
    "decal": "Decal",
    "bridge": "Bridge",
    "writings": "Writings",
    "gravestones": "Gravestones",
    "special_tmap": "Texture Map Object",
    "switch": "Switch",
    "trap": "Trap",
    "trigger": "Trigger",
    "animation": "Animated Object",
    "unknown": "Unknown",
}

# Potion types and their effects
POTION_EFFECTS: Dict[int, str] = {
    0x0BB: "mana",      # Red potion
    0x0BC: "health",    # Green potion
}

# Door ID ranges for categorization
CLOSED_DOOR_IDS = range(0x140, 0x146)
OPEN_DOOR_IDS = range(0x148, 0x14E)


def get_category(item_id: int) -> str:
    """Get the base category name for an item ID."""
    for (low, high), category in OBJECT_CATEGORIES.items():
        if low <= item_id <= high:
            return category
    return "unknown"


def get_detailed_category(item_id: int, is_enchanted: bool = False, 
                          owner: int = 0, special_link: int = 0,
                          can_be_picked_up: bool = False) -> str:
    """
    Get a more detailed category for an item based on its ID and properties.
    
    Args:
        item_id: The object type ID
        is_enchanted: Whether the object has the enchanted flag set
        owner: The owner field (used for door lock status)
        special_link: The special_link field (used for door lock status)
        can_be_picked_up: Whether the object can be picked up by the player
    
    Returns:
        A more specific category string
    """
    # Import here to avoid circular imports
    from .food import FOOD_IDS
    
    base_category = get_category(item_id)
    
    # Check if item is food (including items like plants that are in FOOD_IDS but in scenery range)
    if item_id in FOOD_IDS:
        return 'food'
    
    # Special cases: these scenery items go to misc_item category
    if item_id in (0x0CC, 0x0CD, 0x0DB, 0x0D8):  # piece of wood (2 variants), pile of wood chips, pole
        return 'misc_item'
    
    # Special cases: campfire (0x12A) and fountain (0x12E) should be categorized as scenery
    if item_id in (0x12A, 0x12E):  # campfire, fountain
        return 'scenery'
    
    # Special case: cauldron (0x12F) should be categorized as furniture (not storage - no items found in game)
    if item_id == 0x12F:
        return 'furniture'
    
    # Special case: lever (0x161) should be categorized as switch (not decal/scenery)
    if item_id == 0x161:
        return 'switch'
    
    # Special case: bridge (0x164) should be categorized as bridge (not decal/scenery)
    if item_id == 0x164:
        return 'bridge'
    
    # Special case: writing (0x166) and gravestone (0x165) should be categorized separately
    if item_id == 0x165:
        return 'gravestones'
    if item_id == 0x166:
        return 'writings'
    
    # Scenery items (0x0C0-0x0DF): split into scenery vs useless_item
    # Items that can be picked up are "useless_item", items that can't are "scenery"
    # Use manual list since COMOBJ.DAT flag is not reliable for scenery items
    if base_category == 'scenery':
        # Check manual list first, then fall back to flag
        if item_id in SCENERY_PICKUPABLE_ITEMS or can_be_picked_up:
            return 'useless_item'
        return 'scenery'
    
    # Static containers (urn, barrel, chest, etc.) - categorize as "storage"
    if item_id in STATIC_CONTAINERS:
        return 'storage'
    
    # Carryable containers stay as "container"
    if item_id in CARRYABLE_CONTAINERS:
        return 'container'
    
    # Books and scrolls: distinguish readable from spell scrolls
    if base_category in ('book', 'scroll'):
        if is_enchanted:
            return 'spell_scroll'
        else:
            return f'readable_{base_category}'
    
    # Doors: distinguish locked from unlocked
    if base_category == 'door':
        # A door is locked if:
        # 1. It has a non-zero special_link (pointing to a lock object 0x10F), OR
        # 2. It has a non-zero owner (for template doors at 0,0)
        # The lock ID (what key opens it) is stored in the door's quality field
        if special_link != 0 or owner != 0:
            return 'door_locked'
        return 'door_unlocked'
    
    # Open doors: distinguish locked from unlocked based on lock capability
    if base_category == 'open_door':
        # An open door can be locked if it has lock information
        # Check if it has a non-zero special_link (pointing to a lock object 0x10F) or owner
        if special_link != 0 or owner != 0:
            return 'door_locked'
        return 'door_unlocked'
    
    # Portcullis: distinguish locked from unlocked
    if base_category == 'portcullis':
        if owner != 0 or special_link != 0:
            return 'portcullis_locked'
        return 'portcullis'
    
    return base_category


def get_potion_effect(item_id: int) -> Optional[str]:
    """Get the effect type of a potion (mana, health, etc.)"""
    return POTION_EFFECTS.get(item_id)


def is_door(item_id: int) -> bool:
    """Check if an item ID is any type of door."""
    return 0x140 <= item_id <= 0x14F


def is_locked_door(item_id: int, owner: int = 0, special_link: int = 0) -> bool:
    """Check if a door is locked based on its ID, owner, and special_link.
    
    A door is locked if it has a non-zero special_link (pointing to a lock
    object 0x10F) or a non-zero owner (for template doors).
    The lock ID (what key opens it) is stored in the door's quality field.
    Keys with owner matching the lock ID can open the door.
    """
    if not is_door(item_id):
        return False
    # Open doors and open portcullises are not locked
    if item_id in range(0x148, 0x14F):
        return False
    # Locked if special_link points to a lock or owner is non-zero
    return special_link != 0 or owner != 0


def is_secret_door(item_id: int) -> bool:
    """Check if an item ID is a secret door."""
    return item_id in (0x147, 0x14F)


def is_special_tmap(item_id: int) -> bool:
    """Check if an item ID is a special texture map object."""
    return item_id in (0x16E, 0x16F)


def get_tmap_info(quality: int, owner: int) -> Dict[str, Any]:
    """
    Get information about a special tmap object.
    
    The special_tmap objects (0x16E, 0x16F) are used for:
    - Wall textures modifications
    - Level transition markers
    - Special visual effects
    
    Args:
        quality: The quality field from the object
        owner: The owner field from the object
    
    Returns:
        Dictionary with decoded tmap information
    """
    info = {
        'texture_index': owner,
    }
    
    # Quality 40 is common for wall textures
    if quality == 40:
        info['type'] = 'wall_texture'
        info['texture_id'] = owner
    # Quality 0 might indicate special usage
    elif quality == 0:
        info['type'] = 'special'
    # Other quality values may encode destination data
    else:
        info['type'] = 'level_marker'
        info['marker_data'] = quality
    
    return info


# Special Wands with unique spells that can't be cast normally
# These wands have spells that aren't in the spell table, so they show as "unknown spell"
# Key: (level, tile_x, tile_y) -> description dict
SPECIAL_WANDS = {
    # Bullfrog Wand on Level 4 - used to solve the Puzzle of the Bullfrog
    (3, 46, 47): {
        'name': 'Bullfrog Wand',
    },
}


def get_special_wand_info(level: int, tile_x: int, tile_y: int) -> Optional[Dict[str, str]]:
    """
    Get information about a special wand at a specific location.
    
    Args:
        level: The level index (0-based)
        tile_x: X coordinate on the tilemap
        tile_y: Y coordinate on the tilemap
    
    Returns:
        Dictionary with wand info or None if not a special wand
    """
    return SPECIAL_WANDS.get((level, tile_x, tile_y))


# Location-based category overrides
# These override the normal category assignment for items at specific locations
# Key: (level, tile_x, tile_y, item_id) -> category string
# Note: item_id can be None to match any item at that location
LOCATION_CATEGORY_OVERRIDES: Dict[Tuple[int, int, int, Optional[int]], str] = {
    # Pile of debris on level 1 that should be categorized as useless_item
    (0, 32, 9, None): 'useless_item',  # Level 1 (index 0), coordinates (32, 9) - pile of debris
}


def get_location_category_override(level: int, tile_x: int, tile_y: int, item_id: int) -> Optional[str]:
    """
    Get a category override for an item at a specific location.
    
    Args:
        level: The level index (0-based)
        tile_x: X coordinate on the tilemap
        tile_y: Y coordinate on the tilemap
        item_id: The object type ID
    
    Returns:
        Override category string, or None if no override exists
    """
    # First try exact match with item_id
    exact_key = (level, tile_x, tile_y, item_id)
    if exact_key in LOCATION_CATEGORY_OVERRIDES:
        return LOCATION_CATEGORY_OVERRIDES[exact_key]
    
    # Then try match without item_id (None matches any item at that location)
    any_key = (level, tile_x, tile_y, None)
    if any_key in LOCATION_CATEGORY_OVERRIDES:
        return LOCATION_CATEGORY_OVERRIDES[any_key]
    
    return None