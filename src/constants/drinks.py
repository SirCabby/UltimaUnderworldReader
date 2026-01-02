"""
Drink/beverage constants for Ultima Underworld.

Beverage items are in the ID range 0x0BA-0x0BF (excluding potions 0xBB-0xBC).

IMPORTANT: Ultima Underworld has NO thirst system - only hunger matters.
- Water (0xBD) has NO practical effect - it doesn't fill you up or heal you
- Alcoholic drinks (ale, port) cause intoxication when consumed
- Wine of Compassion (0xBF) is a quest item (Talisman of Sir Cabirus)

Alcoholic drinks cause intoxication - drinking multiple servings in quick
succession can cause the player to become drunk and potentially pass out.
"""

from typing import Dict, Optional

# Beverage item IDs
# Note: 0xBB (red potion) and 0xBC (green potion) are potions, not drinks
DRINK_IDS = {
    0xBA: "bottle of ale",
    0xBD: "bottle of water",
    0xBE: "flask of port",
    0xBF: "bottle of wine",   # Wine of Compassion - quest item
}

# Alcoholic drinks - these cause intoxication when consumed
# The intoxication value represents how quickly you get drunk
# Higher values = more intoxicating
ALCOHOLIC_DRINKS: Dict[int, int] = {
    0xBA: 125,  # Bottle of Ale - very intoxicating
    0xBE: 120,  # Flask of Port - strong alcohol
    # 0xBF Wine is a quest item, not consumable
}

# Intoxication values for alcoholic beverages
# When the player drinks alcohol, this value is added to their intoxication counter
# Drinking enough will cause the player to become drunk and potentially pass out
DRINK_INTOXICATION: Dict[int, int] = {
    0xBA: 125,  # Bottle of Ale - highly intoxicating
    0xBD: 0,    # Water - no intoxication (no effect at all)
    0xBE: 120,  # Flask of Port - strong intoxication
    0xBF: 0,    # Wine of Compassion - quest item, not consumable
}

# Nutrition values for beverages
# IMPORTANT: Water has NO nutrition - UW1 has no thirst system!
# Alcohols provide minimal nutrition - you drink them for the buzz
DRINK_NUTRITION: Dict[int, int] = {
    0xBA: 5,    # Bottle of Ale - minimal nutrition
    0xBD: 0,    # Water - NO nutrition (no effect in game!)
    0xBE: 8,    # Flask of Port - minimal nutrition
    0xBF: 0,    # Wine of Compassion - quest item
}

# Drink notes for display
DRINK_NOTES: Dict[int, str] = {
    0xBA: "Alcoholic - causes intoxication!",
    0xBD: "No effect - UW1 has no thirst system",
    0xBE: "Strong alcohol - causes intoxication!",
    0xBF: "Wine of Compassion - Talisman of Sir Cabirus (quest item)",
}

# Drink ID range constants
DRINK_ID_MIN = 0xBA
DRINK_ID_MAX = 0xBF

# IDs that are actually beverages (excluding potions 0xBB, 0xBC)
ACTUAL_DRINK_IDS = {0xBA, 0xBD, 0xBE, 0xBF}

# Consumable beverages (ale, water, port - NOT wine which is a quest item)
CONSUMABLE_DRINK_IDS = {0xBA, 0xBD, 0xBE}


def is_drink(item_id: int) -> bool:
    """Check if an item ID is a drink (excluding potions)."""
    return item_id in ACTUAL_DRINK_IDS


def is_alcoholic(item_id: int) -> bool:
    """Check if a drink is alcoholic (causes intoxication)."""
    return item_id in ALCOHOLIC_DRINKS


def get_drink_nutrition(item_id: int) -> Optional[int]:
    """
    Get the nutrition value for a drink item.
    
    Args:
        item_id: The object type ID
        
    Returns:
        Nutrition value (0-127), or None if not a drink
    """
    return DRINK_NUTRITION.get(item_id)


def get_drink_intoxication(item_id: int) -> Optional[int]:
    """
    Get the intoxication value for a drink item.
    
    Args:
        item_id: The object type ID
        
    Returns:
        Intoxication value (0-125), or None if not a drink
        0 means no intoxication (water, quest wine)
    """
    return DRINK_INTOXICATION.get(item_id)


def get_drink_note(item_id: int) -> str:
    """
    Get a note/description for a drink item.
    
    Args:
        item_id: The object type ID
        
    Returns:
        Note string, or empty string if not a drink
    """
    return DRINK_NOTES.get(item_id, "")
