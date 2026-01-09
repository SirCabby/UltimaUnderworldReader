"""
Image Parser for Ultima Underworld .GR files

Parses .GR graphics files that contain sprite images.
Based on format documentation:
- Bitmap header: type (Int8), width (Int8), height (Int8), [aux palette for 4-bit], data_size (Int16)
- 8-bit images use palette 0 (256 colors)
- 4-bit images use auxiliary palettes
- Index 0 is transparency
"""

import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from enum import IntEnum

try:
    from PIL import Image
except ImportError:
    Image = None


class BitmapType(IntEnum):
    """Bitmap format types."""
    UNCOMPRESSED_8BIT = 0x04
    RLE_4BIT = 0x08
    UNCOMPRESSED_4BIT = 0x0A


@dataclass
class BitmapHeader:
    """Header for a bitmap in a .GR file."""
    bitmap_type: int
    width: int
    height: int
    aux_palette: Optional[int] = None  # For 4-bit images
    data_size: int = 0
    data_offset: int = 0


@dataclass
class SpriteImage:
    """A sprite image extracted from a .GR file."""
    index: int
    width: int
    height: int
    data: bytes
    bitmap_type: int
    aux_palette: Optional[int] = None


class GrFileParser:
    """
    Parser for .GR graphics files.
    
    .GR files can contain multiple bitmaps. The structure varies:
    - Some .GR files have an offset table (like ARK format)
    - Some .GR files have bitmaps stored sequentially
    
    Usage:
        parser = GrFileParser("path/to/OBJECTS.GR")
        parser.parse()
        
        # Get sprite by index
        sprite = parser.get_sprite(0)
        
        # Convert to PIL Image (requires palette)
        img = parser.sprite_to_image(sprite, palette)
    """
    
    def __init__(self, filepath: str | Path):
        self.filepath = Path(filepath)
        self._data: bytes = b''
        self.sprites: Dict[int, SpriteImage] = {}
        self._parsed = False
        self._has_offset_table = False
        self._offset_table: List[int] = []
    
    def parse(self) -> None:
        """Parse the .GR file."""
        with open(self.filepath, 'rb') as f:
            self._data = f.read()
        
        if len(self._data) < 2:
            return
        
        # Try to detect format by checking first bytes
        # Some .GR files have an offset table (like TMOBJ.GR)
        # Others have sequential bitmaps (like OBJECTS.GR)
        
        # Check if it looks like an offset table format
        # Some .GR files start directly with offsets (no count header)
        # Try to detect by looking for increasing offset values
        
        # GR file format: byte 0 = file type, bytes 1-2 = count (little endian), bytes 3+ = offset table
        # Check if this looks like a GR file with offset table
        if len(self._data) >= 3:
            file_type = self._data[0]
            count = struct.unpack_from('<H', self._data, 1)[0]  # Bytes 1-2 = count
            
            # Check if count is reasonable and we have enough data for offset table
            if 10 < count < 10000 and len(self._data) >= 3 + count * 4:
                # Read all offsets
                offsets = []
                for i in range(count):
                    offset = struct.unpack_from('<I', self._data, 3 + i * 4)[0]
                    if offset < len(self._data) and offset > 0:
                        offsets.append(offset)
                    else:
                        # Some offsets might be 0 (unused slots), continue anyway
                        offsets.append(0)
                
                # Check if we have enough valid offsets that are increasing
                valid_offsets = [o for o in offsets if o > 0]
                if len(valid_offsets) > 10:
                    # Check if valid offsets are generally increasing (allow some out of order)
                    increasing_count = sum(1 for i in range(len(valid_offsets)-1) if valid_offsets[i] < valid_offsets[i+1])
                    if increasing_count > len(valid_offsets) * 0.8:  # At least 80% increasing
                        self._has_offset_table = True
                        self._offset_table = offsets
                        self._parse_with_offset_table()
                        self._parsed = True
                        return
        
        # Fall back to sequential parsing
        self._parse_sequential()
        
        self._parsed = True
    
    def _parse_with_offset_table(self) -> None:
        """Parse .GR file with offset table."""
        for idx, offset in enumerate(self._offset_table):
            # Skip invalid offsets (0 or out of bounds)
            if offset == 0 or offset >= len(self._data):
                continue
            
            try:
                header = self._read_bitmap_header(offset)
                if header:
                    data_start = header.data_offset
                    # Calculate exact expected data size based on format
                    if header.bitmap_type == BitmapType.UNCOMPRESSED_8BIT:
                        # 8-bit: exactly width*height bytes
                        expected_bytes = header.width * header.height
                        data_size = expected_bytes
                    elif header.bitmap_type == BitmapType.UNCOMPRESSED_4BIT:
                        # 4-bit: exactly (width*height+1)//2 bytes
                        expected_bytes = (header.width * header.height + 1) // 2
                        data_size = expected_bytes
                    else:  # RLE
                        # For RLE, use the header data_size (already converted from nibbles to bytes)
                        max_rle_bytes = (header.width * header.height + 1) // 2 * 2
                        data_size = min(header.data_size, max_rle_bytes)
                    
                    data_end = data_start + data_size
                    
                    if data_end > len(self._data):
                        data_end = len(self._data)
                        data_size = data_end - data_start
                    
                    if data_end <= len(self._data):
                        sprite_data = self._data[data_start:data_end]
                        
                        self.sprites[idx] = SpriteImage(
                            index=idx,
                            width=header.width,
                            height=header.height,
                            data=sprite_data,
                            bitmap_type=header.bitmap_type,
                            aux_palette=header.aux_palette
                        )
            except Exception as e:
                # Skip invalid sprites
                continue
    
    def _parse_sequential(self) -> None:
        """Parse .GR file with sequential bitmaps."""
        # First, try to find sprite headers by scanning
        # Some .GR files have sprites scattered throughout, not in a simple sequence
        found_offsets = []
        
        # Scan for valid bitmap headers
        for offset in range(0, min(len(self._data) - 10, 10000), 1):
            try:
                header = self._read_bitmap_header(offset)
                if header:
                    data_start = header.data_offset
                    data_end = data_start + header.data_size
                    
                    if data_end <= len(self._data):
                        # This looks like a valid sprite
                        found_offsets.append((offset, header))
            except Exception:
                continue
        
        # Sort by offset and extract sprites
        found_offsets.sort(key=lambda x: x[0])
        
        for sprite_idx, (offset, header) in enumerate(found_offsets):
            try:
                data_start = header.data_offset
                # Calculate exact expected data size based on format
                if header.bitmap_type == BitmapType.UNCOMPRESSED_8BIT:
                    # 8-bit: exactly width*height bytes (ignore header data_size which may be wrong)
                    expected_bytes = header.width * header.height
                    data_size = expected_bytes
                elif header.bitmap_type == BitmapType.UNCOMPRESSED_4BIT:
                    # 4-bit: exactly (width*height+1)//2 bytes (2 pixels per byte)
                    expected_bytes = (header.width * header.height + 1) // 2
                    data_size = expected_bytes
                else:  # RLE
                    # For RLE, use the header data_size (already converted from nibbles to bytes)
                    # But cap it at reasonable maximum
                    max_rle_bytes = (header.width * header.height + 1) // 2 * 2  # Allow up to 2x uncompressed
                    data_size = min(header.data_size, max_rle_bytes)
                
                data_end = data_start + data_size
                
                if data_end > len(self._data):
                    data_end = len(self._data)
                    data_size = data_end - data_start
                
                sprite_data = self._data[data_start:data_end]
                
                self.sprites[sprite_idx] = SpriteImage(
                    index=sprite_idx,
                    width=header.width,
                    height=header.height,
                    data=sprite_data,
                    bitmap_type=header.bitmap_type,
                    aux_palette=header.aux_palette
                )
                
                # Safety: don't parse more than 1000 sprites
                if sprite_idx >= 1000:
                    break
            except Exception:
                continue
    
    def _read_bitmap_header(self, offset: int) -> Optional[BitmapHeader]:
        """Read a bitmap header from the given offset."""
        if offset + 5 > len(self._data):
            return None
        
        bitmap_type = struct.unpack_from('<B', self._data, offset)[0]
        width = struct.unpack_from('<B', self._data, offset + 1)[0]
        height = struct.unpack_from('<B', self._data, offset + 2)[0]
        
        # Debug: log first few attempts to see what we're reading
        # (commented out for production, but useful for debugging)
        # if offset < 100:
        #     print(f"      Offset {offset}: type={bitmap_type}, w={width}, h={height}")
        
        # Determine header size based on bitmap type
        if bitmap_type == BitmapType.UNCOMPRESSED_8BIT:
            # 8-bit: type, width, height, data_size (2 bytes)
            if offset + 5 > len(self._data):
                return None
            data_size = struct.unpack_from('<H', self._data, offset + 3)[0]
            data_offset = offset + 5
            aux_palette = None
        elif bitmap_type in (BitmapType.RLE_4BIT, BitmapType.UNCOMPRESSED_4BIT):
            # 4-bit: type, width, height, aux_palette, data_size (2 bytes)
            # NOTE: For 4-bit formats, data_size is in NIBBLES, not bytes!
            if offset + 6 > len(self._data):
                return None
            aux_palette = struct.unpack_from('<B', self._data, offset + 3)[0]
            data_size_nibbles = struct.unpack_from('<H', self._data, offset + 4)[0]
            # Convert nibbles to bytes (round up)
            data_size = (data_size_nibbles + 1) // 2
            data_offset = offset + 6
        else:
            # Unknown type, skip
            return None
        
        # Validate dimensions
        if width == 0 or height == 0 or width > 256 or height > 256:
            return None
        
        # Validate data size (should be reasonable for the dimensions)
        expected_size_8bit = width * height
        expected_size_4bit = (width * height + 1) // 2  # 4-bit = 2 pixels per byte
        
        # More lenient validation - allow data_size to be up to 4x expected (for padding/alignment)
        # RLE can be smaller than uncompressed, so be more lenient
        if bitmap_type == BitmapType.UNCOMPRESSED_8BIT:
            if data_size > expected_size_8bit * 4:  # Allow more overhead for alignment
                return None
            # Also check minimum - data should be at least close to expected
            if data_size < expected_size_8bit * 0.5:  # At least half the expected size
                return None
        elif bitmap_type == BitmapType.UNCOMPRESSED_4BIT:
            if data_size > expected_size_4bit * 4:
                return None
            if data_size < expected_size_4bit * 0.5:
                return None
        elif bitmap_type == BitmapType.RLE_4BIT:
            # RLE can be much smaller than uncompressed, so be very lenient
            # Minimum: at least 1 byte, maximum: up to uncompressed size * 2 (for worst case RLE)
            if data_size < 1:
                return None
            if data_size > expected_size_4bit * 2:
                return None
        
        return BitmapHeader(
            bitmap_type=bitmap_type,
            width=width,
            height=height,
            aux_palette=aux_palette,
            data_size=data_size,
            data_offset=data_offset
        )
    
    def get_sprite(self, index: int) -> Optional[SpriteImage]:
        """Get a sprite by index."""
        if not self._parsed:
            self.parse()
        return self.sprites.get(index)
    
    def get_all_sprites(self) -> Dict[int, SpriteImage]:
        """Get all parsed sprites."""
        if not self._parsed:
            self.parse()
        return self.sprites
    
    def sprite_to_image(self, sprite: SpriteImage, palette: Optional[List[Tuple[int, int, int]]], 
                       aux_palette_parser: Optional[Any] = None) -> Optional['Image.Image']:
        """
        Convert a sprite to a PIL Image.
        
        Args:
            sprite: The sprite to convert
            palette: List of RGB tuples (256 colors for 8-bit)
                    Can be None, in which case a default palette is used
            aux_palette_parser: AuxPaletteParser instance for loading auxiliary palettes for 4-bit images
        
        Returns:
            PIL Image or None if PIL is not available
        """
        if Image is None:
            return None
        
        # Use default palette if none provided
        if palette is None:
            palette = [(i, i, i) for i in range(256)]
        
        if sprite.bitmap_type == BitmapType.UNCOMPRESSED_8BIT:
            # 8-bit uncompressed
            # Create RGBA image directly
            rgba = Image.new('RGBA', (sprite.width, sprite.height), (0, 0, 0, 0))
            
            # Copy pixel data
            pixel_indices = list(sprite.data[:sprite.width * sprite.height])
            if len(pixel_indices) < sprite.width * sprite.height:
                pixel_indices.extend([0] * (sprite.width * sprite.height - len(pixel_indices)))
            
            # Set pixels with palette colors, index 0 = transparent
            # Try reversed rows (data stored bottom-to-top, but we display top-to-bottom)
            pixels = rgba.load()
            for y in range(sprite.height):
                for x in range(sprite.width):
                    # Data stored bottom-to-top: reverse the row index
                    src_y = sprite.height - 1 - y
                    idx = pixel_indices[src_y * sprite.width + x] if (src_y * sprite.width + x) < len(pixel_indices) else 0
                    if idx == 0:
                        # Index 0 = transparent
                        pixels[x, y] = (0, 0, 0, 0)
                    elif idx < len(palette):
                        r, g, b = palette[idx]
                        pixels[x, y] = (r, g, b, 255)
                    else:
                        # Out of range, use black
                        pixels[x, y] = (0, 0, 0, 255)
            
            return rgba
            
        elif sprite.bitmap_type == BitmapType.UNCOMPRESSED_4BIT:
            # 4-bit uncompressed
            # Create RGBA image directly
            rgba = Image.new('RGBA', (sprite.width, sprite.height), (0, 0, 0, 0))
            
            # Load auxiliary palette using the aux_palette index from sprite header
            aux_pal = self._get_aux_palette(sprite.aux_palette, palette, aux_palette_parser)
            
            # Unpack 4-bit data (2 pixels per byte)
            # Upper nibble first, then lower nibble (per format spec)
            pixel_indices = []
            total_pixels = sprite.width * sprite.height
            
            for byte in sprite.data:
                # Upper nibble first, then lower nibble
                pixel_indices.append((byte >> 4) & 0x0F)  # Upper nibble first
                pixel_indices.append(byte & 0x0F)  # Lower nibble second
                if len(pixel_indices) >= total_pixels:
                    break
            
            # Trim to exact size
            pixel_indices = pixel_indices[:total_pixels]
            if len(pixel_indices) < total_pixels:
                pixel_indices.extend([0] * (total_pixels - len(pixel_indices)))
            
            # Set pixels with auxiliary palette colors, index 0 = transparent
            # Format is row-major, top-to-bottom, left-to-right
            pixels = rgba.load()
            for y in range(sprite.height):
                for x in range(sprite.width):
                    idx = pixel_indices[y * sprite.width + x]
                    if idx == 0:
                        # Index 0 = transparent
                        pixels[x, y] = (0, 0, 0, 0)
                    elif idx < len(aux_pal):
                        r, g, b = aux_pal[idx]
                        pixels[x, y] = (r, g, b, 255)
                    else:
                        # Out of range, use black
                        pixels[x, y] = (0, 0, 0, 255)
            
            return rgba
        
        elif sprite.bitmap_type == BitmapType.RLE_4BIT:
            # 4-bit RLE (Run-Length Encoded)
            # Based on working C++ implementation from UnderworldExporter
            # Format: Alternating repeat and run records, starting with repeat
            # Special count values:
            #   count == 1: Skip this repeat record, next is a run record
            #   count == 2: Multiple repeat records - read another count and process that many repeats
            rgba = Image.new('RGBA', (sprite.width, sprite.height), (0, 0, 0, 0))
            
            # Load auxiliary palette using the aux_palette index from sprite header
            aux_pal = self._get_aux_palette(sprite.aux_palette, palette, aux_palette_parser)
            
            # Convert bytes to nibbles (upper nibble first, then lower nibble)
            nibbles = []
            for byte in sprite.data:
                nibbles.append((byte >> 4) & 0x0F)  # Upper nibble first
                nibbles.append(byte & 0x0F)  # Lower nibble second
            
            # Decode RLE
            pixel_indices = []
            total_pixels = sprite.width * sprite.height
            nibble_idx = 0
            state = 0  # 0 = repeat_record_start, 1 = repeat_record, 2 = run_record
            repeatcount = 0
            
            def get_count():
                """Get count value, handling extended counts."""
                nonlocal nibble_idx
                if nibble_idx >= len(nibbles):
                    return 0
                n1 = nibbles[nibble_idx]
                nibble_idx += 1
                count = n1
                
                if count == 0:
                    # Extended count: read 2 more nibbles
                    if nibble_idx + 1 < len(nibbles):
                        n1 = nibbles[nibble_idx]
                        n2 = nibbles[nibble_idx + 1]
                        count = (n1 << 4) | n2
                        nibble_idx += 2
                        if count == 0:
                            # Even more extended: read 3 more nibbles
                            if nibble_idx + 2 < len(nibbles):
                                n1 = nibbles[nibble_idx]
                                n2 = nibbles[nibble_idx + 1]
                                n3 = nibbles[nibble_idx + 2]
                                count = (((n1 << 4) | n2) << 4) | n3
                                nibble_idx += 3
                
                return count
            
            def get_nibble():
                """Get next nibble."""
                nonlocal nibble_idx
                if nibble_idx >= len(nibbles):
                    return 0
                val = nibbles[nibble_idx]
                nibble_idx += 1
                return val
            
            while nibble_idx < len(nibbles) and len(pixel_indices) < total_pixels:
                if state == 0:  # repeat_record_start
                    count = get_count()
                    if count == 1:
                        # Skip this repeat record, next is a run record
                        state = 2  # run_record
                    elif count == 2:
                        # Multiple repeat records
                        repeatcount = get_count() - 1
                        state = 0  # Stay in repeat_record_start
                    else:
                        state = 1  # repeat_record
                
                elif state == 1:  # repeat_record
                    # Read pixel value to repeat
                    pixel_value = get_nibble()
                    # Output pixel value 'count' times
                    for _ in range(min(count, total_pixels - len(pixel_indices))):
                        pixel_indices.append(pixel_value)
                    
                    if repeatcount == 0:
                        state = 2  # Next is run record
                    else:
                        repeatcount -= 1
                        state = 0  # Continue with repeat records
                
                elif state == 2:  # run_record
                    count = get_count()
                    # Read 'count' uncompressed nibbles
                    for _ in range(min(count, total_pixels - len(pixel_indices))):
                        if nibble_idx < len(nibbles):
                            pixel_indices.append(get_nibble())
                        else:
                            break
                    state = 0  # Next is repeat record
            
            # Pad to exact size if needed
            if len(pixel_indices) < total_pixels:
                pixel_indices.extend([0] * (total_pixels - len(pixel_indices)))
            elif len(pixel_indices) > total_pixels:
                pixel_indices = pixel_indices[:total_pixels]
            
            # Set pixels with auxiliary palette colors, index 0 = transparent
            # Format is row-major, top-to-bottom, left-to-right
            pixels = rgba.load()
            for y in range(sprite.height):
                for x in range(sprite.width):
                    idx = pixel_indices[y * sprite.width + x]
                    if idx == 0:
                        # Index 0 = transparent
                        pixels[x, y] = (0, 0, 0, 0)
                    elif idx < len(aux_pal):
                        r, g, b = aux_pal[idx]
                        pixels[x, y] = (r, g, b, 255)
                    else:
                        # Out of range, use black
                        pixels[x, y] = (0, 0, 0, 255)
            
            return rgba
        
        # Unknown bitmap type
        return None
    
    def _get_aux_palette(self, aux_palette_index: Optional[int], main_palette: List[Tuple[int, int, int]], 
                        aux_palette_parser: Optional[Any]) -> List[Tuple[int, int, int]]:
        """
        Get auxiliary palette colors.
        
        Args:
            aux_palette_index: Index of auxiliary palette (from sprite header)
            main_palette: Main 256-color palette
            aux_palette_parser: AuxPaletteParser instance
        
        Returns:
            List of 16 RGB tuples
        """
        if aux_palette_parser and aux_palette_index is not None:
            # Get auxiliary palette indices from file
            aux_indices = aux_palette_parser.get_aux_palette(aux_palette_index)
            if aux_indices:
                # Map indices to actual colors from main palette
                aux_pal = []
                for idx in aux_indices:
                    if idx < len(main_palette):
                        aux_pal.append(main_palette[idx])
                    else:
                        aux_pal.append((0, 0, 0))
                return aux_pal
        
        # Fallback: use first 16 colors of main palette
        if len(main_palette) >= 16:
            return main_palette[:16]
        else:
            return list(main_palette) + [(0, 0, 0)] * (16 - len(main_palette))
