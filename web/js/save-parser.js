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
 * Build a category lookup map from base game data
 * @param {Object} baseData - The base game data (web_map_data.json)
 * @returns {Map} - Map from object_id to category
 */
function buildCategoryMap(baseData) {
    const categoryMap = new Map();
    
    if (!baseData || !baseData.levels) {
        return categoryMap;
    }
    
    // Scan all base game objects to build category map
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
    
    if (!baseData || !baseData.levels) {
        return nameMap;
    }
    
    // Scan all base game objects to build name map
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
        
        // Get name from base data
        const name = nameMap.get(obj.item_id) || `Object ${obj.item_id}`;
        
        // Determine if this is an NPC
        const isNpc = obj.is_npc && obj.is_mobile;
        
        if (isNpc) {
            // Process as NPC
            npcs.push({
                id: idx,
                object_id: obj.item_id,
                name: name,
                creature_type: name,
                tile_x: obj.tile_x,
                tile_y: obj.tile_y,
                z: obj.z_pos,
                hp: obj.npc_hp,
                level: obj.npc_level,
                attitude: 'unknown',
                has_conversation: obj.npc_whoami > 0,
                conversation_slot: obj.npc_whoami
            });
        } else {
            // Process as regular object
            const category = categoryMap.get(obj.item_id) || 'misc';
            
            const objData = {
                id: idx,
                object_id: obj.item_id,
                name: name,
                tile_x: obj.tile_x,
                tile_y: obj.tile_y,
                z: obj.z_pos,
                category: category,
                is_enchanted: obj.is_enchanted,
                quality: obj.quality,
                owner: obj.owner
            };
            
            // Add quantity if present
            if (obj.is_quantity && obj.quantity_or_link > 0) {
                objData.quantity = obj.quantity_or_link;
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
