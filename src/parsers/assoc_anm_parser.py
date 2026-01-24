"""
ASSOC.ANM Parser for Ultima Underworld

Parses the animation association file that maps NPC IDs to animation files.

Format:
- Bytes 0-255: 32 animation names (8 bytes each, null-padded)
  - Animation 0 -> CR00PAGE, Animation 1 -> CR01PAGE, etc. (octal numbering)
- Bytes 256-383: 64 NPC mappings (2 bytes each)
  - Byte 0: animation index (0-31) -> maps to CR{index:02o}PAGE file
  - Byte 1: auxiliary palette index (0-3) -> selects palette within animation file

The animation files (CrXXpage.nYY) contain 4 auxiliary palettes at offset 0x00-0x7F,
and the auxpal index selects which one to use (each palette is 32 bytes).
"""

import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class NPCAnimationInfo:
    """Animation information for an NPC."""
    npc_id: int                    # NPC object ID (0x40-0x7F)
    animation_index: int           # Index into animation table (0-31)
    animation_name: str            # Human-readable animation name
    animation_filename: str        # Animation filename (e.g., "CR00PAGE")
    auxpal_index: int              # Auxiliary palette index (0-3)


class AssocAnmParser:
    """
    Parser for ASSOC.ANM animation association file.
    
    Usage:
        parser = AssocAnmParser("Input/UW1/CRIT/ASSOC.ANM")
        parser.parse()
        
        # Get animation info for an NPC
        info = parser.get_npc_animation_info(0x4F)  # Headless
        print(f"Animation file: {info.animation_filename}")
        print(f"Aux palette: {info.auxpal_index}")
    """
    
    ANIMATION_NAME_SIZE = 8
    NUM_ANIMATIONS = 32
    NUM_NPCS = 64
    NPC_MAPPING_OFFSET = 256  # Starts after animation names
    
    def __init__(self, filepath: str | Path):
        self.filepath = Path(filepath)
        self._data: bytes = b''
        self._parsed = False
        
        # Parsed data
        self.animation_names: List[str] = []  # 32 animation names
        self.npc_mappings: Dict[int, NPCAnimationInfo] = {}  # NPC ID -> info
    
    def parse(self) -> None:
        """Parse the ASSOC.ANM file."""
        if not self.filepath.exists():
            return
        
        with open(self.filepath, 'rb') as f:
            self._data = f.read()
        
        expected_size = self.NPC_MAPPING_OFFSET + self.NUM_NPCS * 2
        if len(self._data) < expected_size:
            return
        
        # Parse animation names (32 × 8 bytes)
        self._parse_animation_names()
        
        # Parse NPC mappings (64 × 2 bytes)
        self._parse_npc_mappings()
        
        self._parsed = True
    
    def _parse_animation_names(self) -> None:
        """Parse the 32 animation names."""
        self.animation_names = []
        
        for i in range(self.NUM_ANIMATIONS):
            offset = i * self.ANIMATION_NAME_SIZE
            name_bytes = self._data[offset:offset + self.ANIMATION_NAME_SIZE]
            # Extract null-terminated string
            name = name_bytes.split(b'\x00')[0].decode('ascii', errors='replace')
            self.animation_names.append(name)
    
    def _parse_npc_mappings(self) -> None:
        """Parse the 64 NPC-to-animation mappings."""
        self.npc_mappings = {}
        
        for npc_slot in range(self.NUM_NPCS):
            offset = self.NPC_MAPPING_OFFSET + npc_slot * 2
            anim_idx = self._data[offset]
            auxpal = self._data[offset + 1]
            
            npc_id = 0x40 + npc_slot
            
            # Get animation name and filename
            if anim_idx < len(self.animation_names):
                anim_name = self.animation_names[anim_idx]
            else:
                anim_name = "unknown"
            
            # Animation filename uses octal numbering (e.g., CR00PAGE, CR10PAGE for index 8)
            anim_filename = f"CR{anim_idx:02o}PAGE"
            
            self.npc_mappings[npc_id] = NPCAnimationInfo(
                npc_id=npc_id,
                animation_index=anim_idx,
                animation_name=anim_name,
                animation_filename=anim_filename,
                auxpal_index=auxpal
            )
    
    def get_npc_animation_info(self, npc_id: int) -> Optional[NPCAnimationInfo]:
        """
        Get animation information for an NPC.
        
        Args:
            npc_id: NPC object ID (0x40-0x7F)
            
        Returns:
            NPCAnimationInfo or None if not found
        """
        if not self._parsed:
            self.parse()
        return self.npc_mappings.get(npc_id)
    
    def get_animation_filename(self, anim_index: int) -> str:
        """
        Get the animation filename for an animation index.
        
        Args:
            anim_index: Animation index (0-31)
            
        Returns:
            Animation filename (e.g., "CR00PAGE" for index 0)
        """
        return f"CR{anim_index:02o}PAGE"
    
    def get_animation_name(self, anim_index: int) -> Optional[str]:
        """
        Get the human-readable animation name for an index.
        
        Args:
            anim_index: Animation index (0-31)
            
        Returns:
            Animation name or None if not found
        """
        if not self._parsed:
            self.parse()
        
        if 0 <= anim_index < len(self.animation_names):
            return self.animation_names[anim_index]
        return None
    
    def get_all_npc_mappings(self) -> Dict[int, NPCAnimationInfo]:
        """Get all NPC-to-animation mappings."""
        if not self._parsed:
            self.parse()
        return self.npc_mappings
    
    def get_animation_names_list(self) -> List[str]:
        """Get the list of all animation names."""
        if not self._parsed:
            self.parse()
        return self.animation_names
