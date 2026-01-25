"""
Placed objects and related sheet exports for Excel exporter.
"""

from typing import Dict, List, Set

from ...constants import (
    CATEGORY_DISPLAY_NAMES,
    SPELL_DESCRIPTIONS,
    get_special_wand_info,
)
from ...utils import parse_item_name, get_quality_description


class PlacedObjectsSheetsMixin:
    """Mixin providing placed objects sheet exports."""
    
    def export_placed_objects(self, placed_items: List, item_types: Dict, 
                             strings_parser, level_parser=None) -> None:
        """Export placed objects with actual locations, descriptions, and effects."""
        headers = [
            "Level", "Tile X", "Tile Y", "Item Name", "Item ID",
            "Category", "Description", "Enchantment/Effect"
        ]
        ws = self._create_sheet("Placed Objects", headers)
        
        obj_names = strings_parser.get_block(4) or []
        block3 = strings_parser.get_block(3) or []
        block5 = strings_parser.get_block(5) or []
        spell_names = strings_parser.get_block(6) or []
        
        # Filter to objects with actual tile positions
        placed_with_coords = [i for i in placed_items if i.tile_x > 0 or i.tile_y > 0]
        sorted_items = sorted(placed_with_coords, key=lambda x: (x.level, x.tile_x, x.tile_y))
        
        row = 2
        for item in sorted_items:
            # Skip NPCs, doors, triggers, traps
            if 0x40 <= item.object_id <= 0x7F:  # NPCs
                continue
            if 0x140 <= item.object_id <= 0x17F:  # Doors
                continue
            if 0x180 <= item.object_id <= 0x1BF:  # Traps/triggers
                continue
            
            name, _, _ = parse_item_name(obj_names[item.object_id] if item.object_id < len(obj_names) else "")
            
            cat_raw = getattr(item, 'detailed_category', None) or item.object_class
            cat_raw = cat_raw if isinstance(cat_raw, str) else ""
            category = CATEGORY_DISPLAY_NAMES.get(cat_raw, cat_raw.replace('_', ' ').title() if cat_raw else "Unknown")
            
            description = self._get_item_description(item, block3, block5, spell_names, level_parser)
            effect = self._get_item_effect(item, strings_parser, level_parser)
            
            values = [
                item.level + 1, item.tile_x, item.tile_y, name, f"0x{item.object_id:03X}",
                category, description, effect
            ]
            self._add_row(ws, row, values, row % 2 == 0)
            row += 1
        self._auto_column_width(ws)
    
    def _get_item_description(self, item, block3, block5, spell_names, level_parser=None) -> str:
        """Get item description based on type and quality/owner fields."""
        object_id = item.object_id
        link_value = item.quantity if item.is_quantity else item.special_link
        
        # Keys (0x100-0x10E)
        if 0x100 <= object_id <= 0x10E:
            if item.owner > 0:
                desc_idx = 100 + item.owner
                if desc_idx < len(block5) and block5[desc_idx]:
                    return block5[desc_idx]
            if object_id == 0x101:
                return "A lockpick"
            return ""
        
        # Books (0x130-0x137)
        if 0x130 <= object_id <= 0x137:
            if item.is_quantity and link_value >= 512:
                text_idx = link_value - 512
                if text_idx < len(block3) and block3[text_idx]:
                    return block3[text_idx].strip()
            return ""
        
        # Scrolls (0x138-0x13F, except 0x13B map)
        if 0x138 <= object_id <= 0x13F and object_id != 0x13B:
            if item.is_quantity and link_value >= 512:
                text_idx = link_value - 512
                if text_idx < len(block3) and block3[text_idx]:
                    return block3[text_idx].strip()
            return ""
        
        # Wands (0x98-0x9B)
        if 0x98 <= object_id <= 0x9B:
            return self._get_wand_description(item, spell_names, level_parser)
        
        # Map (0x13B)
        if object_id == 0x13B:
            return "Shows explored areas"
        
        # Potions (0xBB = red, 0xBC = green)
        if object_id in (0xBB, 0xBC):
            if item.is_quantity:
                link = item.quantity
                if link >= 512:
                    ench_idx = link - 512
                    spell = ""
                    if ench_idx + 256 < len(spell_names) and spell_names[ench_idx + 256]:
                        spell = spell_names[ench_idx + 256]
                    if not spell and ench_idx < len(spell_names) and spell_names[ench_idx]:
                        spell = spell_names[ench_idx]
                    if spell:
                        return f"Potion of {spell}"
                    return f"Potion (unknown effect #{ench_idx})"
            return ""
        
        # Coins
        if object_id == 0xA0:
            if item.is_quantity:
                return f"{item.quantity} gold pieces"
            return "Gold coin"
        
        # Arrows/bolts
        if object_id in (0x10, 0x11, 0x12):
            if item.is_quantity:
                return f"Stack of {item.quantity}"
            return ""
        
        # Runes
        if 0xE0 <= object_id <= 0xFF:
            return ""
        
        # Rings
        if object_id in (0x36, 0x38, 0x39, 0x3A):
            if item.is_enchanted and item.is_quantity:
                link = item.quantity
                if link >= 512:
                    ench_idx = link - 512
                    spell = spell_names[ench_idx] if ench_idx < len(spell_names) else ""
                    if spell:
                        return f"Ring of {spell}"
            return ""
        
        # Scenery
        if 0xC0 <= object_id <= 0xDF:
            return ""
        if object_id in (0x125,):
            return ""
        
        return get_quality_description(object_id, item.quality, block5)
    
    def _get_wand_description(self, item, spell_names, level_parser) -> str:
        """Get wand description with spell and charges."""
        special_wand = get_special_wand_info(item.level, item.tile_x, item.tile_y)
        charges = item.quality
        spell = ""
        
        if level_parser and not item.is_quantity:
            level = level_parser.get_level(item.level)
            if level and item.special_link in level.objects:
                spell_obj = level.objects[item.special_link]
                if spell_obj.item_id == 0x120:
                    charges = spell_obj.quality
                    v = spell_obj.quantity_or_link
                    candidates = []
                    if spell_obj.is_quantity:
                        if v >= 256:
                            candidates.append(v - 256)
                        candidates.extend([v, v + 256, v + 144])
                    else:
                        candidates.extend([v, v - 256, v + 256])
                    for cand in candidates:
                        if 0 <= cand < len(spell_names) and spell_names[cand]:
                            spell = spell_names[cand]
                            break
        
        if special_wand:
            return f"{special_wand['name']} ({charges} charges)"
        if spell:
            return f"Wand of {spell}"
        return f"Wand (unknown spell, {charges} charges)"
    
    def _get_item_effect(self, item, strings_parser, level_parser=None) -> str:
        """Get enchantment/effect description for an item."""
        spell_names = {}
        if strings_parser:
            block6 = strings_parser.get_block(6) or []
            for i, name in enumerate(block6):
                if name and name.strip():
                    spell_names[i] = name.strip()
        
        object_id = item.object_id
        link_value = item.quantity if item.is_quantity else item.special_link
        
        def format_spell_with_description(spell_name: str) -> str:
            if not spell_name:
                return ""
            desc = SPELL_DESCRIPTIONS.get(spell_name, "")
            if desc:
                return f"{spell_name} ({desc})"
            return spell_name
        
        # Wands
        if 0x98 <= object_id <= 0x9B:
            return self._get_wand_effect(item, spell_names, level_parser, format_spell_with_description)
        
        # Keys
        if 0x100 <= object_id <= 0x10E:
            if item.owner > 0:
                return f"Opens lock #{item.owner}"
            return ""
        
        # Books/Scrolls
        if 0x130 <= object_id <= 0x13F and object_id != 0x13B:
            if item.is_quantity and link_value >= 512:
                text_idx = link_value - 512
                if item.is_enchanted:
                    for offset in [256, 144, 0]:
                        spell = spell_names.get(text_idx + offset, "")
                        if spell:
                            return format_spell_with_description(spell)
                    return f"Spell #{text_idx}"
                return f"Text #{text_idx}"
            return ""
        
        # Potions
        if object_id in (0xBB, 0xBC):
            if item.is_quantity and link_value >= 512:
                raw_idx = link_value - 512
                for offset in [256, 0]:
                    spell = spell_names.get(raw_idx + offset, "")
                    if spell:
                        return format_spell_with_description(spell)
                return f"Effect #{raw_idx}"
            return "Restores Mana" if object_id == 0xBB else "Heals Wounds"
        
        # Sceptres
        if object_id == 0x0AA:
            return self._get_sceptre_effect(item, spell_names, format_spell_with_description)
        
        # Treasure items (non-sceptres)
        if 0xA0 <= object_id <= 0xAF and object_id != 0x0AA:
            return self._get_treasure_effect(item, spell_names, format_spell_with_description)
        
        # Armor (check even without enchanted flag)
        if 0x20 <= object_id < 0x40:
            return self._get_armor_effect(item, spell_names, format_spell_with_description)
        
        if not item.is_enchanted:
            return ""
        
        # Weapons
        if object_id < 0x20:
            return self._get_weapon_effect(item, spell_names, format_spell_with_description)
        
        # Rings
        if object_id in (0x36, 0x38, 0x39, 0x3A):
            return self._get_ring_effect(item, spell_names, format_spell_with_description)
        
        return ""
    
    def _get_wand_effect(self, item, spell_names, level_parser, format_spell) -> str:
        """Get wand effect string."""
        special_wand = get_special_wand_info(item.level, item.tile_x, item.tile_y)
        charges = item.quality
        spell = ""
        
        if level_parser and not item.is_quantity:
            level = level_parser.get_level(item.level)
            if level and item.special_link in level.objects:
                spell_obj = level.objects[item.special_link]
                if spell_obj.item_id == 0x120:
                    charges = spell_obj.quality
                    v = spell_obj.quantity_or_link
                    candidates = []
                    if spell_obj.is_quantity:
                        if v >= 256:
                            candidates.append(v - 256)
                        candidates.extend([v, v + 256, v + 144])
                    else:
                        candidates.extend([v, v - 256, v + 256])
                    for cand in candidates:
                        if cand in spell_names and spell_names[cand]:
                            spell = spell_names[cand]
                            break
        
        if special_wand:
            return f"{special_wand['name']} ({charges} charges)"
        if spell:
            return f"{format_spell(spell)} ({charges} charges)"
        return f"Unknown spell ({charges} charges)" if charges > 0 else "Empty"
    
    def _get_sceptre_effect(self, item, spell_names, format_spell) -> str:
        """Get sceptre effect string."""
        for field in ['special_link', 'quantity']:
            link = getattr(item, field, 0) if field == 'special_link' else item.quantity
            if link >= 512:
                ench_property = link - 512
                for offset in [73, 76]:
                    spell_idx = ench_property - offset
                    spell = spell_names.get(spell_idx, "")
                    if spell:
                        return format_spell(spell)
                return f"Unknown enchantment ({ench_property})"
        return ""
    
    def _get_treasure_effect(self, item, spell_names, format_spell) -> str:
        """Get treasure item effect string."""
        link = item.quantity if item.is_quantity else item.special_link
        if link >= 512:
            ench_property = link - 512
            spell_idx = ench_property * 2
            spell = spell_names.get(spell_idx, "")
            if spell:
                return format_spell(spell)
            return f"Enchantment #{ench_property}"
        return ""
    
    def _get_armor_effect(self, item, spell_names, format_spell) -> str:
        """Get armor effect string."""
        link = item.quantity if item.is_quantity else item.special_link
        if link < 512:
            return ""
        
        ench_property = link - 512
        
        if 192 <= ench_property <= 199:
            spell_idx = 464 + (ench_property - 192)
            spell = spell_names.get(spell_idx, "")
            if spell:
                return format_spell(spell)
            return f"Protection +{ench_property - 191}"
        elif 200 <= ench_property <= 207:
            spell_idx = 472 + (ench_property - 200)
            spell = spell_names.get(spell_idx, "")
            if spell:
                return format_spell(spell)
            return f"Toughness +{ench_property - 199}"
        elif ench_property < 64:
            spell = spell_names.get(ench_property, "")
            if spell:
                return format_spell(spell)
            spell_idx = 256 + ench_property
            spell = spell_names.get(spell_idx, "")
            if spell:
                return format_spell(spell)
            return f"Enchantment #{ench_property}"
        else:
            spell = spell_names.get(ench_property, "")
            if spell:
                return format_spell(spell)
            return f"Enchantment #{ench_property}"
    
    def _get_weapon_effect(self, item, spell_names, format_spell) -> str:
        """Get weapon effect string."""
        link = item.quantity if item.is_quantity else item.special_link
        if link < 512:
            return ""
        
        ench_property = link - 512
        
        if 192 <= ench_property <= 199:
            spell_idx = 448 + (ench_property - 192)
            spell = spell_names.get(spell_idx, "")
            if spell:
                return format_spell(spell)
            return f"Accuracy +{ench_property - 191}"
        elif 200 <= ench_property <= 207:
            spell_idx = 456 + (ench_property - 200)
            spell = spell_names.get(spell_idx, "")
            if spell:
                return format_spell(spell)
            return f"Damage +{ench_property - 199}"
        elif ench_property < 64:
            spell_idx = 256 + ench_property
            spell = spell_names.get(spell_idx, "")
            return format_spell(spell)
        else:
            spell = spell_names.get(ench_property, "")
            if spell:
                return format_spell(spell)
            return f"Enchantment #{ench_property}"
    
    def _get_ring_effect(self, item, spell_names, format_spell) -> str:
        """Get ring effect string."""
        link = item.quantity if item.is_quantity else item.special_link
        if link < 512:
            return ""
        
        ench_property = link - 512
        spell = spell_names.get(ench_property, "")
        if spell:
            return format_spell(spell)
        return f"Unknown enchantment ({ench_property})"
    
    def export_unused_items(self, item_types: Dict, placed_items: List, strings_parser) -> None:
        """Export items never placed in game."""
        headers = ["ID", "ID (Hex)", "Name", "Category", "Notes"]
        ws = self._create_sheet("Unused Items", headers)
        
        obj_names = strings_parser.get_block(4) or []
        placed_ids: Set[int] = {item.object_id for item in placed_items}
        
        row = 2
        for item_id in sorted(item_types.keys()):
            if item_id not in placed_ids:
                item = item_types[item_id]
                
                name, _, _ = parse_item_name(obj_names[item_id] if item_id < len(obj_names) else "")
                if not name:
                    name = "(unnamed)"
                
                notes = ""
                if 0x1C0 <= item_id <= 0x1FF:
                    notes = "System object"
                elif not name or name == "(unnamed)":
                    notes = "Unused/padding"
                else:
                    notes = "Defined but never placed"
                
                values = [item_id, f"0x{item_id:03X}", name, item.category, notes]
                self._add_row(ws, row, values, row % 2 == 0)
                row += 1
        self._auto_column_width(ws)
    
    def export_secrets(self, secrets: List) -> None:
        """Export secrets."""
        headers = ["Level", "Type", "Tile X", "Tile Y", "Object ID", "Description"]
        ws = self._create_sheet("Secrets & Traps", headers)
        
        sorted_secrets = sorted(secrets, key=lambda s: (s.level, s.secret_type, s.tile_x, s.tile_y))
        
        row = 2
        for secret in sorted_secrets:
            values = [
                secret.level + 1, secret.secret_type, secret.tile_x, secret.tile_y,
                f"0x{secret.object_id:03X}" if secret.object_id else "",
                secret.description
            ]
            self._add_row(ws, row, values, row % 2 == 0)
            row += 1
        self._auto_column_width(ws)
