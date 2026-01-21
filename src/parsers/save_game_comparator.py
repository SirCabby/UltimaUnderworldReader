"""
Save Game Comparator for Ultima Underworld

Compares save game data with base game data to identify changes:
- Removed: Objects present in base but missing in save
- Added: Objects present in save but missing in base
- Moved: Objects with same ID but different position
- Modified: Objects with same position but different properties
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass


@dataclass
class ObjectChange:
    """Represents a change to an object between base and save game."""
    change_type: str  # 'removed', 'added', 'moved', 'modified', 'unchanged'
    object_id: int
    level: int
    base_data: Optional[Dict] = None
    save_data: Optional[Dict] = None
    base_index: Optional[int] = None
    save_index: Optional[int] = None


class SaveGameComparator:
    """
    Compares base game data with save game data to identify changes.
    
    Usage:
        comparator = SaveGameComparator(base_data, save_data)
        changes = comparator.compare()
    """
    
    def __init__(self, base_data: Dict, save_data: Dict):
        """
        Initialize comparator with base and save game data.
        
        Args:
            base_data: Base game data in web map format (from web_map_data.json)
            save_data: Save game data in web map format (from SaveGameParser)
        """
        self.base_data = base_data
        self.save_data = save_data
        self.changes: Dict[int, Dict[str, List[ObjectChange]]] = {
            level: {
                'removed': [],
                'added': [],
                'moved': [],
                'modified': [],
                'unchanged': []
            }
            for level in range(9)
        }
    
    def _create_object_key(self, obj: Dict, include_position: bool = True) -> Tuple:
        """
        Create a unique key for an object for comparison.
        
        Args:
            obj: Object dictionary
            include_position: Whether to include position in the key
            
        Returns:
            Tuple that uniquely identifies the object
        """
        if include_position:
            return (
                obj.get('object_id', 0),
                obj.get('tile_x', 0),
                obj.get('tile_y', 0),
                obj.get('z', 0)
            )
        else:
            return (obj.get('object_id', 0),)
    
    def _create_object_index_map(self, objects: List[Dict], is_npc: bool = False) -> Dict[Tuple, Dict]:
        """
        Create a map from object keys to object data.
        
        Args:
            objects: List of object dictionaries
            is_npc: Whether these are NPC objects
            
        Returns:
            Dictionary mapping object keys to object data
        """
        index_map = {}
        for obj in objects:
            # For NPCs, use object_id + index as key (more stable)
            if is_npc:
                key = (obj.get('object_id', 0), obj.get('id', 0))
            else:
                # For static objects, use position-based key
                key = self._create_object_key(obj, include_position=True)
            
            index_map[key] = obj
        return index_map
    
    def _objects_match(self, base_obj: Dict, save_obj: Dict) -> bool:
        """
        Check if two objects represent the same object (same ID and similar position).
        
        Args:
            base_obj: Base game object
            save_obj: Save game object
            
        Returns:
            True if objects match
        """
        base_id = base_obj.get('object_id', 0)
        save_id = save_obj.get('object_id', 0)
        
        if base_id != save_id:
            return False
        
        # For NPCs, also check index
        if base_obj.get('is_npc') or save_obj.get('is_npc'):
            base_idx = base_obj.get('id', 0)
            save_idx = save_obj.get('id', 0)
            return base_idx == save_idx
        
        # For static objects, check if positions are close (within same tile)
        base_x = base_obj.get('tile_x', 0)
        base_y = base_obj.get('tile_y', 0)
        save_x = save_obj.get('tile_x', 0)
        save_y = save_obj.get('tile_y', 0)
        
        # Allow small position differences (objects can move within a tile)
        return abs(base_x - save_x) <= 1 and abs(base_y - save_y) <= 1
    
    def _object_properties_changed(self, base_obj: Dict, save_obj: Dict) -> bool:
        """
        Check if object properties changed (quality, owner, enchanted status, etc.).
        
        Args:
            base_obj: Base game object
            save_obj: Save game object
            
        Returns:
            True if properties changed
        """
        # Compare key properties
        props_to_check = [
            'quality', 'owner', 'is_enchanted', 'quantity',
            'hp', 'level', 'attitude'  # For NPCs
        ]
        
        for prop in props_to_check:
            base_val = base_obj.get(prop)
            save_val = save_obj.get(prop)
            if base_val != save_val:
                return True
        
        # Check extra_info for important changes (door lock status, etc.)
        base_extra = base_obj.get('extra_info', {})
        save_extra = save_obj.get('extra_info', {})
        
        # Check door/container lock status
        base_locked = base_extra.get('is_locked')
        save_locked = save_extra.get('is_locked')
        if base_locked != save_locked:
            return True
        
        # Check door open status
        base_open = base_extra.get('is_open')
        save_open = save_extra.get('is_open')
        if base_open != save_open:
            return True
        
        # Check lock_id if present (lock might have changed)
        base_lock_id = base_extra.get('lock_id')
        save_lock_id = save_extra.get('lock_id')
        if base_lock_id != save_lock_id:
            return True
        
        return False
    
    def _object_position_changed(self, base_obj: Dict, save_obj: Dict) -> bool:
        """
        Check if object position changed significantly.
        
        Args:
            base_obj: Base game object
            save_obj: Save game object
            
        Returns:
            True if position changed significantly
        """
        base_x = base_obj.get('tile_x', 0)
        base_y = base_obj.get('tile_y', 0)
        base_z = base_obj.get('z', 0)
        
        save_x = save_obj.get('tile_x', 0)
        save_y = save_obj.get('tile_y', 0)
        save_z = save_obj.get('z', 0)
        
        # Consider it moved if position changed by more than 1 tile
        return (abs(base_x - save_x) > 1 or 
                abs(base_y - save_y) > 1 or 
                abs(base_z - save_z) > 10)
    
    def compare(self) -> Dict[int, Dict[str, List[ObjectChange]]]:
        """
        Compare base and save game data to identify changes.
        
        Returns:
            Dictionary mapping level numbers to change lists
        """
        # Get levels from both datasets
        base_levels = self.base_data.get('levels', [])
        save_levels = self.save_data.get('levels', [])
        
        # Create level maps
        base_level_map = {level.get('level', i): level for i, level in enumerate(base_levels)}
        save_level_map = {level.get('level', i): level for i, level in enumerate(save_levels)}
        
        # Compare each level
        for level_num in range(9):
            base_level = base_level_map.get(level_num, {})
            save_level = save_level_map.get(level_num, {})
            
            base_objects = base_level.get('objects', [])
            base_npcs = base_level.get('npcs', [])
            save_objects = save_level.get('objects', [])
            save_npcs = save_level.get('npcs', [])
            
            # Compare objects
            self._compare_object_lists(
                level_num, base_objects, save_objects, is_npc=False
            )
            
            # Compare NPCs
            self._compare_object_lists(
                level_num, base_npcs, save_npcs, is_npc=True
            )
        
        return self.changes
    
    def _is_door(self, obj: Dict) -> bool:
        """Check if an object is a door (object_id in 0x140-0x14F range)."""
        obj_id = obj.get('object_id', 0)
        return 0x140 <= obj_id <= 0x14F
    
    def _compare_object_lists(
        self, 
        level_num: int, 
        base_list: List[Dict], 
        save_list: List[Dict],
        is_npc: bool = False
    ) -> None:
        """
        Compare two lists of objects and identify changes.
        
        Args:
            level_num: Level number
            base_list: Base game objects
            save_list: Save game objects
            is_npc: Whether these are NPC objects
        """
        # Create maps for efficient lookup
        # For NPCs, use (object_id, index) as key
        # For static objects, use (object_id, tile_x, tile_y, z) as key
        base_map = {}
        save_map = {}
        
        for obj in base_list:
            if is_npc:
                key = (obj.get('object_id', 0), obj.get('id', 0))
            else:
                key = self._create_object_key(obj, include_position=True)
            base_map[key] = obj
        
        for obj in save_list:
            if is_npc:
                key = (obj.get('object_id', 0), obj.get('id', 0))
            else:
                key = self._create_object_key(obj, include_position=True)
            save_map[key] = obj
        
        # Find removed objects (in base but not in save)
        removed_doors = []  # Track removed doors for special matching
        for key, base_obj in base_map.items():
            if key not in save_map:
                # Object was removed
                change = ObjectChange(
                    change_type='removed',
                    object_id=base_obj.get('object_id', 0),
                    level=level_num,
                    base_data=base_obj,
                    base_index=base_obj.get('id', 0)
                )
                self.changes[level_num]['removed'].append(change)
                # Track doors for special matching
                if not is_npc and self._is_door(base_obj):
                    removed_doors.append((key, base_obj, change))
        
        # Find added objects (in save but not in base)
        added_doors = []  # Track added doors for special matching
        for key, save_obj in save_map.items():
            if key not in base_map:
                # Object was added
                change = ObjectChange(
                    change_type='added',
                    object_id=save_obj.get('object_id', 0),
                    level=level_num,
                    save_data=save_obj,
                    save_index=save_obj.get('id', 0)
                )
                self.changes[level_num]['added'].append(change)
                # Track doors for special matching
                if not is_npc and self._is_door(save_obj):
                    added_doors.append((key, save_obj, change))
        
        # Special handling: Match doors by position even if object_id changed
        # This handles cases where a door's object_id changes when locked/unlocked
        if not is_npc and removed_doors and added_doors:
            matched_pairs = []
            matched_removed = set()  # Track which removed doors have been matched
            matched_added = set()    # Track which added doors have been matched
            
            for rem_key, rem_obj, rem_change in removed_doors:
                if rem_change in matched_removed:
                    continue  # Already matched
                
                rem_x = rem_obj.get('tile_x', 0)
                rem_y = rem_obj.get('tile_y', 0)
                rem_z = rem_obj.get('z', 0)
                
                for add_key, add_obj, add_change in added_doors:
                    if add_change in matched_added:
                        continue  # Already matched
                    
                    add_x = add_obj.get('tile_x', 0)
                    add_y = add_obj.get('tile_y', 0)
                    add_z = add_obj.get('z', 0)
                    
                    # Check if positions match (same tile, same z)
                    if rem_x == add_x and rem_y == add_y and rem_z == add_z:
                        # Both are doors at the same position - treat as modified
                        matched_pairs.append((rem_obj, add_obj, rem_change, add_change))
                        matched_removed.add(rem_change)
                        matched_added.add(add_change)
                        break
            
            # Convert matched door pairs from removed/added to modified
            for rem_obj, add_obj, rem_change, add_change in matched_pairs:
                # Remove from removed/added lists
                self.changes[level_num]['removed'].remove(rem_change)
                self.changes[level_num]['added'].remove(add_change)
                
                # Add as modified
                change = ObjectChange(
                    change_type='modified',
                    object_id=add_obj.get('object_id', 0),
                    level=level_num,
                    base_data=rem_obj,
                    save_data=add_obj,
                    base_index=rem_obj.get('id', 0),
                    save_index=add_obj.get('id', 0)
                )
                self.changes[level_num]['modified'].append(change)
        
        # Find moved/modified objects (in both but different)
        for key in base_map.keys() & save_map.keys():
            base_obj = base_map[key]
            save_obj = save_map[key]
            
            # Check if position changed significantly
            if self._object_position_changed(base_obj, save_obj):
                change = ObjectChange(
                    change_type='moved',
                    object_id=base_obj.get('object_id', 0),
                    level=level_num,
                    base_data=base_obj,
                    save_data=save_obj,
                    base_index=base_obj.get('id', 0),
                    save_index=save_obj.get('id', 0)
                )
                self.changes[level_num]['moved'].append(change)
            # Check if properties changed
            elif self._object_properties_changed(base_obj, save_obj):
                change = ObjectChange(
                    change_type='modified',
                    object_id=base_obj.get('object_id', 0),
                    level=level_num,
                    base_data=base_obj,
                    save_data=save_obj,
                    base_index=base_obj.get('id', 0),
                    save_index=save_obj.get('id', 0)
                )
                self.changes[level_num]['modified'].append(change)
            else:
                # Object unchanged
                change = ObjectChange(
                    change_type='unchanged',
                    object_id=base_obj.get('object_id', 0),
                    level=level_num,
                    base_data=base_obj,
                    save_data=save_obj,
                    base_index=base_obj.get('id', 0),
                    save_index=save_obj.get('id', 0)
                )
                self.changes[level_num]['unchanged'].append(change)
    
    def get_changes_summary(self) -> Dict[str, int]:
        """
        Get a summary of changes across all levels.
        
        Returns:
            Dictionary with counts of each change type
        """
        summary = {
            'removed': 0,
            'added': 0,
            'moved': 0,
            'modified': 0,
            'unchanged': 0
        }
        
        for level_changes in self.changes.values():
            for change_type, changes in level_changes.items():
                summary[change_type] += len(changes)
        
        return summary
    
    def apply_changes_to_save_data(self) -> Dict:
        """
        Apply change metadata to save data objects.
        
        This adds a 'change_type' field to each object in the save data
        so the frontend can visualize changes.
        
        Returns:
            Save data with change metadata added
        """
        result = self.save_data.copy()
        result['levels'] = []
        
        for level_num in range(9):
            level_changes = self.changes[level_num]
            save_level = next(
                (l for l in self.save_data.get('levels', []) if l.get('level') == level_num),
                {'level': level_num, 'objects': [], 'npcs': []}
            )
            
            # Create change lookup maps
            added_map = {c.save_index: c for c in level_changes['added']}
            moved_map = {c.save_index: c for c in level_changes['moved']}
            modified_map = {c.save_index: c for c in level_changes['modified']}
            
            # Add change metadata to objects
            objects_with_changes = []
            for obj in save_level.get('objects', []):
                obj_copy = obj.copy()
                obj_id = obj.get('id', 0)
                
                if obj_id in added_map:
                    obj_copy['change_type'] = 'added'
                elif obj_id in moved_map:
                    obj_copy['change_type'] = 'moved'
                elif obj_id in modified_map:
                    obj_copy['change_type'] = 'modified'
                else:
                    obj_copy['change_type'] = 'unchanged'
                
                objects_with_changes.append(obj_copy)
            
            # Add change metadata to NPCs
            npcs_with_changes = []
            for npc in save_level.get('npcs', []):
                npc_copy = npc.copy()
                npc_id = npc.get('id', 0)
                
                if npc_id in added_map:
                    npc_copy['change_type'] = 'added'
                elif npc_id in moved_map:
                    npc_copy['change_type'] = 'moved'
                elif npc_id in modified_map:
                    npc_copy['change_type'] = 'modified'
                else:
                    npc_copy['change_type'] = 'unchanged'
                
                npcs_with_changes.append(npc_copy)
            
            result['levels'].append({
                'level': level_num,
                'name': save_level.get('name', f'Level {level_num + 1}'),
                'objects': objects_with_changes,
                'npcs': npcs_with_changes,
            })
        
        return result
