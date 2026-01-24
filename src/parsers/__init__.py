# Ultima Underworld Binary File Parsers
#
# Low-level parsers for the various binary file formats used by
# Ultima Underworld I.

from .strings_parser import StringsParser, HuffmanNode, StringBlock
from .ark_parser import ArkParser, LevArkParser, CnvArkParser, ArkBlock
from .level_parser import LevelParser, Level, Tile, GameObject, TileType
from .objects_parser import (
    ObjectsParser,
    CommonObjectsParser,
    MeleeWeaponProperties,
    RangedWeaponProperties,
    ArmourProperties,
    ContainerProperties,
    LightSourceProperties,
    CritterProperties,
    AnimationProperties,
    CommonObjectProperties,
    ObjectClass,
    WeaponSkillType,
    ArmourCategory,
)
from .conversation_parser import (
    ConversationParser,
    Conversation,
    Instruction,
    Import,
    Opcode,
)
from .terrain_parser import (
    TerrainParser,
    TerrainData,
    TerrainType,
)
from .animation_parser import (
    AnimationFileParser,
    AnimationFrame,
)
from .assoc_anm_parser import (
    AssocAnmParser,
    NPCAnimationInfo,
)
from .texture_parser import (
    TextureParser,
    TextureData,
)
from .image_parser import (
    GrFileParser,
    BitmapType,
    BitmapHeader,
    SpriteImage,
)
from .save_game_parser import SaveGameParser
from .save_game_comparator import SaveGameComparator, ObjectChange

__all__ = [
    # Strings
    'StringsParser',
    'HuffmanNode',
    'StringBlock',
    # ARK containers
    'ArkParser',
    'LevArkParser',
    'CnvArkParser',
    'ArkBlock',
    # Levels
    'LevelParser',
    'Level',
    'Tile',
    'GameObject',
    'TileType',
    # Objects
    'ObjectsParser',
    'CommonObjectsParser',
    'MeleeWeaponProperties',
    'RangedWeaponProperties',
    'ArmourProperties',
    'ContainerProperties',
    'LightSourceProperties',
    'CritterProperties',
    'AnimationProperties',
    'CommonObjectProperties',
    'ObjectClass',
    'WeaponSkillType',
    'ArmourCategory',
    # Conversations
    'ConversationParser',
    'Conversation',
    'Instruction',
    'Import',
    'Opcode',
    # Terrain
    'TerrainParser',
    'TerrainData',
    'TerrainType',
    # Images
    'GrFileParser',
    'BitmapType',
    'BitmapHeader',
    'SpriteImage',
    'PaletteParser',
    # Animations
    'AnimationFileParser',
    'AnimationFrame',
    # Animation associations (NPC -> animation file mapping)
    'AssocAnmParser',
    'NPCAnimationInfo',
    # Textures (.TR files)
    'TextureParser',
    'TextureData',
    # Save games
    'SaveGameParser',
    'SaveGameComparator',
    'ObjectChange',
]
