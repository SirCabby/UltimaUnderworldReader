"""
Lock resolution for doors and containers.

Extracts lock information from game objects including:
- Lock ID (which key opens it)
- Lock type (keyed, special, or unlocked)
- Whether the lock is pickable

This consolidates the lock parsing logic that was duplicated in
item_extractor.py and secret_finder.py.
"""

from typing import Dict, Any, Optional


# Lock object ID in Ultima Underworld
LOCK_OBJECT_ID = 0x10F


def resolve_lock_info(
    obj,
    level_objects: Optional[Dict[int, Any]] = None
) -> Dict[str, Any]:
    """
    Resolve lock information for any lockable object (door or container).
    
    The lock mechanism in UW1:
    - A door/container is locked if it has a non-zero special_link
      pointing to a lock object (0x10F), OR has a non-zero owner
      (for template objects at position 0,0)
    - The lock ID (what key opens it) is stored in the lock object's
      quantity field as: quantity - 512 = lock_id
    - Keys with owner=lock_id can open the lock
    - Lock quality determines pickability: 40=pickable, 63=special/unpickable
    
    Args:
        obj: The game object (door/container) with properties:
            - is_quantity: bool
            - quantity_or_link: int
            - owner: int
        level_objects: Optional dict mapping object indices to objects
    
    Returns:
        Dictionary with lock info:
            - is_locked: bool
            - lock_id: int (if locked and has a key)
            - lock_type: 'keyed', 'special', or None
            - is_pickable: bool
    """
    # Get special_link based on is_quantity flag
    special_link = obj.quantity_or_link if not obj.is_quantity else 0
    
    # Check if locked
    is_locked = special_link != 0 or obj.owner != 0
    
    result = {
        'is_locked': is_locked,
        'lock_id': None,
        'lock_type': None,
        'is_pickable': False
    }
    
    if not is_locked:
        return result
    
    # Try to get lock details from the lock object
    lock_id = None
    lock_quality = None
    
    if special_link != 0 and level_objects:
        lock_obj = level_objects.get(special_link)
        if lock_obj and lock_obj.item_id == LOCK_OBJECT_ID:
            # Lock ID is stored as quantity - 512
            lock_quantity = lock_obj.quantity_or_link if lock_obj.is_quantity else 0
            if lock_quantity >= 512:
                lock_id = lock_quantity - 512
            lock_quality = lock_obj.quality
    
    # Fallback to owner for template objects at (0,0)
    if lock_id is None and obj.owner != 0:
        lock_id = obj.owner
    
    if lock_id is not None and lock_id > 0:
        result['lock_id'] = lock_id
        result['lock_type'] = 'keyed'  # Needs key with owner=lock_id
    else:
        # No lock ID found - might be trigger-opened
        result['lock_type'] = 'special'
    
    # Check if lock is pickable based on lock quality
    # Quality 40 = pickable, Quality 63 = special/not pickable
    if lock_quality is not None:
        result['is_pickable'] = lock_quality == 40
    
    return result


def resolve_door_lock(
    obj,
    level_objects: Optional[Dict[int, Any]] = None
) -> Dict[str, Any]:
    """
    Resolve lock information specifically for doors.
    
    This is a convenience wrapper around resolve_lock_info that adds
    door-specific context.
    
    Args:
        obj: The door object
        level_objects: Optional dict mapping object indices to objects
    
    Returns:
        Dictionary with lock info (same as resolve_lock_info)
    """
    return resolve_lock_info(obj, level_objects)


def resolve_container_lock(
    obj,
    level_objects: Optional[Dict[int, Any]] = None
) -> Dict[str, Any]:
    """
    Resolve lock information specifically for containers.
    
    Containers use the same lock mechanism as doors:
    - special_link points to a lock object (0x10F)
    - Lock ID stored in lock.quantity - 512
    
    Args:
        obj: The container object
        level_objects: Optional dict mapping object indices to objects
    
    Returns:
        Dictionary with lock info including:
            - is_locked: bool
            - lock_id: int (if locked and has a key)
            - lock_type: 'keyed' or 'special'
            - is_pickable: bool
    """
    # Get special_link based on is_quantity flag
    special_link = obj.quantity_or_link if not obj.is_quantity else 0
    
    result = {
        'is_locked': False,
        'lock_id': None,
        'lock_type': None,
        'is_pickable': False
    }
    
    # Containers are only locked if special_link points to a lock object
    if special_link == 0 or not level_objects:
        return result
    
    lock_obj = level_objects.get(special_link)
    if not lock_obj or lock_obj.item_id != LOCK_OBJECT_ID:
        # special_link points to something else (probably contents), not locked
        return result
    
    result['is_locked'] = True
    
    # Get lock ID from lock object's quantity field
    lock_quality = lock_obj.quality
    lock_quantity = lock_obj.quantity_or_link if lock_obj.is_quantity else 0
    
    lock_id = None
    if lock_quantity >= 512:
        lock_id = lock_quantity - 512
    
    if lock_id is not None and lock_id > 0:
        result['lock_id'] = lock_id
        result['lock_type'] = 'keyed'  # Needs key with owner=lock_id
    else:
        # No lock ID found - might be trigger-opened or special
        result['lock_type'] = 'special'
    
    # Check if lock is pickable based on lock quality
    # Quality 40 = pickable, Quality 63 = special/not pickable
    result['is_pickable'] = lock_quality == 40
    
    return result


def get_door_condition(health: int, max_health: int = 40) -> str:
    """
    Get door condition description based on health.
    
    Args:
        health: Current door health (0-40)
        max_health: Maximum door health (default 40)
    
    Returns:
        Condition string: 'broken', 'badly damaged', 'damaged', 
        'undamaged', or 'sturdy'
    """
    if health <= 0:
        return 'broken'
    elif health <= max_health // 3:
        return 'badly damaged'
    elif health <= 2 * max_health // 3:
        return 'damaged'
    elif health == max_health:
        return 'sturdy'
    else:
        return 'undamaged'
