"""
Trap and Trigger constants for Ultima Underworld.

The game uses a two-level system:
- TRIGGERS (0x1A0-0x1BF) detect player actions and activate traps
- TRAPS (0x180-0x19F) perform actual game effects

Key encoding for triggers:
- quality/owner often encode destination coordinates for the effect
- quantity_or_link (when is_quantity=False) points to the trap to execute
- If link=0, the trigger may use quality/owner for its own effect

Key encoding for traps:
- quality often encodes the effect magnitude (damage amount, spell ID, etc.)
- owner often encodes secondary parameters
- quantity_or_link points to target objects

Teleport system (for level transitions like stairs):
- teleport_trap (0x181): quality=dest_x, owner=dest_y
- z_pos appears to encode destination level (needs verification)
- Teleport traps can be stepped on directly or linked from triggers
"""

from typing import Dict, Tuple, Optional, NamedTuple

# Trap ID range: 0x180-0x19F (32 types, but only some are known)
TRAP_ID_MIN = 0x180
TRAP_ID_MAX = 0x19F

# Trigger ID range: 0x1A0-0x1BF (32 types, but only some are known)
TRIGGER_ID_MIN = 0x1A0
TRIGGER_ID_MAX = 0x1BF


class TrapInfo(NamedTuple):
    """Information about a trap type."""
    name: str
    description: str
    quality_meaning: str  # What the quality field encodes
    owner_meaning: str    # What the owner field encodes
    link_meaning: str     # What the link field points to


class TriggerInfo(NamedTuple):
    """Information about a trigger type."""
    name: str
    description: str
    activation: str       # How the trigger is activated
    quality_meaning: str  # What quality encodes (often dest_x)
    owner_meaning: str    # What owner encodes (often dest_y)


# Trap types (0x180-0x19F)
TRAP_TYPES: Dict[int, TrapInfo] = {
    0x180: TrapInfo(
        name="damage_trap",
        description="Deals damage to player when stepped on",
        quality_meaning="Damage amount",
        owner_meaning="Unknown",
        link_meaning="Unused"
    ),
    0x181: TrapInfo(
        name="teleport_trap",
        description="Teleports player to another location",
        quality_meaning="Destination X coordinate",
        owner_meaning="Destination Y coordinate",
        link_meaning="Unused (z_pos may encode dest level)"
    ),
    0x182: TrapInfo(
        name="arrow_trap",
        description="Shoots projectile at player",
        quality_meaning="Arrow type or damage",
        owner_meaning="Direction",
        link_meaning="Unknown"
    ),
    0x183: TrapInfo(
        name="do_trap",
        description="Executes a sequence of actions",
        quality_meaning="Action type",
        owner_meaning="Parameter",
        link_meaning="Linked action chain"
    ),
    0x184: TrapInfo(
        name="pit_trap",
        description="Creates pit or drops player down",
        quality_meaning="Unknown",
        owner_meaning="Unknown",
        link_meaning="Unknown"
    ),
    0x185: TrapInfo(
        name="change_terrain_trap",
        description="Modifies terrain (illusory walls, bridges)",
        quality_meaning="new_height|(new_type<<4)",
        owner_meaning="New wall texture (63=unchanged)",
        link_meaning="Chained terrain change"
    ),
    0x186: TrapInfo(
        name="spell_trap",
        description="Casts a spell effect",
        quality_meaning="Spell ID or power",
        owner_meaning="Direction",
        link_meaning="Target or spell object"
    ),
    0x187: TrapInfo(
        name="create_object_trap",
        description="Creates an object at location",
        quality_meaning="Object quality",
        owner_meaning="Unknown",
        link_meaning="Object template index"
    ),
    0x188: TrapInfo(
        name="door_trap",
        description="Opens, closes, or toggles a door",
        quality_meaning="Operation type",
        owner_meaning="Unknown",
        link_meaning="Target door object"
    ),
    0x189: TrapInfo(
        name="ward_trap",
        description="Protective ward or barrier",
        quality_meaning="Ward type or power",
        owner_meaning="Unknown",
        link_meaning="Unknown"
    ),
    0x18A: TrapInfo(
        name="tell_trap",
        description="Displays a text message",
        quality_meaning="Text group",
        owner_meaning="Text offset",
        link_meaning="String index"
    ),
    0x18B: TrapInfo(
        name="delete_object_trap",
        description="Removes an object from the level",
        quality_meaning="Target X",
        owner_meaning="Target Y",
        link_meaning="Object to delete (or uses qty if is_quantity)"
    ),
    0x18C: TrapInfo(
        name="inventory_trap",
        description="Modifies player inventory",
        quality_meaning="Item type or slot",
        owner_meaning="Count or action",
        link_meaning="Item template"
    ),
    0x18D: TrapInfo(
        name="set_variable_trap",
        description="Sets a game variable",
        quality_meaning="Variable value",
        owner_meaning="Variable ID",
        link_meaning="Chained action"
    ),
    0x18E: TrapInfo(
        name="check_variable_trap",
        description="Checks a condition and branches",
        quality_meaning="Expected value",
        owner_meaning="Variable ID",
        link_meaning="Action if true"
    ),
    0x18F: TrapInfo(
        name="combination_trap",
        description="Executes multiple traps in sequence",
        quality_meaning="Unknown",
        owner_meaning="Unknown",
        link_meaning="First trap in chain"
    ),
    0x190: TrapInfo(
        name="text_string_trap",
        description="Shows text message to player",
        quality_meaning="Text block offset",
        owner_meaning="Text index",
        link_meaning="Unknown"
    ),
    # Unknown trap types (0x191-0x19F)
    0x191: TrapInfo("unknown_0x191", "Unknown trap function", "", "", ""),
    0x192: TrapInfo("unknown_0x192", "Unknown trap function", "", "", ""),
    0x193: TrapInfo("unknown_0x193", "Unknown trap function", "", "", ""),
    0x194: TrapInfo("unknown_0x194", "Unknown trap function", "", "", ""),
    0x195: TrapInfo("unknown_0x195", "Unknown trap function", "", "", ""),
    0x196: TrapInfo("camera_trap", "Camera or view effect", "", "", ""),
    0x197: TrapInfo("platform_trap", "Moving platform", "", "", ""),
    0x198: TrapInfo("unknown_0x198", "Unknown trap function", "", "", ""),
    0x199: TrapInfo("unknown_0x199", "Unknown trap function", "", "", ""),
    0x19A: TrapInfo("unknown_0x19A", "Unknown trap function", "", "", ""),
    0x19B: TrapInfo("unknown_0x19B", "Unknown trap function", "", "", ""),
    0x19C: TrapInfo("unknown_0x19C", "Unknown trap function", "", "", ""),
    0x19D: TrapInfo("unknown_0x19D", "Unknown trap function", "", "", ""),
    0x19E: TrapInfo("unknown_0x19E", "Unknown trap function", "", "", ""),
    0x19F: TrapInfo("unknown_0x19F", "Unknown trap function", "", "", ""),
}

# Trigger types (0x1A0-0x1BF)
TRIGGER_TYPES: Dict[int, TriggerInfo] = {
    0x1A0: TriggerInfo(
        name="move_trigger",
        description="Activates when player enters the tile",
        activation="Player movement into tile",
        quality_meaning="Destination/effect X coordinate",
        owner_meaning="Destination/effect Y coordinate"
    ),
    0x1A1: TriggerInfo(
        name="pick_up_trigger",
        description="Activates when attached object is picked up",
        activation="Picking up object",
        quality_meaning="Unknown",
        owner_meaning="Unknown"
    ),
    0x1A2: TriggerInfo(
        name="use_trigger",
        description="Activates when attached object is used",
        activation="Using/activating object",
        quality_meaning="Unknown",
        owner_meaning="Unknown"
    ),
    0x1A3: TriggerInfo(
        name="look_trigger",
        description="Activates when attached object is examined",
        activation="Looking at/examining object",
        quality_meaning="Unknown",
        owner_meaning="Unknown"
    ),
    0x1A4: TriggerInfo(
        name="step_on_trigger",
        description="Activates when stepped on directly",
        activation="Stepping on object",
        quality_meaning="Unknown",
        owner_meaning="Unknown"
    ),
    0x1A5: TriggerInfo(
        name="open_trigger",
        description="Activates when container is opened",
        activation="Opening container",
        quality_meaning="Unknown",
        owner_meaning="Unknown"
    ),
    0x1A6: TriggerInfo(
        name="unlock_trigger",
        description="Activates when lock is unlocked",
        activation="Unlocking",
        quality_meaning="Unknown",
        owner_meaning="Unknown"
    ),
    0x1A7: TriggerInfo(
        name="timer_trigger",
        description="Activates after time delay",
        activation="Timer expiration",
        quality_meaning="Time value",
        owner_meaning="Unknown"
    ),
    0x1A8: TriggerInfo(
        name="scheduled_trigger",
        description="Activates at specific game time",
        activation="Game clock reaching time",
        quality_meaning="Time value",
        owner_meaning="Unknown"
    ),
    # Unknown trigger types (0x1A9-0x1BF)
    # These appear in the game data but their function is not fully documented
}

# Add unknown triggers
for i in range(0x1A9, 0x1C0):
    TRIGGER_TYPES[i] = TriggerInfo(
        name=f"unknown_0x{i:03X}",
        description="Unknown trigger function",
        activation="Unknown",
        quality_meaning="",
        owner_meaning=""
    )


def is_trap(item_id: int) -> bool:
    """Check if an object ID is a trap."""
    return TRAP_ID_MIN <= item_id <= TRAP_ID_MAX


def is_trigger(item_id: int) -> bool:
    """Check if an object ID is a trigger."""
    return TRIGGER_ID_MIN <= item_id <= TRIGGER_ID_MAX


def get_trap_info(item_id: int) -> Optional[TrapInfo]:
    """Get trap information for an object ID."""
    return TRAP_TYPES.get(item_id)


def get_trigger_info(item_id: int) -> Optional[TriggerInfo]:
    """Get trigger information for an object ID."""
    return TRIGGER_TYPES.get(item_id)


def get_trap_name(item_id: int) -> str:
    """Get the trap type name for an object ID."""
    info = TRAP_TYPES.get(item_id)
    return info.name if info else f"trap_0x{item_id:03X}"


def get_trigger_name(item_id: int) -> str:
    """Get the trigger type name for an object ID."""
    info = TRIGGER_TYPES.get(item_id)
    return info.name if info else f"trigger_0x{item_id:03X}"


def describe_teleport(quality: int, owner: int, z_pos: int, 
                      trap_x: int = -1, trap_y: int = -1, 
                      current_level: int = -1) -> str:
    """
    Describe a teleport trap's destination.
    
    Args:
        quality: Destination X coordinate
        owner: Destination Y coordinate  
        z_pos: Appears to encode destination level (1-9)
        trap_x: Source X coordinate (for detecting same-level vs level change)
        trap_y: Source Y coordinate
        current_level: Current level number (0-indexed)
    
    Returns:
        Human-readable description of the teleport effect
    """
    dest_x, dest_y = quality, owner
    
    # Determine destination level
    # z_pos appears to encode destination level as 1-indexed
    if z_pos > 0 and z_pos <= 9:
        dest_level = z_pos  # 1-indexed level number
    else:
        # If z_pos doesn't indicate level, assume same level
        dest_level = current_level + 1 if current_level >= 0 else 0
    
    # Determine if this is same-level warp or level transition
    is_same_level = (current_level >= 0 and dest_level == current_level + 1)
    
    # Check if coordinates indicate a staircase (small movement)
    # Stairs typically keep you in the same general area (within 5 tiles)
    is_stairs = False
    if trap_x >= 0 and trap_y >= 0:
        dx = abs(dest_x - trap_x)
        dy = abs(dest_y - trap_y)
        is_stairs = (dx <= 5 and dy <= 5)
    
    # Build description
    if is_same_level:
        return f"Warp to ({dest_x}, {dest_y}) [same level]"
    elif is_stairs:
        return f"Stairs to Level {dest_level} at ({dest_x}, {dest_y})"
    else:
        return f"Teleport to Level {dest_level} at ({dest_x}, {dest_y})"


def describe_damage(quality: int) -> str:
    """Describe a damage trap's effect."""
    return f"Deals {quality} damage"


def describe_change_terrain(quality: int, owner: int) -> str:
    """Describe a change terrain trap's effect."""
    new_height = quality & 0xF
    new_type = (quality >> 4) & 0xF
    
    type_names = {
        0: "SOLID",
        1: "OPEN",
        2: "DIAG_SE",
        3: "DIAG_SW", 
        4: "DIAG_NE",
        5: "DIAG_NW",
        6: "SLOPE_N",
        7: "SLOPE_S",
        8: "SLOPE_E",
        9: "SLOPE_W",
    }
    
    type_name = type_names.get(new_type, f"type_{new_type}")
    texture_info = "" if owner == 63 else f", texture={owner}"
    
    return f"Changes to {type_name} height={new_height}{texture_info}"


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


def _get_direction_name(direction: int) -> str:
    """Get compass direction name from direction value (0-7).
    
    Values > 7 are modulo 8 to get valid direction.
    """
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return directions[direction % 8]


# Known game variables and their meanings
# These are internal state flags used by the game engine
# Variable IDs are stored in the 'owner' field of set/check variable traps
GAME_VARIABLES = {
    0: "puzzle_state",      # General puzzle/mechanism state
    6: "door_unlocked",     # Door unlock state (Level 3 mine area)
    7: "lever_activated",   # Lever/switch activation flag
    26: "quest_progress",   # Quest progress flag (Level 5)
}


def _get_variable_name(var_id: int) -> str:
    """Get descriptive name for a game variable."""
    if var_id in GAME_VARIABLES:
        return GAME_VARIABLES[var_id]
    return f"var_{var_id}"


def _find_door_for_lock(level_objects: dict, lock_index: int, object_names: list = None) -> tuple:
    """Find the door that links to a given lock object.
    
    Returns (door_obj, door_name) or (None, None) if not found.
    """
    if not level_objects or lock_index <= 0:
        return None, None
    
    # Search all objects for a door (0x140-0x14F) that links to this lock
    for idx, obj in level_objects.items():
        if 0x140 <= obj.item_id <= 0x14F:
            # Doors link to locks via quantity_or_link when is_quantity=False
            if not obj.is_quantity and obj.quantity_or_link == lock_index:
                door_name = "door"
                if object_names and obj.item_id < len(object_names):
                    door_name = _clean_object_name(object_names[obj.item_id])
                return obj, door_name
    
    return None, None


def describe_trap_effect(trap_id: int, quality: int, owner: int, z_pos: int = 0,
                         trap_x: int = -1, trap_y: int = -1,
                         current_level: int = -1,
                         # Optional context for enhanced descriptions
                         is_quantity: bool = False,
                         quantity_or_link: int = 0,
                         level_objects: dict = None,
                         object_names: list = None,
                         trap_messages: list = None,
                         spell_names: list = None) -> str:
    """
    Generate a human-readable description of a trap's effect.
    
    Args:
        trap_id: The trap object ID (0x180-0x19F)
        quality: The trap's quality field
        owner: The trap's owner field
        z_pos: The trap's z_pos field (used by teleports for dest level)
        trap_x: The trap's tile X coordinate
        trap_y: The trap's tile Y coordinate
        current_level: The level the trap is on (0-indexed)
        is_quantity: Whether quantity_or_link is a quantity (True) or link (False)
        quantity_or_link: The trap's quantity/link field
        level_objects: Dict of object index -> GameObject for following links
        object_names: List of object names from STRINGS.PAK block 4
        trap_messages: List of trap messages from STRINGS.PAK block 9
        spell_names: List of spell names from STRINGS.PAK block 6
    
    Returns:
        Human-readable effect description
    """
    # Helper to follow link to get linked object
    def get_linked_object():
        if is_quantity or quantity_or_link <= 0 or not level_objects:
            return None
        return level_objects.get(quantity_or_link)
    
    # Helper to get object name from ID
    def get_obj_name(item_id: int) -> str:
        if object_names and item_id < len(object_names):
            return _clean_object_name(object_names[item_id])
        return f"object #{item_id}"
    
    # Damage trap
    if trap_id == 0x180:
        return describe_damage(quality)
    
    # Teleport trap
    if trap_id == 0x181:
        return describe_teleport(quality, owner, z_pos, trap_x, trap_y, current_level)
    
    # Arrow trap
    if trap_id == 0x182:
        direction = _get_direction_name(owner)
        if quality > 0:
            return f"Fires arrow {direction} (damage ~{quality})"
        return f"Fires arrow {direction}"
    
    # Do trap (executes actions)
    if trap_id == 0x183:
        # quality encodes action type, owner is a parameter
        if quality > 0 or owner > 0:
            return f"Executes action (type={quality}, param={owner})"
        return "Executes action sequence"
    
    # Pit trap
    if trap_id == 0x184:
        return "Opens pit trap"
    
    # Change terrain trap
    if trap_id == 0x185:
        return describe_change_terrain(quality, owner)
    
    # Spell trap
    if trap_id == 0x186:
        direction = _get_direction_name(owner)
        # Try to look up spell name
        if spell_names and quality < len(spell_names) and spell_names[quality]:
            spell_name = spell_names[quality]
            return f"Casts {spell_name} {direction}"
        return f"Casts spell #{quality} {direction}"
    
    # Create object trap
    if trap_id == 0x187:
        linked = get_linked_object()
        if linked:
            obj_name = get_obj_name(linked.item_id)
            return f"Creates {obj_name}"
        return "Creates object"
    
    # Door trap
    if trap_id == 0x188:
        operations = {0: "Closes", 1: "Opens", 2: "Toggles", 3: "Toggles"}
        op = operations.get(quality, "Toggles")
        
        # door_trap links to a lock (0x10F) which is connected to a door
        # We need to find the door that the lock controls
        # Strategy 1: Find door that links to our linked lock object
        linked = get_linked_object()
        if linked and linked.item_id == 0x10F and level_objects:
            # Search for a door that links to this lock index
            for idx, obj in level_objects.items():
                if 0x140 <= obj.item_id <= 0x14F and obj.tile_x > 0:
                    if not obj.is_quantity and obj.quantity_or_link == quantity_or_link:
                        door_name = get_obj_name(obj.item_id)
                        return f"{op} {door_name} at ({obj.tile_x}, {obj.tile_y})"
        
        # Strategy 2: For traps at (0,0), search for nearest door to trigger location
        # (trigger location should be passed as trap_x, trap_y when called from trigger context)
        if trap_x > 0 and trap_y > 0 and level_objects:
            nearest_door = None
            min_distance = 999
            for obj in level_objects.values():
                if 0x140 <= obj.item_id <= 0x14F and obj.tile_x > 0:
                    dx = abs(obj.tile_x - trap_x)
                    dy = abs(obj.tile_y - trap_y)
                    distance = dx + dy
                    if distance < min_distance:
                        min_distance = distance
                        nearest_door = obj
            
            if nearest_door and min_distance <= 15:
                door_name = get_obj_name(nearest_door.item_id)
                return f"{op} {door_name} at ({nearest_door.tile_x}, {nearest_door.tile_y})"
        
        return f"{op} door"
    
    # Ward trap
    if trap_id == 0x189:
        return f"Activates ward (power {quality})"
    
    # Tell trap (message) - uses quality + owner*64 as message index
    if trap_id == 0x18A:
        msg_index = quality + owner * 64
        if trap_messages and msg_index < len(trap_messages) and trap_messages[msg_index]:
            msg = trap_messages[msg_index]
            # Truncate long messages
            if len(msg) > 60:
                msg = msg[:57] + "..."
            return f'Message: "{msg}"'
        return f"Shows message #{msg_index}"
    
    # Delete object trap
    if trap_id == 0x18B:
        # quality=target_x, owner=target_y when is_quantity=True
        # quantity_or_link points to the object to delete
        linked = get_linked_object()
        if linked:
            obj_name = get_obj_name(linked.item_id)
            return f"Removes {obj_name} at ({quality}, {owner})"
        return f"Removes object at ({quality}, {owner})"
    
    # Inventory trap
    if trap_id == 0x18C:
        return f"Modifies inventory (slot {quality})"
    
    # Set variable trap
    if trap_id == 0x18D:
        # owner = variable ID, quality = value to set
        var_name = _get_variable_name(owner)
        return f"Sets {var_name} = {quality}"
    
    # Check variable trap
    if trap_id == 0x18E:
        # owner = variable ID, quality = expected value
        var_name = _get_variable_name(owner)
        return f"Checks {var_name} == {quality}"
    
    # Combination trap
    if trap_id == 0x18F:
        return "Multiple actions"
    
    # Text string trap - uses quality + owner*64 as message index
    if trap_id == 0x190:
        msg_index = quality + owner * 64
        if trap_messages and msg_index < len(trap_messages) and trap_messages[msg_index]:
            msg = trap_messages[msg_index]
            # Truncate long messages
            if len(msg) > 60:
                msg = msg[:57] + "..."
            return f'Message: "{msg}"'
        return f"Shows message #{msg_index}"
    
    # Camera trap
    if trap_id == 0x196:
        return f"Camera effect (param {quality})"
    
    # Platform trap
    if trap_id == 0x197:
        return f"Moving platform"
    
    # Unknown traps
    trap_name = get_trap_name(trap_id)
    return f"Activates {trap_name}"


# Special purpose classifications
class TrapPurpose:
    """High-level purpose of a trap for categorization."""
    DAMAGE = "damage"        # Hurts the player
    TELEPORT = "teleport"    # Moves the player
    TERRAIN = "terrain"      # Changes the map
    OBJECT = "object"        # Creates/modifies objects
    MESSAGE = "message"      # Shows text
    DOOR = "door"           # Operates doors
    VARIABLE = "variable"    # Game state
    SPELL = "spell"         # Casts spells
    UNKNOWN = "unknown"


def get_trap_purpose(item_id: int) -> str:
    """Get the high-level purpose of a trap type."""
    purpose_map = {
        0x180: TrapPurpose.DAMAGE,
        0x181: TrapPurpose.TELEPORT,
        0x182: TrapPurpose.DAMAGE,      # Arrow trap damages
        0x183: TrapPurpose.UNKNOWN,     # do_trap - varies
        0x184: TrapPurpose.DAMAGE,      # Pit trap damages
        0x185: TrapPurpose.TERRAIN,
        0x186: TrapPurpose.SPELL,
        0x187: TrapPurpose.OBJECT,      # create_object
        0x188: TrapPurpose.DOOR,
        0x189: TrapPurpose.SPELL,       # Ward is like a spell
        0x18A: TrapPurpose.MESSAGE,
        0x18B: TrapPurpose.OBJECT,      # delete_object
        0x18C: TrapPurpose.OBJECT,      # inventory
        0x18D: TrapPurpose.VARIABLE,
        0x18E: TrapPurpose.VARIABLE,
        0x18F: TrapPurpose.UNKNOWN,     # combination
        0x190: TrapPurpose.MESSAGE,     # text_string
    }
    return purpose_map.get(item_id, TrapPurpose.UNKNOWN)


# Level transition detection
def is_level_transition_teleport(quality: int, owner: int, 
                                  trap_x: int, trap_y: int,
                                  z_pos: int = -1, current_level: int = -1) -> bool:
    """
    Check if a teleport trap likely represents a level transition (stairs).
    
    Level transitions typically have:
    - Destination coordinates similar to source (same area of map)
    - Small coordinate differences (stairs are adjacent)
    - z_pos field encoding a different level (1-9, 1-indexed)
    """
    # If z_pos indicates a different level, it's likely a level transition
    # z_pos encodes destination level as 1-indexed (1-9)
    if z_pos > 0 and z_pos <= 9 and current_level >= 0:
        dest_level_1idx = z_pos
        current_level_1idx = current_level + 1  # Convert to 1-indexed
        if dest_level_1idx != current_level_1idx:
            # Different level - this is a level transition
            return True
    
    # If destination is same as source, it's likely a level change
    # (the X,Y stay same but level changes)
    if quality == trap_x and owner == trap_y:
        return True
    
    # Small differences might also indicate stairs
    # Stairs typically keep you in the same general area (within 5 tiles)
    # This threshold is more permissive to catch stairs that aren't exactly adjacent
    dx = abs(quality - trap_x)
    dy = abs(owner - trap_y)
    if dx <= 5 and dy <= 5:
        return True
    
    return False

