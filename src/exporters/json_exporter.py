"""
JSON Exporter for Ultima Underworld extracted data.

Exports all extracted game data to JSON files.
"""

import json
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime


class JsonExporter:
    """
    Exports game data to JSON files.
    
    Usage:
        exporter = JsonExporter("output_folder")
        exporter.export_items(item_types, placed_items)
        exporter.export_npcs(npcs)
        exporter.export_spells(spells, mantras)
        exporter.export_secrets(secrets)
    """
    
    def __init__(self, output_path: str | Path):
        self.output_path = Path(output_path)
        self.output_path.mkdir(parents=True, exist_ok=True)
    
    def _write_json(self, filename: str, data: Any) -> Path:
        """Write data to a JSON file."""
        filepath = self.output_path / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return filepath
    
    def export_items(self, item_types: Dict, placed_items: List, image_paths: Dict[int, str] = None) -> None:
        """Export item data."""
        # Export item types
        items_list = []
        for item in item_types.values():
            item_dict = item.to_dict()
            # Add image path if available
            if image_paths and item.item_id in image_paths:
                item_dict['image_path'] = image_paths[item.item_id]
            items_list.append(item_dict)
        
        types_data = {
            'metadata': {
                'type': 'item_types',
                'game': 'Ultima Underworld I',
                'generated': datetime.now().isoformat(),
                'count': len(item_types)
            },
            'items': items_list
        }
        self._write_json('items.json', types_data)
        
        # Export placed items
        placed_data = {
            'metadata': {
                'type': 'placed_objects',
                'game': 'Ultima Underworld I',
                'generated': datetime.now().isoformat(),
                'count': len(placed_items)
            },
            'objects': [item.to_dict() for item in placed_items]
        }
        self._write_json('placed_objects.json', placed_data)
    
    def export_npcs(self, npcs: List, npc_names: Dict = None) -> None:
        """Export NPC data."""
        npc_data = {
            'metadata': {
                'type': 'npcs',
                'game': 'Ultima Underworld I',
                'generated': datetime.now().isoformat(),
                'count': len(npcs)
            },
            'npc_names': npc_names or {},
            'npcs': [npc.to_dict() for npc in npcs]
        }
        self._write_json('npcs.json', npc_data)
    
    def export_spells(self, spells: List, mantras: List, runes: Dict, spell_runes: Dict) -> None:
        """Export spell and mantra data."""
        spell_data = {
            'metadata': {
                'type': 'magic',
                'game': 'Ultima Underworld I',
                'generated': datetime.now().isoformat()
            },
            'runes': runes,
            'spell_runes': spell_runes,
            'spells': [s.to_dict() for s in spells],
            'mantras': [m.to_dict() for m in mantras]
        }
        self._write_json('spells.json', spell_data)
    
    def export_secrets(self, secrets: List) -> None:
        """Export secrets data."""
        secrets_data = {
            'metadata': {
                'type': 'secrets',
                'game': 'Ultima Underworld I',
                'generated': datetime.now().isoformat(),
                'count': len(secrets)
            },
            'secrets': [s.to_dict() for s in secrets]
        }
        self._write_json('secrets.json', secrets_data)
    
    def export_conversations(self, conversations: Dict, strings_parser) -> None:
        """Export conversation data."""
        conv_data = {
            'metadata': {
                'type': 'conversations',
                'game': 'Ultima Underworld I',
                'generated': datetime.now().isoformat(),
                'count': len(conversations)
            },
            'conversations': []
        }
        
        for slot, conv in conversations.items():
            # Get dialogue strings from the conversation's string block
            strings = strings_parser.get_block(conv.string_block) or []
            
            conv_entry = {
                'slot': slot,
                'string_block': conv.string_block,
                'num_variables': conv.num_variables,
                'imports': [
                    {
                        'name': imp.name,
                        'id': imp.id_or_addr,
                        'is_function': imp.is_function
                    }
                    for imp in conv.imports
                ],
                'code_size': len(conv.code),
                'strings': strings[:50]  # First 50 strings
            }
            conv_data['conversations'].append(conv_entry)
        
        self._write_json('conversations.json', conv_data)
    
    def export_map_data(self, levels: Dict) -> None:
        """Export map/level data."""
        map_data = {
            'metadata': {
                'type': 'maps',
                'game': 'Ultima Underworld I',
                'generated': datetime.now().isoformat(),
                'levels': len(levels)
            },
            'levels': []
        }
        
        for level_num, level in levels.items():
            # Summarize tile types
            tile_counts = {}
            for row in level.tiles:
                for tile in row:
                    tt = tile.tile_type.name
                    tile_counts[tt] = tile_counts.get(tt, 0) + 1
            
            level_entry = {
                'level': level_num,
                'size': '64x64',
                'tile_counts': tile_counts,
                'object_count': len(level.objects),
                'mobile_count': len(level.mobile_objects),
                'static_count': len(level.static_objects),
                'npc_count': len(level.get_all_npcs())
            }
            map_data['levels'].append(level_entry)
        
        self._write_json('map_data.json', map_data)
    
    def export_all_strings(self, strings_parser) -> None:
        """Export all game strings."""
        all_blocks = strings_parser.get_all_blocks()
        
        strings_data = {
            'metadata': {
                'type': 'strings',
                'game': 'Ultima Underworld I',
                'generated': datetime.now().isoformat(),
                'block_count': len(all_blocks)
            },
            'blocks': {}
        }
        
        block_names = {
            1: 'ui',
            2: 'chargen_mantras',
            3: 'scrolls_books',
            4: 'object_names',
            5: 'object_look',
            6: 'spell_names',
            7: 'npc_names',
            8: 'wall_text',
            9: 'trap_messages',
            10: 'wall_floor_desc',
            24: 'debug'
        }
        
        for block_num, strings in all_blocks.items():
            block_name = block_names.get(block_num, f'block_{block_num}')
            if block_num >= 0x0C00:
                block_name = f'conversation_{block_num:04X}'
            elif block_num >= 0x0E00:
                block_name = f'conv_strings_{block_num:04X}'
            
            strings_data['blocks'][str(block_num)] = {
                'name': block_name,
                'count': len(strings),
                'strings': strings
            }
        
        self._write_json('strings.json', strings_data)

    def export_web_map_data(self, placed_items: List, npcs: List, npc_names: Dict, 
                            item_types: Dict = None, levels: Dict = None,
                            strings_parser = None, secrets: List = None,
                            conversations: Dict = None, image_paths: Dict[int, str] = None,
                            npc_image_paths: Dict[int, str] = None) -> Path:
        """Export optimized data for the interactive web map viewer.
        
        Creates a single JSON file with all placed objects and NPCs,
        filtered to exclude template objects (those at tile 0,0).
        
        Args:
            placed_items: List of placed GameObjectInfo objects
            npcs: List of NPCInfo objects
            npc_names: Dict mapping conversation slots to NPC names
            item_types: Dict of ItemInfo objects for looking up item names
            levels: Dict of Level objects for following container chains
            strings_parser: StringsParser for looking up text (books, scrolls, keys, spells)
            secrets: List of Secret objects (illusory walls, secret doors, etc.)
            conversations: Dict of conversation slot -> Conversation (to verify dialogue exists)
            image_paths: Dict mapping object_id -> image_path for object images
            npc_image_paths: Dict mapping npc_object_id -> image_path for NPC images
        """
        from ..constants import SPELL_DESCRIPTIONS
        
        # Get string blocks for rich descriptions
        block3 = strings_parser.get_block(3) or [] if strings_parser else []  # Book/scroll text
        block4 = strings_parser.get_block(4) or [] if strings_parser else []  # Object names
        block5 = strings_parser.get_block(5) or [] if strings_parser else []  # Quality descriptions
        spell_names_list = strings_parser.get_block(6) or [] if strings_parser else []
        block8 = strings_parser.get_block(8) or [] if strings_parser else []  # Wall/sign text (for writing/gravestones)
        block9 = strings_parser.get_block(9) or [] if strings_parser else []  # Trap messages
        
        # Build spell names dict for lookups
        spell_names = {}
        for i, name in enumerate(spell_names_list):
            if name and name.strip():
                spell_names[i] = name.strip()
        
        def get_item_description(item, object_id: int, is_enchanted: bool, is_quantity: bool, 
                                 quantity: int, quality: int, owner: int,
                                 special_link: int, level_num: int) -> str:
            """Get item description based on type (books, scrolls, keys, wands, etc.).
            
            Note: Spell scrolls (enchanted books/scrolls) don't have readable text -
            they cast spells instead. Only non-enchanted books/scrolls have readable content.
            """
            link_value = quantity if is_quantity else special_link
            
            # Keys (0x100-0x10E)
            if 0x100 <= object_id <= 0x10E:
                if owner > 0:
                    desc_idx = 100 + owner
                    if desc_idx < len(block5) and block5[desc_idx]:
                        return block5[desc_idx]
                if object_id == 0x101:
                    return "A lockpick"
                return ""
            
            # Books (0x130-0x137) - only readable if NOT enchanted (spell scrolls don't have text)
            if 0x130 <= object_id <= 0x137:
                # Spell scrolls (enchanted) cast spells, they don't have readable text
                if is_enchanted:
                    return ""
                if is_quantity and link_value >= 512:
                    text_idx = link_value - 512
                    if text_idx < len(block3) and block3[text_idx]:
                        return block3[text_idx].strip()
                return ""
            
            # Scrolls (0x138-0x13F, except 0x13B map) - only readable if NOT enchanted
            if 0x138 <= object_id <= 0x13F and object_id != 0x13B:
                # Spell scrolls (enchanted) cast spells, they don't have readable text
                if is_enchanted:
                    return ""
                if is_quantity and link_value >= 512:
                    text_idx = link_value - 512
                    if text_idx < len(block3) and block3[text_idx]:
                        return block3[text_idx].strip()
                return ""
            
            # Writing (0x166) and Gravestone (0x165) - use quantity or special_link offset by 512 as index into block 8 (wall/sign text)
            # Writing/gravestones can have is_quantity=True with quantity >= 512, or is_quantity=False with special_link >= 512
            if object_id in (0x165, 0x166):
                if link_value > 0 and link_value >= 512:
                    # Offset by 512 to get actual index into block 8 (wall/sign text, not block 3)
                    text_idx = link_value - 512
                    if text_idx >= 0 and text_idx < len(block8):
                        desc = block8[text_idx]
                        if desc and desc.strip():
                            return desc.strip()
                return ""
            
            # Wands (0x98-0x9B)
            if 0x98 <= object_id <= 0x9B:
                # Check for special wands with unique spells or incorrect mappings first
                from ..constants import get_special_wand_info
                tile_x = getattr(item, 'tile_x', 0)
                tile_y = getattr(item, 'tile_y', 0)
                special_wand = get_special_wand_info(level_num, tile_x, tile_y)
                if special_wand:
                    return f"{special_wand['name']} ({quality} charges)"
                
                if levels and not is_quantity:
                    level = levels.get(level_num)
                    if level and special_link in level.objects:
                        spell_obj = level.objects[special_link]
                        if spell_obj.item_id == 0x120:
                            # Correct mapping logic: if spell object has is_quantity=True, use quantity_or_link - 256
                            # Otherwise use quality + 256 (if quality < 64)
                            if spell_obj.is_quantity and spell_obj.quantity_or_link >= 256:
                                spell_idx = spell_obj.quantity_or_link - 256
                            else:
                                spell_idx = spell_obj.quality + 256 if spell_obj.quality < 64 else spell_obj.quality
                            if spell_idx in spell_names:
                                return f"Wand of {spell_names[spell_idx]}"
                return f"Wand ({quality} charges)"
            
            # Map (0x13B)
            if object_id == 0x13B:
                return "Shows explored areas"
            
            # Potions (0xBB = red mana, 0xBC = green heal)
            if object_id in (0xBB, 0xBC):
                if is_quantity and link_value >= 512:
                    raw_idx = link_value - 512
                    spell_256 = spell_names.get(raw_idx + 256, "")
                    if spell_256:
                        return f"Potion of {spell_256}"
                    spell_raw = spell_names.get(raw_idx, "")
                    if spell_raw:
                        return f"Potion of {spell_raw}"
                    return f"Potion (effect #{raw_idx})"
                if object_id == 0xBB:
                    return "Restores Mana"
                else:
                    return "Heals Wounds"
            
            # Coins
            if object_id == 0xA0:
                if is_quantity:
                    return f"{quantity} gold pieces"
                return "Gold coin"
            
            # Arrows/bolts - show stack count
            if object_id in (0x10, 0x11, 0x12):
                if is_quantity and quantity > 1:
                    return f"Stack of {quantity}"
                return ""
            
            # Switches (0x170-0x17F) and lever 0x161 - follow link chain to describe effect
            if (0x170 <= object_id <= 0x17F) or object_id == 0x161:
                from ..constants.switches import describe_switch_effect
                from ..constants.traps import is_trap, is_trigger
                
                # Get switch coordinates for finding nearby doors
                switch_x = getattr(item, 'tile_x', 0)
                switch_y = getattr(item, 'tile_y', 0)
                
                # Switches link to triggers which link to traps
                # Chain: Switch -> Trigger -> Trap -> Effect
                if special_link > 0 and levels:
                    level = levels.get(level_num)
                    if level and special_link in level.objects:
                        target = level.objects[special_link]
                        
                        # Check if switch links directly to a trigger
                        if is_trigger(target.item_id):
                            # Follow trigger to its trap
                            trap_link = target.quantity_or_link
                            if trap_link > 0 and trap_link in level.objects:
                                trap_obj = level.objects[trap_link]
                                if is_trap(trap_obj.item_id):
                                    # Get target object for create_object_trap
                                    target_obj = None
                                    target_link = trap_obj.quantity_or_link if not trap_obj.is_quantity else 0
                                    if target_link > 0 and target_link in level.objects:
                                        target_obj = level.objects[target_link]
                                    
                                    return describe_switch_effect(
                                        trap_obj.item_id, trap_obj.quality, trap_obj.owner,
                                        trap_obj.tile_x, trap_obj.tile_y, level_num,
                                        block4, target_obj,
                                        switch_x, switch_y, level.objects,
                                        trap_messages=block9,
                                        spell_names=spell_names_list
                                    )
                            return ""
                        
                        # Check if switch links directly to a trap
                        elif is_trap(target.item_id):
                            # Get target object for delete_object_trap or create_object_trap
                            target_obj = None
                            target_link = target.quantity_or_link if not target.is_quantity else 0
                            if target_link > 0 and target_link in level.objects:
                                target_obj = level.objects[target_link]
                            
                            return describe_switch_effect(
                                target.item_id, target.quality, target.owner,
                                target.tile_x, target.tile_y, level_num,
                                block4, target_obj,
                                switch_x, switch_y, level.objects,
                                trap_messages=block9,
                                spell_names=spell_names_list
                            )
                
                return ""
            
            # Traps (0x180-0x19F) - use detailed descriptions
            if 0x180 <= object_id <= 0x19F:
                from ..constants.traps import describe_trap_effect
                # Get level objects for following links
                level_objs = None
                if levels:
                    level = levels.get(level_num)
                    if level:
                        level_objs = level.objects
                
                return describe_trap_effect(
                    object_id, quality, owner, 
                    getattr(item, 'z_pos', 0) if hasattr(item, 'z_pos') else item.to_dict().get('position', {}).get('z', 0),
                    getattr(item, 'tile_x', 0), getattr(item, 'tile_y', 0),
                    level_num,
                    is_quantity=is_quantity,
                    quantity_or_link=special_link if not is_quantity else quantity,
                    level_objects=level_objs,
                    object_names=block4,
                    trap_messages=block9,
                    spell_names=spell_names_list
                )
            
            # Triggers (0x1A0-0x1BF) - show what trap they link to
            if 0x1A0 <= object_id <= 0x1BF:
                from ..constants.traps import get_trigger_name, describe_trap_effect, is_trap
                
                # Check if trigger links to a trap
                # Note: For triggers, special_link is always the trap link
                # (is_quantity flag doesn't apply to triggers the same way)
                if special_link > 0 and levels:
                    level = levels.get(level_num)
                    if level and special_link in level.objects:
                        target = level.objects[special_link]
                        if is_trap(target.item_id):
                            # For door traps at (0,0), use trigger coordinates for proximity search
                            trigger_x = getattr(item, 'tile_x', 0)
                            trigger_y = getattr(item, 'tile_y', 0)
                            use_x = target.tile_x if target.tile_x > 0 else trigger_x
                            use_y = target.tile_y if target.tile_y > 0 else trigger_y
                            effect = describe_trap_effect(
                                target.item_id, target.quality, target.owner,
                                target.z_pos, use_x, use_y,
                                level_num,
                                is_quantity=target.is_quantity,
                                quantity_or_link=target.quantity_or_link,
                                level_objects=level.objects,
                                object_names=block4,
                                trap_messages=block9,
                                spell_names=spell_names_list
                            )
                            # Return just the effect description without trap type prefix
                            return effect
                
                # For move_trigger with no linked trap, show destination
                if object_id == 0x1A0:
                    return f"Move to ({quality}, {owner})"
                return ""
            
            return ""
        
        def get_item_effect(item, object_id: int, is_enchanted: bool, is_quantity: bool,
                           quantity: int, quality: int, special_link: int, level_num: int) -> str:
            """Get enchantment/effect description for an item."""
            link_value = quantity if is_quantity else special_link
            
            def format_spell(spell_name: str) -> str:
                """Format spell name with description if available."""
                if not spell_name:
                    return ""
                desc = SPELL_DESCRIPTIONS.get(spell_name, "")
                if desc:
                    return f"{spell_name} ({desc})"
                return spell_name
            
            # Wands - show charges and spell
            if 0x98 <= object_id <= 0x9B:
                # Check for special wands with unique spells or incorrect mappings first
                from ..constants import get_special_wand_info
                tile_x = getattr(item, 'tile_x', 0)
                tile_y = getattr(item, 'tile_y', 0)
                special_wand = get_special_wand_info(level_num, tile_x, tile_y)
                if special_wand:
                    return f"{special_wand['name']} ({quality} charges)"
                
                if levels and not is_quantity:
                    level = levels.get(level_num)
                    if level and special_link in level.objects:
                        spell_obj = level.objects[special_link]
                        if spell_obj.item_id == 0x120:
                            # Correct mapping logic: if spell object has is_quantity=True, use quantity_or_link - 256
                            # Otherwise use quality + 256 (if quality < 64)
                            if spell_obj.is_quantity and spell_obj.quantity_or_link >= 256:
                                spell_idx = spell_obj.quantity_or_link - 256
                            else:
                                spell_idx = spell_obj.quality + 256 if spell_obj.quality < 64 else spell_obj.quality
                            spell = spell_names.get(spell_idx, "")
                            if spell:
                                return f"{format_spell(spell)} ({quality} charges)"
                return f"Unknown spell ({quality} charges)" if quality > 0 else "Empty"
            
            # Keys
            if 0x100 <= object_id <= 0x10E:
                if hasattr(item, 'owner') and item.owner > 0:
                    return f"Opens lock #{item.owner}"
                return ""
            
            # Books/Scrolls - text index reference or spell name for spell scrolls
            if 0x130 <= object_id <= 0x13F and object_id != 0x13B:
                if is_quantity and link_value >= 512:
                    text_idx = link_value - 512
                    # For enchanted scrolls (spell scrolls), show the spell name
                    if is_enchanted:
                        # Try multiple offsets: +256 (common), +144 (for some spells like Hallucination), then direct
                        spell_256 = spell_names.get(text_idx + 256, "")
                        if spell_256:
                            return f"Spell: {format_spell(spell_256)}"
                        spell_144 = spell_names.get(text_idx + 144, "")
                        if spell_144:
                            return f"Spell: {format_spell(spell_144)}"
                        # Try raw index
                        spell_raw = spell_names.get(text_idx, "")
                        if spell_raw:
                            return f"Spell: {format_spell(spell_raw)}"
                        return f"Spell #{text_idx}"
                    # Regular readable scrolls/books
                    return f"Text #{text_idx}"
                return ""
            
            # Potions - show spell effect
            if object_id in (0xBB, 0xBC):
                if is_quantity and link_value >= 512:
                    raw_idx = link_value - 512
                    spell_256 = spell_names.get(raw_idx + 256, "")
                    if spell_256:
                        return format_spell(spell_256)
                    spell_raw = spell_names.get(raw_idx, "")
                    if spell_raw:
                        return format_spell(spell_raw)
                    return f"Effect #{raw_idx}"
                if object_id == 0xBB:
                    return "Restores Mana"
                else:
                    return "Heals Wounds"
            
            # For sceptres, check for enchantment even if is_enchanted flag is not set
            # Sceptres encode enchantments with an offset: ench_property - offset = spell_index
            # Try -73 first (works for some sceptres like Ally), then fall back to -76
            # Example: 760 - 512 = 248, then 248 - 76 = 172 ("Restore Mana")
            if object_id == 0x0AA:
                # Try special_link first (standard enchantment encoding)
                link = special_link
                if link >= 512:
                    ench_property = link - 512
                    # Try -73 offset first
                    spell_idx = ench_property - 73
                    spell = spell_names.get(spell_idx, "")
                    if spell:
                        return format_spell(spell)
                    # Fall back to -76 offset
                    spell_idx = ench_property - 76
                    spell = spell_names.get(spell_idx, "")
                    if spell:
                        return format_spell(spell)
                    return f"Unknown enchantment ({ench_property})"
                # Try quantity (may be used for sceptres even when is_quantity is False)
                link = quantity
                if link >= 512:
                    ench_property = link - 512
                    # Try -73 offset first
                    spell_idx = ench_property - 73
                    spell = spell_names.get(spell_idx, "")
                    if spell:
                        return format_spell(spell)
                    # Fall back to -76 offset
                    spell_idx = ench_property - 76
                    spell = spell_names.get(spell_idx, "")
                    if spell:
                        return format_spell(spell)
                    return f"Unknown enchantment ({ench_property})"
                return ""
            
            # For treasure items, check for enchantment even if is_enchanted flag is not set
            # Treasure items (0xA0-0xAF) use ench_property * 2 as spell index
            # Exclude sceptres (0xAA) as they have their own special handling
            if 0xA0 <= object_id <= 0xAF and object_id != 0x0AA and not is_enchanted:
                link = quantity if is_quantity else special_link
                if link >= 512:
                    ench_property = link - 512
                    spell_idx = ench_property * 2
                    spell = spell_names.get(spell_idx, "")
                    if spell:
                        return format_spell(spell)
                    return f"Enchantment #{ench_property}"
            
            # For armor items, check for enchantment even if is_enchanted flag is not set
            # Some armor items may have enchantment data in the link field without the flag set
            if 0x20 <= object_id < 0x40 and not is_enchanted:
                link = quantity if is_quantity else special_link
                if link >= 512:
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
                        # Try direct index first (some spells are at direct index)
                        spell = spell_names.get(ench_property, "")
                        if spell:
                            return format_spell(spell)
                        # Fall back to 256+offset (other spells use this mapping)
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
            
            # Check if enchanted (for other item types)
            if not is_enchanted:
                return ""
            
            link = quantity if is_quantity else special_link
            if link >= 512:
                ench_property = link - 512
            else:
                return ""
            
            # Weapons enchantments
            if object_id < 0x20:
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
            
            # Rings enchantments
            elif object_id in (0x36, 0x38, 0x39, 0x3A):
                spell = spell_names.get(ench_property, "")
                if spell:
                    return format_spell(spell)
                return f"Unknown enchantment ({ench_property})"
            
            # Armor enchantments
            elif 0x20 <= object_id < 0x40:
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
                    # Try direct index first (some spells are at direct index)
                    spell = spell_names.get(ench_property, "")
                    if spell:
                        return format_spell(spell)
                    # Fall back to 256+offset (other spells use this mapping)
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
            
            # Treasure items enchantments
            # Treasure items (0xA0-0xAF) use ench_property * 2 as spell index
            # Exclude sceptres (0xAA) as they have their own special handling
            elif 0xA0 <= object_id <= 0xAF and object_id != 0x0AA:
                spell_idx = ench_property * 2
                spell = spell_names.get(spell_idx, "")
                if spell:
                    return format_spell(spell)
                return f"Enchantment #{ench_property}"
            
            return ""
        
        # Category mapping for objects - maps base/detailed categories to web categories
        category_map = {
            # Weapons
            'melee_weapon': 'weapons',
            'ranged_weapon': 'weapons',
            # Armor
            'armor': 'armor',
            # Containers - portable (bags, packs) vs static (barrels, chests, urns)
            'container': 'containers',
            'storage': 'storage',
            # Keys
            'key': 'keys',
            # Consumables
            'food': 'food',
            'potion': 'potions',
            # Books & Scrolls - now split
            'scroll': 'scrolls',
            'book': 'books',
            'readable_scroll': 'scrolls',
            'readable_book': 'books',
            'quest_book': 'quest',  # Quest books like Book of Honesty
            'spell_scroll': 'spell_scrolls',
            'map': 'books',  # Maps shown with books
            # Light sources
            'light_source': 'light',
            # Runes (talismans/virtue keys are quest items)
            'rune': 'runes',
            'talisman': 'quest',
            # Wands
            'wand': 'wands',
            'broken_wand': 'misc',  # Broken wands can't cast spells, not magical
            'spell': 'misc',  # Internal spell objects
            # Treasure
            'treasure': 'treasure',
            # Doors - now split by type
            'door': 'doors_unlocked',  # Base door category (shouldn't happen, but default to unlocked)
            'door_locked': 'doors_locked',
            'door_unlocked': 'doors_unlocked',
            'secret_door': 'secret_doors',
            'portcullis': 'doors_unlocked',  # Unlocked portcullis = unlocked door
            'portcullis_locked': 'doors_locked',
            'open_portcullis': 'doors_unlocked',  # Open portcullis defaults to unlocked
            # Traps & Triggers
            'trap': 'traps',
            'trigger': 'triggers',
            # Special objects
            'special_tmap': 'texture_objects',
            'switch': 'switches',
            'furniture': 'furniture',
            'shrine': 'shrines',
            'boulder': 'boulders',
            'decal': 'scenery',
            'bridge': 'bridges',
            'gravestones': 'gravestones',
            'writings': 'writings',
            'scenery': 'scenery',
            'useless_item': 'useless_item',
            'animation': 'animations',
            # Quest & misc
            'quest_item': 'quest',
            'misc_item': 'misc',
        }
        
        # Build index lookup for items by level and index
        items_by_level_index = {}
        creature_type_by_level_index = {}
        
        for item in placed_items:
            level = item.level
            index = item.index
            if level not in items_by_level_index:
                items_by_level_index[level] = {}
                creature_type_by_level_index[level] = {}
            items_by_level_index[level][index] = item
            
            # Store creature type name for NPCs
            if 0x40 <= item.object_id <= 0x7F:
                creature_type_by_level_index[level][index] = item.name or ""
        
        def get_item_name(obj_id: int) -> str:
            """Get item name from item_types if available."""
            if item_types and obj_id in item_types:
                return item_types[obj_id].name
            return ""
        
        def get_item_stats(obj_id: int) -> dict:
            """Get item stats (damage, weight, protection, durability, nutrition, intoxication) from item_types if available."""
            from ..constants import FOOD_NUTRITION, FOOD_IDS
            from ..constants import DRINK_INTOXICATION, DRINK_NUTRITION, ACTUAL_DRINK_IDS, is_alcoholic
            
            stats = {}
            if item_types and obj_id in item_types:
                item_type = item_types[obj_id]
                
                # Add weapon damage and durability for melee weapons (0x00-0x0F)
                if obj_id <= 0x0F and item_type.properties:
                    props = item_type.properties
                    if 'slash_damage' in props:
                        stats['slash_damage'] = props['slash_damage']
                    if 'bash_damage' in props:
                        stats['bash_damage'] = props['bash_damage']
                    if 'stab_damage' in props:
                        stats['stab_damage'] = props['stab_damage']
                    if 'durability' in props:
                        stats['durability'] = props['durability']
                
                # Add durability for ranged weapons (0x10-0x1F)
                if 0x10 <= obj_id <= 0x1F and item_type.properties:
                    props = item_type.properties
                    if 'durability' in props:
                        stats['durability'] = props['durability']
                
                # Add armor stats for armor items (0x20-0x3F)
                if 0x20 <= obj_id <= 0x3F and item_type.properties:
                    props = item_type.properties
                    if 'protection' in props:
                        stats['protection'] = props['protection']
                    if 'durability' in props:
                        stats['durability'] = props['durability']
                
                # Add container capacity for containers (0x80-0x8F)
                if 0x80 <= obj_id <= 0x8F and item_type.properties:
                    props = item_type.properties
                    if 'capacity' in props:
                        stats['capacity'] = props['capacity']
                    if 'accepts' in props:
                        stats['accepts'] = props['accepts']
                
                # Add nutrition for food items (includes ale, water, port)
                # Note: Wine (0xBF) is a quest item, not in FOOD_IDS
                if obj_id in FOOD_IDS:
                    nutrition = FOOD_NUTRITION.get(obj_id)
                    if nutrition is not None:
                        stats['nutrition'] = nutrition
                
                # Add intoxication for alcoholic beverages (ale 0xBA, port 0xBE)
                # Wine (0xBF) is a quest item with no intoxication
                intoxication = DRINK_INTOXICATION.get(obj_id)
                if intoxication is not None and intoxication > 0:
                    stats['intoxication'] = intoxication
                
                # Add weight for all items that have mass > 0
                if item_type.mass > 0:
                    stats['weight'] = item_type.mass / 10.0  # Convert to stones
            
            return stats
        
        def is_valid_npc_name(name: str) -> bool:
            """Check if an NPC name is valid (not a bug artifact)."""
            if not name:
                return False
            invalid_names = {'an excellent deal...', 'excellent deal'}
            return name.lower() not in invalid_names and not name.lower().startswith('an excellent deal')
        
        def get_faction_name_from_npc_type(npc_type: str) -> str:
            """Convert NPC type name to human-readable faction name.
            
            Args:
                npc_type: NPC type name from NPC_TYPES (e.g., "green_goblin", "outcast")
            
            Returns:
                Human-readable faction name (e.g., "green goblins", "outcasts")
            """
            from ..constants.npcs import NPC_TYPES
            
            # Mapping from NPC type names to faction names
            faction_map = {
                'green_goblin': 'green goblins',
                'goblin': 'gray goblins',
                'outcast': 'outcasts',
                'rat': 'rats',
                'bandit': 'bandits',
                'troll': 'trolls',
                'skeleton': 'skeletons',
                'ghoul': 'ghouls',
                'ghost': 'ghosts',
                'zombie': 'zombies',
                'gazer': 'gazers',
                'mage': 'mages',
                'dark_mage': 'dark mages',
                'headless': 'headless',
                'imp': 'imps',
                'mongbat': 'mongbats',
                'dire_ghost': 'dire ghosts',
                'shadow_beast': 'shadow beasts',
                'reaper': 'reapers',
                'wisp': 'wisps',
                'fire_elemental': 'fire elementals',
                'golem_stone': 'stone golems',
                'golem_metal': 'metal golems',
                'golem_earth': 'earth golems',
                'lurker': 'lurkers',
                'deep_lurker': 'deep lurkers',
                'slime': 'slimes',
                'vampire_bat': 'vampire bats',
                'bat': 'bats',
                'spider': 'spiders',
                'giant_spider': 'giant spiders',
                'dread_spider': 'dread spiders',
                'acid_slug': 'acid slugs',
                'flesh_slug': 'flesh slugs',
                'rotworm': 'rotworms',
                'bloodworm': 'bloodworms',
                'lizardman': 'lizardmen',
                'gray_lizardman': 'gray lizardmen',
                'red_lizardman': 'red lizardmen',
                'feral_troll': 'feral trolls',
                'great_troll': 'great trolls',
                'dark_ghoul': 'dark ghouls',
                'mountainman': 'mountainmen',
                'fighter': 'fighters',
                'knight': 'knights',
                'mage_female': 'female mages',
                'mage_red': 'red mages',
                'tyball': 'Tyball',
                'slasher': 'slashers',
                'dragon': 'dragons',
                'ethereal_void': 'ethereal voids',
                'daemon': 'daemons',
                'undead_warrior': 'undead warriors',
                'garamon': 'Garamon',
                'dire_reaper': 'dire reapers',
                'spectre': 'spectres',
                'liche': 'liches',
                'demon': 'demons',
                'mountain_folk': 'mountain folk',
                'human_male': 'humans',
                'human_female': 'humans',
            }
            
            # Return mapped faction name, or convert snake_case to title case as fallback
            if npc_type in faction_map:
                return faction_map[npc_type]
            
            # Fallback: convert snake_case to title case
            return npc_type.replace('_', ' ').title()
        
        def get_owner_name(owner_value: int, object_id: int, level_num: int = None, npcs: List[Any] = None) -> str:
            """Get the faction/group name for an item owner.
            
            The owner field represents a conversation slot. This function finds all NPCs
            on the same level with that conversation slot and determines the faction
            based on their NPC types.
            
            Args:
                owner_value: The owner field value (0-63), represents conversation slot
                object_id: The item's object ID (to exclude keys which use owner for lock ID)
                level_num: The level number (0-8) where the item is located
                npcs: List of NPCInfo objects to search for matching NPCs
            
            Returns:
                Faction/group name if found, empty string if no owner or if it's a key
            """
            from ..constants.npcs import NPC_TYPES, get_npc_type_name
            
            # Keys use owner field for lock ID, not NPC ownership
            if 0x100 <= object_id <= 0x10E:
                return ""
            
            # No owner
            if owner_value <= 0:
                return ""
            
            # Level-specific owner value mappings (check these first, before NPC lookup)
            # On level 2, owner value 10 (Lanugo's conversation slot) maps to mountainmen
            if level_num == 1 and owner_value == 10:
                return 'mountainmen'
            # On level 3, owner value 11 (Thorlson's conversation slot) maps to lizardmen
            if level_num == 2 and owner_value == 11:
                return 'lizardmen'
            # On level 4, owner value 13 (Morlock's conversation slot) maps to knights
            if level_num == 3 and owner_value == 13:
                return 'knights'
            # On level 4, owner value 15 maps to trolls
            if level_num == 3 and owner_value == 15:
                return 'trolls'
            # On level 4, owner value 31 maps to knights (Level 4 is "The Knights")
            if level_num == 3 and owner_value == 31:
                return 'knights'
            # On level 7, owner value 20 (Gulik's conversation slot) maps to golems
            if level_num == 6 and owner_value == 20:
                return 'golems'
            
            # First, check if we have a known name-to-faction mapping
            # This takes precedence because some NPCs might not be on the level or might be the wrong type
            known_name_to_faction = {
                'marrowsuck': 'green goblins',  # Green goblin leader
                'vernix': 'gray goblins',       # Gray goblin leader  
                'garamon': 'outcasts',          # Outcast leader
                'lanugo': 'mountainmen',       # Mountainman leader on level 2
            }
            
            # Level-specific owner value mappings
            # On level 2, if there are mountainmen on the level, prefer them over reapers
            # This handles cases where reapers share conversation slots with mountainmen
            if level_num == 1 and npcs is not None:
                all_level_npcs = [npc for npc in npcs if npc.level == 1]
                mountainmen_on_level = [npc for npc in all_level_npcs if get_npc_type_name(npc.object_id) == 'mountainman']
                reapers_on_level = [npc for npc in all_level_npcs if get_npc_type_name(npc.object_id) == 'reaper']
                
                # If there are mountainmen on level 2 and this owner value matches reapers' conversation slot
                # (or if reapers exist and we might get reapers as result), prefer mountainmen
                if mountainmen_on_level and reapers_on_level:
                    matching_reapers = [npc for npc in reapers_on_level if npc.conversation_slot == owner_value]
                    # If this owner value matches reapers, return mountainmen instead
                    if matching_reapers:
                        return 'mountainmen'
            
            if owner_value in npc_names:
                npc_name = npc_names[owner_value].lower()
                if is_valid_npc_name(npc_names[owner_value]) and npc_name in known_name_to_faction:
                    return known_name_to_faction[npc_name]
            
            # Special case for npc #36 - check for rats on the level
            # Owner values might map to NPC indices, conversation slots, or other identifiers
            # Try multiple matching strategies
            # Known mapping: owner 36 on level 1 (0-indexed) = rats
            if owner_value == 36:
                # Direct mapping for level 1 (0-indexed)
                if level_num == 0:
                    return 'rats'
                if npcs is not None and level_num is not None:
                    # Strategy 1: Check if there's an NPC with index 36 that is a rat
                    npc_with_index_36 = [npc for npc in npcs if npc.level == level_num and npc.index == 36]
                    if npc_with_index_36:
                        for npc in npc_with_index_36:
                            if get_npc_type_name(npc.object_id) == 'rat':
                                return 'rats'
                    
                    # Strategy 2: Check if there are NPCs with conversation slot 36 that are rats
                    rat_npcs_with_slot = [
                        npc for npc in npcs
                        if npc.level == level_num and npc.conversation_slot == 36 and get_npc_type_name(npc.object_id) == 'rat'
                    ]
                    if rat_npcs_with_slot:
                        return 'rats'
                    
                    # Strategy 3: Check if there are NPCs with owner field 36 that are rats
                    rat_npcs_with_owner = [
                        npc for npc in npcs
                        if npc.level == level_num and npc.owner == 36 and get_npc_type_name(npc.object_id) == 'rat'
                    ]
                    if rat_npcs_with_owner:
                        return 'rats'
                    
                    # Strategy 4: If no specific match, check if there are any rats on the level at all
                    # (owner 36 on level 1 typically means rats)
                    level_npcs = [npc for npc in npcs if npc.level == level_num]
                    rat_npcs = [npc for npc in level_npcs if get_npc_type_name(npc.object_id) == 'rat']
                    if rat_npcs:
                        return 'rats'
                # If we don't have level info but have NPCs, check all rats
                elif npcs is not None and len(npcs) > 0:
                    # Check for NPC with index 36
                    npc_with_index_36 = [npc for npc in npcs if npc.index == 36]
                    if npc_with_index_36:
                        for npc in npc_with_index_36:
                            if get_npc_type_name(npc.object_id) == 'rat':
                                return 'rats'
                    # Otherwise check all rats
                    rat_npcs = [npc for npc in npcs if get_npc_type_name(npc.object_id) == 'rat']
                    if rat_npcs:
                        return 'rats'
            
            # If we have NPCs and level info, try to determine faction from NPC types
            if npcs is not None and level_num is not None and len(npcs) > 0:
                # The owner_value might represent:
                # 1. Conversation slot (npc_whoami)
                # 2. NPC index in the object list
                # 3. NPC owner field
                # Try all three strategies
                
                # Strategy 1: Match by conversation slot
                matching_npcs = [
                    npc for npc in npcs
                    if npc.level == level_num and npc.conversation_slot == owner_value
                ]
                
                # Strategy 2: Match by NPC index (owner value might be object index)
                if not matching_npcs:
                    matching_npcs = [
                        npc for npc in npcs
                        if npc.level == level_num and npc.index == owner_value
                    ]
                
                # Strategy 3: Match by NPC owner field
                if not matching_npcs:
                    matching_npcs = [
                        npc for npc in npcs
                        if npc.level == level_num and npc.owner == owner_value
                    ]
                
                # If still no matches and owner_value is a known conversation slot,
                # try to find NPCs with that conversation slot on ANY level (maybe the NPC
                # is on a different level but items on this level are owned by them)
                if not matching_npcs and owner_value in npc_names:
                    matching_npcs = [
                        npc for npc in npcs
                        if npc.conversation_slot == owner_value
                    ]
                    # If we found NPCs on other levels, use the first one's type
                    # (assuming faction is consistent across levels)
                    if matching_npcs:
                        # Use the first NPC's type (or most common if multiple)
                        type_counts = {}
                        for npc in matching_npcs:
                            npc_type = get_npc_type_name(npc.object_id)
                            type_counts[npc_type] = type_counts.get(npc_type, 0) + 1
                        if type_counts:
                            # Level-specific overrides: prioritize certain factions on specific levels
                            # On level 2, if the conversation slot is Lanugo (10), use mountainmen
                            if level_num == 1 and owner_value == 10:
                                # Lanugo on level 2 should map to mountainmen, not reapers
                                dominant_type = 'mountainman'
                            # On level 2, if mountainmen are present, prefer them over reapers
                            elif level_num == 1 and 'mountainman' in type_counts:
                                if 'reaper' in type_counts:
                                    dominant_type = 'mountainman'
                                else:
                                    dominant_type = max(type_counts.items(), key=lambda x: x[1])[0]
                            else:
                                dominant_type = max(type_counts.items(), key=lambda x: x[1])[0]
                            faction_name = get_faction_name_from_npc_type(dominant_type)
                            return faction_name
                
                if matching_npcs:
                    # Count NPC types
                    type_counts = {}
                    for npc in matching_npcs:
                        npc_type = get_npc_type_name(npc.object_id)
                        type_counts[npc_type] = type_counts.get(npc_type, 0) + 1
                    
                    # Find the most common NPC type
                    if type_counts:
                        dominant_type = max(type_counts.items(), key=lambda x: x[1])[0]
                    else:
                        dominant_type = None
                    
                    if dominant_type:
                        faction_name = get_faction_name_from_npc_type(dominant_type)
                        
                        # Level 2 specific override: if result would be "reapers" but mountainmen exist, use mountainmen
                        # This is a known game data issue where reapers share conversation slots with mountainmen on level 2
                        if level_num == 1 and dominant_type == 'reaper' and npcs is not None:
                            # Check if mountainmen are in the matching NPCs
                            if 'mountainman' in type_counts:
                                dominant_type = 'mountainman'
                                faction_name = get_faction_name_from_npc_type(dominant_type)
                            else:
                                # Check all NPCs on level 2 - if there are mountainmen, use them
                                all_level_npcs = [npc for npc in npcs if npc.level == 1]
                                mountainmen_on_level = [npc for npc in all_level_npcs if get_npc_type_name(npc.object_id) == 'mountainman']
                                if mountainmen_on_level:
                                    dominant_type = 'mountainman'
                                    faction_name = get_faction_name_from_npc_type(dominant_type)
                        
                        # Check if there's a named NPC (leader) with this conversation slot
                        has_named_npc = (
                            owner_value in npc_names and 
                            npc_names[owner_value] and
                            is_valid_npc_name(npc_names[owner_value])
                        )
                        
                        # Final safety check: on level 2, if result is "reapers" but mountainmen exist, use mountainmen
                        if level_num == 1 and faction_name == 'reapers' and npcs is not None:
                            all_level_npcs = [npc for npc in npcs if npc.level == 1]
                            mountainmen_on_level = [npc for npc in all_level_npcs if get_npc_type_name(npc.object_id) == 'mountainman']
                            if mountainmen_on_level:
                                faction_name = 'mountainmen'
                        
                        # If there's a named NPC and multiple NPCs, show as "faction (leader)"
                        if has_named_npc and len(matching_npcs) > 1:
                            return f"{faction_name} (leader)"
                        elif has_named_npc:
                            # Single named NPC - return faction name
                            return faction_name
                        else:
                            return faction_name
            
            # If we have NPC data but couldn't find a match, or if we found NPCs but they might be wrong type,
            # try to infer from NPC name using known mappings
            if npcs is not None and len(npcs) > 0 and owner_value in npc_names:
                npc_name = npc_names[owner_value].lower()
                if is_valid_npc_name(npc_names[owner_value]):
                    # Known mappings from game knowledge - these NPCs belong to specific factions
                    name_to_faction = {
                        'marrowsuck': 'green goblins',  # Green goblin leader
                        'vernix': 'gray goblins',       # Gray goblin leader
                        'garamon': 'outcasts',          # Outcast leader
                    }
                    
                    # Check if we have a direct mapping
                    if npc_name in name_to_faction:
                        return name_to_faction[npc_name]
            
            # Fallback: Only use NPC name lookup if we don't have NPC data available
            # (This preserves backward compatibility but shouldn't be used when NPCs are available)
            if npcs is None or len(npcs) == 0:
                if owner_value in npc_names:
                    npc_name = npc_names[owner_value]
                    if is_valid_npc_name(npc_name):
                        return npc_name
                return f"NPC #{owner_value}"
            
            # Final fallback for unknown owner
            return f"NPC #{owner_value}"
        
        def get_container_contents(level_num: int, container_link: int, 
                                   visited: set = None) -> List[Dict]:
            """Follow the object chain to get container contents."""
            from ..constants import STATIC_CONTAINERS, CARRYABLE_CONTAINERS
            if visited is None:
                visited = set()
            
            contents = []
            current_idx = container_link
            
            while current_idx > 0 and current_idx not in visited:
                visited.add(current_idx)
                
                if level_num in items_by_level_index:
                    item = items_by_level_index[level_num].get(current_idx)
                    if item:
                        # Skip lock objects (0x10F) - they're not container contents
                        if item.object_id == 0x10F:
                            # Lock object - follow its next_index to get actual contents
                            current_idx = item.next_index
                            continue
                        
                        item_dict = item.to_dict()
                        detailed_cat = item_dict.get('detailed_category', '')
                        obj_class = item_dict.get('object_class', 'unknown')
                        
                        # Check if this is a quest book (e.g., Book of Honesty) in container
                        cont_category = category_map.get(detailed_cat, category_map.get(obj_class, 'misc'))
                        if 0x130 <= item.object_id <= 0x137 and item.is_quantity and item.quantity >= 512:
                            from ..constants import is_quest_book
                            text_idx = item.quantity - 512
                            if is_quest_book(text_idx):
                                cont_category = 'quest'
                        
                        # Get rich description and effect for this item
                        item_desc = get_item_description(
                            item, item.object_id, item.is_enchanted, item.is_quantity,
                            item.quantity, item.quality, 
                            getattr(item, 'owner', 0),
                            item.special_link, level_num
                        )
                        item_effect = get_item_effect(
                            item, item.object_id, item.is_enchanted, item.is_quantity,
                            item.quantity, item.quality, item.special_link, level_num
                        )
                        
                        # Determine actual quantity (not enchantment data)
                        # If is_quantity and quantity >= 512, it's actually enchantment data
                        actual_quantity = 1
                        if item.is_quantity:
                            if item.quantity < 512:
                                actual_quantity = item.quantity
                            # else: quantity >= 512 is enchantment data, show as 1
                        
                        content_item = {
                            'object_id': item.object_id,
                            'name': item.name or get_item_name(item.object_id),
                            'category': cont_category,
                            'quantity': actual_quantity,
                        }
                        # Add image path if available
                        if image_paths and item.object_id in image_paths:
                            content_item['image_path'] = image_paths[item.object_id]
                        # Only include description and effect if they have meaningful values
                        if item_desc:
                            content_item['description'] = item_desc
                        if item_effect:
                            content_item['effect'] = item_effect
                        
                        # Add owner information for items inside containers
                        item_owner = getattr(item, 'owner', 0)
                        if item_owner > 0 and not (0x100 <= item.object_id <= 0x10E):
                            content_item['owner'] = item_owner
                            cont_owner_name = get_owner_name(item_owner, item.object_id, level_num, npcs)
                            if cont_owner_name:
                                content_item['owner_name'] = cont_owner_name
                        
                        # Add item stats (weapon damage, armor stats, weight, nutrition, intoxication) for contained items
                        cont_item_stats = get_item_stats(item.object_id)
                        if cont_item_stats:
                            if 'slash_damage' in cont_item_stats:
                                content_item['slash_damage'] = cont_item_stats['slash_damage']
                            if 'bash_damage' in cont_item_stats:
                                content_item['bash_damage'] = cont_item_stats['bash_damage']
                            if 'stab_damage' in cont_item_stats:
                                content_item['stab_damage'] = cont_item_stats['stab_damage']
                            if 'protection' in cont_item_stats:
                                content_item['protection'] = cont_item_stats['protection']
                            if 'durability' in cont_item_stats:
                                # max_durability: from OBJECTS.DAT - the item type's maximum durability
                                content_item['max_durability'] = cont_item_stats['durability']
                                # quality: from placed object data (bits 0-5 of word 2, range 0-63)
                                if item.object_id <= 0x3F:  # Weapons and Armor
                                    content_item['quality'] = item.quality
                            if 'weight' in cont_item_stats:
                                content_item['weight'] = cont_item_stats['weight']
                            if 'nutrition' in cont_item_stats:
                                content_item['nutrition'] = cont_item_stats['nutrition']
                            if 'intoxication' in cont_item_stats:
                                content_item['intoxication'] = cont_item_stats['intoxication']
                        
                        # If this item is also a container, get its contents recursively
                        # Check for both portable containers and static ones (barrel, chest, urn, etc.)
                        is_nested_container = (item.object_id in CARRYABLE_CONTAINERS) or (item.object_id in STATIC_CONTAINERS)
                        if is_nested_container and item.special_link > 0:
                            nested_contents = get_container_contents(
                                level_num, item.special_link, visited.copy()
                            )
                            if nested_contents:
                                content_item['contents'] = nested_contents
                        
                        contents.append(content_item)
                        current_idx = item.next_index
                    else:
                        break
                else:
                    break
            
            return contents
        
        # Process placed objects - filter out templates at (0,0) and NPCs
        objects_by_level = {i: [] for i in range(9)}
        
        for item in placed_items:
            item_dict = item.to_dict()
            pos = item_dict.get('position', {})
            tile_x = pos.get('tile_x', 0)
            tile_y = pos.get('tile_y', 0)
            
            # Skip objects at origin (templates)
            if tile_x == 0 and tile_y == 0:
                continue
            
            # Get object class to determine if we should show invisible objects
            obj_class = item_dict.get('object_class', 'unknown')
            
            # Skip invisible objects EXCEPT for traps and triggers
            # (traps/triggers are typically invisible game mechanics we want to show on the map)
            if item_dict.get('is_invisible', False):
                if obj_class not in ('trap', 'trigger'):
                    continue
            
            # Skip NPCs - they are exported separately
            obj_id = item_dict.get('object_id', 0)
            if 0x40 <= obj_id <= 0x7F:
                continue
            
            # Skip secret doors - they are exported in the secrets array
            if obj_id == 0x147:
                continue
                
            level = item_dict.get('level', 0)
            # Use detailed_category if available, otherwise fall back to object_class
            detailed_cat = item_dict.get('detailed_category', '')
            obj_class = item_dict.get('object_class', 'unknown')
            # First try detailed category, then base category
            category = category_map.get(detailed_cat, category_map.get(obj_class, 'misc'))
            
            # Check if this is a quest book (e.g., Book of Honesty)
            obj_id = item.object_id
            if 0x130 <= obj_id <= 0x137 and item.is_quantity and item.quantity >= 512:
                from ..constants import is_quest_book
                text_idx = item.quantity - 512
                if is_quest_book(text_idx):
                    category = 'quest'
                    detailed_cat = 'quest_book'
            
            # Get rich description and effect for this item
            is_quantity = item.is_quantity
            quantity = item.quantity
            quality = item.quality
            owner = item.owner
            special_link = item.special_link
            is_enchanted = item.is_enchanted
            
            # Check if this is a move trigger that links to a level-changing teleport trap (stairs)
            stairs_dest_level = None  # Will be set if this is a stairs trigger
            if obj_id == 0x1A0:  # move_trigger
                from ..constants.traps import is_trap, is_level_transition_teleport
                TELEPORT_TRAP_ID = 0x181  # teleport_trap
                if special_link > 0 and levels:
                    level_obj = levels.get(level)
                    if level_obj and special_link in level_obj.objects:
                        target = level_obj.objects[special_link]
                        if is_trap(target.item_id) and target.item_id == TELEPORT_TRAP_ID:
                            # Check if this teleport trap is a level transition
                            # Use trigger coordinates for level transition detection
                            # (teleport traps at 0,0 are templates, use trigger position instead)
                            trap_x = target.tile_x if target.tile_x > 0 else tile_x
                            trap_y = target.tile_y if target.tile_y > 0 else tile_y
                            if is_level_transition_teleport(
                                target.quality, target.owner,
                                trap_x, trap_y,
                                target.z_pos, level
                            ):
                                category = 'stairs'
                                # Store destination level for stairs direction (1-indexed)
                                # z_pos appears to encode destination level (1-indexed: 1-9)
                                stairs_dest_level = target.z_pos if target.z_pos > 0 and target.z_pos <= 9 else level + 2
            
            item_desc = get_item_description(
                item, obj_id, is_enchanted, is_quantity, quantity, quality, owner, special_link, level
            )
            item_effect = get_item_effect(
                item, obj_id, is_enchanted, is_quantity, quantity, quality, special_link, level
            )
            
            # Create simplified object for web
            # Use name from placed item, but prefer item_types name for quest/enchanted items
            # (item_types should have the identified names)
            item_name = item_dict.get('name', '')
            
            # For quest items, talismans, and enchanted items, prefer item_types name
            # which should have the identified name from _get_identified_name()
            is_quest_or_talisman = (
                (0x110 <= obj_id <= 0x11F or obj_id == 0x1CA) or
                (0xE1 <= obj_id <= 0xE7 or obj_id == 0xBF)
            )
            if (is_quest_or_talisman or is_enchanted) and item_types and obj_id in item_types:
                item_name = item_types[obj_id].name
            elif not item_name and item_types and obj_id in item_types:
                item_name = item_types[obj_id].name
            
            web_obj = {
                'id': item_dict.get('index', 0),
                'object_id': obj_id,
                'name': item_name,
                'tile_x': tile_x,
                'tile_y': tile_y,
                'z': pos.get('z', 0),
                'category': category,
                'object_class': obj_class,
                'detailed_category': detailed_cat,
            }
            # Add image path if available
            if image_paths and obj_id in image_paths:
                web_obj['image_path'] = image_paths[obj_id]
            # Only include description and effect if they have meaningful values
            if item_desc:
                web_obj['description'] = item_desc
            if item_effect:
                web_obj['effect'] = item_effect
            
            # Add stairs destination level if this is a stairs trigger
            if category == 'stairs' and stairs_dest_level is not None:
                web_obj['stairs_dest_level'] = stairs_dest_level  # 1-indexed
            
            # Add quantity for stackable items
            # is_quantity flag means the quantity_or_link field holds a count
            # quantity >= 512 means it's enchantment data, not a real quantity
            
            # Items that always have quantity (gems, coins):
            quantity_capable_items = [
                0x0A2,  # Ruby
                0x0A3,  # Red gem
                0x0A4,  # Small blue gem (tiny blue gem)
                0x0A6,  # Sapphire
                0x0A7,  # Emerald
            ]
            can_have_quantity = obj_id in quantity_capable_items
            
            if is_quantity and quantity > 0 and quantity < 512:
                web_obj['quantity'] = quantity
            # Coins (0xA0) and gold coins (0xA1) always have quantity - default to 1
            elif obj_id in (0xA0, 0xA1):
                web_obj['quantity'] = 1
            # For quantity-capable items, always include quantity
            # These items can have quantity even when is_quantity is False or quantity is 0/1
            elif can_have_quantity:
                # If quantity is 0, it means quantity is 1 (default single item)
                # If quantity is already set (from item_extractor fix), use it
                web_obj['quantity'] = quantity if quantity > 0 else 1
            
            # Add owner information (for items that belong to NPCs)
            # Keys use owner for lock ID, which is already shown in effect/description
            # Texture map objects, traps, and triggers should not have ownership attributes
            from ..constants import is_special_tmap
            from ..constants.traps import is_trap, is_trigger
            if owner > 0 and not (0x100 <= obj_id <= 0x10E) and not is_special_tmap(obj_id) and not is_trap(obj_id) and not is_trigger(obj_id):
                web_obj['owner'] = owner
                owner_name = get_owner_name(owner, obj_id, level, npcs)
                if owner_name:
                    web_obj['owner_name'] = owner_name
            
            # For traps and triggers, store quality and owner for debugging and message lookup
            # These are needed for text_string_trap and tell_trap message index calculation
            if is_trap(obj_id) or is_trigger(obj_id):
                web_obj['quality'] = quality
                web_obj['owner'] = owner
            
            # Include extra_info for special object types (potions, doors, etc.)
            extra_info = item_dict.get('extra_info', {})
            if extra_info:
                web_obj['extra_info'] = extra_info
            
            # Add item stats (weapon damage, armor stats, weight, nutrition, intoxication)
            item_stats = get_item_stats(obj_id)
            if item_stats:
                if 'slash_damage' in item_stats:
                    web_obj['slash_damage'] = item_stats['slash_damage']
                if 'bash_damage' in item_stats:
                    web_obj['bash_damage'] = item_stats['bash_damage']
                if 'stab_damage' in item_stats:
                    web_obj['stab_damage'] = item_stats['stab_damage']
                if 'protection' in item_stats:
                    web_obj['protection'] = item_stats['protection']
                if 'durability' in item_stats:
                    # max_durability: from OBJECTS.DAT - the item type's maximum durability
                    web_obj['max_durability'] = item_stats['durability']
                    # quality: from placed object data (bits 0-5 of word 2, range 0-63)
                    # This represents the item's current condition as a percentage (0=destroyed, 63=pristine)
                    if obj_id <= 0x3F:  # Weapons (0x00-0x1F) and Armor (0x20-0x3F)
                        web_obj['quality'] = quality
                # Don't add weight or capacity for storage items (barrels, chests, urns, cauldrons, tables)
                # Storage items should not display these stats in the UI
                from ..constants import STATIC_CONTAINERS
                is_storage = obj_id in STATIC_CONTAINERS
                # Don't add weight for scenery items (0xC0-0xDF), campfire (0x12A), or fountain (0x12E)
                # But allow weight for items categorized as useless_item (like pile of debris)
                is_scenery = ((0xC0 <= obj_id <= 0xDF) or obj_id in (0x12A, 0x12E)) and detailed_cat != 'useless_item'
                if 'weight' in item_stats and not is_storage and not is_scenery:
                    web_obj['weight'] = item_stats['weight']
                if 'capacity' in item_stats and not is_storage:
                    web_obj['capacity'] = item_stats['capacity']
                if 'accepts' in item_stats:
                    web_obj['accepts'] = item_stats['accepts']
                if 'nutrition' in item_stats:
                    web_obj['nutrition'] = item_stats['nutrition']
                if 'intoxication' in item_stats:
                    web_obj['intoxication'] = item_stats['intoxication']
            
            # For containers (both portable and static like barrels/chests), add their contents
            special_link = item_dict.get('special_link', 0)
            obj_id = item.object_id
            # Check if this is any type of container
            from ..constants import STATIC_CONTAINERS, CARRYABLE_CONTAINERS
            is_container_item = (obj_id in CARRYABLE_CONTAINERS) or (obj_id in STATIC_CONTAINERS)
            if is_container_item and special_link > 0:
                # Check if special_link points to a lock object (0x10F) - if so, follow lock's next_index
                if level in items_by_level_index:
                    link_obj = items_by_level_index[level].get(special_link)
                    if link_obj and link_obj.object_id == 0x10F:
                        # special_link points to lock, contents are in lock's next_index chain
                        if link_obj.next_index > 0:
                            contents = get_container_contents(level, link_obj.next_index)
                        else:
                            contents = []
                    else:
                        # special_link points directly to contents
                        contents = get_container_contents(level, special_link)
                else:
                    contents = get_container_contents(level, special_link)
                
                if contents:
                    web_obj['contents'] = contents
            
            objects_by_level[level].append(web_obj)
        
        # Process NPCs - merge with creature type data
        npcs_by_level = {i: [] for i in range(9)}
        
        for npc in npcs:
            npc_dict = npc.to_dict()
            pos = npc_dict.get('position', {})
            tile_x = pos.get('tile_x', 0)
            tile_y = pos.get('tile_y', 0)
            
            # Skip NPCs at origin (templates)
            if tile_x == 0 and tile_y == 0:
                continue
                
            level = npc_dict.get('level', 0)
            npc_index = npc_dict.get('index', 0)
            
            # Get creature type name from the placed items data
            creature_type = ""
            if level in creature_type_by_level_index:
                creature_type = creature_type_by_level_index[level].get(npc_index, "")
            
            if not creature_type:
                obj_id = npc_dict.get('object_id', 0)
                creature_type = get_item_name(obj_id)
            
            conv_slot = npc_dict.get('conversation', {}).get('slot', 0)
            npc_name = npc_dict.get('name', '')
            
            if not is_valid_npc_name(npc_name) and conv_slot > 0 and conv_slot in npc_names:
                npc_name = npc_names.get(conv_slot, '')
            
            if is_valid_npc_name(npc_name):
                display_name = npc_name
            else:
                display_name = creature_type
            
            obj_id = npc_dict.get('object_id', 0)
            web_npc = {
                'id': npc_index,
                'object_id': obj_id,
                'name': display_name,
                'creature_type': creature_type,
                'tile_x': tile_x,
                'tile_y': tile_y,
                'z': pos.get('z', 0),
                'hp': npc_dict.get('stats', {}).get('hp', 0),
                'level': npc_dict.get('stats', {}).get('level', 0),
                'attitude': npc_dict.get('behavior', {}).get('attitude_name', 'unknown'),
                'attitude_raw': npc_dict.get('behavior', {}).get('attitude', 0),  # Store raw value (0-3)
                'has_conversation': conv_slot > 0 and (conversations is not None and conv_slot in conversations),
                'conversation_slot': conv_slot,
            }
            
            # Add NPC image path if available
            if npc_image_paths and obj_id in npc_image_paths:
                web_npc['image_path'] = npc_image_paths[obj_id]
            
            # Add NPC inventory if they have items (using special_link)
            special_link = npc.special_link
            if special_link > 0:
                inventory = get_container_contents(level, special_link)
                if inventory:
                    web_npc['inventory'] = inventory
            
            npcs_by_level[level].append(web_npc)
        
        # Build object types lookup table (all 512 object types with names)
        # Use category_map to convert Python categories to web categories
        object_types = {}
        if item_types:
            for obj_id, item_info in item_types.items():
                # Map Python category to web category using the same category_map
                web_category = category_map.get(item_info.category, 'misc')
                object_types[obj_id] = {
                    'name': item_info.name,
                    'category': web_category
                }
        
        # Build final data structure
        web_data = {
            'metadata': {
                'type': 'web_map_data',
                'game': 'Ultima Underworld I',
                'generated': datetime.now().isoformat(),
                'grid_size': 64,
                'num_levels': 9,
            },
            'object_types': object_types,
            'categories': [
                # Weapons & Armor
                {'id': 'weapons', 'name': 'Weapons', 'color': '#e03131'},
                {'id': 'armor', 'name': 'Armor', 'color': '#5c7cfa'},
                # Keys & Containers
                {'id': 'keys', 'name': 'Keys', 'color': '#fab005'},
                {'id': 'containers', 'name': 'Containers', 'color': '#f08c00'},
                {'id': 'storage', 'name': 'Storage', 'color': '#d9480f'},
                # Food & Potions
                {'id': 'food', 'name': 'Food', 'color': '#a9e34b'},
                {'id': 'potions', 'name': 'Potions', 'color': '#f783ac'},
                # Books & Scrolls
                {'id': 'books', 'name': 'Readable Books', 'color': '#e8d4b8'},
                {'id': 'scrolls', 'name': 'Readable Scrolls', 'color': '#d4c4a8'},
                {'id': 'spell_scrolls', 'name': 'Spell Scrolls', 'color': '#da77f2'},
                {'id': 'writings', 'name': 'Writings', 'color': '#d4c4a8'},
                {'id': 'gravestones', 'name': 'Gravestones', 'color': '#c4a484'},
                # Magic Items - split by type
                {'id': 'runes', 'name': 'Runestones', 'color': '#9775fa'},
                {'id': 'wands', 'name': 'Wands', 'color': '#7950f2'},
                # Treasure & Light
                {'id': 'treasure', 'name': 'Treasure', 'color': '#fcc419'},
                {'id': 'light', 'name': 'Light Sources', 'color': '#ffe066'},
                # Doors
                {'id': 'doors_locked', 'name': 'Locked Doors', 'color': '#ff6b6b'},
                {'id': 'doors_unlocked', 'name': 'Unlocked Doors', 'color': '#69db7c'},
                {'id': 'secret_doors', 'name': 'Secret Doors', 'color': '#ffd43b'},
                # Mechanics
                {'id': 'switches', 'name': 'Switches & Levers', 'color': '#ffa94d'},
                {'id': 'traps', 'name': 'Traps', 'color': '#ff8787'},
                {'id': 'triggers', 'name': 'Triggers', 'color': '#748ffc'},
                {'id': 'stairs', 'name': 'Stairs', 'color': '#6c757d'},
                {'id': 'illusory_walls', 'name': 'Illusory Walls', 'color': '#ff00ff'},
                # Special Objects
                {'id': 'texture_objects', 'name': 'Texture Map Objects', 'color': '#845ef7'},
                {'id': 'furniture', 'name': 'Furniture', 'color': '#b197a8'},
                {'id': 'shrines', 'name': 'Shrines', 'color': '#d4a574'},
                {'id': 'boulders', 'name': 'Boulders', 'color': '#8b7355'},
                {'id': 'bridges', 'name': 'Bridges', 'color': '#8B5A2B'},
                {'id': 'scenery', 'name': 'Scenery', 'color': '#a9a9a9'},
                {'id': 'useless_item', 'name': 'Useless Items', 'color': '#868e96'},
                {'id': 'animations', 'name': 'Animations', 'color': '#20c997'},
                {'id': 'quest', 'name': 'Quest Items', 'color': '#22b8cf'},
                {'id': 'misc', 'name': 'Miscellaneous', 'color': '#868e96'},
            ],
            'levels': []
        }
        
        level_names = [
            "Level 1 - The Abyss Entrance",
            "Level 2 - The Mountainfolk",
            "Level 3 - The Lizardmen",
            "Level 4 - The Knights",
            "Level 5 - The Ghouls",
            "Level 6 - The Seers",
            "Level 7 - The Pits",
            "Level 8 - The Tyball's Domain",
            "Level 9 - The Chamber of Virtue",
        ]
        
        # Process secrets into per-level lists
        # First pass: collect all illusory walls (these take priority)
        secrets_by_level = {i: [] for i in range(9)}
        illusory_wall_coords = {i: set() for i in range(9)}  # Track coords with illusory walls
        
        if secrets:
            # First pass: add illusory walls
            for secret in secrets:
                secret_dict = secret.to_dict()
                level = secret_dict.get('level', 0)
                pos = secret_dict.get('position', {})
                secret_type = secret_dict.get('type', '')
                
                # Only process illusory walls in first pass
                if secret_type != 'illusory_wall':
                    continue
                
                # Skip secrets at origin (templates)
                tile_x = pos.get('x', 0)
                tile_y = pos.get('y', 0)
                if tile_x == 0 and tile_y == 0:
                    continue
                
                coord = (tile_x, tile_y)
                if coord in illusory_wall_coords[level]:
                    continue  # Skip duplicate
                
                illusory_wall_coords[level].add(coord)
                
                web_secret = {
                    'id': f"secret_{level}_{tile_x}_{tile_y}",
                    'type': secret_type,
                    'tile_x': tile_x,
                    'tile_y': tile_y,
                    'description': secret_dict.get('description', ''),
                    'category': 'illusory_walls',  # Illusory walls get their own category
                }
                
                details = secret_dict.get('details', {})
                if details:
                    web_secret['details'] = details
                
                secrets_by_level[level].append(web_secret)
            
            # Second pass: add secret doors only where there's no illusory wall
            for secret in secrets:
                secret_dict = secret.to_dict()
                level = secret_dict.get('level', 0)
                pos = secret_dict.get('position', {})
                secret_type = secret_dict.get('type', '')
                
                # Only process secret doors in second pass
                if secret_type != 'secret_door':
                    continue
                
                tile_x = pos.get('x', 0)
                tile_y = pos.get('y', 0)
                if tile_x == 0 and tile_y == 0:
                    continue
                
                coord = (tile_x, tile_y)
                # Skip if there's already an illusory wall at this location
                if coord in illusory_wall_coords[level]:
                    continue
                
                # Also skip if we already have a secret door at this coord
                existing_coords = {(s['tile_x'], s['tile_y']) for s in secrets_by_level[level]}
                if coord in existing_coords:
                    continue
                
                web_secret = {
                    'id': f"secret_{level}_{tile_x}_{tile_y}",
                    'type': secret_type,
                    'tile_x': tile_x,
                    'tile_y': tile_y,
                    'description': secret_dict.get('description', ''),
                    'category': 'secret_doors',  # Secret doors go with other secret doors
                }
                
                details = secret_dict.get('details', {})
                if details:
                    web_secret['details'] = details
                
                secrets_by_level[level].append(web_secret)
        
        for level_num in range(9):
            level_entry = {
                'level': level_num,
                'name': level_names[level_num] if level_num < len(level_names) else f"Level {level_num + 1}",
                'objects': objects_by_level[level_num],
                'npcs': npcs_by_level[level_num],
                'secrets': secrets_by_level[level_num],
                'object_count': len(objects_by_level[level_num]),
                'npc_count': len(npcs_by_level[level_num]),
                'secret_count': len(secrets_by_level[level_num]),
            }
            web_data['levels'].append(level_entry)
        
        output_file = self._write_json('web_map_data.json', web_data)
        
        # Also copy to web/data/ folder for the web viewer
        import shutil
        web_data_dir = self.output_path.parent / 'web' / 'data'
        if web_data_dir.exists():
            shutil.copy(output_file, web_data_dir / 'web_map_data.json')
        
        return output_file
