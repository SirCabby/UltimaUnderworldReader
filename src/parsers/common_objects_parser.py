"""
Common Object Properties Parser for Ultima Underworld

COMOBJ.DAT - Common object properties for all 512 object types.
Contains weight, value, and various flags for each object.

File format:
- 2-byte header (skip)
- 512 x 11-byte entries containing weight, value, and various flags
"""

import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional
from enum import IntFlag


class CommonObjectFlags(IntFlag):
    """Flags from COMOBJ.DAT for each object."""
    NONE = 0
    CAN_BE_OWNED = 0x0001
    ENCHANTABLE = 0x0002
    CAN_HAVE_QUALITY = 0x0004  
    # More flags TBD


@dataclass
class CommonObjectProperties:
    """Common properties for any object type from COMOBJ.DAT.
    
    Format (11 bytes per object):
    [0] bits 0-4: 3D height, bits 5-7: radius
    [1] bits 0-3: unknown flags, bits 4-7: mass fractional part (in 0.1 stones)
    [2] mass whole part (in 1.6 stone units, multiply by 16 to get 0.1 stones)
    [3] quality/type flags (0x60 = 96 is common)
    [4] value in gold pieces
    [5] bits 0-3: look description block, bit 4: can be picked up
    [6-10]: various flags
    
    Mass formula: mass_in_tenths = byte[2] * 16 + ((byte[1] >> 4) & 0x0F)
    This gives mass in 0.1 stone units (divide by 10 for stones).
    """
    object_id: int
    raw_data: bytes  # Raw 11-byte entry
    
    # Parsed fields (based on format analysis)
    height: int      # 3D height
    mass_value: int  # Combined mass/value field (legacy, use mass property)
    flags: int
    
    @property
    def is_3d_object(self) -> bool:
        """Check if this renders as a 3D object."""
        return self.height > 0
    
    @property
    def mass(self) -> int:
        """Mass in 0.1 stones (tenths of a stone).
        
        Formula: byte[2] * 16 + ((byte[1] >> 4) & 0x0F)
        - byte[2] represents 1.6 stone units (16 tenths each)
        - bits 4-7 of byte[1] represent the fractional part in 0.1 stones
        """
        return self.raw_data[2] * 16 + ((self.raw_data[1] >> 4) & 0x0F)
    
    @property
    def mass_stones(self) -> float:
        """Mass in stones (e.g., 2.4 stones)."""
        return self.mass / 10.0
    
    @property
    def value(self) -> int:
        """Value in gold pieces (not tenths)."""
        return self.raw_data[4]
    
    @property 
    def value_gold(self) -> float:
        """Value in gold pieces (same as value, for API consistency)."""
        return float(self.value)
    
    @property
    def can_be_picked_up(self) -> bool:
        """Whether this object can be picked up by the player."""
        return bool(self.raw_data[5] & 0x10)


class CommonObjectsParser:
    """
    Parser for COMOBJ.DAT - common properties for all 512 object types.
    
    Usage:
        parser = CommonObjectsParser("path/to/COMOBJ.DAT")
        parser.parse()
        
        # Get properties for an object
        sword = parser.get_object(5)
        print(f"Mass: {sword.mass_stones} stones")
        print(f"Value: {sword.value} gold")
    """
    
    HEADER_SIZE = 2
    ENTRY_SIZE = 11
    NUM_OBJECTS = 512
    
    def __init__(self, filepath: str | Path):
        self.filepath = Path(filepath)
        self._data: bytes = b''
        self._parsed = False
        self.objects: Dict[int, CommonObjectProperties] = {}
    
    def parse(self) -> None:
        """Parse the COMOBJ.DAT file."""
        with open(self.filepath, 'rb') as f:
            self._data = f.read()
        
        # Parse each object entry (skip 2-byte header)
        for i in range(self.NUM_OBJECTS):
            offset = self.HEADER_SIZE + i * self.ENTRY_SIZE
            if offset + self.ENTRY_SIZE > len(self._data):
                break
            
            raw = self._data[offset:offset + self.ENTRY_SIZE]
            
            # Parse basic fields
            height = raw[0] & 0x1F  # Lower 5 bits
            mass_value = struct.unpack_from('<H', raw, 1)[0]
            flags = struct.unpack_from('<H', raw, 3)[0]
            
            self.objects[i] = CommonObjectProperties(
                object_id=i,
                raw_data=raw,
                height=height,
                mass_value=mass_value,
                flags=flags
            )
        
        self._parsed = True
    
    def get_object(self, object_id: int) -> Optional[CommonObjectProperties]:
        """Get common properties for an object ID."""
        if not self._parsed:
            self.parse()
        return self.objects.get(object_id)
    
    def get_all_objects(self) -> Dict[int, CommonObjectProperties]:
        """Get all object properties."""
        if not self._parsed:
            self.parse()
        return self.objects


def main():
    """Test the common objects parser."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python common_objects_parser.py <COMOBJ.DAT>")
        sys.exit(1)
    
    parser = CommonObjectsParser(sys.argv[1])
    parser.parse()
    
    print("COMOBJ.DAT Contents (first 32 entries)")
    print("=" * 60)
    
    for obj_id in range(32):
        obj = parser.objects.get(obj_id)
        if obj:
            hex_data = ' '.join(f'{b:02X}' for b in obj.raw_data)
            print(f"  {obj_id:3d} (0x{obj_id:02X}): {hex_data}")
            print(f"       Mass: {obj.mass_stones:.1f} stones, Value: {obj.value} gold")


if __name__ == '__main__':
    main()
