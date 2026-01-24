"""
Animation File Parser for Ultima Underworld

Parses CrXXpage.nYY animation files that contain NPC walking/action sprites.
These files use 5-bit RLE compression and contain multiple animation frames.

Based on uw-formats.txt specification (section 3.6.1):

File format (variable-length header):
- Byte 0: anim slot base
- Byte 1: number of anim slots (=nslot)
- Bytes 2 to nslot+1: list of segment indices
- Byte nslot+2: number of anim segments (=nsegs)
- Next 8*nsegs bytes: anim frame indices for each segment
- Next byte: number of aux palettes (=npals)
- Next npals*32 bytes: auxiliary palette indices (32 bytes each)
- Next byte: number of frame offsets (=noffsets)
- Next byte: compression type (always 06)
- Next noffsets*2 bytes: absolute offsets to frame headers

Each frame header (at offset from table):
- Width (1 byte)
- Height (1 byte)
- Hotspot X (1 byte)
- Hotspot Y (1 byte)
- Compression type (1 byte, 06 = 5-bit RLE, 08 = 4-bit RLE)
- Data length in words (2 bytes, Int16)
- Frame data (RLE compressed)
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
    
    Based on uw-formats.txt specification and UWXtract implementation.
    
    Usage:
        parser = AnimationFileParser("Input/UW1/CRIT/CR00PAGE.N00")
        parser.parse()
        
        # Get a frame (e.g., idle animation at angle 0, slot 0x20)
        frame = parser.get_frame(0x20)  # Or try other slots
        
        # Convert to image (requires palette)
        img = parser.frame_to_image(frame, palette, auxpal_index=0)
    """
    
    COMPRESSION_5BIT_RLE = 0x06
    COMPRESSION_4BIT_RLE = 0x08  # 4-bit RLE format
    
    def __init__(self, filepath: str | Path):
        self.filepath = Path(filepath)
        self._data: bytes = b''
        self._parsed = False
        
        # Header info
        self.slot_base: int = 0
        self.num_slots: int = 0
        self.slot_offsets: List[int] = []  # Segment indices for each slot
        self.num_segments: int = 0
        self.segment_frames: List[List[int]] = []  # Frame indices for each segment
        self.num_aux_palettes: int = 0
        self.aux_palettes: List[List[int]] = []  # List of 32-byte auxiliary palettes
        self.num_offsets: int = 0
        self.frame_offsets: List[int] = []  # Absolute offsets to frame headers
        
        # Parsed frames
        self.frames: Dict[int, AnimationFrame] = {}  # frame_index -> frame
        
        # Legacy compatibility
        self.atom_to_fragment: List[int] = []  # Will be filled from first aux palette
        self.offset_table: List[int] = []  # Will be filled from frame_offsets
    
    def parse(self) -> None:
        """Parse the animation file according to uw-formats.txt specification."""
        if not self.filepath.exists():
            return
        
        with open(self.filepath, 'rb') as f:
            self._data = f.read()
        
        if len(self._data) < 4:  # Minimum header size
            return
        
        try:
            pos = 0
            
            # Read header
            self.slot_base = self._data[pos]
            pos += 1
            self.num_slots = self._data[pos]
            pos += 1
            
            if self.num_slots == 0:
                return
            
            # Read slot offsets (segment indices for each slot)
            self.slot_offsets = []
            for i in range(self.num_slots):
                if pos < len(self._data):
                    self.slot_offsets.append(self._data[pos])
                    pos += 1
            
            # Read number of segments
            if pos >= len(self._data):
                return
            self.num_segments = self._data[pos]
            pos += 1
            
            # Read segment frame indices (8 bytes per segment)
            self.segment_frames = []
            for i in range(self.num_segments):
                frames = []
                for j in range(8):
                    if pos < len(self._data):
                        frames.append(self._data[pos])
                        pos += 1
                self.segment_frames.append(frames)
            
            # Read number of auxiliary palettes
            if pos >= len(self._data):
                return
            self.num_aux_palettes = self._data[pos]
            pos += 1
            
            # Read auxiliary palettes (32 bytes each)
            self.aux_palettes = []
            for i in range(self.num_aux_palettes):
                palette = []
                for j in range(32):
                    if pos < len(self._data):
                        palette.append(self._data[pos])
                        pos += 1
                    else:
                        palette.append(0)
                self.aux_palettes.append(palette)
            
            # Read number of frame offsets
            if pos >= len(self._data):
                return
            self.num_offsets = self._data[pos]
            pos += 1
            
            # Read unknown byte (compression type indicator, usually 0x06)
            if pos >= len(self._data):
                return
            _unknown = self._data[pos]
            pos += 1
            
            # Read frame offsets (16-bit absolute offsets)
            self.frame_offsets = []
            for i in range(self.num_offsets):
                if pos + 1 < len(self._data):
                    offset = struct.unpack_from('<H', self._data, pos)[0]
                    self.frame_offsets.append(offset)
                    pos += 2
                else:
                    self.frame_offsets.append(0)
            
            # Legacy compatibility: fill atom_to_fragment from first aux palette
            self.atom_to_fragment = []
            for pal in self.aux_palettes:
                self.atom_to_fragment.extend(pal)
            # Pad to 128 if needed
            while len(self.atom_to_fragment) < 128:
                self.atom_to_fragment.append(0)
            
            # Legacy compatibility: fill offset_table
            self.offset_table = self.frame_offsets.copy()
            
            # Parse frames
            self._parse_frames()
            
            self._parsed = True
            
        except Exception as e:
            # Parsing failed, file format may be different or corrupted
            return
    
    def _parse_frames(self) -> None:
        """Parse animation frames using the frame offset table."""
        for frame_index, frame_offset in enumerate(self.frame_offsets):
            if frame_offset == 0 or frame_offset >= len(self._data):
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
                if width == 0 or height == 0:
                    continue
                
                # Validate reasonable dimensions (NPC sprites are typically 8-128 pixels)
                if width > 256 or height > 256:
                    continue
                
                # Accept compression formats:
                # 0x06 = 5-bit RLE (common)
                # 0x08 = 4-bit RLE (also used)
                # Some files may have type != 6, which means 4-bit
                if compression == self.COMPRESSION_5BIT_RLE:
                    word_size = 5
                else:
                    word_size = 4  # Default to 4-bit for type != 6
                
                # Calculate estimated data size in bytes
                # data_length_words is the number of 4-bit or 5-bit words
                data_size_bytes = (data_length_words * word_size + 7) // 8
                
                data_start = frame_offset + 7
                
                # Find the next frame offset to determine actual data boundaries
                next_offset = len(self._data)  # Default to end of file
                for other_offset in self.frame_offsets:
                    if other_offset > frame_offset and other_offset < next_offset:
                        next_offset = other_offset
                
                # Use the smaller of calculated size or actual frame boundary
                data_end = min(data_start + data_size_bytes, next_offset, len(self._data))
                actual_data_size = data_end - data_start
                
                # Need at least some data
                if actual_data_size < 1:
                    continue
                
                frame_data = self._data[data_start:data_end]
                
                self.frames[frame_index] = AnimationFrame(
                    frame_index=frame_index,
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
                      aux_palette_parser: Optional[Any] = None,
                      auxpal_index: int = 0) -> Optional['Image.Image']:
        """
        Convert an animation frame to a PIL Image.
        
        Based on UWXtract's algorithm:
        1. Decompress RLE to get atom indices (5-bit or 4-bit values)
        2. Map atom indices through auxiliary palette to get main palette indices
        3. Look up colors from main palette
        
        Args:
            frame: AnimationFrame to convert
            palette: Main 256-color palette (from PALS.DAT)
            aux_palette_parser: (unused, for compatibility)
            auxpal_index: Index of auxiliary palette within animation file (0-3).
                         Different NPCs using the same animation file may use different palettes.
            
        Returns:
            PIL Image or None if conversion fails
        """
        if Image is None:
            return None
        
        expected_pixels = frame.width * frame.height
        
        # Determine word size based on compression type
        # Type 0x06 = 5-bit, otherwise 4-bit (per uw-formats.txt)
        if frame.compression_type == self.COMPRESSION_5BIT_RLE:
            word_size = 5
        else:
            word_size = 4
        
        # Decompress RLE to get atom indices
        atom_indices = self._decompress_rle(frame.data, word_size, expected_pixels)
        
        if not atom_indices or len(atom_indices) < expected_pixels:
            return None
        
        # Get the auxiliary palette for this NPC (maps atom indices to main palette indices)
        aux_pal = None
        if self.aux_palettes and auxpal_index < len(self.aux_palettes):
            aux_pal = self.aux_palettes[auxpal_index]
        elif self.atom_to_fragment:
            # Legacy fallback - use atom_to_fragment
            palette_offset = auxpal_index * 32
            if len(self.atom_to_fragment) >= palette_offset + 32:
                aux_pal = self.atom_to_fragment[palette_offset:palette_offset + 32]
            elif len(self.atom_to_fragment) >= 32:
                aux_pal = self.atom_to_fragment[:32]
        
        # Create RGBA image
        rgba = Image.new('RGBA', (frame.width, frame.height), (0, 0, 0, 0))
        pixels = rgba.load()
        
        # Convert atom indices to colors
        for y in range(frame.height):
            for x in range(frame.width):
                pixel_idx = y * frame.width + x
                if pixel_idx >= len(atom_indices):
                    continue
                
                # Get atom index from decompressed data
                atom_index = atom_indices[pixel_idx]
                
                # Index 0 = transparent
                if atom_index == 0:
                    pixels[x, y] = (0, 0, 0, 0)
                    continue
                
                # Map atom index through auxiliary palette to get main palette index
                if aux_pal and atom_index < len(aux_pal):
                    palette_index = aux_pal[atom_index]
                else:
                    # Fallback: use atom index directly (likely wrong, but better than crash)
                    palette_index = atom_index
                
                # Look up color from main palette
                if palette_index < len(palette):
                    r, g, b = palette[palette_index]
                    pixels[x, y] = (r, g, b, 255)
                else:
                    # Out of range, use black
                    pixels[x, y] = (0, 0, 0, 255)
        
        return rgba
    
    def _decompress_rle(self, data: bytes, bits: int, expected_pixels: int) -> List[int]:
        """
        Decompress RLE data using the UWXtract algorithm.
        
        Based on UWXtract's ImageDecode4BitRLE function and uw-formats.txt.
        
        Args:
            data: Compressed data bytes
            bits: Word size in bits (4 or 5)
            expected_pixels: Expected number of pixels after decompression
            
        Returns:
            List of pixel indices (0-15 for 4-bit, 0-31 for 5-bit)
        """
        # Bit extraction variables
        bits_avail = 0
        rawbits = 0
        bitmask = ((1 << bits) - 1) << (8 - bits)
        data_pos = 0
        
        # RLE decoding state
        pixel_indices = []
        stage = 0  # Count extraction stage (0-5)
        record = 0  # Record type: 0=repeat start, 1=repeat value, 2=multiple repeat, 3=run start, 4=run value
        count = 0
        repeatcount = 0
        
        while len(pixel_indices) < expected_pixels:
            # Get new nibble/word
            if bits_avail < bits:
                # Not enough bits available
                if bits_avail > 0:
                    nibble = ((rawbits & bitmask) >> (8 - bits_avail))
                    nibble <<= (bits - bits_avail)
                else:
                    nibble = 0
                
                if data_pos >= len(data):
                    break  # End of data
                
                rawbits = data[data_pos]
                data_pos += 1
                
                shiftval = 8 - (bits - bits_avail)
                nibble |= (rawbits >> shiftval)
                rawbits = (rawbits << (8 - shiftval)) & 0xFF
                bits_avail = shiftval
            else:
                # We still have enough bits
                nibble = (rawbits & bitmask) >> (8 - bits)
                bits_avail -= bits
                rawbits = (rawbits << bits) & 0xFF
            
            # Process nibble based on stage (count extraction)
            if stage == 0:
                if nibble == 0:
                    stage = 1
                else:
                    count = nibble
                    stage = 6  # Count complete
            elif stage == 1:
                count = nibble
                stage = 2
            elif stage == 2:
                count = (count << 4) | nibble
                if count == 0:
                    stage = 3
                else:
                    stage = 6  # Count complete
            elif stage in (3, 4, 5):
                count = (count << 4) | nibble
                stage += 1
            
            if stage < 6:
                continue
            
            # Process record based on type
            if record == 0:  # Repeat record start
                if count == 1:
                    record = 3  # Skip this record; a run follows
                elif count == 2:
                    record = 2  # Multiple repeat records
                else:
                    record = 1  # Read next nibble; it's the color to repeat
                    continue
            elif record == 1:  # Repeat record - write color 'count' times
                for _ in range(count):
                    if len(pixel_indices) >= expected_pixels:
                        break
                    pixel_indices.append(nibble)
                
                if repeatcount == 0:
                    record = 3  # Next one is a run record
                else:
                    repeatcount -= 1
                    record = 0  # Continue with repeat records
            elif record == 2:  # Multiple repeat - 'count' specifies number of repeat records
                repeatcount = count - 1
                record = 0
            elif record == 3:  # Run record start - copy 'count' nibbles
                record = 4
                continue
            elif record == 4:  # Run record - write nibble
                pixel_indices.append(nibble)
                count -= 1
                if count == 0:
                    record = 0  # Next one is a repeat again
                else:
                    continue
            
            stage = 0  # Reset stage for next count
        
        # Pad to expected size if needed
        while len(pixel_indices) < expected_pixels:
            pixel_indices.append(0)
        
        return pixel_indices[:expected_pixels]
    
    def _decompress_5bit_rle(self, data: bytes, data_length_words: int, expected_pixels: int) -> List[int]:
        """
        Decompress 5-bit RLE data.
        
        Args:
            data: Compressed data bytes
            data_length_words: Expected number of 5-bit words (for reference)
            expected_pixels: Expected number of pixels after decompression
            
        Returns:
            List of pixel indices (0-31 for 5-bit)
        """
        return self._decompress_rle(data, 5, expected_pixels)
    
    def _decompress_4bit_rle(self, data: bytes, data_length_nibbles: int, expected_pixels: int) -> List[int]:
        """
        Decompress 4-bit RLE data.
        
        Args:
            data: Compressed data bytes
            data_length_nibbles: Expected number of 4-bit nibbles (for reference)
            expected_pixels: Expected number of pixels after decompression
            
        Returns:
            List of pixel indices (0-15 for 4-bit)
        """
        return self._decompress_rle(data, 4, expected_pixels)
    
    def _get_animation_palette(self, main_palette: List[Tuple[int, int, int]], 
                               aux_palette_parser: Optional[Any]) -> List[Tuple[int, int, int]]:
        """
        Get palette for animation frames (32 colors for 5-bit indices).
        
        Uses the first auxiliary palette from the animation file.
        """
        return self._get_animation_palette_by_index(main_palette, 0)
    
    def _get_animation_palette_by_index(self, main_palette: List[Tuple[int, int, int]], 
                                        auxpal_index: int = 0) -> List[Tuple[int, int, int]]:
        """
        Get palette for animation frames using specific auxiliary palette index.
        
        Animation files contain auxiliary palettes (typically 4, each 32 bytes).
        Each byte is an index into the main 256-color palette.
        
        Args:
            main_palette: Main 256-color palette
            auxpal_index: Which auxiliary palette to use (0-3)
            
        Returns:
            32-color palette as list of RGB tuples
        """
        # Clamp auxpal_index to valid range
        if self.aux_palettes:
            auxpal_index = max(0, min(len(self.aux_palettes) - 1, auxpal_index))
        else:
            auxpal_index = 0
        
        # Use the correctly parsed aux_palettes if available
        if self.aux_palettes and auxpal_index < len(self.aux_palettes):
            aux_pal = self.aux_palettes[auxpal_index]
            anim_pal = []
            for i in range(min(32, len(aux_pal))):
                palette_idx = aux_pal[i]
                if palette_idx < len(main_palette):
                    anim_pal.append(main_palette[palette_idx])
                else:
                    anim_pal.append((0, 0, 0))
            # Pad to 32 colors if needed
            while len(anim_pal) < 32:
                anim_pal.append((0, 0, 0))
            return anim_pal
        
        # Fallback: use legacy atom_to_fragment mapping
        if self.atom_to_fragment:
            palette_offset = auxpal_index * 32
            palette_end = palette_offset + 32
            
            if len(self.atom_to_fragment) >= palette_end:
                anim_pal = []
                for i in range(32):
                    atom_idx = self.atom_to_fragment[palette_offset + i]
                    if atom_idx < len(main_palette):
                        anim_pal.append(main_palette[atom_idx])
                    else:
                        anim_pal.append((0, 0, 0))
                return anim_pal
            elif len(self.atom_to_fragment) >= 32:
                # Fallback: use first 32 entries
                anim_pal = []
                for i in range(32):
                    atom_idx = self.atom_to_fragment[i] if i < len(self.atom_to_fragment) else i
                    if atom_idx < len(main_palette):
                        anim_pal.append(main_palette[atom_idx])
                    else:
                        anim_pal.append((0, 0, 0))
                return anim_pal
        
        # Final fallback: use first 32 colors of main palette
        if len(main_palette) >= 32:
            return list(main_palette[:32])
        else:
            return list(main_palette) + [(0, 0, 0)] * (32 - len(main_palette))
