# Ultima Underworld Game Constants
#
# This module consolidates all game-specific constants and data
# that were previously scattered across multiple files.

from .runes import RUNE_NAMES, RUNE_MEANINGS
from .spells import (
    SPELL_RUNES,
    SPELL_DESCRIPTIONS,
    SPELL_CIRCLES,
    SPELL_MANA_COSTS,
    SPELL_MIN_LEVELS,
    UNDOCUMENTED_SPELLS,
    NPC_ONLY_SPELLS,
    PLAYER_SPELLS,
    PROTECTION_SPELL_TIERS,
    LIGHT_SPELL_LEVELS,
    HEALING_SPELL_TIERS,
    ENCHANTMENT_SPELL_RANGES,
    get_spell_mana_cost,
    get_spell_min_level,
    is_undocumented_spell,
    get_spell_info,
)
from .npcs import (
    NPC_TYPES,
    NPC_GOALS,
    NPC_ATTITUDES,
    get_npc_type_name,
)
from .objects import (
    OBJECT_CATEGORIES,
    STACKABLE_ITEMS,
    CARRYABLE_CATEGORIES,
    CARRYABLE_CONTAINERS,
    CATEGORY_DISPLAY_NAMES,
    get_category,
)
from .mantras import COMPLETE_MANTRAS
from .traps import (
    TRAP_ID_MIN,
    TRAP_ID_MAX,
    TRIGGER_ID_MIN,
    TRIGGER_ID_MAX,
    TRAP_TYPES,
    TRIGGER_TYPES,
    TrapInfo,
    TriggerInfo,
    TrapPurpose,
    is_trap,
    is_trigger,
    get_trap_info,
    get_trigger_info,
    get_trap_name,
    get_trigger_name,
    get_trap_purpose,
    describe_teleport,
    describe_damage,
    describe_change_terrain,
    describe_trap_effect,
    is_level_transition_teleport,
)

__all__ = [
    # Runes
    'RUNE_NAMES',
    'RUNE_MEANINGS',
    # Spells
    'SPELL_RUNES',
    'SPELL_DESCRIPTIONS',
    'SPELL_CIRCLES',
    'SPELL_MANA_COSTS',
    'SPELL_MIN_LEVELS',
    'UNDOCUMENTED_SPELLS',
    'NPC_ONLY_SPELLS',
    'PLAYER_SPELLS',
    'PROTECTION_SPELL_TIERS',
    'LIGHT_SPELL_LEVELS',
    'HEALING_SPELL_TIERS',
    'ENCHANTMENT_SPELL_RANGES',
    'get_spell_mana_cost',
    'get_spell_min_level',
    'is_undocumented_spell',
    'get_spell_info',
    # NPCs
    'NPC_TYPES',
    'NPC_GOALS',
    'NPC_ATTITUDES',
    'get_npc_type_name',
    # Mantras
    'COMPLETE_MANTRAS',
    # Objects
    'OBJECT_CATEGORIES',
    'STACKABLE_ITEMS',
    'CARRYABLE_CATEGORIES',
    'CARRYABLE_CONTAINERS',
    'CATEGORY_DISPLAY_NAMES',
    'get_category',
    # Traps and Triggers
    'TRAP_ID_MIN',
    'TRAP_ID_MAX',
    'TRIGGER_ID_MIN',
    'TRIGGER_ID_MAX',
    'TRAP_TYPES',
    'TRIGGER_TYPES',
    'TrapInfo',
    'TriggerInfo',
    'TrapPurpose',
    'is_trap',
    'is_trigger',
    'get_trap_info',
    'get_trigger_info',
    'get_trap_name',
    'get_trigger_name',
    'get_trap_purpose',
    'describe_teleport',
    'describe_damage',
    'describe_change_terrain',
    'describe_trap_effect',
    'is_level_transition_teleport',
]
