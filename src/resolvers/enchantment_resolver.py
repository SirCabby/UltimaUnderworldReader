"""
Enchantment resolution for weapons, armor, and other items.

Resolves enchantment effects from raw object data, mapping enchantment
property values to spell names and effect descriptions.
"""

from typing import Dict, Optional, Any

from .spell_resolver import get_spell_names


# Spell descriptions for common enchantments
SPELL_DESCRIPTIONS = {
    # Combat spells
    "Light": "Creates light",
    "Magic Arrow": "Fires magic projectile",
    "Resist Blows": "Reduces physical damage",
    "Stealth": "Harder to detect",
    "Conceal": "Become invisible",
    "Fly": "Grants flight",
    "Water Walk": "Walk on water",
    "Speed": "Move faster",
    "Flameproof": "Resist fire damage",
    "Poison Resistance": "Resist poison",
    "Open": "Opens locks",
    "Telekinesis": "Move objects at distance",
    "Luck": "Improves luck",
    "Night Vision": "See in dark",
    "Mending": "Repairs items",
    "Valor": "Increases combat ability",
    "Thick Skin": "Reduces damage",
    "Roaming Sight": "See through walls",
    "Iron Flesh": "Greatly reduces damage",
    "Name Enchantment": "Identifies items",
    "Gate Travel": "Teleport to moongate",
    "Restoration": "Heals wounds",
    "Heal": "Heals wounds",
    "Cure Poison": "Removes poison",
    "Mana Boost": "Restores mana",
    "Restore Mana": "Restores mana",
    "Ally": "Befriends creature",
    "Hallucination": "Causes confusion",
    "Lesser Heal": "Heals minor wounds",
    "Greater Heal": "Heals major wounds",
    "Regeneration": "Slowly heals over time",
}


class EnchantmentResolver:
    """
    Resolves enchantment effects for items.
    
    Enchantments are encoded in the quantity_or_link field when
    is_quantity=True and the value is >= 512. The enchantment
    property is value - 512.
    
    Different item types interpret the enchantment property differently:
    - Weapons: 192-199 = accuracy, 200-207 = damage, 0-63 = spell effect
    - Armor: 192-199 = protection, 200-207 = toughness, 0-63 = spell effect
    - Treasure: property * 2 = spell index
    - Rings: direct spell index
    
    Usage:
        resolver = EnchantmentResolver(strings_parser)
        effect = resolver.get_effect(item)
    """
    
    def __init__(self, strings_parser):
        """
        Initialize the enchantment resolver.
        
        Args:
            strings_parser: Parsed StringsParser with game strings
        """
        self.spell_names = get_spell_names(strings_parser)
    
    def format_spell_with_description(self, spell_name: str) -> str:
        """
        Format spell name with description if available.
        
        Args:
            spell_name: Name of the spell
        
        Returns:
            Formatted string like "Spell Name (description)" or just "Spell Name"
        """
        if not spell_name:
            return ""
        desc = SPELL_DESCRIPTIONS.get(spell_name, "")
        if desc:
            return f"{spell_name} ({desc})"
        return spell_name
    
    def get_enchantment_property(self, item) -> Optional[int]:
        """
        Extract the enchantment property value from an item.
        
        Args:
            item: Game object with is_quantity, quantity, special_link fields
        
        Returns:
            Enchantment property (0-255) or None if not enchanted
        """
        if item.is_quantity:
            link = item.quantity
        else:
            link = item.special_link
        
        if link >= 512:
            return link - 512
        return None
    
    def get_weapon_effect(self, item) -> str:
        """
        Get enchantment effect for a weapon (0x00-0x1F).
        
        Args:
            item: Weapon object
        
        Returns:
            Effect description string
        """
        ench_property = self.get_enchantment_property(item)
        if ench_property is None:
            return ""
        
        # Accuracy enchantments (192-199)
        if 192 <= ench_property <= 199:
            spell_idx = 448 + (ench_property - 192)
            spell = self.spell_names.get(spell_idx, "")
            if spell:
                return self.format_spell_with_description(spell)
            return f"Accuracy +{ench_property - 191}"
        
        # Damage enchantments (200-207)
        elif 200 <= ench_property <= 207:
            spell_idx = 456 + (ench_property - 200)
            spell = self.spell_names.get(spell_idx, "")
            if spell:
                return self.format_spell_with_description(spell)
            return f"Damage +{ench_property - 199}"
        
        # Spell enchantments (0-63)
        elif ench_property < 64:
            spell_idx = 256 + ench_property
            spell = self.spell_names.get(spell_idx, "")
            return self.format_spell_with_description(spell)
        
        # Other values (64-191): look up directly
        else:
            spell = self.spell_names.get(ench_property, "")
            if spell:
                return self.format_spell_with_description(spell)
            return f"Enchantment #{ench_property}"
    
    def get_armor_effect(self, item) -> str:
        """
        Get enchantment effect for armor (0x20-0x3F).
        
        Args:
            item: Armor object
        
        Returns:
            Effect description string
        """
        ench_property = self.get_enchantment_property(item)
        if ench_property is None:
            return ""
        
        # Protection enchantments (192-199)
        if 192 <= ench_property <= 199:
            spell_idx = 464 + (ench_property - 192)
            spell = self.spell_names.get(spell_idx, "")
            if spell:
                return self.format_spell_with_description(spell)
            return f"Protection +{ench_property - 191}"
        
        # Toughness enchantments (200-207)
        elif 200 <= ench_property <= 207:
            spell_idx = 472 + (ench_property - 200)
            spell = self.spell_names.get(spell_idx, "")
            if spell:
                return self.format_spell_with_description(spell)
            return f"Toughness +{ench_property - 199}"
        
        # Spell enchantments (0-63)
        elif ench_property < 64:
            # Try direct index first (some spells are at direct index)
            spell = self.spell_names.get(ench_property, "")
            if spell:
                return self.format_spell_with_description(spell)
            # Fall back to 256+offset (other spells use this mapping)
            spell_idx = 256 + ench_property
            spell = self.spell_names.get(spell_idx, "")
            if spell:
                return self.format_spell_with_description(spell)
            return f"Enchantment #{ench_property}"
        
        # Other values (64-191): look up directly
        else:
            spell = self.spell_names.get(ench_property, "")
            if spell:
                return self.format_spell_with_description(spell)
            return f"Enchantment #{ench_property}"
    
    def get_ring_effect(self, item) -> str:
        """
        Get enchantment effect for rings.
        
        Rings use the enchantment property directly as the spell index.
        
        Args:
            item: Ring object (0x36, 0x38, 0x39, 0x3A)
        
        Returns:
            Effect description string
        """
        ench_property = self.get_enchantment_property(item)
        if ench_property is None:
            return ""
        
        spell = self.spell_names.get(ench_property, "")
        if spell:
            return self.format_spell_with_description(spell)
        return f"Unknown enchantment ({ench_property})"
    
    def get_treasure_effect(self, item) -> str:
        """
        Get enchantment effect for treasure items (0xA0-0xAF).
        
        Treasure items use ench_property * 2 as the spell index.
        Sceptres (0xAA) use different encoding.
        
        Args:
            item: Treasure object
        
        Returns:
            Effect description string
        """
        ench_property = self.get_enchantment_property(item)
        if ench_property is None:
            return ""
        
        object_id = item.object_id
        
        # Sceptres use special encoding
        if object_id == 0x0AA:
            # Try -73 offset first
            spell_idx = ench_property - 73
            spell = self.spell_names.get(spell_idx, "")
            if spell:
                return self.format_spell_with_description(spell)
            # Fall back to -76 offset
            spell_idx = ench_property - 76
            spell = self.spell_names.get(spell_idx, "")
            if spell:
                return self.format_spell_with_description(spell)
            return f"Unknown enchantment ({ench_property})"
        
        # Other treasure items use property * 2
        spell_idx = ench_property * 2
        spell = self.spell_names.get(spell_idx, "")
        if spell:
            return self.format_spell_with_description(spell)
        return f"Enchantment #{ench_property}"


def get_item_effect(item, strings_parser, level_parser=None) -> str:
    """
    Get the enchantment/effect description for any item.
    
    This is a convenience function that creates an EnchantmentResolver
    and delegates to the appropriate method based on item type.
    
    Args:
        item: Game object
        strings_parser: Parsed StringsParser with game strings
        level_parser: Optional level parser for wand spell lookup
    
    Returns:
        Effect description string
    """
    from ..constants import get_special_wand_info
    from .spell_resolver import SpellResolver
    
    resolver = EnchantmentResolver(strings_parser)
    spell_resolver = SpellResolver(strings_parser)
    object_id = item.object_id
    
    # Wands (0x98-0x9B)
    if 0x98 <= object_id <= 0x9B:
        # Check for special wands first
        special_wand = get_special_wand_info(item.level, item.tile_x, item.tile_y)
        
        if level_parser:
            spell_info = spell_resolver.resolve_wand_spell(item, level_parser)
            charges = spell_info['charges']
            spell_name = spell_info['spell_name']
        else:
            charges = item.quality
            spell_name = None
        
        if special_wand:
            return f"{special_wand['name']} ({charges} charges)"
        
        if spell_name:
            spell_with_desc = resolver.format_spell_with_description(spell_name)
            return f"{spell_with_desc} ({charges} charges)"
        return f"Unknown spell ({charges} charges)" if charges > 0 else "Empty"
    
    # Keys (0x100-0x10E)
    if 0x100 <= object_id <= 0x10E:
        if item.owner > 0:
            return f"Opens lock #{item.owner}"
        return ""
    
    # Books/Scrolls (0x130-0x13F, except map 0x13B)
    if 0x130 <= object_id <= 0x13F and object_id != 0x13B:
        link_value = item.quantity if item.is_quantity else item.special_link
        if item.is_quantity and link_value >= 512:
            text_idx = link_value - 512
            if item.is_enchanted:
                scroll_info = spell_resolver.resolve_scroll_spell(item)
                if scroll_info['spell_name']:
                    return resolver.format_spell_with_description(scroll_info['spell_name'])
                return f"Spell #{text_idx}"
            return f"Text #{text_idx}"
        return ""
    
    # Potions (0xBB red mana, 0xBC green health)
    if object_id in (0xBB, 0xBC):
        link_value = item.quantity if item.is_quantity else item.special_link
        if item.is_quantity and link_value >= 512:
            raw_idx = link_value - 512
            for offset in [256, 0]:
                spell = resolver.spell_names.get(raw_idx + offset, "")
                if spell:
                    return resolver.format_spell_with_description(spell)
            return f"Effect #{raw_idx}"
        if object_id == 0xBB:
            return "Restores Mana"
        else:
            return "Heals Wounds"
    
    # Sceptres (0x0AA) - special handling even without enchanted flag
    if object_id == 0x0AA:
        return resolver.get_treasure_effect(item)
    
    # Treasure items (0xA0-0xAF) - check even without enchanted flag
    if 0xA0 <= object_id <= 0xAF and object_id != 0x0AA:
        effect = resolver.get_treasure_effect(item)
        if effect:
            return effect
    
    # Armor (0x20-0x3F) - check even without enchanted flag
    if 0x20 <= object_id < 0x40:
        effect = resolver.get_armor_effect(item)
        if effect:
            return effect
    
    # If not enchanted and no special handling, return empty
    if not item.is_enchanted:
        return ""
    
    # Weapons (0x00-0x1F)
    if object_id < 0x20:
        return resolver.get_weapon_effect(item)
    
    # Rings (0x36, 0x38, 0x39, 0x3A)
    if object_id in (0x36, 0x38, 0x39, 0x3A):
        return resolver.get_ring_effect(item)
    
    # Armor (0x20-0x3F) - enchanted
    if 0x20 <= object_id < 0x40:
        return resolver.get_armor_effect(item)
    
    # Treasure items (0xA0-0xAF) - enchanted
    if 0xA0 <= object_id <= 0xAF:
        return resolver.get_treasure_effect(item)
    
    return ""
