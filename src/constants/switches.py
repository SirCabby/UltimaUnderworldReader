"""
Switch constants for Ultima Underworld.

Switches (0x170-0x17F) are interactive objects like buttons, levers,
and pull chains that activate triggers and traps when used.

The switch object's special_link field points to a trigger (0x1A0-0x1BF),
which in turn links to a trap (0x180-0x19F) that performs the actual effect.

Chain: Switch -> Trigger -> Trap -> Effect
"""

from typing import Dict, Optional, NamedTuple


# Switch ID range: 0x170-0x17F (16 types)
SWITCH_ID_MIN = 0x170
SWITCH_ID_MAX = 0x17F


class SwitchInfo(NamedTuple):
    """Information about a switch type."""
    name: str
    description: str
    visual_type: str  # "button", "lever", "pull_chain", "switch"


# Switch types (0x170-0x17F)
# The game has pairs of each type (likely for activated/deactivated states)
SWITCH_TYPES: Dict[int, SwitchInfo] = {
    0x170: SwitchInfo(
        name="button",
        description="A wall-mounted push button",
        visual_type="button"
    ),
    0x171: SwitchInfo(
        name="button",
        description="A wall-mounted push button",
        visual_type="button"
    ),
    0x172: SwitchInfo(
        name="button",
        description="A wall-mounted push button",
        visual_type="button"
    ),
    0x173: SwitchInfo(
        name="switch",
        description="A toggle switch",
        visual_type="switch"
    ),
    0x174: SwitchInfo(
        name="switch",
        description="A toggle switch",
        visual_type="switch"
    ),
    0x175: SwitchInfo(
        name="lever",
        description="A wall-mounted lever",
        visual_type="lever"
    ),
    0x176: SwitchInfo(
        name="pull_chain",
        description="A hanging pull chain",
        visual_type="pull_chain"
    ),
    0x177: SwitchInfo(
        name="pull_chain",
        description="A hanging pull chain",
        visual_type="pull_chain"
    ),
    0x178: SwitchInfo(
        name="button",
        description="A wall-mounted push button",
        visual_type="button"
    ),
    0x179: SwitchInfo(
        name="button",
        description="A wall-mounted push button",
        visual_type="button"
    ),
    0x17A: SwitchInfo(
        name="button",
        description="A wall-mounted push button",
        visual_type="button"
    ),
    0x17B: SwitchInfo(
        name="switch",
        description="A toggle switch",
        visual_type="switch"
    ),
    0x17C: SwitchInfo(
        name="switch",
        description="A toggle switch",
        visual_type="switch"
    ),
    0x17D: SwitchInfo(
        name="lever",
        description="A wall-mounted lever",
        visual_type="lever"
    ),
    0x17E: SwitchInfo(
        name="pull_chain",
        description="A hanging pull chain",
        visual_type="pull_chain"
    ),
    0x17F: SwitchInfo(
        name="pull_chain",
        description="A hanging pull chain",
        visual_type="pull_chain"
    ),
}


def is_switch(item_id: int) -> bool:
    """Check if an object ID is a switch."""
    return SWITCH_ID_MIN <= item_id <= SWITCH_ID_MAX


def get_switch_info(item_id: int) -> Optional[SwitchInfo]:
    """Get switch information for an object ID."""
    return SWITCH_TYPES.get(item_id)


def get_switch_type(item_id: int) -> str:
    """Get the switch visual type (button, lever, pull_chain, switch)."""
    info = SWITCH_TYPES.get(item_id)
    return info.visual_type if info else "switch"


def get_switch_name(item_id: int) -> str:
    """Get the switch type name for an object ID."""
    info = SWITCH_TYPES.get(item_id)
    return info.name if info else f"switch_0x{item_id:03X}"


def describe_switch_effect(trap_id: int, trap_quality: int, trap_owner: int,
                           trap_x: int, trap_y: int, level_num: int,
                           object_names: list = None, target_obj=None,
                           switch_x: int = -1, switch_y: int = -1,
                           level_objects: dict = None) -> str:
    """
    Generate a clean, user-friendly description of what a switch does.
    
    Args:
        trap_id: The trap object ID (0x180-0x19F)
        trap_quality: The trap's quality field
        trap_owner: The trap's owner field
        trap_x: The trap's tile X coordinate (target location for terrain changes)
        trap_y: The trap's tile Y coordinate
        level_num: The level number (0-indexed)
        object_names: Optional list of object names for identifying created objects
        target_obj: Optional target object (for create_object_trap)
        switch_x: The switch's tile X coordinate (for finding nearby doors)
        switch_y: The switch's tile Y coordinate
        level_objects: Dict of all objects on the level (for finding doors)
    
    Returns:
        Clean human-readable effect description
    """
    # Door trap (0x188) - opens/closes a door
    if trap_id == 0x188:
        operations = {0: "Closes", 1: "Opens", 2: "Toggles", 3: "Toggles"}
        op = operations.get(trap_quality, "Toggles")
        
        # Try to find the nearest door to the switch
        nearest_door = None
        min_distance = 999
        if level_objects and switch_x >= 0 and switch_y >= 0:
            for obj in level_objects.values():
                # Check if this is a door (0x140-0x14F)
                if 0x140 <= obj.item_id <= 0x14F and obj.tile_x > 0:
                    dx = abs(obj.tile_x - switch_x)
                    dy = abs(obj.tile_y - switch_y)
                    distance = dx + dy
                    if distance < min_distance:
                        min_distance = distance
                        nearest_door = obj
        
        if nearest_door and min_distance <= 15:
            # Get door name
            door_name = "door"
            if object_names and nearest_door.item_id < len(object_names):
                raw_name = object_names[nearest_door.item_id]
                if raw_name.startswith("a_"):
                    door_name = raw_name[2:].split("&")[0]
                elif raw_name.startswith("an_"):
                    door_name = raw_name[3:].split("&")[0]
                else:
                    door_name = raw_name.split("&")[0]
            return f"{op} {door_name} at ({nearest_door.tile_x}, {nearest_door.tile_y})"
        
        return f"{op} a door"
    
    # Change terrain trap (0x185) - modifies terrain at trap location
    if trap_id == 0x185:
        new_height = trap_quality & 0xF
        new_type = (trap_quality >> 4) & 0xF
        
        # Type 0 = SOLID (closes passage), Type 1 = OPEN (opens passage)
        if new_type == 0:
            return f"Closes passage at ({trap_x}, {trap_y})"
        elif new_type == 1:
            return f"Opens passage at ({trap_x}, {trap_y})"
        else:
            # Diagonal or slope - describe as terrain change
            type_names = {
                2: "diagonal SE", 3: "diagonal SW", 
                4: "diagonal NE", 5: "diagonal NW",
                6: "slope N", 7: "slope S", 8: "slope E", 9: "slope W"
            }
            type_desc = type_names.get(new_type, f"terrain type {new_type}")
            return f"Creates {type_desc} at ({trap_x}, {trap_y})"
    
    # Teleport trap (0x181) - teleports player
    if trap_id == 0x181:
        dest_x, dest_y = trap_quality, trap_owner
        return f"Teleports to ({dest_x}, {dest_y})"
    
    # Create object trap (0x187) - spawns an object
    if trap_id == 0x187:
        if target_obj and object_names and target_obj.item_id < len(object_names):
            obj_name = object_names[target_obj.item_id]
            # Clean up the name (remove article prefix like "a_")
            if obj_name.startswith("a_"):
                obj_name = obj_name[2:]
            elif obj_name.startswith("an_"):
                obj_name = obj_name[3:]
            return f"Spawns {obj_name} at ({trap_x}, {trap_y})"
        return f"Spawns object at ({trap_x}, {trap_y})"
    
    # Set variable trap (0x18D) - sets game state
    if trap_id == 0x18D:
        return "Activates mechanism"
    
    # Check variable trap (0x18E) - conditional mechanism
    if trap_id == 0x18E:
        return "Triggers conditional mechanism"
    
    # Do trap (0x183) - action sequence
    if trap_id == 0x183:
        return "Triggers action sequence"
    
    # Damage trap (0x180)
    if trap_id == 0x180:
        return f"Deals {trap_quality} damage"
    
    # Spell trap (0x186)
    if trap_id == 0x186:
        return "Casts spell effect"
    
    # Delete object trap (0x18B)
    if trap_id == 0x18B:
        return f"Removes object at ({trap_x}, {trap_y})"
    
    # Tell/text traps (0x18A, 0x190)
    if trap_id in (0x18A, 0x190):
        return "Displays message"
    
    # Pit trap (0x184)
    if trap_id == 0x184:
        return "Opens pit"
    
    # Unknown trap
    return "Unknown effect"
