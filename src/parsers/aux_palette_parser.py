"""
Auxiliary Palette Parser for Ultima Underworld

Parses ALLPALS.DAT which contains 16-byte blocks of palette indices.
Each block represents a 16-color auxiliary palette by indexing into the main palette.
"""

import struct
from pathlib import Path
from typing import List, Optional, Dict


class AuxPaletteParser:
    """
    Parser for auxiliary palette files (ALLPALS.DAT).
    
    Each auxiliary palette is 16 bytes, containing indices into the main palette.
    
    Usage:
        parser = AuxPaletteParser("path/to/ALLPALS.DAT")
        parser.parse()
        aux_pal = parser.get_aux_palette(0)  # Get auxiliary palette 0 (16 indices)
    """
    
    COLORS_PER_AUX_PALETTE = 16
    BYTES_PER_AUX_PALETTE = 16
    
    def __init__(self, filepath: str | Path):
        self.filepath = Path(filepath)
        self._data: bytes = b''
        self.aux_palettes: Dict[int, List[int]] = {}
        self._parsed = False
    
    def parse(self) -> None:
        """Parse the auxiliary palette file."""
        if not self.filepath.exists():
            return
        
        with open(self.filepath, 'rb') as f:
            self._data = f.read()
        
        # Calculate number of auxiliary palettes
        num_aux_palettes = len(self._data) // self.BYTES_PER_AUX_PALETTE
        
        # Parse each auxiliary palette
        for i in range(num_aux_palettes):
            offset = i * self.BYTES_PER_AUX_PALETTE
            aux_pal = []
            
            for j in range(self.COLORS_PER_AUX_PALETTE):
                color_idx = offset + j
                if color_idx < len(self._data):
                    palette_index = struct.unpack_from('<B', self._data, color_idx)[0]
                    aux_pal.append(palette_index)
            
            if aux_pal:
                self.aux_palettes[i] = aux_pal
        
        self._parsed = True
    
    def get_aux_palette(self, index: int) -> Optional[List[int]]:
        """Get an auxiliary palette by index (returns list of palette indices)."""
        if not self._parsed:
            self.parse()
        return self.aux_palettes.get(index)
    
    def get_all_aux_palettes(self) -> Dict[int, List[int]]:
        """Get all parsed auxiliary palettes."""
        if not self._parsed:
            self.parse()
        return self.aux_palettes
