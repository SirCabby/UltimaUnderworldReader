"""
ARK Archive Parser for Ultima Underworld

ARK files are container formats that store multiple data blocks.
Used for LEV.ARK (level data) and CNV.ARK (conversations).

Format:
- 2 bytes: number of blocks in file
- N * 4 bytes: absolute file offsets to each block (0 = empty block)
- Block data at each offset

For LEV.ARK (UW1): 135 blocks (9 levels * 15 blocks per level)
  - Blocks 0-8: Level tilemap + master object list
  - Blocks 9-17: Object animation overlay info
  - Blocks 18-26: Texture mapping
  - Blocks 27-35: Automap info
  - Blocks 36-44: Map notes
  - Remaining blocks unused

For CNV.ARK: Up to 256 conversation slots
"""

import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class ArkBlock:
    """A data block from an ARK archive."""
    index: int
    offset: int
    size: int
    data: bytes


class ArkParser:
    """
    Parser for ARK archive files (LEV.ARK, CNV.ARK).
    
    Usage:
        ark = ArkParser("path/to/LEV.ARK")
        ark.parse()
        
        # Get specific block data
        level_0_data = ark.get_block(0)
        
        # Get all non-empty blocks
        all_blocks = ark.get_all_blocks()
    """
    
    def __init__(self, filepath: str | Path):
        self.filepath = Path(filepath)
        self.num_blocks: int = 0
        self.blocks: Dict[int, ArkBlock] = {}
        self._data: bytes = b''
        self._parsed = False
        
    def parse(self) -> None:
        """Parse the ARK archive file."""
        with open(self.filepath, 'rb') as f:
            self._data = f.read()
        
        # Read number of blocks
        self.num_blocks = struct.unpack_from('<H', self._data, 0)[0]
        
        # Read block offset table
        offsets: List[int] = []
        for i in range(self.num_blocks):
            offset = struct.unpack_from('<I', self._data, 2 + i * 4)[0]
            offsets.append(offset)
        
        # Calculate block sizes and extract data
        # Size is determined by distance to next non-zero offset or end of file
        self.blocks = {}
        
        # Get list of (index, offset) pairs for non-empty blocks, sorted by offset
        non_empty = [(i, off) for i, off in enumerate(offsets) if off != 0]
        non_empty.sort(key=lambda x: x[1])
        
        for idx, (block_idx, offset) in enumerate(non_empty):
            # Find the next offset to calculate size
            if idx + 1 < len(non_empty):
                next_offset = non_empty[idx + 1][1]
            else:
                next_offset = len(self._data)
            
            size = next_offset - offset
            data = self._data[offset:offset + size]
            
            self.blocks[block_idx] = ArkBlock(
                index=block_idx,
                offset=offset,
                size=size,
                data=data
            )
        
        self._parsed = True
    
    def get_block(self, index: int) -> Optional[bytes]:
        """Get the raw data for a specific block."""
        if not self._parsed:
            self.parse()
        
        if index in self.blocks:
            return self.blocks[index].data
        return None
    
    def get_block_info(self, index: int) -> Optional[ArkBlock]:
        """Get full block info including offset and size."""
        if not self._parsed:
            self.parse()
        
        return self.blocks.get(index)
    
    def get_all_blocks(self) -> Dict[int, bytes]:
        """Get all non-empty blocks as a dict of index -> data."""
        if not self._parsed:
            self.parse()
        
        return {idx: block.data for idx, block in self.blocks.items()}
    
    def get_block_count(self) -> int:
        """Get total number of block slots (including empty)."""
        if not self._parsed:
            self.parse()
        return self.num_blocks
    
    def get_non_empty_count(self) -> int:
        """Get count of non-empty blocks."""
        if not self._parsed:
            self.parse()
        return len(self.blocks)
    
    def dump_info(self) -> str:
        """Return a summary of the archive."""
        if not self._parsed:
            self.parse()
        
        lines = [
            f"ARK Archive: {self.filepath.name}",
            "=" * 50,
            f"Total block slots: {self.num_blocks}",
            f"Non-empty blocks: {len(self.blocks)}",
            "",
            "Block details:",
            "-" * 50,
        ]
        
        for idx in sorted(self.blocks.keys()):
            block = self.blocks[idx]
            lines.append(
                f"  Block {idx:3d}: offset=0x{block.offset:08X}, "
                f"size={block.size:6d} bytes"
            )
        
        return '\n'.join(lines)


class LevArkParser(ArkParser):
    """
    Specialized parser for LEV.ARK level data.
    
    Block layout for UW1 (135 blocks total, 9 levels):
    - Blocks 0-8: Level tilemap + master object list (one per level)
    - Blocks 9-17: Object animation overlay info
    - Blocks 18-26: Texture mapping
    - Blocks 27-35: Automap info
    - Blocks 36-44: Map notes
    """
    
    NUM_LEVELS = 9
    BLOCKS_PER_CATEGORY = 9
    
    # Block category offsets
    LEVEL_DATA_START = 0
    ANIM_OVERLAY_START = 9
    TEXTURE_MAP_START = 18
    AUTOMAP_START = 27
    MAP_NOTES_START = 36
    
    def get_level_data(self, level: int) -> Optional[bytes]:
        """Get the main level data block (tilemap + objects) for a level."""
        if not 0 <= level < self.NUM_LEVELS:
            return None
        return self.get_block(self.LEVEL_DATA_START + level)
    
    def get_texture_mapping(self, level: int) -> Optional[bytes]:
        """Get the texture mapping data for a level."""
        if not 0 <= level < self.NUM_LEVELS:
            return None
        return self.get_block(self.TEXTURE_MAP_START + level)
    
    def get_automap_info(self, level: int) -> Optional[bytes]:
        """Get the automap data for a level."""
        if not 0 <= level < self.NUM_LEVELS:
            return None
        return self.get_block(self.AUTOMAP_START + level)
    
    def get_animation_overlay(self, level: int) -> Optional[bytes]:
        """Get the animation overlay data for a level."""
        if not 0 <= level < self.NUM_LEVELS:
            return None
        return self.get_block(self.ANIM_OVERLAY_START + level)


class CnvArkParser(ArkParser):
    """
    Specialized parser for CNV.ARK conversation data.
    
    Contains up to 256 conversation slots. Each conversation
    is bytecode for the conversation VM.
    """
    
    MAX_CONVERSATIONS = 256
    
    def get_conversation(self, slot: int) -> Optional[bytes]:
        """Get the conversation bytecode for a specific slot."""
        if not 0 <= slot < self.MAX_CONVERSATIONS:
            return None
        return self.get_block(slot)
    
    def get_all_conversations(self) -> Dict[int, bytes]:
        """Get all non-empty conversation slots."""
        return {
            idx: data 
            for idx, data in self.get_all_blocks().items()
            if idx < self.MAX_CONVERSATIONS
        }


def main():
    """Test the ARK parser."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python ark_parser.py <path_to_ARK_file>")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    # Detect file type and use appropriate parser
    if 'LEV' in filepath.upper():
        parser = LevArkParser(filepath)
    elif 'CNV' in filepath.upper():
        parser = CnvArkParser(filepath)
    else:
        parser = ArkParser(filepath)
    
    parser.parse()
    print(parser.dump_info())
    
    # Show first few bytes of first non-empty block
    if parser.blocks:
        first_idx = min(parser.blocks.keys())
        first_block = parser.blocks[first_idx]
        print(f"\nFirst 64 bytes of block {first_idx}:")
        hex_dump = ' '.join(f'{b:02X}' for b in first_block.data[:64])
        print(hex_dump)


if __name__ == '__main__':
    main()



