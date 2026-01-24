"""
Image Extractor for Ultima Underworld

Extracts object sprite images from .GR files and saves them as PNG files.
Maps object IDs (0-511) to sprite indices in OBJECTS.GR or TMOBJ.GR.
"""

from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
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
from ..parsers.assoc_anm_parser import AssocAnmParser
from ..parsers.texture_parser import TextureParser
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
        self.assoc_anm_parser: Optional[AssocAnmParser] = None
        # Door images: door_texture_index -> image
        self.extracted_door_images: Dict[int, Image.Image] = {}
        self.doors_gr: Optional[GrFileParser] = None
        # TMOBJ images: sprite_index -> image (for writings, gravestones, etc.)
        self.extracted_tmobj_images: Dict[int, Image.Image] = {}
        # Wall textures: texture_index -> image (for special tmap objects)
        self.extracted_wall_textures: Dict[int, Image.Image] = {}
        self.wall_texture_parser: Optional[TextureParser] = None
    
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
    
    def replace_placeholder_sprites(self) -> int:
        """
        Replace placeholder sprites in OBJECTS.GR with actual textures from TMOBJ.GR.
        
        OBJECTS.GR contains placeholder text sprites ("tmap", "tmap c", etc.) for certain
        objects that don't have inventory representations:
        - 0x165 (gravestone): Replace with TMOBJ.GR index 28 (gravestone texture)
        - 0x166 (writing): Replace with TMOBJ.GR index 20 (writing background texture)
        - 0x16E (tmap_c): Replace with TMOBJ.GR index 20 (wall decal texture)
        - 0x16F (tmap_s): Replace with TMOBJ.GR index 20 (wall decal texture)
        
        Returns:
            Number of sprites replaced
        """
        if not PIL_AVAILABLE:
            return 0
        
        # Ensure TMOBJ.GR is loaded
        if not self.tmobj_gr:
            tmobj_gr_path = self.data_path / "TMOBJ.GR"
            if not tmobj_gr_path.exists():
                print("  TMOBJ.GR not found, cannot replace placeholder sprites")
                return 0
            try:
                self.tmobj_gr = GrFileParser(tmobj_gr_path)
                self.tmobj_gr.parse()
            except Exception as e:
                print(f"  Error loading TMOBJ.GR: {e}")
                return 0
        
        # Ensure palette is loaded
        if not self.palette:
            self._load_palette()
        if not self.palette:
            return 0
        
        tmobj_sprites = self.tmobj_gr.get_all_sprites()
        replaced_count = 0
        
        # Define replacements: object_id -> TMOBJ.GR index
        replacements = {
            0x165: 28,  # Gravestone -> gravestone texture with cross
            0x166: 20,  # Writing -> writing background texture (stone with cracks)
            0x16E: 20,  # Special tmap (collision) -> wall decal texture
            0x16F: 20,  # Special tmap (solid) -> wall decal texture
        }
        
        for obj_id, tmobj_idx in replacements.items():
            if tmobj_idx not in tmobj_sprites:
                continue
            
            sprite = tmobj_sprites[tmobj_idx]
            try:
                img = self.tmobj_gr.sprite_to_image(
                    sprite, self.palette, self.aux_palette_parser, flip_vertical=False
                )
                if img:
                    self.extracted_images[obj_id] = img
                    replaced_count += 1
                    print(f"    Replaced object 0x{obj_id:02X} with TMOBJ.GR texture {tmobj_idx}")
            except Exception as e:
                print(f"    Warning: Failed to replace object 0x{obj_id:02X}: {e}")
        
        return replaced_count
    
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
    
    def save_images(self, output_dir: str | Path, object_ids_filter: Optional[Set[int]] = None) -> Dict[int, str]:
        """
        Save extracted images to PNG files.
        
        Args:
            output_dir: Directory to save images to
            object_ids_filter: Optional set of object IDs to save. If provided,
                only images for these object IDs will be saved. If None, all
                extracted images will be saved.
            
        Returns:
            Dictionary mapping object_id -> image_path (relative to output_dir)
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        image_paths = {}
        skipped_count = 0
        
        for object_id, img in self.extracted_images.items():
            # Skip if filter is provided and this object ID is not in the filter
            if object_ids_filter is not None and object_id not in object_ids_filter:
                skipped_count += 1
                continue
            
            filename = f"object_{object_id:03d}.png"
            filepath = output_path / filename
            
            try:
                img.save(filepath, 'PNG')
                # Store relative path
                image_paths[object_id] = f"images/objects/{filename}"
            except Exception as e:
                print(f"    Warning: Failed to save {filename}: {e}")
        
        if skipped_count > 0:
            print(f"  Skipped {skipped_count} unused object images (not placed in game)")
        
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
        The mapping from NPC ID to animation file is stored in ASSOC.ANM:
        - Bytes 0-255: 32 animation names (8 bytes each)
        - Bytes 256-383: 64 NPC mappings (2 bytes each: anim_index, auxpal)
        
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
        
        # Load ASSOC.ANM for NPC-to-animation mapping
        assoc_anm_path = crit_dir / "ASSOC.ANM"
        if not assoc_anm_path.exists():
            print("  Error: ASSOC.ANM not found, cannot map NPCs to animation files")
            return False
        
        if not self.assoc_anm_parser:
            try:
                self.assoc_anm_parser = AssocAnmParser(assoc_anm_path)
                self.assoc_anm_parser.parse()
                print(f"  Loaded ASSOC.ANM with {len(self.assoc_anm_parser.animation_names)} animation types")
            except Exception as e:
                print(f"  Error parsing ASSOC.ANM: {e}")
                return False
        
        extracted_frames = 0
        validated_frames = 0
        failed_validation_count = 0
        npcs_with_frames = 0
        
        # Extract frames for each NPC using ASSOC.ANM mapping
        for npc_id in range(0x40, 0x80):  # 0x40 to 0x7F inclusive
            # Get animation info from ASSOC.ANM
            anim_info = self.assoc_anm_parser.get_npc_animation_info(npc_id)
            if not anim_info:
                continue
            
            npc_name = get_npc_type_name(npc_id)
            anim_base = anim_info.animation_filename  # e.g., "CR30PAGE"
            auxpal_index = anim_info.auxpal_index  # Auxiliary palette to use (0-3)
            
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
            # Priority slots for representative image (per uw-formats.txt):
            # 0x24 = idle, facing towards player (0 deg) - BEST for showing NPC
            # 0x23 = idle, 45 deg
            # 0x25 = idle, -45 deg  
            # 0x22 = idle, 90 deg
            # 0x26 = idle, -90 deg
            # 0x21 = idle, 135 deg
            # 0x27 = idle, -135 deg
            # 0x20 = idle, facing away (180 deg) - WORST for showing NPC
            priority_slots = [0x24, 0x23, 0x25, 0x22, 0x26, 0x21, 0x27, 0x20]
            
            # Collect valid frames by slot for priority selection
            valid_frames_by_slot = {}
            
            for (slot, page_idx), (frame, anim_parser, page_suffix) in sorted(valid_frames_all_pages.items()):
                # Convert frame to image using the correct auxiliary palette from ASSOC.ANM
                img = anim_parser.frame_to_image(frame, self.palette, self.aux_palette_parser, auxpal_index)
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
                        
                        # Track valid frames by base slot for priority selection
                        frame_size = img.width * img.height
                        if slot not in valid_frames_by_slot or frame_size > valid_frames_by_slot[slot][1]:
                            valid_frames_by_slot[slot] = (img, frame_size)
                        
                        # Use the first valid frame as fallback if no preferred frame found
                        if first_valid_frame is None:
                            first_valid_frame = img
                    else:
                        failed_validation_count += 1
            
            # Select representative frame using priority order
            # Prefer forward-facing idle frames (0x20, 0x24) with size-based scoring
            representative_frame = None
            for slot in priority_slots:
                if slot in valid_frames_by_slot:
                    representative_frame = valid_frames_by_slot[slot][0]
                    break
            
            # Fall back to first valid frame if no priority slot found
            if representative_frame is None:
                representative_frame = first_valid_frame
            
            if npc_frames:
                self.extracted_npc_frames[npc_id] = npc_frames
                if representative_frame:
                    self.extracted_npc_images[npc_id] = representative_frame
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
        
        Saves only the main representative image for each NPC as npc_XX.png (2-digit hex).
        
        Note: Frame image saving has been commented out as the web UI only uses
        the main representative images. Uncomment the frame saving code below
        if you need animation frames for other purposes.
        
        Args:
            output_dir: Directory to save images to
            
        Returns:
            Dictionary mapping NPC object ID to main image file path
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        image_paths = {}
        total_saved = 0
        
        # Save main representative image for each NPC
        for npc_id, frames_dict in self.extracted_npc_frames.items():
            if not frames_dict:
                continue
            
            # Save the main representative image (preferred idle frame or first valid frame)
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
            
            # NOTE: Frame images commented out - web UI only uses main representative images
            # Uncomment if you need animation frames for other purposes
            # 
            # # Save all additional frames with slot numbers
            # for slot, img in frames_dict.items():
            #     # Skip if this is the same as the main image (don't duplicate)
            #     if npc_id in self.extracted_npc_images and img is self.extracted_npc_images[npc_id]:
            #         continue
            #     
            #     # Format slot number: if >= 0x100, it's from .N01, use 3-digit hex, otherwise 2-digit
            #     if slot >= 0x100:
            #         # Slot from .N01: format as 0xXXX (3-digit) to distinguish from .N00 slots
            #         filename = f"npc_{npc_id:02X}_frame_{slot:03X}.png"
            #     else:
            #         # Slot from .N00: use 2-digit hex
            #         filename = f"npc_{npc_id:02X}_frame_{slot:02X}.png"
            #     filepath = output_path / filename
            #     try:
            #         img.save(filepath, "PNG")
            #         total_saved += 1
            #     except Exception as e:
            #         npc_name = get_npc_type_name(npc_id)
            #         print(f"    Warning: Failed to save NPC 0x{npc_id:02X} ({npc_name}) frame 0x{slot:03X}: {e}")
        
        if total_saved > 0:
            print(f"  Saved {total_saved} NPC images")
        
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
    
    def extract_door_images(self) -> bool:
        """
        Extract door texture images from DOORS.GR.
        
        DOORS.GR contains 13 door textures (32x64 pixels each).
        Door object IDs are 0x140-0x14F:
        - 0x140-0x145: Closed doors (different styles)
        - 0x0146: Portcullis
        - 0x0147: Secret door
        - 0x148-0x14F: Open versions of closed doors
        
        Returns:
            True if any door images were successfully extracted, False otherwise
        """
        if not PIL_AVAILABLE:
            print("Warning: PIL/Pillow not available, cannot extract door images")
            return False
        
        # Ensure palette is loaded
        if not self.palette:
            self._load_palette()
            if not self.palette:
                print("  Warning: Could not load palette for door images, using default grayscale palette")
                self.palette = [(i, i, i) for i in range(256)]
        
        # Load auxiliary palette file if not already loaded
        if not self.aux_palette_parser:
            self._load_aux_palettes()
        
        # Load DOORS.GR
        doors_gr_path = self.data_path / "DOORS.GR"
        if not doors_gr_path.exists():
            print("  Error: DOORS.GR not found, cannot extract door images")
            return False
        
        try:
            print(f"  Parsing DOORS.GR...")
            self.doors_gr = GrFileParser(doors_gr_path)
            self.doors_gr.parse()
            sprites = self.doors_gr.get_all_sprites()
            print(f"    Found {len(sprites)} door textures")
        except Exception as e:
            print(f"    Error parsing DOORS.GR: {e}")
            return False
        
        extracted_count = 0
        for sprite_idx, sprite in sorted(sprites.items()):
            try:
                # Door textures don't need flipping (they're already correct orientation)
                img = self.doors_gr.sprite_to_image(sprite, self.palette, self.aux_palette_parser, flip_vertical=False)
                if img:
                    self.extracted_door_images[sprite_idx] = img
                    extracted_count += 1
            except Exception as e:
                print(f"    Warning: Failed to extract door texture {sprite_idx}: {e}")
                continue
        
        print(f"  Extracted {extracted_count} door texture images")
        return extracted_count > 0
    
    def save_door_images(self, output_dir: str | Path) -> Dict[int, str]:
        """
        Save extracted door images to PNG files.
        
        Args:
            output_dir: Directory to save images to
            
        Returns:
            Dictionary mapping door texture index to image file path
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        image_paths = {}
        
        for door_idx, img in self.extracted_door_images.items():
            filename = f"door_{door_idx:02d}.png"
            filepath = output_path / filename
            
            try:
                img.save(filepath, 'PNG')
                image_paths[door_idx] = f"images/doors/{filename}"
            except Exception as e:
                print(f"    Warning: Failed to save {filename}: {e}")
        
        if image_paths:
            print(f"  Saved {len(image_paths)} door images")
        
        return image_paths
    
    def get_door_image_path(self, door_texture_idx: int) -> Optional[str]:
        """
        Get the image path for a door texture index.
        
        Args:
            door_texture_idx: Door texture index (0-12)
            
        Returns:
            Image path string or None if no image available
        """
        if door_texture_idx in self.extracted_door_images:
            return f"images/doors/door_{door_texture_idx:02d}.png"
        return None
    
    def has_door_image(self, door_texture_idx: int) -> bool:
        """Check if a door image exists for a texture index."""
        return door_texture_idx in self.extracted_door_images
    
    def extract_tmobj_images(self) -> bool:
        """
        Extract texture images from TMOBJ.GR for various 3D model objects.
        
        TMOBJ.GR contains textures for:
        - Pillars (0x160): image at offset flags
        - Levers (0x161): image at offset flags+4
        - Switches (0x162): image starting at 12
        - Writings (0x166): image at offset flags+20
        - Gravestones (0x165): image at offset flags+28
        - Bridges (0x164): image at offset 30+flags (for flags<2)
        - Tables (0x158): texture 32
        - Chairs (0x15c): texture 38
        - Shelves (0x169, UW2): texture flags+36
        - Pictures (0x163, UW2): texture flags+42
        
        Returns:
            True if any images were successfully extracted, False otherwise
        """
        if not PIL_AVAILABLE:
            print("Warning: PIL/Pillow not available, cannot extract TMOBJ images")
            return False
        
        # Ensure palette is loaded
        if not self.palette:
            self._load_palette()
            if not self.palette:
                print("  Warning: Could not load palette for TMOBJ images, using default grayscale palette")
                self.palette = [(i, i, i) for i in range(256)]
        
        # Load auxiliary palette file if not already loaded
        if not self.aux_palette_parser:
            self._load_aux_palettes()
        
        # Load TMOBJ.GR (reuse if already loaded)
        tmobj_gr_path = self.data_path / "TMOBJ.GR"
        if not tmobj_gr_path.exists():
            print("  Error: TMOBJ.GR not found, cannot extract decal images")
            return False
        
        try:
            print(f"  Parsing TMOBJ.GR...")
            tmobj_gr = GrFileParser(tmobj_gr_path)
            tmobj_gr.parse()
            sprites = tmobj_gr.get_all_sprites()
            print(f"    Found {len(sprites)} textures")
        except Exception as e:
            print(f"    Error parsing TMOBJ.GR: {e}")
            return False
        
        extracted_count = 0
        for sprite_idx, sprite in sorted(sprites.items()):
            try:
                # TMOBJ textures are used as wall/floor decals, don't flip
                img = tmobj_gr.sprite_to_image(sprite, self.palette, self.aux_palette_parser, flip_vertical=False)
                if img:
                    self.extracted_tmobj_images[sprite_idx] = img
                    extracted_count += 1
            except Exception as e:
                print(f"    Warning: Failed to extract TMOBJ texture {sprite_idx}: {e}")
                continue
        
        print(f"  Extracted {extracted_count} TMOBJ texture images")
        return extracted_count > 0
    
    def save_tmobj_images(self, output_dir: str | Path) -> Dict[int, str]:
        """
        Save extracted TMOBJ images to PNG files.
        
        Args:
            output_dir: Directory to save images to
            
        Returns:
            Dictionary mapping sprite index to image file path
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        image_paths = {}
        
        for sprite_idx, img in self.extracted_tmobj_images.items():
            filename = f"tmobj_{sprite_idx:02d}.png"
            filepath = output_path / filename
            
            try:
                img.save(filepath, 'PNG')
                image_paths[sprite_idx] = f"images/tmobj/{filename}"
            except Exception as e:
                print(f"    Warning: Failed to save {filename}: {e}")
        
        if image_paths:
            print(f"  Saved {len(image_paths)} TMOBJ images")
        
        return image_paths
    
    def get_writing_image_path(self, flags: int) -> Optional[str]:
        """
        Get the image path for a writing object (0x166) based on flags.
        
        Writings use TMOBJ.GR texture at index flags+20.
        
        Args:
            flags: The flags value from the object (determines texture variant)
            
        Returns:
            Image path string or None if no image available
        """
        texture_idx = flags + 20
        if texture_idx in self.extracted_tmobj_images:
            return f"images/tmobj/tmobj_{texture_idx:02d}.png"
        return None
    
    def get_gravestone_image_path(self, flags: int) -> Optional[str]:
        """
        Get the image path for a gravestone object (0x165) based on flags.
        
        Gravestones use TMOBJ.GR texture at index flags+28.
        
        Args:
            flags: The flags value from the object (determines texture variant)
            
        Returns:
            Image path string or None if no image available
        """
        texture_idx = flags + 28
        if texture_idx in self.extracted_tmobj_images:
            return f"images/tmobj/tmobj_{texture_idx:02d}.png"
        return None
    
    def get_lever_image_path(self, flags: int) -> Optional[str]:
        """
        Get the image path for a lever object (0x161) based on flags.
        
        Levers use TMOBJ.GR texture at index (flags & 0x07)+4.
        
        Args:
            flags: The flags value from the object (lower 3 bits determine texture)
            
        Returns:
            Image path string or None if no image available
        """
        texture_idx = (flags & 0x07) + 4
        if texture_idx in self.extracted_tmobj_images:
            return f"images/tmobj/tmobj_{texture_idx:02d}.png"
        return None
    
    def get_pillar_image_path(self, flags: int) -> Optional[str]:
        """
        Get the image path for a pillar object (0x160) based on flags.
        
        Pillars use TMOBJ.GR texture at index flags (lower byte).
        
        Args:
            flags: The flags value from the object
            
        Returns:
            Image path string or None if no image available
        """
        texture_idx = flags & 0xFF
        if texture_idx in self.extracted_tmobj_images:
            return f"images/tmobj/tmobj_{texture_idx:02d}.png"
        return None
    
    def has_tmobj_image(self, sprite_idx: int) -> bool:
        """Check if a TMOBJ image exists for a sprite index."""
        return sprite_idx in self.extracted_tmobj_images
    
    def extract_wall_textures(self) -> bool:
        """
        Extract wall textures from W64.TR for special tmap objects.
        
        Special tmap objects (item_id 0x016E, 0x016F) use wall textures:
        - 0x016E (tmap_c): texture from "owner" field -> index into wall texture table
        - 0x016F (tmap_s): same but with collision detection
        
        The "owner" field is an index into the texture mapping table, which then
        references a texture in W64.TR.
        
        Returns:
            True if any textures were successfully extracted, False otherwise
        """
        if not PIL_AVAILABLE:
            print("Warning: PIL/Pillow not available, cannot extract wall textures")
            return False
        
        # Ensure palette is loaded
        if not self.palette:
            self._load_palette()
            if not self.palette:
                print("  Warning: Could not load palette for wall textures, using default grayscale palette")
                self.palette = [(i, i, i) for i in range(256)]
        
        # Load W64.TR
        w64_path = self.data_path / "W64.TR"
        if not w64_path.exists():
            print("  Error: W64.TR not found, cannot extract wall textures")
            return False
        
        try:
            print(f"  Parsing W64.TR...")
            self.wall_texture_parser = TextureParser(w64_path)
            self.wall_texture_parser.parse()
            textures = self.wall_texture_parser.get_all_textures()
            print(f"    Found {len(textures)} wall textures ({self.wall_texture_parser.resolution}x{self.wall_texture_parser.resolution})")
        except Exception as e:
            print(f"    Error parsing W64.TR: {e}")
            return False
        
        extracted_count = 0
        for texture_idx, texture in sorted(textures.items()):
            try:
                img = self.wall_texture_parser.texture_to_image(texture, self.palette)
                if img:
                    self.extracted_wall_textures[texture_idx] = img
                    extracted_count += 1
            except Exception as e:
                print(f"    Warning: Failed to extract wall texture {texture_idx}: {e}")
                continue
        
        print(f"  Extracted {extracted_count} wall texture images")
        return extracted_count > 0
    
    def save_wall_textures(self, output_dir: str | Path, 
                          texture_indices: Optional[Set[int]] = None) -> Dict[int, str]:
        """
        Save extracted wall textures to PNG files.
        
        Args:
            output_dir: Directory to save images to
            texture_indices: Optional set of texture indices to save.
                           If None, saves all textures.
            
        Returns:
            Dictionary mapping texture index to image file path
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        image_paths = {}
        skipped = 0
        
        for texture_idx, img in self.extracted_wall_textures.items():
            if texture_indices is not None and texture_idx not in texture_indices:
                skipped += 1
                continue
            
            filename = f"wall_{texture_idx:03d}.png"
            filepath = output_path / filename
            
            try:
                img.save(filepath, 'PNG')
                image_paths[texture_idx] = f"images/walls/{filename}"
            except Exception as e:
                print(f"    Warning: Failed to save {filename}: {e}")
        
        if image_paths:
            print(f"  Saved {len(image_paths)} wall texture images")
        if skipped > 0:
            print(f"  Skipped {skipped} unused wall textures")
        
        return image_paths
    
    def get_special_tmap_image_path(self, owner_field: int) -> Optional[str]:
        """
        Get the image path for a special tmap object (0x016E, 0x016F) based on owner field.
        
        The owner field is an index into the wall texture table (W64.TR).
        
        Args:
            owner_field: The owner field from the object (indexes wall texture)
            
        Returns:
            Image path string or None if no image available
        """
        texture_idx = owner_field
        if texture_idx in self.extracted_wall_textures:
            return f"images/walls/wall_{texture_idx:03d}.png"
        return None
    
    def has_wall_texture(self, texture_idx: int) -> bool:
        """Check if a wall texture exists for an index."""
        return texture_idx in self.extracted_wall_textures
    
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
