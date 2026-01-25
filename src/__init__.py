# Ultima Underworld Data Extraction Toolkit
#
# A comprehensive toolkit for extracting and analyzing game data from
# Ultima Underworld I: The Stygian Abyss.
#
# Main components:
# - parsers: Low-level binary file parsers (ARK, strings, objects, levels)
# - extractors: High-level data extractors (items, NPCs, spells, secrets)
# - models: Data models for game objects
# - exporters: Export formats (JSON, XLSX)
# - constants: Game-specific constants and data tables
# - resolvers: Shared resolution logic (enchantments, locks, spells)

from .parsers import (
    StringsParser,
    LevelParser,
    ObjectsParser,
    CommonObjectsParser,
    ConversationParser,
    ArkParser,
    LevArkParser,
    CnvArkParser,
)

from .extractors import (
    ItemExtractor,
    NPCExtractor,
    SpellExtractor,
    SecretFinder,
)

from .models import (
    GameObjectInfo,
    ItemInfo,
    NPCInfo,
)

from .exporters import (
    JsonExporter,
)

from .resolvers import (
    resolve_lock_info,
    resolve_door_lock,
    resolve_container_lock,
    SpellResolver,
    get_spell_names,
    EnchantmentResolver,
    get_item_effect,
)

from .utils import (
    parse_item_name,
    extract_name_only,
    format_hex_id,
    clamp,
    quality_to_offset,
    get_quality_description,
    get_door_condition,
    is_massive_door,
)

__version__ = "1.0.0"

__all__ = [
    # Parsers
    'StringsParser',
    'LevelParser',
    'ObjectsParser',
    'CommonObjectsParser',
    'ConversationParser',
    'ArkParser',
    'LevArkParser',
    'CnvArkParser',
    # Extractors
    'ItemExtractor',
    'NPCExtractor',
    'SpellExtractor',
    'SecretFinder',
    # Models
    'GameObjectInfo',
    'ItemInfo',
    'NPCInfo',
    # Output
    'JsonExporter',
    # Resolvers
    'resolve_lock_info',
    'resolve_door_lock',
    'resolve_container_lock',
    'SpellResolver',
    'get_spell_names',
    'EnchantmentResolver',
    'get_item_effect',
    # Utils
    'parse_item_name',
    'extract_name_only',
    'format_hex_id',
    'clamp',
    'quality_to_offset',
    'get_quality_description',
    'get_door_condition',
    'is_massive_door',
]
