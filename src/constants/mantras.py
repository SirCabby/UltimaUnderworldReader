"""
Mantra constants for Ultima Underworld.

Mantras are spoken at shrines to gain skill points.
Each skill has an associated mantra. Speaking the correct mantra
at a shrine grants 1-3 points depending on the player's karma.

KARMA AND SHRINE SYSTEM:
- Karma ranges from 0 (bad) to 64 (good), starting at 32
- Killing innocents, stealing decreases karma
- Helping NPCs, completing quests increases karma
- Point increases depend on karma: higher karma = better increases
- Each skill mantra can only be used once per shrine visit
- Using a shrine advances game time by 8 hours

POINT INCREASE FORMULA:
- Base increase: 1-3 points depending on karma level
- Low karma (0-21): +1 point
- Medium karma (22-42): +2 points
- High karma (43-64): +3 points

Mantra strings are stored in STRINGS.PAK block 2.
"""

from typing import List, Tuple

# Complete mantra list from game strings block 2 and NPC dialogues
# Format: (mantra, skill(s) affected, effect description, point increase)
COMPLETE_MANTRAS: List[Tuple[str, str, str, str]] = [
    # Combat skill mantras (from STRINGS.PAK block 2 indices 51-57)
    ("RA", "Attack", "Increases attack effectiveness", "1-3 points"),
    ("ANRA", "Defense", "Improves defensive ability", "1-3 points"),
    ("ORA", "Unarmed", "Mantra of Unarmed combat", "1-3 points"),
    ("AMO", "Sword", "Increases swordfighting ability", "1-3 points"),
    ("GAR", "Axe", "Greater skill with axes", "1-3 points"),
    ("KOH", "Mace", "For blunt weapons", "1-3 points"),
    ("FAHM", "Missile", "Makes arrows fly true", "1-3 points"),
    
    # Magic skill mantras (from STRINGS.PAK block 2 indices 58-60)
    ("IMU", "Mana", "Increases magical stamina", "1-3 points"),
    ("LAHN", "Lore", "Helps identify possessions", "1-3 points"),
    ("SOL", "Casting", "Shortcut to magical power", "1-3 points"),
    
    # Practical skill mantras (from STRINGS.PAK block 2 indices 61-70)
    ("ROMM", "Traps", "Disarm traps better", "1-3 points"),
    ("LU", "Search", "Better eyesight/searching", "1-3 points"),
    ("SAHF", "Track", "Gain tracking ability", "1-3 points"),
    ("MUL", "Sneak", "Move more quietly", "1-3 points"),
    ("LON", "Repair", "Helps repair items", "1-3 points"),
    ("UN", "Charm", "Make better deals", "1-3 points"),
    ("AAM", "Picklock", "Improves lockpicking", "1-3 points"),
    ("FAL", "Acrobat", "Increases nimbleness", "1-3 points"),
    ("HUNN", "Appraise", "Better gauge quality", "1-3 points"),
    ("ONO", "Swimming", "To swim better", "1-3 points"),
    
    # Virtue mantras (from STRINGS.PAK block 2 indices 74-76)
    # These grant bonuses to multiple related skills at once
    ("SUMM RA", "Attack, Defense, Sword", "Mantra of Courage - combat skills", "+1 each (3 skills)"),
    ("MU AHM", "Casting, Mana, Lore", "Mantra of Truth - magic skills", "+1 each (3 skills)"),
    ("OM CAH", "Charm, Picklock, Traps", "Mantra of Love - practical skills", "+1 each (3 skills)"),
    
    # Universal mantra (from STRINGS.PAK block 2 index 71)
    ("INSAHN", "All Skills", "Grants small improvement to all 18 skills simultaneously", "+1 to all skills"),
    
    # Special quest-related mantra
    ("FANLO", "Special", "Part of tripartite key mantra; spoken at shrine reveals Key of Truth location", "Quest item"),
]

# Mapping of mantras to skills for quick lookup
MANTRA_TO_SKILL = {mantra.lower(): skill for mantra, skill, _, _ in COMPLETE_MANTRAS}

