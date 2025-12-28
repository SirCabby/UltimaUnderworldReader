"""
Object constants for Ultima Underworld.

The game has 512 object types (IDs 0x000-0x1FF).
Objects are organized into categories based on ID ranges.
"""

from typing import Dict, Set, Tuple

# Object category names by ID range
# Each tuple is (start_id, end_id): category_name
OBJECT_CATEGORIES: Dict[Tuple[int, int], str] = {
    (0x000, 0x00F): "melee_weapon",
    (0x010, 0x01F): "ranged_weapon",
    (0x020, 0x03F): "armor",
    (0x040, 0x07F): "npc",
    (0x080, 0x08F): "container",
    (0x090, 0x097): "light_source",
    (0x098, 0x09F): "wand",
    (0x0A0, 0x0AF): "treasure",
    (0x0B0, 0x0BF): "food",
    (0x0C0, 0x0DF): "scenery",
    (0x0E0, 0x0FF): "rune",
    (0x100, 0x10F): "key",
    (0x110, 0x11F): "quest_item",
    (0x120, 0x12F): "inventory",
    (0x130, 0x13F): "book",
    (0x140, 0x14F): "door",
    (0x150, 0x15F): "furniture",
    (0x160, 0x16F): "decal",
    (0x170, 0x17F): "switch",
    (0x180, 0x19F): "trap",
    (0x1A0, 0x1BF): "trigger",
    (0x1C0, 0x1CF): "animation",
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
    "rune",
    "key",
    "quest_item",
    "inventory",
    "book",
}

# Carryable container IDs (excluding open versions and non-carryable)
# Odd IDs (0x81, 0x83, etc.) are "open" versions - skip them
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

# Category display names for UI
CATEGORY_DISPLAY_NAMES: Dict[str, str] = {
    "melee_weapon": "Melee Weapon",
    "ranged_weapon": "Ranged Weapon",
    "armor": "Armor",
    "npc": "NPC",
    "container": "Container",
    "light_source": "Light Source",
    "wand": "Wand",
    "treasure": "Treasure",
    "food": "Food & Drink",
    "scenery": "Scenery",
    "rune": "Rune",
    "key": "Key",
    "quest_item": "Quest Item",
    "inventory": "Misc Item",
    "book": "Book/Scroll",
    "door": "Door",
    "furniture": "Furniture",
    "decal": "Decal",
    "switch": "Switch",
    "trap": "Trap",
    "trigger": "Trigger",
    "animation": "Animated Object",
    "unknown": "Unknown",
}


def get_category(item_id: int) -> str:
    """Get the category name for an item ID."""
    for (low, high), category in OBJECT_CATEGORIES.items():
        if low <= item_id <= high:
            return category
    return "unknown"

