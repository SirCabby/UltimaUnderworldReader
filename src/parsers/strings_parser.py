"""
STRINGS.PAK Parser for Ultima Underworld

The STRINGS.PAK file uses Huffman compression to store all game text.
Format:
- 2 bytes: number of nodes in Huffman tree
- N * 4 bytes: Huffman tree nodes (symbol, parent, left, right)
- 2 bytes: number of string blocks  
- M * 6 bytes: block directory (block_number:2, offset:4)
- Compressed string data

String blocks contain different types of game text:
- Block 1: General UI strings
- Block 2: Character creation, mantras
- Block 3: Scroll/book text
- Block 4: Object descriptions
- Block 5: Object "look" descriptions
- Block 6: Spell names
- Block 7: Conversation partner names
- Block 8: Wall/sign text
- Block 9: Text trap messages
- Block 10 (0x0a): Wall/floor descriptions
- Blocks 0x0c00+: Cutscene and conversation text
"""

import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class HuffmanNode:
    """A node in the Huffman tree."""
    symbol: int      # Character symbol (0-255)
    parent: int      # Parent node index
    left: int        # Left child index (-1 for leaf)
    right: int       # Right child index (-1 for leaf)
    
    def is_leaf(self) -> bool:
        """Check if this is a leaf node (no children)."""
        return self.left == 0xFF and self.right == 0xFF


@dataclass  
class StringBlock:
    """A block of strings from STRINGS.PAK."""
    block_number: int
    strings: List[str]


class StringsParser:
    """
    Parser for STRINGS.PAK Huffman-compressed string files.
    
    Usage:
        parser = StringsParser("path/to/STRINGS.PAK")
        parser.parse()
        
        # Get all strings from block 4 (object descriptions)
        descriptions = parser.get_block(4)
        
        # Get a specific string
        sword_desc = parser.get_string(4, 0)  # First item in block 4
    """
    
    # Well-known string block IDs
    BLOCK_UI = 1
    BLOCK_CHARGEN_MANTRAS = 2
    BLOCK_SCROLLS_BOOKS = 3
    BLOCK_OBJECT_NAMES = 4
    BLOCK_OBJECT_LOOK = 5
    BLOCK_SPELL_NAMES = 6
    BLOCK_NPC_NAMES = 7
    BLOCK_WALL_TEXT = 8
    BLOCK_TRAP_MESSAGES = 9
    BLOCK_WALL_FLOOR_DESC = 0x0a
    BLOCK_DEBUG = 0x18
    
    def __init__(self, filepath: str | Path):
        self.filepath = Path(filepath)
        self.nodes: List[HuffmanNode] = []
        self.root_node: int = 0
        self.blocks: Dict[int, StringBlock] = {}
        self._data: bytes = b''
        self._parsed = False
        
    def parse(self) -> None:
        """Parse the STRINGS.PAK file."""
        with open(self.filepath, 'rb') as f:
            self._data = f.read()
        
        offset = 0
        
        # Read number of Huffman nodes
        num_nodes = struct.unpack_from('<H', self._data, offset)[0]
        offset += 2
        
        # Read Huffman tree nodes
        self.nodes = []
        for i in range(num_nodes):
            symbol, parent, left, right = struct.unpack_from('BBBB', self._data, offset)
            self.nodes.append(HuffmanNode(symbol, parent, left, right))
            offset += 4
        
        # The root node is the last one
        self.root_node = num_nodes - 1
        
        # Read number of string blocks
        num_blocks = struct.unpack_from('<H', self._data, offset)[0]
        offset += 2
        
        # Read block directory
        block_directory: List[Tuple[int, int]] = []
        for _ in range(num_blocks):
            block_num, block_offset = struct.unpack_from('<HI', self._data, offset)
            block_directory.append((block_num, block_offset))
            offset += 6
        
        # Parse each string block
        for block_num, block_offset in block_directory:
            if block_offset == 0:
                continue
            strings = self._parse_block(block_offset)
            self.blocks[block_num] = StringBlock(block_num, strings)
        
        self._parsed = True
    
    def _parse_block(self, block_offset: int) -> List[str]:
        """Parse a single string block at the given offset."""
        # Block header: number of strings, then offsets to each string
        num_strings = struct.unpack_from('<H', self._data, block_offset)[0]
        
        # Read string offsets (relative to end of header)
        string_offsets: List[int] = []
        header_size = 2 + num_strings * 2
        
        for i in range(num_strings):
            str_offset = struct.unpack_from('<H', self._data, block_offset + 2 + i * 2)[0]
            # Offset is relative to end of header
            string_offsets.append(block_offset + header_size + str_offset)
        
        # Decode each string
        strings: List[str] = []
        for str_offset in string_offsets:
            decoded = self._decode_string(str_offset)
            strings.append(decoded)
        
        return strings
    
    def _decode_string(self, offset: int) -> str:
        """Decode a Huffman-compressed string starting at offset."""
        result = []
        bit_pos = 0
        byte_offset = offset
        
        while True:
            # Start at root node
            node_idx = self.root_node
            
            # Traverse tree until we hit a leaf
            while not self.nodes[node_idx].is_leaf():
                # Get next bit (big-endian: MSB first)
                byte_val = self._data[byte_offset]
                bit = (byte_val >> (7 - bit_pos)) & 1
                
                bit_pos += 1
                if bit_pos >= 8:
                    bit_pos = 0
                    byte_offset += 1
                
                # Traverse: 1 = right, 0 = left
                if bit == 1:
                    node_idx = self.nodes[node_idx].right
                else:
                    node_idx = self.nodes[node_idx].left
            
            # Got a leaf - extract symbol
            symbol = self.nodes[node_idx].symbol
            
            # '|' marks end of string
            if symbol == ord('|'):
                break
            
            result.append(chr(symbol))
        
        return ''.join(result)
    
    def get_block(self, block_number: int) -> Optional[List[str]]:
        """Get all strings from a specific block."""
        if not self._parsed:
            self.parse()
        
        if block_number in self.blocks:
            return self.blocks[block_number].strings
        return None
    
    def get_string(self, block_number: int, string_index: int) -> Optional[str]:
        """Get a specific string from a block."""
        block = self.get_block(block_number)
        if block and 0 <= string_index < len(block):
            return block[string_index]
        return None
    
    def get_all_blocks(self) -> Dict[int, List[str]]:
        """Get all parsed string blocks."""
        if not self._parsed:
            self.parse()
        return {num: block.strings for num, block in self.blocks.items()}
    
    def get_object_name(self, object_id: int) -> Optional[str]:
        """
        Get the name/description for an object ID.
        Object descriptions are in block 4.
        The format includes article separated by '_' and plural by '&'.
        """
        desc = self.get_string(self.BLOCK_OBJECT_NAMES, object_id)
        if desc:
            # Parse the description format: "article_name&plural"
            return desc
        return None
    
    def get_spell_name(self, spell_id: int) -> Optional[str]:
        """Get the name of a spell by ID."""
        return self.get_string(self.BLOCK_SPELL_NAMES, spell_id)
    
    def get_mantra(self, mantra_id: int) -> Optional[str]:
        """Get a mantra string."""
        return self.get_string(self.BLOCK_CHARGEN_MANTRAS, mantra_id)
    
    def dump_block_info(self) -> str:
        """Return a summary of all parsed blocks."""
        if not self._parsed:
            self.parse()
        
        lines = ["STRINGS.PAK Block Summary", "=" * 40]
        for block_num in sorted(self.blocks.keys()):
            block = self.blocks[block_num]
            lines.append(f"Block 0x{block_num:04X} ({block_num}): {len(block.strings)} strings")
        return '\n'.join(lines)


def main():
    """Test the strings parser."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python strings_parser.py <path_to_STRINGS.PAK>")
        sys.exit(1)
    
    parser = StringsParser(sys.argv[1])
    parser.parse()
    
    print(parser.dump_block_info())
    print()
    
    # Print first 10 object names
    print("First 20 Object Names (Block 4):")
    print("-" * 40)
    names = parser.get_block(StringsParser.BLOCK_OBJECT_NAMES)
    if names:
        for i, name in enumerate(names[:20]):
            print(f"  {i:3d} (0x{i:03X}): {name}")
    
    print()
    
    # Print spell names
    print("Spell Names (Block 6):")
    print("-" * 40)
    spells = parser.get_block(StringsParser.BLOCK_SPELL_NAMES)
    if spells:
        for i, spell in enumerate(spells[:30]):
            print(f"  {i:3d}: {spell}")


if __name__ == '__main__':
    main()



