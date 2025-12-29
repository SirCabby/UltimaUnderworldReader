"""
Game object and item data models for Ultima Underworld.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional

from ..constants import OBJECT_CATEGORIES, get_category, get_detailed_category

# Re-export for backward compatibility
__all__ = ['GameObjectInfo', 'ItemInfo', 'OBJECT_CATEGORIES', 'get_category']


@dataclass
class GameObjectInfo:
    """Complete information about a placed game object."""
    # Object identification
    object_id: int              # Item type ID (0-511)
    index: int                  # Index in master object list
    level: int                  # Level number (0-8)
    
    # Name and description
    name: str = ""              # Object name from strings
    description: str = ""       # Full description
    
    # Position
    tile_x: int = 0
    tile_y: int = 0
    x_pos: int = 0              # Position within tile (0-7)
    y_pos: int = 0
    z_pos: int = 0              # Height
    heading: int = 0            # Direction (0-7)
    
    # Properties
    quality: int = 0
    owner: int = 0
    quantity: int = 0
    flags: int = 0
    
    # State flags
    is_enchanted: bool = False
    is_invisible: bool = False
    is_quantity: bool = False
    
    # Object classification
    object_class: str = ""      # Base category e.g., "weapon", "armor", "container"
    detailed_category: str = "" # Detailed category e.g., "door_locked", "spell_scroll"
    
    # Linked objects
    next_index: int = 0
    special_link: int = 0
    
    # Extra metadata (for special objects like tmap, doors, etc.)
    extra_info: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON export."""
        result = {
            'object_id': self.object_id,
            'object_id_hex': f'0x{self.object_id:03X}',
            'index': self.index,
            'level': self.level,
            'name': self.name,
            'description': self.description,
            'position': {
                'tile_x': self.tile_x,
                'tile_y': self.tile_y,
                'x': self.x_pos,
                'y': self.y_pos,
                'z': self.z_pos,
                'heading': self.heading
            },
            'quality': self.quality,
            'owner': self.owner,
            'quantity': self.quantity,
            'flags': self.flags,
            'is_enchanted': self.is_enchanted,
            'is_invisible': self.is_invisible,
            'object_class': self.object_class,
            'detailed_category': self.detailed_category,
            'next_index': self.next_index,
            'special_link': self.special_link
        }
        
        # Include extra_info if present
        if self.extra_info:
            result['extra_info'] = self.extra_info
        
        return result


@dataclass
class ItemInfo:
    """Information about an item type (not placed instance)."""
    item_id: int                # Object type ID
    name: str                   # Item name
    name_plural: str = ""       # Plural form
    article: str = "a"          # Article (a, an, some)
    
    # Object classification
    object_class: int = 0       # Class bits 6-8
    object_subclass: int = 0    # Subclass bits 4-5
    category: str = ""          # Human-readable category
    
    # Class-specific properties
    properties: Dict[str, Any] = field(default_factory=dict)
    
    # Common properties from COMOBJ.DAT
    height: int = 0
    mass: int = 0               # Mass in 0.1 stones
    value: int = 0              # Value in 0.1 gold pieces
    flags: int = 0
    
    # Flags
    can_be_owned: bool = False
    is_enchantable: bool = False
    can_be_picked_up: bool = False  # Whether player can carry this
    
    @property
    def mass_stones(self) -> float:
        """Mass in stones (for display)."""
        return self.mass / 10.0
    
    @property
    def value_gold(self) -> float:
        """Value in gold pieces (for display)."""
        return self.value / 10.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON export."""
        return {
            'item_id': self.item_id,
            'item_id_hex': f'0x{self.item_id:03X}',
            'name': self.name,
            'name_plural': self.name_plural,
            'article': self.article,
            'category': self.category,
            'object_class': self.object_class,
            'object_subclass': self.object_subclass,
            'height': self.height,
            'mass': self.mass,
            'value': self.value,
            'flags': self.flags,
            'properties': self.properties
        }
