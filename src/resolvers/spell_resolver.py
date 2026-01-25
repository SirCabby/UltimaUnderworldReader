"""
Spell resolution for wands, scrolls, and enchanted items.

Provides utilities for looking up spell names and resolving wand spells
from the linked spell object.
"""

from typing import Dict, Optional, Any


def get_spell_names(strings_parser) -> Dict[int, str]:
    """
    Extract spell names from the strings parser.
    
    Args:
        strings_parser: Parsed StringsParser with game strings
    
    Returns:
        Dictionary mapping spell index to spell name
    """
    spell_names = {}
    block6 = strings_parser.get_block(6) or []
    
    for i, name in enumerate(block6):
        if name and name.strip():
            spell_names[i] = name.strip()
    
    return spell_names


class SpellResolver:
    """
    Resolves spell information for wands and enchanted items.
    
    Wands link to spell objects (0x120) which store:
    - quality: remaining charges
    - quantity_or_link: encoded spell index
    
    Usage:
        resolver = SpellResolver(strings_parser)
        spell_info = resolver.get_wand_spell(wand_obj, level)
    """
    
    SPELL_OBJECT_ID = 0x120
    
    def __init__(self, strings_parser):
        """
        Initialize the spell resolver.
        
        Args:
            strings_parser: Parsed StringsParser with game strings
        """
        self.spell_names = get_spell_names(strings_parser)
    
    def get_spell_name(self, spell_index: int) -> Optional[str]:
        """
        Get the name of a spell by index.
        
        Args:
            spell_index: Index into the spell names table
        
        Returns:
            Spell name or None if not found
        """
        return self.spell_names.get(spell_index)
    
    def resolve_wand_spell(
        self,
        wand_obj,
        level_parser,
    ) -> Dict[str, Any]:
        """
        Resolve the spell and charges for a wand object.
        
        Wands (0x98-0x9B) link to a spell object (0x120) via special_link.
        The spell object's quantity_or_link encodes the spell index.
        
        Args:
            wand_obj: The wand object
            level_parser: The parsed level data
        
        Returns:
            Dictionary with:
                - spell_name: str or None
                - spell_index: int or None
                - charges: int
                - raw_value: int (the encoded value from spell object)
        """
        result = {
            'spell_name': None,
            'spell_index': None,
            'charges': wand_obj.quality,  # Default to wand's quality
            'raw_value': None
        }
        
        # If wand has is_quantity set, special_link won't be valid
        if wand_obj.is_quantity:
            return result
        
        # Get the level and find the spell object
        level = level_parser.get_level(wand_obj.level)
        if not level:
            return result
        
        special_link = wand_obj.quantity_or_link if not wand_obj.is_quantity else 0
        if special_link not in level.objects:
            return result
        
        spell_obj = level.objects[special_link]
        if spell_obj.item_id != self.SPELL_OBJECT_ID:
            return result
        
        # Spell object found - get charges and spell index
        result['charges'] = spell_obj.quality
        v = spell_obj.quantity_or_link
        result['raw_value'] = v
        
        # Try different offset candidates to decode the spell index
        # The encoding varies: sometimes v-256, sometimes direct, etc.
        candidates = []
        if spell_obj.is_quantity:
            if v >= 256:
                candidates.append(v - 256)
            candidates.extend([v, v + 256, v + 144])
        else:
            candidates.extend([v, v - 256, v + 256])
        
        for cand in candidates:
            if cand in self.spell_names and self.spell_names[cand]:
                result['spell_index'] = cand
                result['spell_name'] = self.spell_names[cand]
                break
        
        return result
    
    def resolve_scroll_spell(
        self,
        scroll_obj,
    ) -> Dict[str, Any]:
        """
        Resolve the spell for an enchanted scroll.
        
        Enchanted scrolls (spell scrolls) store the spell info in their
        quantity field: spell_index = quantity - 512
        
        Args:
            scroll_obj: The scroll object (must be enchanted)
        
        Returns:
            Dictionary with:
                - spell_name: str or None
                - spell_index: int or None
                - is_spell_scroll: bool
        """
        result = {
            'spell_name': None,
            'spell_index': None,
            'is_spell_scroll': False
        }
        
        if not scroll_obj.is_enchanted:
            return result
        
        if not (0x130 <= scroll_obj.object_id <= 0x13F):
            return result
        
        link_value = scroll_obj.quantity if scroll_obj.is_quantity else scroll_obj.special_link
        
        if scroll_obj.is_quantity and link_value >= 512:
            text_idx = link_value - 512
            result['is_spell_scroll'] = True
            
            # Try multiple offsets: +256 (common), +144 (for some spells), then direct
            for offset in [256, 144, 0]:
                spell_idx = text_idx + offset
                if spell_idx in self.spell_names and self.spell_names[spell_idx]:
                    result['spell_index'] = spell_idx
                    result['spell_name'] = self.spell_names[spell_idx]
                    break
            
            if result['spell_name'] is None:
                result['spell_index'] = text_idx
        
        return result
