"""
Animation File Parser for Ultima Underworld

Parses CrXXpage.nYY animation files that contain NPC walking/action sprites.
These files use 5-bit RLE compression and contain multiple animation frames.

Format:
- 0x0000-0x007F: Atom to Fragment Mapping (auxiliary palette mappings)
- 0x0080-0x027F: Offset Table (16-bit offsets to frame data, 256 entries)
- 0x0280+: Frame data (5-bit RLE compressed)

Each frame header:
- Width (1 byte)
- Height (1 byte)
- Hotspot X (1 byte)
- Hotspot Y (1 byte)
- Compression type (1 byte, 06 = 5-bit RLE)
- Data length in words (2 bytes, Int16)
"""

import struct
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

try:
    from PIL import Image
except ImportError:
    Image = None


@dataclass
class AnimationFrame:
    """A single frame from an animation file."""
    frame_index: int
    width: int
    height: int
    hotspot_x: int
    hotspot_y: int
    compression_type: int
    data_length: int  # In words (5-bit units)
    data: bytes
    data_offset: int


class AnimationFileParser:
    """
    Parser for Ultima Underworld animation files (CrXXpage.nYY format).
    
    Usage:
        parser = AnimationFileParser("Input/UW1/CRIT/CR00PAGE.N00")
        parser.parse()
        
        # Get a frame (e.g., idle animation at angle 0, slot 0x20)
        frame = parser.get_frame(0x20)  # Or try other slots
        
        # Convert to image (requires palette and aux palette parser)
        img = parser.frame_to_image(frame, palette, aux_palette_parser)
    """
    
    ATOM_TO_FRAGMENT_OFFSET = 0x0000
    ATOM_TO_FRAGMENT_SIZE = 0x0080  # 128 bytes
    OFFSET_TABLE_OFFSET = 0x0080
    OFFSET_TABLE_SIZE = 0x0200  # 512 bytes (256 entries × 2 bytes)
    FRAME_DATA_OFFSET = 0x0280
    
    COMPRESSION_5BIT_RLE = 0x06
    COMPRESSION_4BIT_RLE = 0x08  # 4-bit RLE format (common in animation files)
    
    def __init__(self, filepath: str | Path):
        self.filepath = Path(filepath)
        self._data: bytes = b''
        self._parsed = False
        
        # Parsed data
        self.atom_to_fragment: List[int] = []  # 128 entries (0x00-0x7F)
        self.offset_table: List[int] = []  # 256 entries (offsets to frame data)
        self.frames: Dict[int, AnimationFrame] = {}  # slot_index -> frame
    
    def parse(self) -> None:
        """Parse the animation file."""
        if not self.filepath.exists():
            return
        
        with open(self.filepath, 'rb') as f:
            self._data = f.read()
        
        if len(self._data) < self.FRAME_DATA_OFFSET:
            return
        
        # Parse atom to fragment mapping (0x0000-0x007F, 128 bytes)
        self._parse_atom_to_fragment()
        
        # Parse offset table (0x0080-0x027F, 512 bytes = 256 entries × 2 bytes)
        self._parse_offset_table()
        
        # Parse frames using offset table
        self._parse_frames()
        
        self._parsed = True
    
    def _parse_atom_to_fragment(self) -> None:
        """Parse atom to fragment mapping (auxiliary palette mappings)."""
        self.atom_to_fragment = []
        for i in range(self.ATOM_TO_FRAGMENT_SIZE):
            offset = self.ATOM_TO_FRAGMENT_OFFSET + i
            if offset < len(self._data):
                value = struct.unpack_from('<B', self._data, offset)[0]
                self.atom_to_fragment.append(value)
            else:
                self.atom_to_fragment.append(0)
    
    def _parse_offset_table(self) -> None:
        """Parse offset table (256 entries of 16-bit offsets)."""
        self.offset_table = []
        for i in range(256):  # 256 slots
            offset = self.OFFSET_TABLE_OFFSET + i * 2
            if offset + 1 < len(self._data):
                frame_offset = struct.unpack_from('<H', self._data, offset)[0]
                # Offset is relative to start of file, but frame data starts at 0x0280
                # If offset is 0, this slot is unused
                self.offset_table.append(frame_offset if frame_offset > 0 else 0)
            else:
                self.offset_table.append(0)
    
    def _parse_frames(self) -> None:
        """Parse animation frames using the offset table."""
        for slot_index, frame_offset in enumerate(self.offset_table):
            if frame_offset == 0 or frame_offset >= len(self._data):
                continue
            
            # Skip very small offsets (likely invalid or pointing to other data structures)
            # Frame data typically starts at 0x0280, but valid frames might start earlier
            # However, offsets < 0x0100 are likely invalid or point to header/table data
            if frame_offset < 0x0100:
                continue
            
            # Frame header is 7 bytes: width, height, hotspot_x, hotspot_y, compression, data_length
            if frame_offset + 7 > len(self._data):
                continue
            
            try:
                width = struct.unpack_from('<B', self._data, frame_offset)[0]
                height = struct.unpack_from('<B', self._data, frame_offset + 1)[0]
                hotspot_x = struct.unpack_from('<B', self._data, frame_offset + 2)[0]
                hotspot_y = struct.unpack_from('<B', self._data, frame_offset + 3)[0]
                compression = struct.unpack_from('<B', self._data, frame_offset + 4)[0]
                data_length_words = struct.unpack_from('<H', self._data, frame_offset + 5)[0]
                
                # Validate frame header
                # Some frames have 0 width/height which means unused, skip those
                if width == 0 or height == 0:
                    continue
                
                # Validate reasonable dimensions (NPC sprites are typically 8-128 pixels)
                if width > 256 or height > 256:
                    continue
                
                # Accept multiple compression formats:
                # 0x00 = uncompressed (common in animation files)
                # 0x06 = 5-bit RLE (common)
                # 0x08 = 4-bit RLE (common)
                if compression not in (0x00, self.COMPRESSION_5BIT_RLE, self.COMPRESSION_4BIT_RLE):
                    # Skip unsupported compression formats for now
                    continue
                
                # Calculate data size in bytes based on compression type
                if compression == 0x00:
                    # Uncompressed: data_length is in bytes, or could be width*height for 8-bit
                    # For now, assume it's width*height bytes for 8-bit uncompressed
                    data_size_bytes = width * height
                elif compression == self.COMPRESSION_5BIT_RLE:
                    # 5-bit words: (data_length_words * 5 + 7) / 8 bytes (round up)
                    data_size_bytes = (data_length_words * 5 + 7) // 8
                elif compression == self.COMPRESSION_4BIT_RLE:
                    # 4-bit RLE: data_length is in nibbles (4-bit units)
                    # Convert nibbles to bytes: (data_length_nibbles + 1) // 2
                    data_size_bytes = (data_length_words + 1) // 2
                else:
                    continue  # Unknown compression type
                
                data_start = frame_offset + 7
                data_end = data_start + data_size_bytes
                
                # Find the next frame offset to determine actual data size
                # (frames may have padding/alignment, so use actual boundaries)
                next_offset = len(self._data)  # Default to end of file
                for i in range(256):
                    check_offset = 0x0080 + i * 2
                    if check_offset + 1 < len(self._data):
                        next_frame_offset = struct.unpack_from('<H', self._data, check_offset)[0]
                        if (next_frame_offset > frame_offset and 
                            next_frame_offset < next_offset and
                            next_frame_offset >= data_start):
                            next_offset = next_frame_offset
                
                # Use the smaller of calculated size or actual frame boundary
                if next_offset < len(self._data):
                    actual_data_end = min(data_end, next_offset)
                else:
                    actual_data_end = min(data_end, len(self._data))
                
                data_size_bytes = actual_data_end - data_start
                
                # Validate we have reasonable data size (at least a few bytes)
                if data_size_bytes < 4:  # At least 4 bytes for a minimal frame
                    continue
                
                if data_size_bytes > 0:
                    frame_data = self._data[data_start:actual_data_end]
                    
                    self.frames[slot_index] = AnimationFrame(
                        frame_index=slot_index,
                        width=width,
                        height=height,
                        hotspot_x=hotspot_x,
                        hotspot_y=hotspot_y,
                        compression_type=compression,
                        data_length=data_length_words,
                        data=frame_data,
                        data_offset=frame_offset
                    )
            except Exception:
                # Skip invalid frames
                continue
    
    def get_frame(self, slot_index: int) -> Optional[AnimationFrame]:
        """Get an animation frame by slot index."""
        if not self._parsed:
            self.parse()
        return self.frames.get(slot_index)
    
    def get_all_frames(self) -> Dict[int, AnimationFrame]:
        """Get all parsed frames."""
        if not self._parsed:
            self.parse()
        return self.frames
    
    def frame_to_image(self, frame: AnimationFrame, 
                      palette: List[Tuple[int, int, int]],
                      aux_palette_parser: Optional[Any] = None) -> Optional['Image.Image']:
        """
        Convert an animation frame to a PIL Image.
        
        Args:
            frame: AnimationFrame to convert
            palette: Main 256-color palette
            aux_palette_parser: AuxPaletteParser for loading auxiliary palettes
            
        Returns:
            PIL Image or None if conversion fails
        """
        if Image is None:
            return None
        
        # Decompress based on compression type
        if frame.compression_type == 0x00:
            # Uncompressed 8-bit: each byte is a palette index
            pixel_indices = list(frame.data[:frame.width * frame.height])
            # Pad if needed
            while len(pixel_indices) < frame.width * frame.height:
                pixel_indices.append(0)
        elif frame.compression_type == self.COMPRESSION_5BIT_RLE:
            pixel_indices = self._decompress_5bit_rle(frame.data, frame.data_length, frame.width * frame.height)
        elif frame.compression_type == self.COMPRESSION_4BIT_RLE:
            pixel_indices = self._decompress_4bit_rle(frame.data, frame.data_length, frame.width * frame.height)
        else:
            return None  # Unsupported compression type
        
        if not pixel_indices or len(pixel_indices) < frame.width * frame.height:
            return None
        
        # Get palette based on compression type
        # 0x00 (uncompressed) uses 256-color palette (indices 0-255)
        # 5-bit RLE uses 32-color palette (indices 0-31)
        # 4-bit RLE uses 16-color palette (indices 0-15)
        if frame.compression_type == 0x00:
            # Uncompressed: use full 256-color main palette directly
            final_palette_rgb = palette[:256] if len(palette) >= 256 else list(palette) + [(0, 0, 0)] * (256 - len(palette))
        elif frame.compression_type == self.COMPRESSION_5BIT_RLE:
            # 5-bit indices (0-31), need 32-color palette
            final_palette_rgb = []
            
            if aux_palette_parser:
                # Animation files typically use auxiliary palette 0 (default)
                aux_pal_indices = aux_palette_parser.get_aux_palette(0)
                
                if aux_pal_indices and len(aux_pal_indices) >= 16:
                    # Map aux palette indices to RGB colors from main palette
                    for i in range(32):  # 5-bit indices are 0-31
                        aux_idx = i % len(aux_pal_indices)  # Cycle through 16-color aux palette
                        main_pal_idx = aux_pal_indices[aux_idx]
                        if main_pal_idx < len(palette):
                            final_palette_rgb.append(palette[main_pal_idx])
                        else:
                            final_palette_rgb.append((0, 0, 0))
                else:
                    final_palette_rgb = self._get_animation_palette(palette, aux_palette_parser)
            else:
                final_palette_rgb = self._get_animation_palette(palette, aux_palette_parser)
            
            # Ensure we have 32 colors
            while len(final_palette_rgb) < 32:
                final_palette_rgb.append((0, 0, 0))
        else:
            # 4-bit RLE uses 16-color palette (indices 0-15)
            final_palette_rgb = []
            
            if aux_palette_parser:
                # Use auxiliary palette 0 (default for animation files)
                aux_pal_indices = aux_palette_parser.get_aux_palette(0)
                
                if aux_pal_indices and len(aux_pal_indices) >= 16:
                    # Map aux palette indices to RGB colors from main palette
                    for idx in aux_pal_indices[:16]:
                        if idx < len(palette):
                            final_palette_rgb.append(palette[idx])
                        else:
                            final_palette_rgb.append((0, 0, 0))
                else:
                    # Fallback: use first 16 colors of main palette
                    if len(palette) >= 16:
                        final_palette_rgb = palette[:16]
                    else:
                        final_palette_rgb = list(palette) + [(0, 0, 0)] * (16 - len(palette))
            else:
                # Fallback: use first 16 colors of main palette
                if len(palette) >= 16:
                    final_palette_rgb = palette[:16]
                else:
                    final_palette_rgb = list(palette) + [(0, 0, 0)] * (16 - len(palette))
            
            # Ensure we have 16 colors
            while len(final_palette_rgb) < 16:
                final_palette_rgb.append((0, 0, 0))
        
        # Create RGBA image
        rgba = Image.new('RGBA', (frame.width, frame.height), (0, 0, 0, 0))
        pixels = rgba.load()
        
        # Animation frames are stored top-to-bottom (not flipped like GR files)
        # Pixel indices should be in row-major order (left to right, top to bottom)
        for y in range(frame.height):
            for x in range(frame.width):
                pixel_idx = y * frame.width + x
                if pixel_idx >= len(pixel_indices):
                    # Out of bounds, transparent
                    pixels[x, y] = (0, 0, 0, 0)
                    continue
                
                # Get pixel index from decompressed data
                pixel_index = pixel_indices[pixel_idx]
                if pixel_index == 0:
                    # Index 0 = transparent
                    pixels[x, y] = (0, 0, 0, 0)
                elif pixel_index < len(final_palette_rgb):
                    r, g, b = final_palette_rgb[pixel_index]
                    pixels[x, y] = (r, g, b, 255)
                else:
                    # Out of range, use black
                    pixels[x, y] = (0, 0, 0, 255)
        
        return rgba
    
    def _decompress_5bit_rle(self, data: bytes, data_length_words: int, expected_pixels: int) -> List[int]:
        """
        Decompress 5-bit RLE data using the correct bit buffer algorithm.
        
        Based on Ultima Underworld format specification:
        - Uses a bit buffer that reads bytes and extracts 5-bit codes
        - CodeBits = 5
        - Buffer maintains bits across byte boundaries
        
        Args:
            data: Compressed data bytes
            data_length_words: Expected number of 5-bit words
            expected_pixels: Expected number of pixels after decompression
            
        Returns:
            List of pixel indices (0-31 for 5-bit)
        """
        # 5-bit RLE: Extract 5-bit words using a bit buffer algorithm
        # Algorithm: ReadCode() extracts 5 bits from a buffer that maintains bits across bytes
        words = []
        bit_buffer = 0  # Bit buffer
        bit_buffer_count = 0  # Number of bits in buffer
        data_pos = 0  # Position in data byte array
        
        def read_code():
            """Read next 5-bit code from bit buffer."""
            nonlocal bit_buffer, bit_buffer_count, data_pos
            
            # We need 5 bits, ensure buffer has enough
            while bit_buffer_count < 5:
                if data_pos >= len(data):
                    return 0  # End of data
                # Read next byte into buffer (MSB first)
                bit_buffer = (bit_buffer << 8) | data[data_pos]
                bit_buffer_count += 8
                data_pos += 1
            
            # Extract 5 bits from MSB of buffer
            bit_buffer_count -= 5
            code = (bit_buffer >> bit_buffer_count) & 0x1F
            bit_buffer &= (1 << bit_buffer_count) - 1  # Clear extracted bits
            
            return code
        
        # Extract all 5-bit words
        for _ in range(min(data_length_words, expected_pixels * 4)):  # Cap at reasonable limit
            word = read_code()
            if data_pos > len(data) and bit_buffer_count < 5:
                break
            words.append(word)
            
            if len(words) >= data_length_words:
                break
        
        # Decompress RLE (similar to 4-bit RLE but with 5-bit values)
        # Format: alternating repeat and run records, starting with repeat
        # This is similar to the 4-bit RLE format from the image parser
        pixel_indices = []
        word_idx = 0
        state = 0  # 0 = repeat_record_start, 1 = repeat_record, 2 = run_record
        repeatcount = 0
        
        def get_count():
            """Get count value, handling extended counts (5-bit values)."""
            nonlocal word_idx
            if word_idx >= len(words):
                return 0
            w = words[word_idx] & 0x1F
            word_idx += 1
            count = w
            
            if count == 0:
                # Extended count: read more 5-bit words
                if word_idx + 1 < len(words):
                    w1 = words[word_idx] & 0x1F
                    w2 = words[word_idx + 1] & 0x1F
                    count = (w1 << 5) | w2
                    word_idx += 2
                    if count == 0 and word_idx + 1 < len(words):
                        w3 = words[word_idx] & 0x1F
                        count = (count << 5) | w3
                        word_idx += 1
            
            return count
        
        def get_value():
            """Get next 5-bit value."""
            nonlocal word_idx
            if word_idx >= len(words):
                return 0
            val = words[word_idx] & 0x1F
            word_idx += 1
            return val
        
        while word_idx < len(words) and len(pixel_indices) < expected_pixels:
            if state == 0:  # repeat_record_start
                count = get_count()
                if count == 1:
                    state = 2  # run_record (skip repeat, next is run)
                elif count == 2:
                    # Multiple repeat records
                    repeatcount = get_count() - 1
                    state = 0  # Stay in repeat_record_start
                else:
                    state = 1  # repeat_record
            
            elif state == 1:  # repeat_record
                pixel_value = get_value()
                for _ in range(min(count, expected_pixels - len(pixel_indices))):
                    pixel_indices.append(pixel_value)
                
                if repeatcount == 0:
                    state = 2  # run_record
                else:
                    repeatcount -= 1
                    state = 0  # Continue with repeat records
            
            elif state == 2:  # run_record
                count = get_count()
                for _ in range(min(count, expected_pixels - len(pixel_indices))):
                    if word_idx < len(words):
                        pixel_indices.append(get_value())
                    else:
                        break
                state = 0  # Next is repeat record
        
        # Pad or trim to exact size
        if len(pixel_indices) < expected_pixels:
            pixel_indices.extend([0] * (expected_pixels - len(pixel_indices)))
        elif len(pixel_indices) > expected_pixels:
            pixel_indices = pixel_indices[:expected_pixels]
        
        return pixel_indices
    
    def _decompress_4bit_rle(self, data: bytes, data_length_nibbles: int, expected_pixels: int) -> List[int]:
        """
        Decompress 4-bit RLE data.
        
        Based on the 4-bit RLE implementation from image_parser.py.
        Format: Alternating repeat and run records, starting with repeat.
        
        Args:
            data: Compressed data bytes
            data_length_nibbles: Expected number of 4-bit nibbles (for reference, may not match exactly)
            expected_pixels: Expected number of pixels after decompression
            
        Returns:
            List of pixel indices (0-15 for 4-bit)
        """
        # Convert bytes to nibbles (upper nibble first, then lower nibble)
        # This matches the format used in GR files
        nibbles = []
        for byte in data:
            nibbles.append((byte >> 4) & 0x0F)  # Upper nibble first (MSB)
            nibbles.append(byte & 0x0F)  # Lower nibble second (LSB)
        
        # Decode RLE (same algorithm as in image_parser.py)
        pixel_indices = []
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
                    if count == 0 and nibble_idx + 2 < len(nibbles):
                        # Even more extended: read 3 more nibbles
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
        
        while nibble_idx < len(nibbles) and len(pixel_indices) < expected_pixels:
            if state == 0:  # repeat_record_start
                count = get_count()
                if count == 1:
                    state = 2  # run_record (skip repeat, next is run)
                elif count == 2:
                    # Multiple repeat records
                    repeatcount = get_count() - 1
                    state = 0  # Stay in repeat_record_start
                else:
                    state = 1  # repeat_record
            
            elif state == 1:  # repeat_record
                pixel_value = get_nibble()
                for _ in range(min(count, expected_pixels - len(pixel_indices))):
                    pixel_indices.append(pixel_value)
                
                if repeatcount == 0:
                    state = 2  # run_record
                else:
                    repeatcount -= 1
                    state = 0  # Continue with repeat records
            
            elif state == 2:  # run_record
                count = get_count()
                for _ in range(min(count, expected_pixels - len(pixel_indices))):
                    if nibble_idx < len(nibbles):
                        pixel_indices.append(get_nibble())
                    else:
                        break
                state = 0  # Next is repeat record
        
        # Pad or trim to exact size
        if len(pixel_indices) < expected_pixels:
            pixel_indices.extend([0] * (expected_pixels - len(pixel_indices)))
        elif len(pixel_indices) > expected_pixels:
            pixel_indices = pixel_indices[:expected_pixels]
        
        return pixel_indices
    
    def _get_animation_palette(self, main_palette: List[Tuple[int, int, int]], 
                               aux_palette_parser: Optional[Any]) -> List[Tuple[int, int, int]]:
        """
        Get palette for animation frames (32 colors for 5-bit indices).
        
        Animation files use 5-bit indices (0-31), but typically map through
        auxiliary palettes. The atom_to_fragment mapping might be used.
        For now, use a standard mapping or fallback to first 32 colors.
        """
        # Use atom_to_fragment mapping if available
        if self.atom_to_fragment and len(self.atom_to_fragment) >= 32:
            anim_pal = []
            for i in range(32):
                atom_idx = self.atom_to_fragment[i] if i < len(self.atom_to_fragment) else i
                if atom_idx < len(main_palette):
                    anim_pal.append(main_palette[atom_idx])
                else:
                    anim_pal.append((0, 0, 0))
            return anim_pal
        
        # Fallback: use first 32 colors of main palette
        if len(main_palette) >= 32:
            return main_palette[:32]
        else:
            return list(main_palette) + [(0, 0, 0)] * (32 - len(main_palette))
