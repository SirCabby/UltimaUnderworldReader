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
    
    def export_items(self, item_types: Dict, placed_items: List) -> None:
        """Export item data."""
        # Export item types
        types_data = {
            'metadata': {
                'type': 'item_types',
                'game': 'Ultima Underworld I',
                'generated': datetime.now().isoformat(),
                'count': len(item_types)
            },
            'items': [item.to_dict() for item in item_types.values()]
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
                            item_types: Dict = None, levels: Dict = None) -> Path:
        """Export optimized data for the interactive web map viewer.
        
        Creates a single JSON file with all placed objects and NPCs,
        filtered to exclude template objects (those at tile 0,0).
        
        Args:
            placed_items: List of placed GameObjectInfo objects
            npcs: List of NPCInfo objects
            npc_names: Dict mapping conversation slots to NPC names
            item_types: Dict of ItemInfo objects for looking up item names
            levels: Dict of Level objects for following container chains
        """
        # Category mapping for objects
        category_map = {
            'melee_weapon': 'weapons',
            'ranged_weapon': 'weapons',
            'armor': 'armor',
            'container': 'containers',
            'key': 'keys',
            'food': 'consumables',
            'potion': 'consumables',
            'scroll': 'readable',
            'book': 'readable',
            'light_source': 'light',
            'rune': 'magic',
            'wand': 'magic',
            'treasure': 'treasure',
            'door': 'doors',
            'trap': 'traps',
            'trigger': 'triggers',
        }
        
        # Build index lookup for items by level and index
        items_by_level_index = {}
        # Also build an index of creature type names for NPCs (object_id 0x40-0x7F)
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
        
        def is_valid_npc_name(name: str) -> bool:
            """Check if an NPC name is valid (not a bug artifact)."""
            if not name:
                return False
            # Filter out known buggy names that come from wrong string lookups
            invalid_names = {'an excellent deal...', 'excellent deal'}
            return name.lower() not in invalid_names and not name.lower().startswith('an excellent deal')
        
        def get_container_contents(level_num: int, container_link: int, 
                                   visited: set = None) -> List[Dict]:
            """Follow the object chain to get container contents."""
            if visited is None:
                visited = set()
            
            contents = []
            current_idx = container_link
            
            while current_idx > 0 and current_idx not in visited:
                visited.add(current_idx)
                
                # Try to find this object in our items
                if level_num in items_by_level_index:
                    item = items_by_level_index[level_num].get(current_idx)
                    if item:
                        item_dict = item.to_dict()
                        obj_class = item_dict.get('object_class', 'unknown')
                        
                        content_item = {
                            'object_id': item.object_id,
                            'name': item.name or get_item_name(item.object_id),
                            'category': category_map.get(obj_class, 'misc'),
                            'quality': item.quality,
                            'quantity': item.quantity if item.is_quantity else 1,
                            'is_enchanted': item.is_enchanted,
                        }
                        
                        # If this item is also a container, get its contents recursively
                        if 0x80 <= item.object_id <= 0x8F and item.special_link > 0:
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
            
            # Skip objects at origin (templates) and invisible objects
            if tile_x == 0 and tile_y == 0:
                continue
            if item_dict.get('is_invisible', False):
                continue
            
            # Skip NPCs - they are exported separately in the npcs array with merged data
            obj_id = item_dict.get('object_id', 0)
            if 0x40 <= obj_id <= 0x7F:
                continue
                
            level = item_dict.get('level', 0)
            obj_class = item_dict.get('object_class', 'unknown')
            category = category_map.get(obj_class, 'misc')
            
            # Create simplified object for web
            web_obj = {
                'id': item_dict.get('index', 0),
                'object_id': item_dict.get('object_id', 0),
                'name': item_dict.get('name', ''),
                'tile_x': tile_x,
                'tile_y': tile_y,
                'z': pos.get('z', 0),
                'category': category,
                'object_class': obj_class,
                'quality': item_dict.get('quality', 0),
                'is_enchanted': item_dict.get('is_enchanted', False),
                'description': item_dict.get('description', ''),
            }
            
            # For containers, add their contents
            special_link = item_dict.get('special_link', 0)
            if category == 'containers' and special_link > 0:
                contents = get_container_contents(level, special_link)
                if contents:
                    web_obj['contents'] = contents
            
            objects_by_level[level].append(web_obj)
        
        # Process NPCs - merge with creature type data, filter out templates at (0,0)
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
            
            # If no creature type found, try to get from item_types
            if not creature_type:
                obj_id = npc_dict.get('object_id', 0)
                creature_type = get_item_name(obj_id)
            
            # Get NPC proper name - only use if valid (not a bug artifact)
            conv_slot = npc_dict.get('conversation', {}).get('slot', 0)
            npc_name = npc_dict.get('name', '')
            
            # Also check npc_names dict
            if not is_valid_npc_name(npc_name) and conv_slot > 0 and conv_slot in npc_names:
                npc_name = npc_names.get(conv_slot, '')
            
            # Determine display name: use NPC name if valid, otherwise creature type
            if is_valid_npc_name(npc_name):
                display_name = npc_name
            else:
                display_name = creature_type
            
            # Create simplified NPC for web with merged data
            web_npc = {
                'id': npc_index,
                'object_id': npc_dict.get('object_id', 0),
                'name': display_name,
                'creature_type': creature_type,
                'tile_x': tile_x,
                'tile_y': tile_y,
                'z': pos.get('z', 0),
                'hp': npc_dict.get('stats', {}).get('hp', 0),
                'level': npc_dict.get('stats', {}).get('level', 0),
                'attitude': npc_dict.get('behavior', {}).get('attitude_name', 'unknown'),
                'has_conversation': conv_slot > 0,
                'conversation_slot': conv_slot,
            }
            
            npcs_by_level[level].append(web_npc)
        
        # Build final data structure
        web_data = {
            'metadata': {
                'type': 'web_map_data',
                'game': 'Ultima Underworld I',
                'generated': datetime.now().isoformat(),
                'grid_size': 64,
                'num_levels': 9,
            },
            'categories': [
                {'id': 'npcs', 'name': 'NPCs', 'color': '#ff6b6b'},
                {'id': 'weapons', 'name': 'Weapons', 'color': '#4dabf7'},
                {'id': 'armor', 'name': 'Armor', 'color': '#69db7c'},
                {'id': 'keys', 'name': 'Keys', 'color': '#ffd43b'},
                {'id': 'containers', 'name': 'Containers', 'color': '#da77f2'},
                {'id': 'consumables', 'name': 'Food & Potions', 'color': '#f783ac'},
                {'id': 'readable', 'name': 'Books & Scrolls', 'color': '#e8d4b8'},
                {'id': 'magic', 'name': 'Magic Items', 'color': '#9775fa'},
                {'id': 'treasure', 'name': 'Treasure', 'color': '#fcc419'},
                {'id': 'light', 'name': 'Light Sources', 'color': '#ffe066'},
                {'id': 'doors', 'name': 'Doors', 'color': '#adb5bd'},
                {'id': 'traps', 'name': 'Traps', 'color': '#ff8787'},
                {'id': 'triggers', 'name': 'Triggers', 'color': '#748ffc'},
                {'id': 'misc', 'name': 'Miscellaneous', 'color': '#868e96'},
            ],
            'levels': []
        }
        
        # Level names for reference
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
        
        for level_num in range(9):
            level_entry = {
                'level': level_num,
                'name': level_names[level_num] if level_num < len(level_names) else f"Level {level_num + 1}",
                'objects': objects_by_level[level_num],
                'npcs': npcs_by_level[level_num],
                'object_count': len(objects_by_level[level_num]),
                'npc_count': len(npcs_by_level[level_num]),
            }
            web_data['levels'].append(level_entry)
        
        return self._write_json('web_map_data.json', web_data)



