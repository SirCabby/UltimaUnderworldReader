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
    0x161: SwitchInfo(
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
    0x161: SwitchInfo(
        name="dial",
        description="A wall-mounted dial",
        visual_type="dial"
    ),
}


def is_switch(item_id: int) -> bool:
    """Check if an object ID is a switch."""
    # Include lever 0x161 which is in the decal range but functions as a switch
    return (SWITCH_ID_MIN <= item_id <= SWITCH_ID_MAX) or item_id == 0x161


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


def _clean_object_name(raw_name: str) -> str:
    """Clean object name by removing article prefix and plural suffix."""
    if not raw_name:
        return ""
    # Remove article prefix (a_, an_, some_)
    if raw_name.startswith("a_"):
        name = raw_name[2:]
    elif raw_name.startswith("an_"):
        name = raw_name[3:]
    elif raw_name.startswith("some_"):
        name = raw_name[5:]
    else:
        name = raw_name
    # Remove plural suffix
    if "&" in name:
        name = name.split("&")[0]
    return name


# Import from traps module for variable names
from .traps import GAME_VARIABLES, _get_variable_name, _find_door_for_lock


def describe_switch_effect(trap_id: int, trap_quality: int, trap_owner: int,
                           trap_x: int, trap_y: int, level_num: int,
                           object_names: list = None, target_obj=None,
                           switch_x: int = -1, switch_y: int = -1,
                           level_objects: dict = None,
                           trap_messages: list = None,
                           spell_names: list = None) -> str:
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
        trap_messages: Optional list of trap messages from STRINGS.PAK block 9
        spell_names: Optional list of spell names from STRINGS.PAK block 6
    
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
                door_name = _clean_object_name(object_names[nearest_door.item_id])
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
            obj_name = _clean_object_name(object_names[target_obj.item_id])
            return f"Spawns {obj_name} at ({trap_x}, {trap_y})"
        return f"Spawns object at ({trap_x}, {trap_y})"
    
    # Set variable trap (0x18D) - sets game state
    if trap_id == 0x18D:
        var_name = _get_variable_name(trap_owner)
        return f"Sets {var_name} = {trap_quality}"
    
    # Check variable trap (0x18E) - conditional mechanism
    if trap_id == 0x18E:
        var_name = _get_variable_name(trap_owner)
        return f"Checks {var_name} == {trap_quality}"
    
    # Do trap (0x183) - action sequence
    if trap_id == 0x183:
        if trap_quality > 0 or trap_owner > 0:
            return f"Triggers action (type={trap_quality}, param={trap_owner})"
        return "Triggers action sequence"
    
    # Damage trap (0x180)
    if trap_id == 0x180:
        return f"Deals {trap_quality} damage"
    
    # Spell trap (0x186)
    if trap_id == 0x186:
        if spell_names and trap_quality < len(spell_names) and spell_names[trap_quality]:
            spell_name = spell_names[trap_quality]
            return f"Casts {spell_name}"
        return f"Casts spell #{trap_quality}"
    
    # Delete object trap (0x18B)
    if trap_id == 0x18B:
        if target_obj and object_names and target_obj.item_id < len(object_names):
            obj_name = _clean_object_name(object_names[target_obj.item_id])
            return f"Removes {obj_name} at ({trap_quality}, {trap_owner})"
        return f"Removes object at ({trap_quality}, {trap_owner})"
    
    # Tell/text traps (0x18A, 0x190)
    if trap_id in (0x18A, 0x190):
        msg_index = trap_quality + trap_owner * 64
        if trap_messages and msg_index < len(trap_messages) and trap_messages[msg_index]:
            msg = trap_messages[msg_index]
            if len(msg) > 50:
                msg = msg[:47] + "..."
            return f'Displays: "{msg}"'
        return f"Displays message #{msg_index}"
    
    # Pit trap (0x184)
    if trap_id == 0x184:
        return "Opens pit"
    
    # Unknown trap
    return "Unknown effect"
