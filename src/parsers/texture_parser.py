"""
Texture Parser for Ultima Underworld .TR files

Parses .TR texture files that contain wall and floor textures.

Format:
- Byte 0: File type (always 2 for textures)
- Byte 1: X and Y resolution (textures are always square)
- Bytes 2-3: Number of textures (Int16)
- Bytes 4+: Offset table (Int32 per texture)
- Data: Raw palette indices, xyres^2 bytes per texture
- All textures use palette #0
"""

import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from PIL import Image
except ImportError:
    Image = None


@dataclass
class TextureData:
    """A single texture from a .TR file."""
    index: int
    resolution: int
    data: bytes


class TextureParser:
    """
    Parser for .TR texture files.
    
    Usage:
        parser = TextureParser("path/to/W64.TR")
        parser.parse()
        
        # Get a texture by index
        texture = parser.get_texture(0)
        
        # Convert to PIL Image (requires palette)
        img = parser.texture_to_image(texture, palette)
    """
    
    def __init__(self, filepath: str | Path):
        self.filepath = Path(filepath)
        self._data: bytes = b''
        self._parsed = False
        
        # File properties
        self.file_type: int = 0
        self.resolution: int = 0
        self.num_textures: int = 0
        
        # Parsed textures
        self.textures: Dict[int, TextureData] = {}
    
    def parse(self) -> None:
        """Parse the .TR texture file."""
        if not self.filepath.exists():
            return
        
        with open(self.filepath, 'rb') as f:
            self._data = f.read()
        
        if len(self._data) < 4:
            return
        
        # Read header
        self.file_type = self._data[0]
        self.resolution = self._data[1]
        self.num_textures = struct.unpack_from('<H', self._data, 2)[0]
        
        # Validate
        if self.file_type != 2:
            return  # Not a texture file
        
        if self.resolution == 0 or self.resolution > 128:
            return  # Invalid resolution
        
        # Calculate texture size
        texture_size = self.resolution * self.resolution
        
        # Read offset table
        header_size = 4 + self.num_textures * 4
        if len(self._data) < header_size:
            return
        
        offsets = []
        for i in range(self.num_textures):
            offset = struct.unpack_from('<I', self._data, 4 + i * 4)[0]
            offsets.append(offset)
        
        # Read textures
        for i, offset in enumerate(offsets):
            if offset == 0:
                continue
            
            end_offset = offset + texture_size
            if end_offset > len(self._data):
                continue
            
            texture_data = self._data[offset:end_offset]
            self.textures[i] = TextureData(
                index=i,
                resolution=self.resolution,
                data=texture_data
            )
        
        self._parsed = True
    
    def get_texture(self, index: int) -> Optional[TextureData]:
        """Get a texture by index."""
        if not self._parsed:
            self.parse()
        return self.textures.get(index)
    
    def get_all_textures(self) -> Dict[int, TextureData]:
        """Get all parsed textures."""
        if not self._parsed:
            self.parse()
        return self.textures
    
    def texture_to_image(self, texture: TextureData, 
                        palette: List[Tuple[int, int, int]]) -> Optional['Image.Image']:
        """
        Convert a texture to a PIL Image.
        
        Args:
            texture: TextureData to convert
            palette: List of RGB tuples (256 colors)
        
        Returns:
            PIL Image or None if PIL is not available
        """
        if Image is None:
            return None
        
        if not texture or not texture.data:
            return None
        
        res = texture.resolution
        
        # Create RGBA image (textures don't have transparency, but use RGBA for consistency)
        rgba = Image.new('RGBA', (res, res), (0, 0, 0, 255))
        pixels = rgba.load()
        
        # Texture data is stored row by row
        for y in range(res):
            for x in range(res):
                idx = y * res + x
                if idx < len(texture.data):
                    pal_idx = texture.data[idx]
                    if pal_idx < len(palette):
                        r, g, b = palette[pal_idx]
                        pixels[x, y] = (r, g, b, 255)
                    else:
                        pixels[x, y] = (0, 0, 0, 255)
        
        return rgba
