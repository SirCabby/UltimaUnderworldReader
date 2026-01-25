"""
NPC-related sheet exports for Excel exporter.
"""

from typing import Dict, List

from ...constants import NPC_GOALS, NPC_ATTITUDES
from ...utils import parse_item_name


class NPCSheetsMixin:
    """Mixin providing NPC-related sheet exports."""
    
    def export_npcs(self, npcs: List, npc_names: Dict, strings_parser, level_parser=None) -> None:
        """Export NPCs with correct name mapping, goal descriptions, and inventory."""
        has_images = self._images_available
        
        if has_images:
            headers = [
                "Image", "Level", "Tile X", "Tile Y", "Creature Type", "Creature ID",
                "Named NPC", "Conv Slot", "HP",
                "Attitude", "Goal", "Goal Description", "Inventory", "Home X", "Home Y"
            ]
        else:
            headers = [
                "Level", "Tile X", "Tile Y", "Creature Type", "Creature ID",
                "Named NPC", "Conv Slot", "HP",
                "Attitude", "Goal", "Goal Description", "Inventory", "Home X", "Home Y"
            ]
        ws = self._create_sheet("NPCs", headers)
        
        if has_images:
            ws.column_dimensions['A'].width = 6
        
        obj_names = strings_parser.get_block(4) or []
        block7 = strings_parser.get_block(7) or []
        
        # Filter to placed NPCs only
        placed_npcs = [n for n in npcs if n.tile_x > 0 or n.tile_y > 0]
        sorted_npcs = sorted(placed_npcs, key=lambda n: (n.level, n.tile_x, n.tile_y))
        
        row = 2
        for npc in sorted_npcs:
            # Get creature type from object names
            creature_type = ""
            if npc.object_id < len(obj_names):
                raw = obj_names[npc.object_id]
                if raw:
                    creature_type, _, _ = parse_item_name(raw)
            
            # Get named NPC from conversation slot
            named_npc = ""
            if npc.conversation_slot > 0:
                name_idx = npc.conversation_slot + 16
                if name_idx < len(block7) and block7[name_idx]:
                    named_npc = block7[name_idx]
            
            goal_desc = NPC_GOALS.get(npc.goal, f"Unknown ({npc.goal})")
            attitude_name = NPC_ATTITUDES.get(npc.attitude, str(npc.attitude))
            
            # Get NPC inventory
            inventory_str = self._get_npc_inventory(npc, level_parser, strings_parser, obj_names)
            
            if has_images:
                values = [
                    "",  # Placeholder for image
                    npc.level + 1, npc.tile_x, npc.tile_y, creature_type, f"0x{npc.object_id:02X}",
                    named_npc, npc.conversation_slot if npc.conversation_slot > 0 else "",
                    npc.hp,
                    attitude_name, npc.goal, goal_desc, inventory_str,
                    npc.home_x, npc.home_y
                ]
            else:
                values = [
                    npc.level + 1, npc.tile_x, npc.tile_y, creature_type, f"0x{npc.object_id:02X}",
                    named_npc, npc.conversation_slot if npc.conversation_slot > 0 else "",
                    npc.hp,
                    attitude_name, npc.goal, goal_desc, inventory_str,
                    npc.home_x, npc.home_y
                ]
            self._add_row(ws, row, values, row % 2 == 0)
            
            # Add NPC image if available
            if has_images:
                pil_img = self._get_npc_image(npc.object_id)
                if pil_img:
                    self._add_image_to_cell(ws, pil_img, f'A{row}')
                    self._set_row_height_for_image(ws, row)
            
            row += 1
        self._auto_column_width(ws, skip_columns=['A'] if has_images else [])
    
    def _get_npc_inventory(self, npc, level_parser, strings_parser, obj_names) -> str:
        """Get inventory string for an NPC."""
        if not level_parser or not hasattr(npc, 'special_link') or npc.special_link <= 0:
            return ""
        
        level = level_parser.get_level(npc.level)
        if not level:
            return ""
        
        spell_names = strings_parser.get_block(6) or []
        block5 = strings_parser.get_block(5) or []
        inv_items = []
        current = npc.special_link
        seen = set()
        
        while current > 0 and current not in seen and len(inv_items) < 20:
            seen.add(current)
            if current not in level.objects:
                break
            
            obj = level.objects[current]
            item_name, _, _ = parse_item_name(obj_names[obj.item_id] if obj.item_id < len(obj_names) else "")
            
            if item_name:
                item_desc = self._format_inventory_item(
                    obj, item_name, npc.level, spell_names, block5, level
                )
                inv_items.append(item_desc)
            
            current = obj.next_index
        
        return ", ".join(inv_items) if inv_items else ""
    
    def _format_inventory_item(self, obj, item_name, level_num, spell_names, block5, level) -> str:
        """Format an inventory item with appropriate metadata."""
        item_desc = item_name
        
        # Keys
        if 0x100 <= obj.item_id <= 0x10E:
            if obj.owner > 0:
                desc_idx = 100 + obj.owner
                if desc_idx < len(block5) and block5[desc_idx]:
                    key_desc = block5[desc_idx]
                    item_desc = f"key ({key_desc[:40]}...)" if len(key_desc) > 40 else f"key ({key_desc})"
                else:
                    item_desc = f"key (lock #{obj.owner})"
        
        # Scrolls
        elif 0x138 <= obj.item_id <= 0x13F and obj.item_id != 0x13B:
            link = obj.quantity_or_link
            if obj.is_quantity and link >= 512:
                item_desc = f"scroll (text #{link-512})"
            else:
                item_desc = "scroll"
        
        # Books
        elif 0x130 <= obj.item_id <= 0x137:
            link = obj.quantity_or_link
            if obj.is_quantity and link >= 512:
                item_desc = f"book (text #{link-512})"
            else:
                item_desc = "book"
        
        # Potions
        elif obj.item_id == 0xBB:
            item_desc = "red potion (mana)"
        elif obj.item_id == 0xBC:
            item_desc = "green potion (heal)"
        
        # Wands
        elif 0x98 <= obj.item_id <= 0x9B:
            item_desc = self._format_wand(obj, level_num, spell_names, level)
        
        return item_desc
    
    def _format_wand(self, obj, level_num, spell_names, level) -> str:
        """Format a wand with spell and charges."""
        from ...constants import get_special_wand_info
        
        special_wand = get_special_wand_info(level_num, obj.tile_x, obj.tile_y)
        charges = obj.quality
        spell = ""
        
        if not obj.is_quantity:
            link = obj.quantity_or_link
            if link in level.objects:
                spell_obj = level.objects[link]
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
            return f"wand of {special_wand['name']} ({charges} charges)"
        elif spell:
            return f"wand of {spell} ({charges} charges)"
        else:
            return f"wand ({charges} charges)"
    
    def export_npc_names(self, npc_names: Dict, strings_parser=None) -> None:
        """Export NPC names (filtering out non-NPC strings)."""
        headers = ["Conv Slot", "NPC Name"]
        ws = self._create_sheet("NPC Names", headers)
        
        row = 2
        for slot in sorted(npc_names.keys()):
            name = npc_names[slot]
            # Filter non-NPC entries
            if not name or not name.strip():
                continue
            if "deal" in name.lower():
                continue
            if name.startswith("..."):
                continue
            if "cannot talk" in name.lower() or "no response" in name.lower():
                continue
            if "that I am getting" in name:
                continue
            
            self._add_row(ws, row, [slot, name.strip()], row % 2 == 0)
            row += 1
        self._auto_column_width(ws)
