"""
NPC data model for Ultima Underworld.
"""

from dataclasses import dataclass
from typing import Dict, Any

from ..constants import NPC_TYPES, NPC_GOALS, NPC_ATTITUDES, get_npc_type_name

# Re-export for backward compatibility
__all__ = ['NPCInfo', 'NPC_TYPES', 'get_npc_type_name']


@dataclass
class NPCInfo:
    """Complete information about an NPC."""
    # Object identification
    object_id: int              # NPC type ID (0x40-0x7F)
    index: int                  # Index in master object list
    level: int                  # Level number (0-8)
    
    # Name
    name: str = ""              # NPC type name from strings
    
    # Position
    tile_x: int = 0
    tile_y: int = 0
    z_pos: int = 0
    heading: int = 0
    
    # NPC stats
    hp: int = 0
    npc_level: int = 0
    
    # Behavior
    goal: int = 0
    goal_target: int = 0
    attitude: int = 0           # 0=hostile, 1=upset, 2=mellow, 3=friendly
    home_x: int = 0
    home_y: int = 0
    hunger: int = 0
    
    # Conversation
    conversation_slot: int = 0  # npc_whoami - which conversation to use
    talked_to: bool = False
    
    # Properties
    quality: int = 0
    owner: int = 0
    special_link: int = 0       # Link to first inventory item
    
    # State
    is_invisible: bool = False
    
    @property
    def attitude_name(self) -> str:
        """Get attitude name from constants."""
        return NPC_ATTITUDES.get(self.attitude, f'unknown({self.attitude})')
    
    @property
    def goal_name(self) -> str:
        """Get human-readable goal."""
        return NPC_GOALS.get(self.goal, f'goal_{self.goal}')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON export."""
        return {
            'object_id': self.object_id,
            'object_id_hex': f'0x{self.object_id:02X}',
            'index': self.index,
            'level': self.level,
            'name': self.name,
            'position': {
                'tile_x': self.tile_x,
                'tile_y': self.tile_y,
                'z': self.z_pos,
                'heading': self.heading
            },
            'stats': {
                'hp': self.hp,
                'level': self.npc_level,
                'hunger': self.hunger
            },
            'behavior': {
                'goal': self.goal,
                'goal_name': self.goal_name,
                'goal_target': self.goal_target,
                'attitude': self.attitude,
                'attitude_name': self.attitude_name,
                'home_x': self.home_x,
                'home_y': self.home_y
            },
            'conversation': {
                'slot': self.conversation_slot,
                'talked_to': self.talked_to
            },
            'quality': self.quality,
            'owner': self.owner,
            'is_invisible': self.is_invisible
        }
