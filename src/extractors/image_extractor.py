"""
Image Extractor for Ultima Underworld

Extracts object sprite images from .GR files and saves them as PNG files.
Maps object IDs (0-511) to sprite indices in OBJECTS.GR or TMOBJ.GR.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None

from ..parsers.image_parser import GrFileParser
from ..parsers.palette_parser import PaletteParser
from ..parsers.aux_palette_parser import AuxPaletteParser
from ..parsers.animation_parser import AnimationFileParser
from ..parsers.objects_parser import ObjectsParser
from ..constants.npcs import get_npc_type_name


class ImageExtractor:
    """
    Extracts object images from .GR files.
    
    Usage:
        extractor = ImageExtractor("path/to/DATA")
        extractor.extract()
        extractor.save_images("web/images/objects/")
    """
    
    NUM_OBJECT_TYPES = 512
    
    def __init__(self, data_path: str | Path):
        self.data_path = Path(data_path)
        self.objects_gr: Optional[GrFileParser] = None
        self.tmobj_gr: Optional[GrFileParser] = None
        self.palette: Optional[List[tuple]] = None
        self.aux_palette_parser: Optional[AuxPaletteParser] = None
        self.extracted_images: Dict[int, Image.Image] = {}
        self.extracted_npc_images: Dict[int, Image.Image] = {}  # Single "representative" image per NPC
        self.extracted_npc_frames: Dict[int, Dict[int, Image.Image]] = {}  # All frames per NPC: {npc_id: {slot: image}}
        self._extracted = False
        self.chr_gr: Optional[GrFileParser] = None
        self.objects_parser: Optional[ObjectsParser] = None
    
    def extract(self) -> bool:
        """
        Extract all object images.
        
        Returns:
            True if extraction was successful, False otherwise
        """
        if not PIL_AVAILABLE:
            print("Warning: PIL/Pillow not available, cannot extract images")
            return False
        
        # Try to load palette
        self._load_palette()
        
        if not self.palette:
            print("  Warning: Could not load palette, using default grayscale palette")
            # Create a default grayscale palette as fallback
            self.palette = [(i, i, i) for i in range(256)]
        else:
            print(f"  Loaded palette with {len(self.palette)} colors")
        
        # Load auxiliary palette file
        self._load_aux_palettes()
        
        # Try OBJECTS.GR first (most likely to have object sprites)
        objects_gr_path = self.data_path / "OBJECTS.GR"
        if objects_gr_path.exists():
            try:
                print(f"  Parsing {objects_gr_path.name}...")
                self.objects_gr = GrFileParser(objects_gr_path)
                self.objects_gr.parse()
                print(f"    Found {len(self.objects_gr.get_all_sprites())} sprites")
            except Exception as e:
                print(f"    Error parsing OBJECTS.GR: {e}")
        
        # Try TMOBJ.GR as alternative
        tmobj_gr_path = self.data_path / "TMOBJ.GR"
        if tmobj_gr_path.exists():
            try:
                print(f"  Parsing {tmobj_gr_path.name}...")
                self.tmobj_gr = GrFileParser(tmobj_gr_path)
                self.tmobj_gr.parse()
                print(f"    Found {len(self.tmobj_gr.get_all_sprites())} sprites")
            except Exception as e:
                print(f"    Error parsing TMOBJ.GR: {e}")
        
        if not self.objects_gr and not self.tmobj_gr:
            print("  No .GR files found for object images")
            return False
        
        # Extract images for all 512 object types
        # Use whichever parser has sprites (prefer OBJECTS.GR if both have sprites)
        gr_parser = None
        if self.objects_gr and len(self.objects_gr.get_all_sprites()) > 0:
            gr_parser = self.objects_gr
        elif self.tmobj_gr and len(self.tmobj_gr.get_all_sprites()) > 0:
            gr_parser = self.tmobj_gr
        
        if not gr_parser:
            print("  No sprites found in either .GR file")
            return False
        
        # First, let's see what sprites we actually have
        all_sprites = gr_parser.get_all_sprites()
        sprite_indices = sorted(all_sprites.keys())
        print(f"  Available sprite indices: {sprite_indices[:20]}..." if len(sprite_indices) > 20 else f"  Available sprite indices: {sprite_indices}")
        
        # Debug: print details of first few sprites
        for idx in sprite_indices[:5]:
            sprite = all_sprites[idx]
            print(f"    Sprite {idx}: type={sprite.bitmap_type}, size={sprite.width}x{sprite.height}, data_len={len(sprite.data)}")
        
        extracted_count = 0
        # Try mapping sprite indices to object IDs
        # For now, try direct mapping (sprite index = object ID)
        for sprite_idx in sprite_indices:
            sprite = all_sprites[sprite_idx]
            object_id = sprite_idx  # Assume direct mapping for now
            
            if object_id >= self.NUM_OBJECT_TYPES:
                continue
            
            try:
                # Object images in GR files are stored top-to-bottom (unlike NPC animation frames)
                # So we should NOT flip them vertically (flip_vertical=False)
                img = gr_parser.sprite_to_image(sprite, self.palette, self.aux_palette_parser, flip_vertical=False)
                if img:
                    self.extracted_images[object_id] = img
                    extracted_count += 1
                    if extracted_count <= 5:  # Print first few successes
                        print(f"    Extracted image for object {object_id} (sprite {sprite_idx})")
                else:
                    # Debug: print why conversion returned None
                    print(f"    Warning: Sprite {sprite_idx} (object {object_id}) conversion returned None (type={sprite.bitmap_type}, size={sprite.width}x{sprite.height}, data_len={len(sprite.data)})")
            except Exception as e:
                # Debug: print conversion errors (but don't print full traceback for known issues)
                if "charmap" not in str(e).lower():
                    print(f"    Error: Failed to convert sprite {sprite_idx} (object {object_id}): {e}")
                continue
        
        print(f"  Extracted {extracted_count} object images")
        self._extracted = True
        return extracted_count > 0
    
    def _load_palette(self) -> None:
        """Load palette from PALS.DAT or ALLPALS.DAT."""
        # Try ALLPALS.DAT first (may contain multiple palettes)
        allpals_path = self.data_path / "ALLPALS.DAT"
        if allpals_path.exists():
            try:
                parser = PaletteParser(allpals_path)
                parser.parse()
                # Use palette 0 (main palette)
                self.palette = parser.get_palette(0)
                if self.palette:
                    return
            except Exception:
                pass
        
        # Try PALS.DAT
        pals_path = self.data_path / "PALS.DAT"
        if pals_path.exists():
            try:
                parser = PaletteParser(pals_path)
                parser.parse()
                self.palette = parser.get_palette(0)
            except Exception:
                pass
    
    def _load_aux_palettes(self) -> None:
        """Load auxiliary palette file (ALLPALS.DAT)."""
        allpals_path = self.data_path / "ALLPALS.DAT"
        if allpals_path.exists():
            try:
                self.aux_palette_parser = AuxPaletteParser(allpals_path)
                self.aux_palette_parser.parse()
                print(f"  Loaded auxiliary palette file with {len(self.aux_palette_parser.get_all_aux_palettes())} palettes")
            except Exception as e:
                print(f"  Warning: Could not load auxiliary palette file: {e}")
    
    def save_images(self, output_dir: str | Path) -> Dict[int, str]:
        """
        Save extracted images to PNG files.
        
        Args:
            output_dir: Directory to save images to
            
        Returns:
            Dictionary mapping object_id -> image_path (relative to output_dir)
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        image_paths = {}
        
        for object_id, img in self.extracted_images.items():
            filename = f"object_{object_id:03d}.png"
            filepath = output_path / filename
            
            try:
                img.save(filepath, 'PNG')
                # Store relative path
                image_paths[object_id] = f"images/objects/{filename}"
            except Exception as e:
                print(f"    Warning: Failed to save {filename}: {e}")
        
        return image_paths
    
    def get_image_path(self, object_id: int) -> Optional[str]:
        """
        Get the image path for an object ID.
        
        Args:
            object_id: Object ID (0-511)
            
        Returns:
            Image path string or None if no image available
        """
        if object_id in self.extracted_images:
            return f"images/objects/object_{object_id:03d}.png"
        return None
    
    def has_image(self, object_id: int) -> bool:
        """Check if an image exists for an object ID."""
        return object_id in self.extracted_images
    
    def extract_npc_images(self) -> bool:
        """
        Extract NPC sprite images (object IDs 0x40-0x7F) from animation files.
        
        NPCs use animation files in the CRIT folder (CrXXpage.nYY format).
        Each NPC has an animation index stored in OBJECTS.DAT (byte 0 of 48-byte critter structure).
        Extract a frame from the idle animation (slot 0x20-0x27) or walking animation (slot 0x07).
        
        Returns:
            True if any NPC images were successfully extracted, False otherwise
        """
        if not PIL_AVAILABLE:
            print("Warning: PIL/Pillow not available, cannot extract NPC images")
            return False
        
        # Ensure palette is loaded
        if not self.palette:
            self._load_palette()
            if not self.palette:
                print("  Warning: Could not load palette for NPC images, using default grayscale palette")
                self.palette = [(i, i, i) for i in range(256)]
        
        # Ensure auxiliary palette parser is loaded
        if not self.aux_palette_parser:
            self._load_aux_palettes()
        
        # Load OBJECTS.DAT to get animation indices for each NPC
        if not self.objects_parser:
            objects_dat_path = self.data_path / "OBJECTS.DAT"
            if objects_dat_path.exists():
                try:
                    self.objects_parser = ObjectsParser(objects_dat_path)
                    self.objects_parser.parse()
                    print(f"  Loaded OBJECTS.DAT for animation index mapping")
                except Exception as e:
                    print(f"  Error parsing OBJECTS.DAT: {e}")
                    return False
            else:
                print("  Error: OBJECTS.DAT not found, cannot extract NPC animation indices")
                return False
        
        # Check if CRIT folder exists
        crit_dir = self.data_path.parent / "CRIT"  # CRIT is typically at Input/UW1/CRIT, not Input/UW1/DATA/CRIT
        if not crit_dir.exists():
            crit_dir = self.data_path / "CRIT"  # Try DATA/CRIT as fallback
        if not crit_dir.exists():
            print("  Error: CRIT folder not found, cannot extract NPC animation files")
            print(f"    Looked in: {self.data_path.parent / 'CRIT'}")
            print(f"    Looked in: {self.data_path / 'CRIT'}")
            return False
        
        print(f"  Using CRIT folder: {crit_dir}")
        
        extracted_frames = 0
        validated_frames = 0
        failed_validation_count = 0
        npcs_with_frames = 0
        
        # Extract ALL frames for each NPC
        for npc_id in range(0x40, 0x80):  # 0x40 to 0x7F inclusive
            critter = self.objects_parser.get_critter(npc_id)
            if not critter:
                continue
            
            animation_index = critter.animation_index
            npc_name = get_npc_type_name(npc_id)
            
            # Map animation index (decimal) to animation file (CrXX where XX is octal)
            # e.g., animation_index=1 → Cr01, animation_index=10 → Cr12 (octal)
            # Check BOTH .N00 and .N01 page files - they contain different animation frames
            anim_base = f"CR{animation_index:02o}PAGE"
            valid_frames_all_pages = {}
            
            # Try both .N00 and .N01 files
            for page_index, page_suffix in enumerate([".N00", ".N01"]):
                anim_file_path = crit_dir / f"{anim_base}{page_suffix}"
                
                if not anim_file_path.exists():
                    continue
                
                try:
                    # Parse animation file
                    anim_parser = AnimationFileParser(anim_file_path)
                    anim_parser.parse()
                    
                    # Get ALL valid frames from this page file
                    all_frames = anim_parser.get_all_frames()
                    
                    # Filter to valid frames with reasonable dimensions
                    # Accept both 5-bit RLE (0x06) and 4-bit RLE (0x08), and uncompressed (0x00)
                    for slot, frame in all_frames.items():
                        if (frame.compression_type in (0x00, 0x06, 0x08) and 
                            frame.width > 0 and frame.height > 0 and 
                            8 <= frame.width <= 128 and 8 <= frame.height <= 128):
                            # Create unique key: (slot, page_index) to avoid duplicates between .N00 and .N01
                            # Use page_index (0 for .N00, 1 for .N01) to differentiate same slots
                            unique_key = (slot, page_index)
                            valid_frames_all_pages[unique_key] = (frame, anim_parser, page_suffix)
                    
                except Exception as e:
                    # Print errors for first few NPCs or if it's a parsing error
                    if npcs_with_frames < 10 and ("parse" in str(e).lower() or "frame" in str(e).lower()):
                        print(f"    Warning: Failed to parse {anim_base}{page_suffix} for NPC 0x{npc_id:02X}: {e}")
                    continue
            
            if not valid_frames_all_pages:
                # Debug: print why no valid frames found
                if npcs_with_frames < 10:
                    print(f"    NPC 0x{npc_id:02X} ({npc_name}): No valid frames found in {anim_base}.N00/.N01")
                continue
            
            # Extract all valid frames for this NPC from all page files
            npc_frames = {}
            first_valid_frame = None
            
            for (slot, page_idx), (frame, anim_parser, page_suffix) in sorted(valid_frames_all_pages.items()):
                # Convert frame to image
                img = anim_parser.frame_to_image(frame, self.palette, self.aux_palette_parser)
                if img:
                    extracted_frames += 1
                    # Validate the image
                    is_valid, reason = self._validate_image(img, object_id=npc_id, is_npc=True)
                    if is_valid:
                        # Create unique slot identifier:
                        # .N00 frames: use slot number directly (0x00-0xFF)
                        # .N01 frames: use slot + 0x100 (0x100-0x1FF) to avoid conflicts
                        unique_slot = slot + (page_idx * 0x100)
                        
                        npc_frames[unique_slot] = img
                        validated_frames += 1
                        # Use the first valid frame as the "representative" image for this NPC
                        if first_valid_frame is None:
                            first_valid_frame = img
                    else:
                        failed_validation_count += 1
            
            if npc_frames:
                self.extracted_npc_frames[npc_id] = npc_frames
                if first_valid_frame:
                    self.extracted_npc_images[npc_id] = first_valid_frame
                npcs_with_frames += 1
                if npcs_with_frames <= 10:  # Print first 10
                    pages_used = []
                    if (crit_dir / f"{anim_base}.N00").exists():
                        pages_used.append(".N00")
                    if (crit_dir / f"{anim_base}.N01").exists():
                        pages_used.append(".N01")
                    pages_str = "+".join(pages_used) if pages_used else "none"
                    print(f"    NPC 0x{npc_id:02X} ({npc_name}): Extracted {len(npc_frames)} frames from {anim_base}({pages_str})")
                elif npcs_with_frames == 11:
                    print(f"    ... (processing remaining NPCs) ...")
        
        print(f"  Extracted {extracted_frames} total frames from animation files")
        print(f"  {validated_frames} frames passed validation across {npcs_with_frames} NPCs")
        if failed_validation_count > 0:
            print(f"  {failed_validation_count} frames failed validation")
        
        return validated_frames > 0
    
    def save_npc_images(self, output_dir: str | Path) -> Dict[int, str]:
        """
        Save extracted NPC images to PNG files.
        
        Saves all frames for each NPC, with the main representative image
        as npc_0x40.png (2-digit hex) and additional frames as npc_0x40_frame_0x30.png.
        
        Args:
            output_dir: Directory to save images to
            
        Returns:
            Dictionary mapping NPC object ID to main image file path
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        image_paths = {}
        total_saved = 0
        
        # Save all frames for each NPC
        for npc_id, frames_dict in self.extracted_npc_frames.items():
            if not frames_dict:
                continue
            
            # Save the main representative image (first valid frame)
            if npc_id in self.extracted_npc_images:
                main_img = self.extracted_npc_images[npc_id]
                filename = f"npc_{npc_id:02X}.png"  # Use 2-digit hex to match existing format
                filepath = output_path / filename
                try:
                    main_img.save(filepath, "PNG")
                    image_paths[npc_id] = f"images/npcs/{filename}"
                    total_saved += 1
                except Exception as e:
                    npc_name = get_npc_type_name(npc_id)
                    print(f"    Warning: Failed to save NPC 0x{npc_id:02X} ({npc_name}) main image: {e}")
            
            # Save all additional frames with slot numbers
            for slot, img in frames_dict.items():
                # Skip if this is the same as the main image (don't duplicate)
                if npc_id in self.extracted_npc_images and img is self.extracted_npc_images[npc_id]:
                    continue
                
                # Format slot number: if >= 0x100, it's from .N01, use 3-digit hex, otherwise 2-digit
                if slot >= 0x100:
                    # Slot from .N01: format as 0xXXX (3-digit) to distinguish from .N00 slots
                    filename = f"npc_{npc_id:02X}_frame_{slot:03X}.png"
                else:
                    # Slot from .N00: use 2-digit hex
                    filename = f"npc_{npc_id:02X}_frame_{slot:02X}.png"
                filepath = output_path / filename
                try:
                    img.save(filepath, "PNG")
                    total_saved += 1
                except Exception as e:
                    npc_name = get_npc_type_name(npc_id)
                    print(f"    Warning: Failed to save NPC 0x{npc_id:02X} ({npc_name}) frame 0x{slot:03X}: {e}")
        
        if total_saved > 0:
            print(f"  Saved {total_saved} NPC frame images ({len(image_paths)} main images + {total_saved - len(image_paths)} additional frames)")
        
        return image_paths
    
    def get_npc_image_path(self, npc_id: int) -> Optional[str]:
        """
        Get the image path for an NPC object ID.
        
        Args:
            npc_id: NPC object ID (0x40-0x7F)
            
        Returns:
            Image path string or None if no image available
        """
        if npc_id in self.extracted_npc_images:
            return f"images/npcs/npc_{npc_id:02X}.png"  # Use 2-digit hex to match save format
        return None
    
    def has_npc_image(self, npc_id: int) -> bool:
        """Check if an NPC image exists for an NPC object ID."""
        return npc_id in self.extracted_npc_images
    
    def _validate_image(self, img: Image.Image, object_id: Optional[int] = None, is_npc: bool = False) -> Tuple[bool, Optional[str]]:
        """
        Validate that an extracted image is not scrambled or corrupted.
        
        Args:
            img: PIL Image to validate
            object_id: Optional object ID for better error messages
            is_npc: True if this is an NPC image (stricter validation)
            
        Returns:
            Tuple of (is_valid, reason) where reason is None if valid, error message otherwise
        """
        if img is None:
            return False, "Image is None"
        
        width, height = img.size
        
        # Check dimensions are reasonable
        if width == 0 or height == 0:
            return False, "Zero dimensions"
        
        if width > 256 or height > 256:
            return False, f"Dimensions too large ({width}x{height})"
        
        # For NPCs, dimensions can be 8-128 pixels (matches our frame extraction filter)
        if is_npc:
            if width < 8 or height < 8 or width > 128 or height > 128:
                return False, f"NPC dimensions out of range ({width}x{height})"
        
        # Check that image has some non-transparent pixels
        pixels = img.load()
        non_transparent_count = 0
        color_set = set()
        
        for y in range(height):
            for x in range(width):
                pixel = pixels[x, y]
                if len(pixel) == 4:  # RGBA
                    r, g, b, a = pixel
                    if a > 0:  # Not fully transparent
                        non_transparent_count += 1
                        if r > 0 or g > 0 or b > 0:  # Not pure black
                            color_set.add((r, g, b))
                else:  # RGB
                    r, g, b = pixel[:3]
                    if r > 0 or g > 0 or b > 0:  # Not pure black
                        non_transparent_count += 1
                        color_set.add((r, g, b))
        
        total_pixels = width * height
        opacity_ratio = non_transparent_count / total_pixels if total_pixels > 0 else 0
        
        # Check opacity - should have at least 5% non-transparent pixels for a valid sprite
        # (some animation frames might be sparse or have large transparent areas)
        min_opacity = 0.05 if is_npc else 0.1
        if opacity_ratio < min_opacity:
            return False, f"Too transparent ({opacity_ratio:.1%} opaque)"
        
        # For NPCs, check color variance - allow at least 2 distinct colors
        # (some frames might be mostly single-color silhouettes, which is valid)
        if is_npc:
            if len(color_set) < 2:
                return False, f"Insufficient color variance ({len(color_set)} distinct colors)"
        
        # Check for obvious scrambling - if we have very uniform distribution, might be noise
        # This is a heuristic - if too many colors suggest random noise, it might be scrambled
        if len(color_set) > 200 and opacity_ratio < 0.3:
            return False, "Suspicious: many colors but low opacity (possible noise)"
        
        # Image appears valid
        return True, None
