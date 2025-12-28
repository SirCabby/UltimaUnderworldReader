"""
NPC Extractor for Ultima Underworld

Extracts all NPC data from game files, including:
- All NPCs in all levels
- Their stats, positions, and conversation slots
"""

from pathlib import Path
from typing import Dict, List, Any

from ..parsers.strings_parser import StringsParser
from ..parsers.level_parser import LevelParser
from ..parsers.conversation_parser import ConversationParser
from ..models.npc import NPCInfo
from ..constants import get_npc_type_name
from ..utils import parse_item_name


class NPCExtractor:
    """
    Extracts all NPC data from Ultima Underworld.
    
    Usage:
        extractor = NPCExtractor("path/to/DATA")
        extractor.extract()
        
        npcs = extractor.get_all_npcs()
    """
    
    def __init__(self, data_path: str | Path):
        self.data_path = Path(data_path)
        
        # Initialize parsers
        self.strings = StringsParser(self.data_path / "STRINGS.PAK")
        self.levels = LevelParser(self.data_path / "LEV.ARK")
        self.conversations = ConversationParser(self.data_path / "CNV.ARK")
        
        # Extracted data
        self.npcs: List[NPCInfo] = []
        self.npc_names: Dict[int, str] = {}  # conversation slot -> name
        
        self._extracted = False
    
    def extract(self) -> None:
        """Extract all NPC data."""
        # Parse source files
        self.strings.parse()
        self.levels.parse()
        self.conversations.parse()
        
        # Extract NPC names from conversation blocks
        self._extract_npc_names()
        
        # Extract NPCs from all levels
        self._extract_npcs()
        
        self._extracted = True
    
    def _extract_npc_names(self) -> None:
        """Extract NPC names from string block 7."""
        # NPC names are in block 7, starting at string 17 for conv slot 1
        names = self.strings.get_block(StringsParser.BLOCK_NPC_NAMES) or []
        
        for i, name in enumerate(names):
            if name.strip():
                # String index 17+ corresponds to conversation slots
                slot = i - 16
                if slot >= 0:
                    self.npc_names[slot] = name.strip()
    
    def _extract_npcs(self) -> None:
        """Extract all NPCs from all levels."""
        object_names = self.strings.get_block(StringsParser.BLOCK_OBJECT_NAMES) or []
        
        for level_num in range(9):
            level = self.levels.get_level(level_num)
            if not level:
                continue
            
            for npc in level.get_all_npcs():
                # Get type name
                type_name = get_npc_type_name(npc.item_id)
                
                # Get display name from object names
                display_name = ""
                if npc.item_id < len(object_names):
                    raw = object_names[npc.item_id]
                    display_name, _, _ = parse_item_name(raw)
                
                # Get conversation name if available
                conv_name = self.npc_names.get(npc.npc_whoami, "")
                name = conv_name if conv_name else display_name
                
                # Get inventory link - for NPCs, quantity_or_link (when not is_quantity) is inventory start
                inv_link = npc.quantity_or_link if not npc.is_quantity else 0
                
                info = NPCInfo(
                    object_id=npc.item_id,
                    index=npc.index,
                    level=level_num,
                    name=name,
                    tile_x=npc.tile_x,
                    tile_y=npc.tile_y,
                    z_pos=npc.z_pos,
                    heading=npc.heading,
                    hp=npc.npc_hp,
                    npc_level=npc.npc_level,
                    goal=npc.npc_goal,
                    goal_target=npc.npc_gtarg,
                    attitude=npc.npc_attitude,
                    home_x=npc.npc_xhome,
                    home_y=npc.npc_yhome,
                    hunger=npc.npc_hunger,
                    conversation_slot=npc.npc_whoami,
                    talked_to=npc.npc_talkedto,
                    quality=npc.quality,
                    owner=npc.owner,
                    special_link=inv_link,
                    is_invisible=npc.is_invisible
                )
                
                self.npcs.append(info)
    
    def get_all_npcs(self) -> List[NPCInfo]:
        """Get all extracted NPCs."""
        if not self._extracted:
            self.extract()
        return self.npcs
    
    def get_npcs_by_level(self, level: int) -> List[NPCInfo]:
        """Get all NPCs on a specific level."""
        if not self._extracted:
            self.extract()
        return [npc for npc in self.npcs if npc.level == level]
    
    def get_npcs_with_conversation(self) -> List[NPCInfo]:
        """Get NPCs that have conversation scripts."""
        if not self._extracted:
            self.extract()
        return [npc for npc in self.npcs 
                if npc.conversation_slot in self.conversations.conversations]
    
    def get_npcs_by_type(self, object_id: int) -> List[NPCInfo]:
        """Get all NPCs of a specific type."""
        if not self._extracted:
            self.extract()
        return [npc for npc in self.npcs if npc.object_id == object_id]
    
    def get_hostile_npcs(self) -> List[NPCInfo]:
        """Get all hostile or berserk NPCs."""
        if not self._extracted:
            self.extract()
        return [npc for npc in self.npcs if npc.attitude >= 2]
    
    def get_npc_summary(self) -> Dict[str, Any]:
        """Get a summary of NPCs."""
        if not self._extracted:
            self.extract()
        
        by_level = {}
        by_attitude = {0: 0, 1: 0, 2: 0, 3: 0}
        by_type = {}
        with_conv = 0
        
        for npc in self.npcs:
            by_level[npc.level] = by_level.get(npc.level, 0) + 1
            by_attitude[npc.attitude] = by_attitude.get(npc.attitude, 0) + 1
            
            type_name = get_npc_type_name(npc.object_id)
            by_type[type_name] = by_type.get(type_name, 0) + 1
            
            if npc.conversation_slot in self.conversations.conversations:
                with_conv += 1
        
        return {
            'total': len(self.npcs),
            'by_level': by_level,
            'by_attitude': {
                'friendly': by_attitude[0],
                'upset': by_attitude[1],
                'hostile': by_attitude[2],
                'berserk': by_attitude[3]
            },
            'by_type': by_type,
            'with_conversation': with_conv
        }


def main():
    """Test the NPC extractor."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python npc_extractor.py <path_to_DATA_folder>")
        sys.exit(1)
    
    extractor = NPCExtractor(sys.argv[1])
    extractor.extract()
    
    summary = extractor.get_npc_summary()
    
    print("NPC Summary:")
    print("=" * 50)
    print(f"Total NPCs: {summary['total']}")
    print(f"With conversations: {summary['with_conversation']}")
    
    print("\nBy Level:")
    for level in range(9):
        count = summary['by_level'].get(level, 0)
        print(f"  Level {level}: {count}")
    
    print("\nBy Attitude:")
    for att, count in summary['by_attitude'].items():
        print(f"  {att}: {count}")
    
    print("\nBy Type (top 10):")
    sorted_types = sorted(summary['by_type'].items(), key=lambda x: -x[1])
    for type_name, count in sorted_types[:10]:
        print(f"  {type_name}: {count}")
    
    # Show some NPCs with conversations
    print("\nNPCs with conversations (first 10):")
    conv_npcs = extractor.get_npcs_with_conversation()[:10]
    for npc in conv_npcs:
        print(f"  {npc.name or get_npc_type_name(npc.object_id)} "
              f"@ L{npc.level} ({npc.tile_x},{npc.tile_y}) "
              f"conv={npc.conversation_slot}")


if __name__ == '__main__':
    main()
