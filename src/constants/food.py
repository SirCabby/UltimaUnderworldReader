"""
Food constants for Ultima Underworld.

Food items are in the ID range 0x0B0-0x0B9.
Nutrition values determine how much each food item fills you up.

In Ultima Underworld, hunger management is important - an empty stomach
leads to less effective rest, resulting in reduced recovery of Vitality
and Mana during sleep.
"""

from typing import Dict, Optional

# Food item IDs and their nutrition values
# Higher values = more filling
# Based on game data analysis and community research
# Note: IDs verified against STRINGS.PAK block 4
FOOD_NUTRITION: Dict[int, int] = {
    0xB0: 64,   # Piece of Meat - most filling solid food
    0xB1: 16,   # Loaf of Bread
    0xB2: 12,   # Piece of Cheese
    0xB3: 6,    # Apple
    0xB4: 25,   # Ear of Corn - best nutrition/weight ratio
    0xB5: 16,   # Loaf of Bread (duplicate item ID)
    0xB6: 48,   # Fish - second most filling
    0xB7: 2,    # Popcorn - least filling
    0xB8: 0,    # Mushroom - provides NO nutrition!
    0xB9: 6,    # Toadstool
}

# Food item names for reference (from STRINGS.PAK block 4)
FOOD_NAMES: Dict[int, str] = {
    0xB0: "piece of meat",
    0xB1: "loaf of bread",
    0xB2: "piece of cheese",
    0xB3: "apple",
    0xB4: "ear of corn",
    0xB5: "loaf of bread",  # Duplicate item ID
    0xB6: "fish",
    0xB7: "popcorn",
    0xB8: "mushroom",
    0xB9: "toadstool",
}

# Notes about each food item
FOOD_NOTES: Dict[int, str] = {
    0xB0: "Most filling food item in the game",
    0xB1: "Common food, moderate nutrition",
    0xB2: "Light snack",
    0xB3: "Light snack, grows on trees",
    0xB4: "Best nutrition-to-weight ratio (250/kg)",
    0xB5: "Duplicate bread item ID",
    0xB6: "Very filling, common near water",
    0xB7: "Almost no nutrition value",
    0xB8: "WARNING: Provides no nutrition!",
    0xB9: "Light snack, may have other effects",
}

# Food ID range constants
FOOD_ID_MIN = 0xB0
FOOD_ID_MAX = 0xB9


def is_food(item_id: int) -> bool:
    """Check if an item ID is a food item."""
    return FOOD_ID_MIN <= item_id <= FOOD_ID_MAX


def get_food_nutrition(item_id: int) -> Optional[int]:
    """
    Get the nutrition value for a food item.
    
    Args:
        item_id: The object type ID
        
    Returns:
        Nutrition value (0-64), or None if not a food item
    """
    return FOOD_NUTRITION.get(item_id)


def get_food_note(item_id: int) -> str:
    """
    Get a note/description for a food item.
    
    Args:
        item_id: The object type ID
        
    Returns:
        Note string, or empty string if not a food item
    """
    return FOOD_NOTES.get(item_id, "")
