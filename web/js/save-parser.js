/**
 * Client-side Save Game Parser for Ultima Underworld
 * 
 * Parses lev.ark files directly in the browser using the File API.
 * This enables save game loading on static hosting (GitHub Pages) without a server.
 * 
 * Ported from Python: src/parsers/ark_parser.py and src/parsers/level_parser.py
 */

// ============================================================================
// Constants
// ============================================================================

const SaveParser = {
    // Level data layout constants
    NUM_LEVELS: 9,
    TILEMAP_SIZE: 64,
    TILEMAP_BYTES: 64 * 64 * 4,  // 0x4000
    
    MOBILE_OBJECT_COUNT: 256,
    MOBILE_OBJECT_SIZE: 27,  // 8 + 19 bytes
    
    STATIC_OBJECT_COUNT: 768,
    STATIC_OBJECT_SIZE: 8,
    
    // Offsets within level data block
    OFFSET_TILEMAP: 0x0000,
    OFFSET_MOBILE: 0x4000,
    OFFSET_STATIC: 0x5B00,
    
    // ARK block layout for LEV.ARK
    LEVEL_DATA_START: 0,
    
    // Object ID constants for stairs detection
    MOVE_TRIGGER_ID: 0x1A0,  // 416 - move_trigger
    TELEPORT_TRAP_ID: 0x181, // 385 - teleport_trap
    
    // Tile types
    TileType: {
        SOLID: 0,
        OPEN: 1,
        DIAG_SE: 2,
        DIAG_SW: 3,
        DIAG_NE: 4,
        DIAG_NW: 5,
        SLOPE_N: 6,
        SLOPE_S: 7,
        SLOPE_E: 8,
        SLOPE_W: 9
    },
    
    // NPC attitude values (0=hostile, 1=upset, 2=mellow, 3=friendly)
    NPC_ATTITUDES: {
        0: 'hostile',
        1: 'upset',
        2: 'mellow',
        3: 'friendly'
    }
};

// ============================================================================
// ARK Container Parsing
// ============================================================================

/**
 * Parse an ARK container file to extract block data
 * @param {ArrayBuffer} buffer - The raw file data
 * @returns {Object} - Block data indexed by block number
 */
function parseArkContainer(buffer) {
    const view = new DataView(buffer);
    
    // Read number of blocks (first 2 bytes, little-endian)
    const numBlocks = view.getUint16(0, true);
    
    // Read block offset table
    const offsets = [];
    for (let i = 0; i < numBlocks; i++) {
        const offset = view.getUint32(2 + i * 4, true);
        offsets.push(offset);
    }
    
    // Get list of (index, offset) pairs for non-empty blocks, sorted by offset
    const nonEmpty = offsets
        .map((offset, index) => ({ index, offset }))
        .filter(item => item.offset !== 0)
        .sort((a, b) => a.offset - b.offset);
    
    // Calculate block sizes and extract data
    const blocks = {};
    
    for (let i = 0; i < nonEmpty.length; i++) {
        const { index: blockIdx, offset } = nonEmpty[i];
        
        // Find the next offset to calculate size
        let nextOffset;
        if (i + 1 < nonEmpty.length) {
            nextOffset = nonEmpty[i + 1].offset;
        } else {
            nextOffset = buffer.byteLength;
        }
        
        const size = nextOffset - offset;
        const data = new Uint8Array(buffer, offset, size);
        
        blocks[blockIdx] = {
            index: blockIdx,
            offset: offset,
            size: size,
            data: data
        };
    }
    
    return {
        numBlocks,
        blocks
    };
}

/**
 * Get level data block from parsed ARK
 * @param {Object} ark - Parsed ARK container
 * @param {number} level - Level number (0-8)
 * @returns {Uint8Array|null} - Level data or null
 */
function getLevelData(ark, level) {
    if (level < 0 || level >= SaveParser.NUM_LEVELS) {
        return null;
    }
    const blockIdx = SaveParser.LEVEL_DATA_START + level;
    return ark.blocks[blockIdx]?.data || null;
}

// ============================================================================
// Level Data Parsing
// ============================================================================

/**
 * Parse the tilemap from level data
 * @param {Uint8Array} data - Level data block
 * @returns {Array} - 64x64 grid of tile objects
 */
function parseTilemap(data) {
    const view = new DataView(data.buffer, data.byteOffset, data.byteLength);
    const tiles = [];
    
    for (let y = 0; y < SaveParser.TILEMAP_SIZE; y++) {
        const row = [];
        for (let x = 0; x < SaveParser.TILEMAP_SIZE; x++) {
            const offset = SaveParser.OFFSET_TILEMAP + (y * SaveParser.TILEMAP_SIZE + x) * 4;
            const word0 = view.getUint16(offset, true);
            const word1 = view.getUint16(offset + 2, true);
            
            row.push({
                x: x,
                y: y,
                tileType: word0 & 0xF,
                floorHeight: (word0 >> 4) & 0xF,
                floorTexture: (word0 >> 10) & 0xF,
                wallTexture: word1 & 0x3F,
                noMagic: Boolean(word0 & 0x4000),
                hasDoor: Boolean(word0 & 0x8000),
                firstObjectIndex: (word1 >> 6) & 0x3FF
            });
        }
        tiles.push(row);
    }
    
    return tiles;
}

/**
 * Parse a single object entry
 * @param {number} index - Object index
 * @param {Uint8Array} data - Level data block
 * @param {number} offset - Offset within data
 * @param {boolean} isMobile - Whether this is a mobile (NPC) object
 * @returns {Object} - Parsed object
 */
function parseObject(index, data, offset, isMobile) {
    const view = new DataView(data.buffer, data.byteOffset, data.byteLength);
    
    // Read the 4 words of general object info
    const word0 = view.getUint16(offset, true);
    const word1 = view.getUint16(offset + 2, true);
    const word2 = view.getUint16(offset + 4, true);
    const word3 = view.getUint16(offset + 6, true);
    
    const itemId = word0 & 0x1FF;
    
    const obj = {
        index: index,
        item_id: itemId,
        flags: (word0 >> 9) & 0xF,
        is_enchanted: Boolean(word0 & 0x1000),
        door_dir: Boolean(word0 & 0x2000),
        is_invisible: Boolean(word0 & 0x4000),
        is_quantity: Boolean(word0 & 0x8000),
        z_pos: word1 & 0x7F,
        heading: (word1 >> 7) & 0x7,
        y_pos: (word1 >> 10) & 0x7,
        x_pos: (word1 >> 13) & 0x7,
        quality: word2 & 0x3F,
        next_index: (word2 >> 6) & 0x3FF,
        owner: word3 & 0x3F,
        quantity_or_link: (word3 >> 6) & 0x3FF,
        is_mobile: isMobile,
        tile_x: 0,
        tile_y: 0,
        // NPC-specific fields
        npc_hp: 0,
        npc_goal: 0,
        npc_gtarg: 0,
        npc_level: 0,
        npc_talkedto: false,
        npc_attitude: 0,
        npc_xhome: 0,
        npc_yhome: 0,
        npc_hunger: 0,
        npc_whoami: 0
    };
    
    // Check if this is an NPC (object IDs 0x40-0x7F)
    obj.is_npc = (itemId >= 0x40 && itemId <= 0x7F);
    
    // Parse mobile object extra info if present
    if (isMobile) {
        const extraOffset = offset + 8;
        
        if (extraOffset + 19 <= data.byteLength) {
            obj.npc_hp = data[extraOffset];
            
            // Word at offset 3-4: goal and gtarg
            const goalWord = view.getUint16(extraOffset + 3, true);
            obj.npc_goal = goalWord & 0xF;
            obj.npc_gtarg = (goalWord >> 4) & 0xFF;
            
            // Word at offset 5-6: level, talkedto, attitude
            const levelWord = view.getUint16(extraOffset + 5, true);
            obj.npc_level = levelWord & 0xF;
            obj.npc_talkedto = Boolean(levelWord & 0x2000);
            obj.npc_attitude = (levelWord >> 14) & 0x3;
            
            // Word at offset 14-15: home coordinates
            const homeWord = view.getUint16(extraOffset + 14, true);
            obj.npc_yhome = (homeWord >> 4) & 0x3F;
            obj.npc_xhome = (homeWord >> 10) & 0x3F;
            
            // Byte at offset 17: hunger
            obj.npc_hunger = data[extraOffset + 17] & 0x7F;
            
            // Byte at offset 18: npc_whoami (conversation slot)
            obj.npc_whoami = data[extraOffset + 18];
        }
    }
    
    return obj;
}

/**
 * Parse all objects from level data
 * @param {Uint8Array} data - Level data block
 * @returns {Object} - Objects indexed by their index
 */
function parseObjects(data) {
    const view = new DataView(data.buffer, data.byteOffset, data.byteLength);
    const objects = {};
    
    // Parse mobile objects (indices 0-255)
    for (let i = 0; i < SaveParser.MOBILE_OBJECT_COUNT; i++) {
        const offset = SaveParser.OFFSET_MOBILE + i * SaveParser.MOBILE_OBJECT_SIZE;
        
        // Check if slot is completely empty (all zeros) before parsing
        const word0 = view.getUint16(offset, true);
        const word1 = view.getUint16(offset + 2, true);
        const word2 = view.getUint16(offset + 4, true);
        const word3 = view.getUint16(offset + 6, true);
        
        if (word0 !== 0 || word1 !== 0 || word2 !== 0 || word3 !== 0) {
            objects[i] = parseObject(i, data, offset, true);
        }
    }
    
    // Parse static objects (indices 256-1023)
    for (let i = 0; i < SaveParser.STATIC_OBJECT_COUNT; i++) {
        const idx = i + 256;
        const offset = SaveParser.OFFSET_STATIC + i * SaveParser.STATIC_OBJECT_SIZE;
        
        // Check if slot is completely empty
        const word0 = view.getUint16(offset, true);
        const word1 = view.getUint16(offset + 2, true);
        const word2 = view.getUint16(offset + 4, true);
        const word3 = view.getUint16(offset + 6, true);
        
        if (word0 !== 0 || word1 !== 0 || word2 !== 0 || word3 !== 0) {
            objects[idx] = parseObject(idx, data, offset, false);
        }
    }
    
    return objects;
}

/**
 * Assign tile coordinates to objects by walking tile chains
 * @param {Array} tiles - 64x64 tile grid
 * @param {Object} objects - Objects indexed by index
 */
function assignTileCoords(tiles, objects) {
    for (let y = 0; y < tiles.length; y++) {
        for (let x = 0; x < tiles[y].length; x++) {
            const tile = tiles[y][x];
            if (tile.firstObjectIndex === 0) {
                continue;
            }
            
            let idx = tile.firstObjectIndex;
            const visited = new Set();
            
            while (idx !== 0 && !visited.has(idx)) {
                visited.add(idx);
                if (objects[idx]) {
                    objects[idx].tile_x = x;
                    objects[idx].tile_y = y;
                    idx = objects[idx].next_index;
                } else {
                    break;
                }
            }
        }
    }
}

/**
 * Parse a single level from level data
 * @param {number} levelNum - Level number
 * @param {Uint8Array} data - Level data block
 * @returns {Object} - Parsed level
 */
function parseLevel(levelNum, data) {
    const tiles = parseTilemap(data);
    const objects = parseObjects(data);
    assignTileCoords(tiles, objects);
    
    return {
        level_num: levelNum,
        tiles: tiles,
        objects: objects
    };
}

// ============================================================================
// Main API
// ============================================================================

/**
 * Parse a lev.ark file and return save game data in web format
 * @param {File} file - The lev.ark file to parse
 * @param {Object} baseData - The base game data (web_map_data.json) for category lookup
 * @returns {Promise<Object>} - Save game data in web map format
 */
async function parseLevArk(file, baseData) {
    const buffer = await file.arrayBuffer();
    const ark = parseArkContainer(buffer);
    
    // Build a lookup map from base data for object categories
    const categoryMap = buildCategoryMap(baseData);
    
    // Parse all levels
    const levels = [];
    
    for (let levelNum = 0; levelNum < SaveParser.NUM_LEVELS; levelNum++) {
        const levelData = getLevelData(ark, levelNum);
        if (!levelData) {
            levels.push({
                level: levelNum,
                name: `Level ${levelNum + 1}`,
                objects: [],
                npcs: []
            });
            continue;
        }
        
        const level = parseLevel(levelNum, levelData);
        
        // Convert to web format
        const webLevel = convertLevelToWebFormat(levelNum, level, categoryMap, baseData);
        levels.push(webLevel);
    }
    
    return { levels };
}

/**
 * Map Python/internal categories to web UI categories
 * This handles cases where object_types has internal category names
 */
const CATEGORY_MAPPING = {
    // Weapons
    'melee_weapon': 'weapons',
    'ranged_weapon': 'weapons',
    // Armor
    'armor': 'armor',
    // Keys & Containers
    'key': 'keys',
    'container': 'containers',
    'static_container': 'storage',
    // Consumables
    'food': 'food',
    'potion': 'potions',
    // Books & Scrolls
    'book': 'readable_scrolls_books',
    'scroll': 'readable_scrolls_books',
    'spell_scroll': 'spell_scrolls',
    // Magic Items
    'rune': 'runes',
    'wand': 'wands',
    // Treasure & Light
    'treasure': 'treasure',
    'light': 'light',
    // Doors
    'door': 'doors_unlocked',
    'door_locked': 'doors_locked',
    'door_unlocked': 'doors_unlocked',
    'open_door': 'doors_unlocked',
    'secret_door': 'secret_doors',
    'portcullis': 'doors_unlocked',
    'portcullis_locked': 'doors_locked',
    'open_portcullis': 'doors_unlocked',
    // Mechanics
    'switch': 'switches',
    'trap': 'traps',
    'trigger': 'triggers',
    // Environment
    'shrine': 'shrines',
    'bridge': 'bridges',
    'boulder': 'boulders',
    'furniture': 'furniture',
    'scenery': 'scenery',
    'useless_item': 'useless_item',
    'animation': 'animations',
    'special_tmap': 'texture_objects',
    'writing': 'writings',
    'gravestone': 'gravestones',
    // Quest items
    'quest': 'quest',
    'talisman': 'quest',
    // Misc
    'misc': 'misc',
    'unknown': 'misc'
};

/**
 * Build a category lookup map from base game data
 * @param {Object} baseData - The base game data (web_map_data.json)
 * @returns {Map} - Map from object_id to category
 */
function buildCategoryMap(baseData) {
    const categoryMap = new Map();
    
    if (!baseData) {
        return categoryMap;
    }
    
    // First, use object_types table if available (complete list of all 512 object types)
    if (baseData.object_types) {
        for (const [idStr, typeInfo] of Object.entries(baseData.object_types)) {
            const objId = parseInt(idStr, 10);
            if (!isNaN(objId) && typeInfo.category) {
                // Map internal category to web category
                const webCategory = CATEGORY_MAPPING[typeInfo.category] || typeInfo.category;
                categoryMap.set(objId, webCategory);
            }
        }
    }
    
    // Fall back to scanning placed objects if object_types is not present
    if (!baseData.levels) {
        return categoryMap;
    }
    
    // Scan all base game objects to build category map (fills any gaps)
    // These already have web categories applied
    for (const level of baseData.levels) {
        if (level.objects) {
            for (const obj of level.objects) {
                if (obj.object_id !== undefined && obj.category) {
                    // Use first occurrence of each object_id's category
                    if (!categoryMap.has(obj.object_id)) {
                        categoryMap.set(obj.object_id, obj.category);
                    }
                }
            }
        }
    }
    
    return categoryMap;
}

/**
 * Build a name lookup map from base game data
 * @param {Object} baseData - The base game data (web_map_data.json)
 * @returns {Map} - Map from object_id to name
 */
function buildNameMap(baseData) {
    const nameMap = new Map();
    
    if (!baseData) {
        return nameMap;
    }
    
    // First, use object_types table if available (complete list of all 512 object types)
    if (baseData.object_types) {
        for (const [idStr, typeInfo] of Object.entries(baseData.object_types)) {
            const objId = parseInt(idStr, 10);
            if (!isNaN(objId) && typeInfo.name) {
                nameMap.set(objId, typeInfo.name);
            }
        }
    }
    
    // Fall back to scanning placed objects if object_types is not present
    if (!baseData.levels) {
        return nameMap;
    }
    
    // Scan all base game objects to build name map (fills any gaps)
    for (const level of baseData.levels) {
        if (level.objects) {
            for (const obj of level.objects) {
                if (obj.object_id !== undefined && obj.name) {
                    if (!nameMap.has(obj.object_id)) {
                        nameMap.set(obj.object_id, obj.name);
                    }
                }
            }
        }
        if (level.npcs) {
            for (const npc of level.npcs) {
                if (npc.object_id !== undefined && npc.creature_type) {
                    if (!nameMap.has(npc.object_id)) {
                        nameMap.set(npc.object_id, npc.creature_type);
                    }
                }
            }
        }
    }
    
    return nameMap;
}

function isDoorObjectId(objId) {
    return objId >= 0x140 && objId <= 0x14F;
}

function doorConditionFromHealth(health) {
    // Door-specific vocabulary (avoid cloth-like terms such as "tattered")
    if (health <= 0) return 'broken';
    if (health <= 13) return 'badly damaged';
    if (health <= 26) return 'damaged';
    return 'undamaged';
}

/**
 * Build door extra_info (lock + health + type) to match base-game export.
 * @param {Object} obj - Parsed object from lev.ark
 * @param {Object} levelObjects - Map of index -> parsed object
 * @param {Map} doorTypeMap - Map of object_id -> door metadata
 * @returns {Object} extra_info object
 */
function buildDoorExtraInfo(obj, levelObjects) {
    const objId = obj.item_id;
    const extra = {};

    extra.is_secret = (objId === 0x147 || objId === 0x14F);
    extra.is_open = ((objId >= 0x148 && objId <= 0x14E) || objId === 0x14F);

    // Doors are locked if they have a non-zero special link (to lock 0x10F) or non-zero owner (template doors)
    const specialLink = (!obj.is_quantity) ? (obj.quantity_or_link || 0) : 0;
    const owner = obj.owner || 0;

    if (specialLink !== 0 || owner !== 0) {
        extra.is_locked = true;

        // Try to decode lock id from linked lock object (0x10F)
        let lockId = undefined;
        let lockQuality = undefined;

        if (specialLink !== 0 && levelObjects && levelObjects[specialLink]) {
            const lockObj = levelObjects[specialLink];
            if (lockObj && lockObj.item_id === 0x10F) {
                const lockQuantity = lockObj.is_quantity ? (lockObj.quantity_or_link || 0) : 0;
                if (lockQuantity >= 512) {
                    lockId = lockQuantity - 512;
                }
                lockQuality = lockObj.quality;
            }
        }

        // Fallback: template doors store lock id in owner field
        if (lockId === undefined && owner !== 0) {
            lockId = owner;
        }

        if (lockId !== undefined) {
            extra.lock_id = lockId;
            extra.lock_type = 'keyed';
        } else {
            extra.lock_type = 'special';
        }

        if (lockQuality !== undefined) {
            extra.is_pickable = (lockQuality === 40);
        } else {
            extra.is_pickable = false;
        }
    } else {
        extra.is_locked = false;
    }

    // Health/type
    // Determine if this door is massive (unbreakable):
    // - object_id 0x145 (door_style_5) is inherently massive regardless of quality
    // - object_id 0x146 (portcullis) is inherently massive regardless of quality
    // - quality==63 on any door type also indicates massive
    const rawQuality = (obj.quality !== undefined) ? obj.quality : 0;
    const isMassiveDoor = (objId === 0x145) || (objId === 0x146) || (rawQuality === 63);
    
    const doorMax = 40;
    const doorHealth = isMassiveDoor ? doorMax : Math.max(0, Math.min(doorMax, rawQuality));
    extra.door_health = doorHealth;
    extra.door_max_health = doorMax;
    extra.door_condition = doorConditionFromHealth(doorHealth);

    // Override condition based on massive determination
    if (isMassiveDoor) {
        extra.door_condition = 'massive';
    } else if (doorHealth === doorMax) {
        extra.door_condition = 'sturdy';
    }

    const statusParts = [];
    statusParts.push(extra.door_condition);
    statusParts.push(extra.is_open ? 'open' : 'closed');
    if (extra.is_locked) statusParts.push('locked');
    if (extra.is_secret) statusParts.push('secret');
    extra.door_status = statusParts.join(', ');

    return extra;
}

/**
 * Check if a teleport trap likely represents a level transition (stairs).
 * 
 * Level transitions typically have:
 * - z_pos field encoding a different level (1-9, 1-indexed)
 * - Destination coordinates similar to source (same area of map)
 * 
 * @param {number} quality - Destination X coordinate (from teleport trap quality field)
 * @param {number} owner - Destination Y coordinate (from teleport trap owner field)
 * @param {number} trapX - Source X coordinate
 * @param {number} trapY - Source Y coordinate
 * @param {number} zPos - z_pos field from teleport trap (encodes destination level 1-9)
 * @param {number} currentLevel - Current level (0-indexed)
 * @returns {boolean} - True if this is a level transition
 */
function isLevelTransitionTeleport(quality, owner, trapX, trapY, zPos, currentLevel) {
    // If z_pos indicates a different level, it's likely a level transition
    // z_pos encodes destination level as 1-indexed (1-9)
    if (zPos > 0 && zPos <= 9 && currentLevel >= 0) {
        const destLevel1Idx = zPos;
        const currentLevel1Idx = currentLevel + 1; // Convert to 1-indexed
        if (destLevel1Idx !== currentLevel1Idx) {
            // Different level - this is a level transition
            return true;
        }
    }
    
    // If destination is same as source, it's likely a level change
    // (the X,Y stay same but level changes)
    if (quality === trapX && owner === trapY) {
        return true;
    }
    
    // Small differences might also indicate stairs
    // Stairs typically keep you in the same general area (within 5 tiles)
    const dx = Math.abs(quality - trapX);
    const dy = Math.abs(owner - trapY);
    if (dx <= 5 && dy <= 5) {
        return true;
    }
    
    return false;
}

/**
 * Check if a move_trigger links to a teleport trap that changes levels (stairs)
 * 
 * @param {Object} obj - The move_trigger object
 * @param {Object} allObjects - All objects in the level, indexed by index
 * @param {number} currentLevel - Current level (0-indexed)
 * @returns {Object|null} - { isStairs: true, destLevel: number } or null if not stairs
 */
function checkForStairs(obj, allObjects, currentLevel) {
    // Only check move_trigger objects
    if (obj.item_id !== SaveParser.MOVE_TRIGGER_ID) {
        return null;
    }
    
    // Get the linked object index from quantity_or_link field
    const linkedIndex = obj.quantity_or_link;
    if (linkedIndex <= 0) {
        return null;
    }
    
    // Look up the linked object
    const linkedObj = allObjects[linkedIndex];
    if (!linkedObj) {
        return null;
    }
    
    // Check if linked object is a teleport trap
    if (linkedObj.item_id !== SaveParser.TELEPORT_TRAP_ID) {
        return null;
    }
    
    // Check if this teleport trap is a level transition
    // Use trigger coordinates for level transition detection
    // (teleport traps at 0,0 are templates, use trigger position instead)
    const trapX = linkedObj.tile_x > 0 ? linkedObj.tile_x : obj.tile_x;
    const trapY = linkedObj.tile_y > 0 ? linkedObj.tile_y : obj.tile_y;
    
    if (isLevelTransitionTeleport(
        linkedObj.quality,
        linkedObj.owner,
        trapX,
        trapY,
        linkedObj.z_pos,
        currentLevel
    )) {
        // This is a stairs - calculate destination level (1-indexed)
        // z_pos encodes destination level (1-indexed: 1-9)
        const destLevel = (linkedObj.z_pos > 0 && linkedObj.z_pos <= 9) 
            ? linkedObj.z_pos 
            : currentLevel + 2; // Fallback
        
        return {
            isStairs: true,
            destLevel: destLevel
        };
    }
    
    return null;
}

/**
 * Build a map of NPC names by their object id (index) for a specific level
 * This allows save game NPCs to inherit their proper names from base data
 * @param {Object} baseData - The base game data (web_map_data.json)
 * @param {number} levelNum - Level number
 * @returns {Map} - Map from NPC id (index) to {name, creature_type}
 */
function buildNpcNameMapForLevel(baseData, levelNum) {
    const npcNameMap = new Map();
    
    if (!baseData || !baseData.levels) {
        return npcNameMap;
    }
    
    // Find the base level
    const baseLevel = baseData.levels.find(l => l.level === levelNum);
    if (!baseLevel || !baseLevel.npcs) {
        return npcNameMap;
    }
    
    // Build map from NPC id to their name and creature_type
    for (const npc of baseLevel.npcs) {
        if (npc.id !== undefined) {
            npcNameMap.set(npc.id, {
                name: npc.name,
                creature_type: npc.creature_type
            });
        }
    }
    
    return npcNameMap;
}

/**
 * Convert a parsed level to web format
 * @param {number} levelNum - Level number
 * @param {Object} level - Parsed level data
 * @param {Map} categoryMap - Object ID to category map
 * @param {Object} baseData - Base game data for name lookup
 * @returns {Object} - Level in web format
 */
function convertLevelToWebFormat(levelNum, level, categoryMap, baseData) {
    const nameMap = buildNameMap(baseData);
    const npcNameMap = buildNpcNameMapForLevel(baseData, levelNum);
    const objects = [];
    const npcs = [];
    
    // Build set of objects that are actually linked to tiles (excluding tile 0,0)
    const linkedObjectIndices = new Set();
    for (let y = 0; y < level.tiles.length; y++) {
        for (let x = 0; x < level.tiles[y].length; x++) {
            // Skip tile (0,0) - typically contains templates
            if (x === 0 && y === 0) {
                continue;
            }
            
            const tile = level.tiles[y][x];
            if (tile.firstObjectIndex === 0) {
                continue;
            }
            
            let idx = tile.firstObjectIndex;
            const visited = new Set();
            
            while (idx !== 0 && !visited.has(idx)) {
                visited.add(idx);
                linkedObjectIndices.add(idx);
                if (level.objects[idx]) {
                    idx = level.objects[idx].next_index;
                } else {
                    break;
                }
            }
        }
    }
    
    // Process all objects
    for (const [idxStr, obj] of Object.entries(level.objects)) {
        const idx = parseInt(idxStr);
        
        // Skip empty objects
        if (obj.item_id === 0) {
            continue;
        }
        
        // Skip objects at origin (0,0) - these are usually templates
        if (obj.tile_x === 0 && obj.tile_y === 0) {
            continue;
        }
        
        // Skip static objects not linked to any tile (uninitialized/free list entries)
        if (!obj.is_mobile && !linkedObjectIndices.has(idx)) {
            continue;
        }
        
        // Get name from base data (type name)
        const typeName = nameMap.get(obj.item_id) || `Object ${obj.item_id}`;
        
        // Determine if this is an NPC
        const isNpc = obj.is_npc && obj.is_mobile;
        
        if (isNpc) {
            // For NPCs, try to get their specific name from base data first (by object id/index)
            // This preserves named NPCs like "Dr. Owl" instead of just showing "Human"
            const baseNpcInfo = npcNameMap.get(idx);
            const npcName = baseNpcInfo ? baseNpcInfo.name : typeName;
            const creatureType = baseNpcInfo ? baseNpcInfo.creature_type : typeName;
            
            // Get attitude name from constants (0=hostile, 1=upset, 2=mellow, 3=friendly)
            const attitudeName = SaveParser.NPC_ATTITUDES[obj.npc_attitude] || `unknown(${obj.npc_attitude})`;
            
            // Process as NPC
            npcs.push({
                id: idx,
                object_id: obj.item_id,
                name: npcName,
                creature_type: creatureType,
                tile_x: obj.tile_x,
                tile_y: obj.tile_y,
                z: obj.z_pos,
                hp: obj.npc_hp,
                level: obj.npc_level,
                attitude: attitudeName,
                has_conversation: obj.npc_whoami > 0,
                conversation_slot: obj.npc_whoami
            });
        } else {
            // Process as regular object
            let category = categoryMap.get(obj.item_id) || 'misc';
            let stairsDestLevel = null;
            
            // Check if this is a move_trigger that links to a level-changing teleport (stairs)
            const stairsInfo = checkForStairs(obj, level.objects, levelNum);
            if (stairsInfo && stairsInfo.isStairs) {
                category = 'stairs';
                stairsDestLevel = stairsInfo.destLevel;
            }
            
            // Quantity handling - must match the Python exporter's logic
            // is_quantity flag means quantity_or_link holds a count
            // Values >= 512 are enchantment data, not real quantities
            const hasQuantity = obj.is_quantity && obj.quantity_or_link > 0 && obj.quantity_or_link < 512;
            
            // Items that always have quantity (gems):
            const QUANTITY_CAPABLE_ITEMS = [
                0x0A2,  // Ruby
                0x0A3,  // Red gem
                0x0A4,  // Small blue gem (tiny blue gem)
                0x0A6,  // Sapphire
                0x0A7,  // Emerald
            ];
            const isQuantityCapable = QUANTITY_CAPABLE_ITEMS.includes(obj.item_id);
            
            // Determine if item is truly enchanted
            // For some items, the is_enchanted flag is set incorrectly when quantity_or_link >= 512
            // Only trust is_enchanted for items that CAN be enchanted (weapons, armor, wands, rings, etc.)
            const ENCHANTABLE_RANGES = [
                [0x000, 0x01F],  // Weapons (melee and ranged)
                [0x020, 0x03F],  // Armor
                [0x098, 0x09B],  // Wands
                [0x0A0, 0x0AF],  // Treasure (can have enchantments)
                [0x130, 0x13F],  // Books and scrolls (spell scrolls)
            ];
            const canBeEnchanted = ENCHANTABLE_RANGES.some(([min, max]) => obj.item_id >= min && obj.item_id <= max);
            const isEnchanted = canBeEnchanted && obj.is_enchanted;
            
            const objData = {
                id: idx,
                object_id: obj.item_id,
                name: typeName,
                tile_x: obj.tile_x,
                tile_y: obj.tile_y,
                z: obj.z_pos,
                category: category,
                is_enchanted: isEnchanted,
                quality: obj.quality,
                owner: obj.owner
            };

            // Doors: add extra_info for lock + health/type/status (matches base export)
            if (isDoorObjectId(obj.item_id)) {
                objData.extra_info = buildDoorExtraInfo(obj, level.objects);
            }
            
            // Add stairs destination level if this is a stairs trigger
            if (category === 'stairs' && stairsDestLevel !== null) {
                objData.stairs_dest_level = stairsDestLevel;
            }
            
            // Add quantity - matching Python exporter's logic
            if (hasQuantity) {
                objData.quantity = obj.quantity_or_link;
            } else if (obj.item_id === 0xA0 || obj.item_id === 0xA1) {
                // Coins always have quantity, default to 1
                objData.quantity = 1;
            } else if (isQuantityCapable) {
                // For quantity-capable items, only use quantity_or_link when is_quantity is true
                // When is_quantity is false, quantity_or_link contains a link value, not a quantity
                // Default to 1 for a single gem
                objData.quantity = 1;
            }
            
            objects.push(objData);
        }
    }
    
    return {
        level: levelNum,
        name: `Level ${levelNum + 1}`,
        objects: objects,
        npcs: npcs
    };
}

/**
 * Find lev.ark file from a list of uploaded files
 * @param {FileList} files - List of uploaded files
 * @returns {File|null} - The lev.ark file or null
 */
function findLevArkFile(files) {
    for (const file of files) {
        // Check the filename (may include path from webkitdirectory)
        const filename = file.name.toLowerCase();
        if (filename === 'lev.ark') {
            return file;
        }
        
        // Also check webkitRelativePath for nested files
        if (file.webkitRelativePath) {
            const pathParts = file.webkitRelativePath.toLowerCase().split('/');
            if (pathParts[pathParts.length - 1] === 'lev.ark') {
                return file;
            }
        }
    }
    return null;
}

/**
 * Extract save folder name from uploaded files
 * @param {FileList} files - List of uploaded files
 * @returns {string} - The save folder name
 */
function extractSaveFolderName(files) {
    for (const file of files) {
        if (file.webkitRelativePath) {
            const pathParts = file.webkitRelativePath.split('/');
            if (pathParts.length > 0) {
                return pathParts[0];
            }
        }
    }
    return 'Save Game';
}

/**
 * Find DESC file from a list of uploaded files
 * The DESC file contains the user-entered save game description/name.
 * @param {FileList} files - List of uploaded files
 * @returns {File|null} - The DESC file or null
 */
function findDescFile(files) {
    for (const file of files) {
        // Check the filename (may include path from webkitdirectory)
        const filename = file.name.toLowerCase();
        if (filename === 'desc') {
            return file;
        }
        
        // Also check webkitRelativePath for nested files
        if (file.webkitRelativePath) {
            const pathParts = file.webkitRelativePath.toLowerCase().split('/');
            if (pathParts[pathParts.length - 1] === 'desc') {
                return file;
            }
        }
    }
    return null;
}

/**
 * Parse DESC file to extract the save game name/description
 * 
 * The DESC file is a simple text file containing the user-entered
 * description for the save slot.
 * 
 * @param {File} file - The DESC file
 * @returns {Promise<string|null>} - The save game name or null on error
 */
async function parseSaveGameName(file) {
    try {
        const text = await file.text();
        
        // Trim whitespace and newlines
        const name = text.trim();
        
        return name || null;
    } catch (error) {
        console.error('Error parsing DESC file:', error);
        return null;
    }
}

// Export for use in app.js
window.SaveParser = {
    parseLevArk,
    findLevArkFile,
    findDescFile,
    parseSaveGameName,
    extractSaveFolderName,
    parseArkContainer,
    buildCategoryMap,
    buildNameMap
};
