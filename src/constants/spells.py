"""
Spell constants for Ultima Underworld.

Spells are organized into 8 circles of increasing power.
Each player-castable spell has a rune combination.
Some spells are NPC-only (monsters can cast them but players cannot).

Spell names are stored in STRINGS.PAK block 6.

Data verified from:
- uw-formats.txt (Underworld Adventures community reverse engineering)
- uw1-walkthrough.txt (verified spell list with rune combinations)
- STRINGS.PAK Block 3 (in-game scroll text)
- STRINGS.PAK Block 6 (spell names and internal IDs)
"""

from typing import Dict, List, Set

# Mana cost formula: Circle * 3
# Minimum casting level: Circle * 2 (rounded up)

# Known spell rune combinations
# Maps spell name to list of rune names
# Verified from uw1-walkthrough.txt
SPELL_RUNES: Dict[str, List[str]] = {
    # Circle 1 (3 mana, Level 1+)
    "Create Food": ["In", "Mani", "Ylem"],
    "Light": ["In", "Lor"],
    "Magic Arrow": ["Ort", "Jux"],
    "Resist Blows": ["Bet", "In", "Sanct"],
    "Stealth": ["Sanct", "Hur"],
    
    # Circle 2 (6 mana, Level 3+)
    "Cause Fear": ["Quas", "Corp"],
    "Detect Monster": ["Wis", "Mani"],
    "Lesser Heal": ["In", "Bet", "Mani"],
    "Rune of Warding": ["In", "Jux"],
    "Slow Fall": ["Rel", "Des", "Por"],
    "Leap": ["Uus", "Por"],  # Undocumented
    
    # Circle 3 (9 mana, Level 5+)
    "Conceal": ["Bet", "Sanct", "Lor"],
    "Lightning": ["Ort", "Grav"],
    "Night Vision": ["Quas", "Lor"],
    "Speed": ["Rel", "Tym", "Por"],
    "Strengthen Door": ["Sanct", "Jux"],
    "Water Walk": ["Ylem", "Por"],  # Undocumented
    
    # Circle 4 (12 mana, Level 7+)
    "Heal": ["In", "Mani"],
    "Levitate": ["Hur", "Por"],
    "Poison": ["Nox", "Mani"],
    "Remove Trap": ["An", "Jux"],
    "Flameproof": ["Sanct", "Flam"],
    "Thick Skin": ["In", "Sanct"],  # Undocumented
    
    # Circle 5 (15 mana, Level 9+)
    "Cure Poison": ["An", "Nox"],
    "Fireball": ["Por", "Flam"],
    "Missile Protection": ["Grav", "Sanct", "Por"],
    "Name Enchantment": ["Ort", "Wis", "Ylem"],
    "Open": ["Ex", "Ylem"],
    "Smite Undead": ["An", "Corp", "Mani"],  # Undocumented
    
    # Circle 6 (18 mana, Level 11+)
    "Daylight": ["Vas", "In", "Lor"],
    "Gate Travel": ["Vas", "Rel", "Por"],
    "Greater Heal": ["Vas", "In", "Mani"],
    "Paralyze": ["An", "Ex", "Por"],
    "Telekinesis": ["Ort", "Por", "Ylem"],
    "Sheet Lightning": ["Vas", "Ort", "Grav"],  # Undocumented
    
    # Circle 7 (21 mana, Level 13+)
    "Ally": ["In", "Mani", "Rel"],
    "Confusion": ["Vas", "An", "Wis"],
    "Fly": ["Vas", "Hur", "Por"],
    "Invisibility": ["Vas", "Sanct", "Lor"],
    "Reveal": ["Ort", "An", "Quas"],
    "Summon Monster": ["Kal", "Mani"],  # Undocumented
    
    # Circle 8 (24 mana, Level 15+)
    "Flame Wind": ["Flam", "Hur"],
    "Freeze Time": ["An", "Tym"],
    "Iron Flesh": ["In", "Vas", "Sanct"],
    "Roaming Sight": ["Ort", "Por", "Wis"],
    "Tremor": ["Vas", "Por", "Ylem"],
    "Armageddon": ["Vas", "Kal", "Corp"],  # Undocumented
    "Curse": ["An", "Sanct"],  # Undocumented
}

# Spell circle assignments
# Verified from uw1-walkthrough.txt
SPELL_CIRCLES: Dict[str, int] = {
    # Circle 1
    "Create Food": 1,
    "Light": 1,
    "Magic Arrow": 1,
    "Resist Blows": 1,
    "Stealth": 1,
    
    # Circle 2
    "Cause Fear": 2,
    "Detect Monster": 2,
    "Lesser Heal": 2,
    "Rune of Warding": 2,
    "Slow Fall": 2,
    "Leap": 2,
    
    # Circle 3
    "Conceal": 3,
    "Lightning": 3,
    "Night Vision": 3,
    "Speed": 3,
    "Strengthen Door": 3,
    "Water Walk": 3,
    
    # Circle 4
    "Heal": 4,
    "Levitate": 4,
    "Poison": 4,
    "Remove Trap": 4,
    "Flameproof": 4,
    "Thick Skin": 4,
    
    # Circle 5
    "Cure Poison": 5,
    "Fireball": 5,
    "Missile Protection": 5,
    "Name Enchantment": 5,
    "Open": 5,
    "Smite Undead": 5,
    
    # Circle 6
    "Daylight": 6,
    "Gate Travel": 6,
    "Greater Heal": 6,
    "Paralyze": 6,
    "Telekinesis": 6,
    "Sheet Lightning": 6,
    
    # Circle 7
    "Ally": 7,
    "Confusion": 7,
    "Fly": 7,
    "Invisibility": 7,
    "Reveal": 7,
    "Summon Monster": 7,
    
    # Circle 8
    "Flame Wind": 8,
    "Freeze Time": 8,
    "Iron Flesh": 8,
    "Roaming Sight": 8,
    "Tremor": 8,
    "Armageddon": 8,
    "Curse": 8,
}

# Mana cost per circle (Circle * 3)
SPELL_MANA_COSTS: Dict[int, int] = {
    1: 3,
    2: 6,
    3: 9,
    4: 12,
    5: 15,
    6: 18,
    7: 21,
    8: 24,
}

# Minimum player level required per circle (Circle * 2, rounded up)
SPELL_MIN_LEVELS: Dict[int, int] = {
    1: 1,
    2: 3,
    3: 5,
    4: 7,
    5: 9,
    6: 11,
    7: 13,
    8: 15,
}

# Spell descriptions with damage/healing values from UnderworldExporter reverse engineering
# Damage values are base damage before skill/armor modifiers
SPELL_DESCRIPTIONS: Dict[str, str] = {
    # Circle 1 - Attack spells
    "Create Food": "Creates random food item in front of caster",
    "Light": "Creates light level 3 around caster (8 levels: 0=dark to 7=bright)",
    "Magic Arrow": "Magic projectile dealing 3 base damage",
    "Resist Blows": "Resistance +1, duration 3 (physical protection)",
    "Stealth": "Reduces detection by enemies",
    
    # Circle 2
    "Cause Fear": "Makes enemies flee in fear",
    "Detect Monster": "Shows nearby creatures on automap",
    "Lesser Heal": "Restores 1-10 HP randomly",
    "Rune of Warding": "Creates protective trap on ground",
    "Slow Fall": "Reduces falling damage",
    "Leap": "Allows higher jumping",
    
    # Circle 3
    "Conceal": "Low-level invisibility",
    "Lightning": "Electrical bolt dealing 8 base damage (electric type)",
    "Night Vision": "See in darkness (black and white), light level 5",
    "Speed": "Move faster temporarily",
    "Strengthen Door": "Reinforce door (like spikes)",
    "Water Walk": "Walk on water surface",
    
    # Circle 4
    "Heal": "Restores 10-20 HP randomly",
    "Levitate": "Float in air",
    "Poison": "Inflicts poison on target",
    "Remove Trap": "Disarms trap",
    "Flameproof": "Fire damage resistance",
    "Thick Skin": "Resistance +2, duration 4 (physical protection)",
    
    # Circle 5
    "Cure Poison": "Removes poison status",
    "Fireball": "Fire projectile dealing 16 base + 4 splash damage in area (fire type)",
    "Missile Protection": "Deflects ranged attacks",
    "Name Enchantment": "Identify item properties",
    "Open": "Opens locked doors/containers",
    "Smite Undead": "Deals 100 base damage to undead creatures",
    
    # Circle 6
    "Daylight": "Maximum illumination, light level 6",
    "Gate Travel": "Teleport to placed moonstone",
    "Greater Heal": "Restores 50-60 HP randomly",
    "Paralyze": "Freezes target in place",
    "Telekinesis": "Manipulate distant objects",
    "Sheet Lightning": "1-3 electric bolts dealing 8 base + 3 splash damage each",
    
    # Circle 7
    "Ally": "Charm creature to be friendly",
    "Confusion": "Enemies wander randomly instead of attacking, duration 3",
    "Fly": "Full flight capability",
    "Invisibility": "Full invisibility",
    "Reveal": "Reveals hidden/invisible things",
    "Summon Monster": "Creates summoned creature",
    
    # Circle 8
    "Flame Wind": "2-5 fire projectiles dealing 16 base + 8 splash damage each (fire type)",
    "Freeze Time": "Stops time for 15 seconds",
    "Iron Flesh": "Resistance +3, duration 5 (physical protection)",
    "Roaming Sight": "Remote viewing",
    "Tremor": "Earthquake effect",
    "Armageddon": "Destroys almost all objects and NPCs in the area",
    "Curse": "Curses target",
    
    # Light spell variants (internal spell IDs 0-7)
    "Darkness": "Removes light, level 0",
    "Burning Match": "Minimal light, level 1",
    "Candlelight": "Low light, level 2",
    "Magic Lantern": "Moderate light, level 4",
    "Sunlight": "Maximum light, level 7",
    
    # Healing spell variants (internal spell IDs 64-79)
    "Enhanced Heal": "Restores 30-40 HP randomly",
    
    # Mana restoration variants (internal spell IDs 160-175)
    "Increase Mana": "Small mana restoration",
    "Mana Boost": "Moderate mana restoration",
    "Regain Mana": "Large mana restoration",
    "Restore Mana": "Full mana restoration",
    
    # Regeneration effects
    "Regeneration": "HP regeneration over time",
    "Mana Regeneration": "Mana regeneration over time",
    
    # Enchantment descriptions (for weapons/armor)
    "Minor Accuracy": "Weapon accuracy +1",
    "Accuracy": "Weapon accuracy +2",
    "Additional Accuracy": "Weapon accuracy +3",
    "Major Accuracy": "Weapon accuracy +4",
    "Great Accuracy": "Weapon accuracy +5",
    "Very Great Accuracy": "Weapon accuracy +6",
    "Tremendous Accuracy": "Weapon accuracy +7",
    "Unsurpassed Accuracy": "Weapon accuracy +8",
    "Minor Damage": "Weapon damage +1",
    "Damage": "Weapon damage +2",
    "Additional Damage": "Weapon damage +3",
    "Major Damage": "Weapon damage +4",
    "Great Damage": "Weapon damage +5",
    "Very Great Damage": "Weapon damage +6",
    "Tremendous Damage": "Weapon damage +7",
    "Unsurpassed Damage": "Weapon damage +8",
    "Minor Protection": "Armor protection +1",
    "Protection": "Armor protection +2",
    "Additional Protection": "Armor protection +3",
    "Major Protection": "Armor protection +4",
    "Great Protection": "Armor protection +5",
    "Very Great Protection": "Armor protection +6",
    "Tremendous Protection": "Armor protection +7",
    "Unsurpassed Protection": "Armor protection +8",
    "Minor Toughness": "Item durability +1",
    "Toughness": "Item durability +2",
    "Additional Toughness": "Item durability +3",
    "Major Toughness": "Item durability +4",
    "Great Toughness": "Item durability +5",
    "Very Great Toughness": "Item durability +6",
    "Tremendous Toughness": "Item durability +7",
    "Unsurpassed Toughness": "Item durability +8",
}

# Undocumented spells - found in-game but not in original manual
# Marked with * in documentation
UNDOCUMENTED_SPELLS: Set[str] = {
    "Curse",           # An Sanct (AS)
    "Leap",            # Uus Por (UP)
    "Summon Monster",  # Kal Mani (KM)
    "Sheet Lightning", # Vas Ort Grav (VOG)
    "Smite Undead",    # An Corp Mani (ACM)
    "Thick Skin",      # In Sanct (IS)
    "Water Walk",      # Ylem Por (YP)
    "Armageddon",      # Vas Kal Corp (VKC)
}

# Spells that only NPCs/monsters can use (not available to player)
NPC_ONLY_SPELLS: Set[str] = {
    "Darkness",
    "Burning Match",
    "Candlelight",
    "Magic Lantern",
    "Sunlight",
    "Enhanced Heal",
    "Increase Mana",
    "Mana Boost",
    "Regain Mana",
    "Restore Mana",
    "Regeneration",
    "Mana Regeneration",
    "Haste",
    "Poison Resistance",
    "Magic Protection",
    "Greater Magic Protection",
}

# Player-castable spells with known rune combinations
PLAYER_SPELLS: Set[str] = set(SPELL_RUNES.keys())

# Protection spells - progressive resistance bonuses
# Values from UnderworldExporter: resistance value and duration multiplier
# Higher resistance = more damage reduction from physical attacks
PROTECTION_SPELL_TIERS: Dict[str, Dict] = {
    "Resist Blows": {"resistance": 1, "duration": 3, "tier": "small"},   # Circle 1
    "Thick Skin": {"resistance": 2, "duration": 4, "tier": "medium"},    # Circle 4 (undocumented)
    "Iron Flesh": {"resistance": 3, "duration": 5, "tier": "major"},     # Circle 8
}

# Light spell intensity levels (internal spell IDs 0-7)
LIGHT_SPELL_LEVELS: Dict[str, int] = {
    "Darkness": 0,
    "Burning Match": 1,
    "Candlelight": 2,
    "Light": 3,          # Player castable
    "Magic Lantern": 4,
    "Night Vision": 5,
    "Daylight": 6,       # Player castable
    "Sunlight": 7,
}

# Healing spell tiers (internal spell IDs 64-79)
# Each tier has 4 potency variants
# HP restoration ranges from UnderworldExporter reverse engineering
HEALING_SPELL_TIERS: Dict[str, Dict] = {
    "Lesser Heal": {"ids": (64, 67), "hp_min": 1, "hp_max": 10},
    "Heal": {"ids": (68, 71), "hp_min": 10, "hp_max": 20},
    "Enhanced Heal": {"ids": (72, 75), "hp_min": 30, "hp_max": 40},
    "Greater Heal": {"ids": (76, 79), "hp_min": 50, "hp_max": 60},
}

# Attack spell damage values from UnderworldExporter reverse engineering
# Base damage is before skill modifiers and armor reduction
ATTACK_SPELL_DAMAGE: Dict[str, Dict] = {
    "Magic Arrow": {"base": 3, "type": "magic"},
    "Lightning": {"base": 8, "type": "electric"},
    "Fireball": {"base": 16, "splash": 4, "radius": 1.0, "type": "fire"},
    "Smite Undead": {"base": 100, "type": "magic", "target": "undead only"},
    "Sheet Lightning": {"base": 8, "splash": 3, "bolts_min": 1, "bolts_max": 3, "type": "electric"},
    "Flame Wind": {"base": 16, "splash": 8, "bolts_min": 2, "bolts_max": 5, "type": "fire"},
}

# Enchantment spell ranges (internal spell IDs 448-479)
# Used for weapon/armor enchantments
ENCHANTMENT_SPELL_RANGES: Dict[str, tuple] = {
    "Accuracy": (448, 455),     # Minor to Unsurpassed Accuracy
    "Damage": (456, 463),       # Minor to Unsurpassed Damage
    "Protection": (464, 471),   # Minor to Unsurpassed Protection
    "Toughness": (472, 479),    # Minor to Unsurpassed Toughness
}


def get_spell_mana_cost(spell_name: str) -> int:
    """Get the mana cost for a spell."""
    circle = SPELL_CIRCLES.get(spell_name, 0)
    return SPELL_MANA_COSTS.get(circle, 0)


def get_spell_min_level(spell_name: str) -> int:
    """Get the minimum player level required for a spell."""
    circle = SPELL_CIRCLES.get(spell_name, 0)
    return SPELL_MIN_LEVELS.get(circle, 0)


def is_undocumented_spell(spell_name: str) -> bool:
    """Check if a spell is undocumented (not in original manual)."""
    return spell_name in UNDOCUMENTED_SPELLS


def get_spell_info(spell_name: str) -> Dict:
    """Get complete information about a spell."""
    circle = SPELL_CIRCLES.get(spell_name, 0)
    return {
        "name": spell_name,
        "circle": circle,
        "mana_cost": SPELL_MANA_COSTS.get(circle, 0),
        "min_level": SPELL_MIN_LEVELS.get(circle, 0),
        "runes": SPELL_RUNES.get(spell_name, []),
        "description": SPELL_DESCRIPTIONS.get(spell_name, ""),
        "undocumented": spell_name in UNDOCUMENTED_SPELLS,
        "npc_only": spell_name in NPC_ONLY_SPELLS,
    }
