"""
Palette Parser for Ultima Underworld

Parses palette files (PALS.DAT, ALLPALS.DAT) to extract color palettes.
Palettes are typically 256 colors, each color is 3 bytes (RGB).
"""

import struct
from pathlib import Path
from typing import List, Tuple, Optional, Dict


class PaletteParser:
    """
    Parser for palette files.
    
    Usage:
        parser = PaletteParser("path/to/PALS.DAT")
        palette = parser.get_palette(0)  # Get palette 0 (256 RGB tuples)
    """
    
    COLORS_PER_PALETTE = 256
    BYTES_PER_COLOR = 3  # RGB
    
    def __init__(self, filepath: str | Path):
        self.filepath = Path(filepath)
        self._data: bytes = b''
        self.palettes: Dict[int, List[Tuple[int, int, int]]] = {}
        self._parsed = False
    
    def parse(self) -> None:
        """Parse the palette file."""
        if not self.filepath.exists():
            return
        
        with open(self.filepath, 'rb') as f:
            self._data = f.read()
        
        # Calculate number of palettes
        palette_size = self.COLORS_PER_PALETTE * self.BYTES_PER_COLOR
        num_palettes = len(self._data) // palette_size
        
        # Parse each palette
        for i in range(num_palettes):
            offset = i * palette_size
            palette = []
            
            for j in range(self.COLORS_PER_PALETTE):
                color_offset = offset + j * self.BYTES_PER_COLOR
                if color_offset + self.BYTES_PER_COLOR <= len(self._data):
                    r, g, b = struct.unpack_from('3B', self._data, color_offset)
                    # VGA palette uses 0-63 range, scale to 0-255
                    palette.append((r * 4, g * 4, b * 4))
            
            if palette:
                self.palettes[i] = palette
        
        self._parsed = True
    
    def get_palette(self, index: int) -> Optional[List[Tuple[int, int, int]]]:
        """Get a palette by index."""
        if not self._parsed:
            self.parse()
        return self.palettes.get(index)
    
    def get_all_palettes(self) -> Dict[int, List[Tuple[int, int, int]]]:
        """Get all parsed palettes."""
        if not self._parsed:
            self.parse()
        return self.palettes
