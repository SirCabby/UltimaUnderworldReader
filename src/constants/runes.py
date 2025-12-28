"""
Rune constants for Ultima Underworld spell casting.

Runes are magical syllables used to cast spells. Each rune has a name
and an associated meaning. Combining runes in the correct order casts spells.

Rune items in the game use object IDs 0xE0-0xFF.
"""

# Rune names by ID (corresponds to rune item objects 0xE0-0xF7)
# These are the 24 runestones the player can collect
RUNE_NAMES = {
    0: "An",      # Negate
    1: "Bet",     # Small
    2: "Corp",    # Death
    3: "Des",     # Down
    4: "Ex",      # Freedom
    5: "Flam",    # Flame
    6: "Grav",    # Energy/Field
    7: "Hur",     # Wind
    8: "In",      # Create/Make
    9: "Jux",     # Danger/Harm
    10: "Kal",    # Summon/Invoke
    11: "Lor",    # Light
    12: "Mani",   # Life/Heal
    13: "Nox",    # Poison
    14: "Ort",    # Magic
    15: "Por",    # Movement
    16: "Quas",   # Illusion
    17: "Rel",    # Change
    18: "Sanct",  # Protection
    19: "Tym",    # Time
    20: "Uus",    # Up
    21: "Vas",    # Great
    22: "Wis",    # Knowledge
    23: "Ylem",   # Matter
}

# Rune meanings - what each syllable represents
RUNE_MEANINGS = {
    "An": "Negate",
    "Bet": "Small",
    "Corp": "Death",
    "Des": "Down/Lower",
    "Ex": "Freedom",
    "Flam": "Flame",
    "Grav": "Energy/Field",
    "Hur": "Wind",
    "In": "Create/Make",
    "Jux": "Danger/Harm",
    "Kal": "Summon/Invoke",
    "Lor": "Light",
    "Mani": "Life/Heal",
    "Nox": "Poison",
    "Ort": "Magic",
    "Por": "Movement",
    "Quas": "Illusion",
    "Rel": "Change",
    "Sanct": "Protection",
    "Tym": "Time",
    "Uus": "Up/Raise",
    "Vas": "Great",
    "Wis": "Knowledge",
    "Ylem": "Matter",
}

