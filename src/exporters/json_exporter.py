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



