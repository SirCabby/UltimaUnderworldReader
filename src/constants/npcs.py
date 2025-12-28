"""
NPC constants for Ultima Underworld.

NPCs use object IDs 0x40-0x7F (64 creature types).
Mobile objects (indices 0-255) contain NPC-specific data like HP, goals, attitudes.
"""

from typing import Dict

# NPC type names by object ID (0x40-0x7F)
NPC_TYPES: Dict[int, str] = {
    0x40: "green_goblin",
    0x41: "goblin",
    0x42: "mountain_folk",
    0x43: "human_male",
    0x44: "human_female",
    0x45: "bandit",
    0x46: "troll",
    0x47: "skeleton",
    0x48: "ghoul",
    0x49: "ghost",
    0x4A: "zombie",
    0x4B: "gazer",
    0x4C: "mage",
    0x4D: "dark_mage",
    0x4E: "outcast",
    0x4F: "headless",
    0x50: "imp",
    0x51: "mongbat",
    0x52: "dire_ghost",
    0x53: "shadow_beast",
    0x54: "reaper",
    0x55: "wisp",
    0x56: "fire_elemental",
    0x57: "golem_stone",
    0x58: "golem_metal",
    0x59: "golem_earth",
    0x5A: "lurker",
    0x5B: "deep_lurker",
    0x5C: "slime",
    0x5D: "vampire_bat",
    0x5E: "bat",
    0x5F: "rat",
    0x60: "spider",
    0x61: "giant_spider",
    0x62: "dread_spider",
    0x63: "acid_slug",
    0x64: "flesh_slug",
    0x65: "rotworm",
    0x66: "bloodworm",
    0x67: "lizardman",
    0x68: "gray_lizardman",
    0x69: "red_lizardman",
    0x6A: "feral_troll",
    0x6B: "great_troll",
    0x6C: "dark_ghoul",
    0x6D: "mountainman",
    0x6E: "fighter",
    0x6F: "knight",
    0x70: "mage_female",
    0x71: "mage_red",
    0x72: "tyball",
    0x73: "slasher",
    0x74: "dragon",
    0x75: "ethereal_void",
    0x76: "daemon",
    0x77: "undead_warrior",
    0x78: "garamon",
    0x79: "dire_reaper",
    0x7A: "spectre",
    0x7B: "liche",
    0x7C: "demon",
    0x7D: "unknown_7d",
    0x7E: "unknown_7e",
    0x7F: "player",  # Avatar as NPC (not used in game)
}

# NPC goal values (from mobile object data)
# Goal determines what action the NPC is trying to perform
NPC_GOALS: Dict[int, str] = {
    0: "Stand guard",
    1: "Attack target",
    2: "Flee",
    3: "Goto XY position",
    4: "Wander randomly",
    5: "Attack player",
    6: "Go home",
    7: "Unknown (7)",
}

# NPC attitude values
# Attitude string indices in block 5: 96=hostile, 97=upset, 98=mellow, 99=friendly
# But the attitude VALUE maps: 0=hostile, 1=upset, 2=mellow, 3=friendly
NPC_ATTITUDES: Dict[int, str] = {
    0: "hostile",
    1: "upset",
    2: "mellow",
    3: "friendly",
}


def get_npc_type_name(object_id: int) -> str:
    """Get the type name for an NPC object ID."""
    return NPC_TYPES.get(object_id, f"npc_0x{object_id:02X}")

