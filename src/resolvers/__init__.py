"""
Resolvers for Ultima Underworld data.

Shared resolution logic for enchantments, locks, spells, and other
game mechanics that need to be interpreted from raw object data.
"""

from .lock_resolver import resolve_lock_info, resolve_door_lock, resolve_container_lock
from .spell_resolver import SpellResolver, get_spell_names
from .enchantment_resolver import EnchantmentResolver, get_item_effect

__all__ = [
    # Lock resolution
    'resolve_lock_info',
    'resolve_door_lock',
    'resolve_container_lock',
    # Spell resolution
    'SpellResolver',
    'get_spell_names',
    # Enchantment resolution
    'EnchantmentResolver',
    'get_item_effect',
]
