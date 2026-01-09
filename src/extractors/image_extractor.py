"""
Image Extractor for Ultima Underworld

Extracts object sprite images from .GR files and saves them as PNG files.
Maps object IDs (0-511) to sprite indices in OBJECTS.GR or TMOBJ.GR.
"""

from pathlib import Path
from typing import Dict, List, Optional
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
        self._extracted = False
    
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
                img = gr_parser.sprite_to_image(sprite, self.palette, self.aux_palette_parser)
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
