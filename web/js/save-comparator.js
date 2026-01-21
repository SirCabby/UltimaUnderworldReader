/**
 * Save Game Comparator for Ultima Underworld
 * 
 * Compares save game data with base game data to identify changes:
 * - Removed: Objects present in base but missing in save (or replaced by different object)
 * - Added: Objects present in save but missing in base (or new in that slot)
 * - Moved: Objects with same ID that changed position
 * - Modified: Objects with same ID and position but different properties
 * 
 * Ported from Python: src/parsers/save_game_comparator.py
 */

// ============================================================================
// Change Types
// ============================================================================

const ChangeType = {
    REMOVED: 'removed',
    ADDED: 'added',
    MOVED: 'moved',
    MODIFIED: 'modified',
    UNCHANGED: 'unchanged'
};

// Human-readable property names for display
const PropertyDisplayNames = {
    'quality': 'Quality',
    'owner': 'Owner',
    'is_enchanted': 'Enchanted',
    'quantity': 'Quantity',
    'hp': 'HP',
    'level': 'Level',
    'attitude': 'Attitude',
    'tile_x': 'X Position',
    'tile_y': 'Y Position',
    'z': 'Z Position',
    'name': 'Name',
    'object_id': 'Object Type'
};

// ============================================================================
// Comparator Class
// ============================================================================

class SaveGameComparator {
    /**
     * Create a comparator for base and save game data
     * @param {Object} baseData - Base game data in web map format
     * @param {Object} saveData - Save game data in web map format
     */
    constructor(baseData, saveData) {
        this.baseData = baseData;
        this.saveData = saveData;
        this.changes = {};
        
        // Initialize changes structure for each level
        for (let level = 0; level < 9; level++) {
            this.changes[level] = {
                removed: [],
                added: [],
                moved: [],
                modified: [],
                unchanged: []
            };
        }
    }
    
    /**
     * Check if two object IDs represent the same object type (e.g., open/closed door pairs)
     * Returns true if the objects are functionally equivalent states of the same thing
     * @param {number} id1 - First object ID
     * @param {number} id2 - Second object ID
     * @returns {boolean} - True if same object type
     */
    _areSameObjectType(id1, id2) {
        if (id1 === id2) return true;
        
        // Normalize both IDs to their "base" type
        const norm1 = this._normalizeObjectId(id1);
        const norm2 = this._normalizeObjectId(id2);
        
        return norm1 === norm2;
    }
    
    /**
     * Normalize an object ID to its "base" type for comparison
     * This maps open/closed door pairs to the same ID, switch on/off states, etc.
     * @param {number} objId - Object ID
     * @returns {number} - Normalized object ID
     */
    _normalizeObjectId(objId) {
        // Closed doors (0x140-0x145) and open doors (0x148-0x14D) are pairs
        // Map closed door 0x140 -> 0x140, open door 0x148 -> 0x140
        // Closed door 0x141 -> 0x141, open door 0x149 -> 0x141, etc.
        if (objId >= 0x140 && objId <= 0x145) {
            return objId; // Keep closed door ID
        }
        if (objId >= 0x148 && objId <= 0x14D) {
            return objId - 8; // Map open door to closed door ID
        }
        
        // Portcullis: 0x146 (closed) and 0x14E (open)
        if (objId === 0x14E) {
            return 0x146;
        }
        
        // Secret doors: 0x147 (closed) and 0x14F (open)
        if (objId === 0x14F) {
            return 0x147;
        }
        
        // Switches/buttons (0x170-0x17F) come in pairs
        // The activated state is +8 from the deactivated state
        // 0x170-0x177 are deactivated, 0x178-0x17F are activated versions
        // Normalize to the deactivated (lower) ID
        if (objId >= 0x178 && objId <= 0x17F) {
            return objId - 8; // Map activated to deactivated
        }
        if (objId >= 0x170 && objId <= 0x177) {
            return objId; // Already deactivated
        }
        
        return objId;
    }
    
    /**
     * Get a human-readable state name for an object ID
     * Used for doors (open/closed) and switches (on/off)
     * @param {number} objId - Object ID
     * @returns {string} - State name
     */
    _getObjectStateName(objId) {
        // Doors
        if (objId >= 0x140 && objId <= 0x145) return 'Closed';
        if (objId >= 0x148 && objId <= 0x14D) return 'Open';
        if (objId === 0x146) return 'Closed';  // Portcullis
        if (objId === 0x14E) return 'Open';    // Portcullis
        if (objId === 0x147) return 'Closed';  // Secret door
        if (objId === 0x14F) return 'Open';    // Secret door
        
        // Switches - 0x178-0x17F are activated states of 0x170-0x177
        if (objId >= 0x178 && objId <= 0x17F) {
            return 'Activated';
        }
        if (objId >= 0x170 && objId <= 0x177) {
            return 'Deactivated';
        }
        
        return `State 0x${objId.toString(16).toUpperCase()}`;
    }
    
    /**
     * Normalize a property value to handle equivalent representations
     * (undefined, null, 'none', '' are treated as default values)
     * @param {*} value - The value to normalize
     * @param {string} property - The property name (for type-specific defaults)
     * @returns {*} - Normalized value
     */
    _normalizeValue(value, property) {
        // Treat undefined, null, 'none', '' as equivalent to default
        if (value === undefined || value === null || value === 'none' || value === '') {
            // Default values per property type
            switch (property) {
                case 'is_enchanted': return false;
                case 'owner': return 0;
                case 'quality': return 40;  // Default quality is 40 (game sets this on save)
                case 'quantity': return 1; // default quantity is 1
                case 'hp': return 0;
                case 'level': return 0;
                case 'attitude': return null;
                default: return null;
            }
        }
        // Convert boolean-like strings
        if (value === 'false') return false;
        if (value === 'true') return true;
        // Convert numeric strings
        if (typeof value === 'string' && !isNaN(value) && value.trim() !== '') {
            const numVal = Number(value);
            if (!isNaN(numVal)) return numVal;
        }
        return value;
    }
    
    /**
     * Check if a property should be ignored for a specific object type
     * Some objects have properties that change on save but are not meaningful
     * @param {number} objectId - The object ID
     * @param {string} property - The property name
     * @returns {boolean} - True if the property should be ignored
     */
    _shouldIgnoreProperty(objectId, property) {
        // Doors (0x140-0x145 closed, 0x148-0x14D open) - quality is lock/key info, changes on save
        // Portcullises (0x146-0x147 closed, 0x14E-0x14F open) - quality used internally
        if (objectId >= 0x140 && objectId <= 0x14F) {
            if (property === 'quality') return true;
        }
        
        // Secret doors (0x150-0x15F) - quality used internally
        if (objectId >= 0x150 && objectId <= 0x15F) {
            if (property === 'quality') return true;
        }
        
        // Skulls (0x0C3) - quality used internally
        if (objectId === 0x0C3) {
            if (property === 'quality') return true;
        }
        
        // Dials (0x161) - quality used internally
        if (objectId === 0x161) {
            if (property === 'quality') return true;
        }
        
        // Animations (0x1C0-0x1FF) - owner field is used internally and changes on save
        // These include fountains, animated objects, etc.
        if (objectId >= 0x1C0 && objectId <= 0x1FF) {
            if (property === 'owner') return true;
        }
        
        // Triggers (0x1A0-0x1BF) - owner/quality are used for targeting, not ownership
        if (objectId >= 0x1A0 && objectId <= 0x1BF) {
            if (property === 'owner' || property === 'quality') return true;
        }
        
        // Traps (0x180-0x19F) - owner/quality are trap parameters, not ownership
        if (objectId >= 0x180 && objectId <= 0x19F) {
            if (property === 'owner' || property === 'quality') return true;
        }
        
        // Switches (0x170-0x17F) - owner/quality used for linking, not ownership
        if (objectId >= 0x170 && objectId <= 0x17F) {
            if (property === 'owner') return true;
        }
        
        // Texture map objects (0x16E-0x16F) - owner/quality are texture parameters
        if (objectId >= 0x16E && objectId <= 0x16F) {
            if (property === 'owner' || property === 'quality') return true;
        }
        
        return false;
    }
    
    /**
     * Get changed properties between two objects
     * @param {Object} baseObj - Base game object
     * @param {Object} saveObj - Save game object
     * @returns {Array} - Array of {property, from, to} objects describing changes
     */
    _getChangedProperties(baseObj, saveObj) {
        const changes = [];
        const propsToCheck = [
            'quality', 'owner', 'is_enchanted', 'quantity',
            'hp', 'level', 'attitude'  // For NPCs
        ];
        
        // Get the object ID (prefer saveObj since it has the current state)
        const objectId = saveObj.object_id || baseObj.object_id || 0;
        
        for (const prop of propsToCheck) {
            // Skip properties that should be ignored for this object type
            if (this._shouldIgnoreProperty(objectId, prop)) {
                continue;
            }
            
            const baseVal = this._normalizeValue(baseObj[prop], prop);
            const saveVal = this._normalizeValue(saveObj[prop], prop);
            
            // Only report change if normalized values differ
            if (baseVal !== saveVal) {
                changes.push({
                    property: prop,
                    displayName: PropertyDisplayNames[prop] || prop,
                    from: baseObj[prop],  // Keep original values for display
                    to: saveObj[prop]
                });
            }
        }
        
        return changes;
    }
    
    /**
     * Check if object position changed
     * @param {Object} baseObj - Base game object
     * @param {Object} saveObj - Save game object
     * @returns {Object|null} - Position change details or null if unchanged
     */
    _getPositionChange(baseObj, saveObj) {
        const baseX = baseObj.tile_x ?? 0;
        const baseY = baseObj.tile_y ?? 0;
        const baseZ = baseObj.z ?? 0;
        
        const saveX = saveObj.tile_x ?? 0;
        const saveY = saveObj.tile_y ?? 0;
        const saveZ = saveObj.z ?? 0;
        
        // Check if position changed at all
        if (baseX !== saveX || baseY !== saveY || baseZ !== saveZ) {
            return {
                from: { x: baseX, y: baseY, z: baseZ },
                to: { x: saveX, y: saveY, z: saveZ }
            };
        }
        
        return null;
    }
    
    /**
     * Compare two lists of objects and identify changes
     * Uses object index (id) as the primary key for matching
     * @param {number} levelNum - Level number
     * @param {Array} baseList - Base game objects
     * @param {Array} saveList - Save game objects
     * @param {boolean} isNpc - Whether these are NPC objects
     */
    _compareObjectLists(levelNum, baseList, saveList, isNpc = false) {
        // Create maps by object index (id) for efficient lookup
        const baseById = new Map();
        const saveById = new Map();
        
        for (const obj of baseList) {
            const id = obj.id;
            if (id !== undefined && id !== null) {
                baseById.set(id, obj);
            }
        }
        
        for (const obj of saveList) {
            const id = obj.id;
            if (id !== undefined && id !== null) {
                saveById.set(id, obj);
            }
        }
        
        // Process all base objects
        for (const [id, baseObj] of baseById) {
            if (saveById.has(id)) {
                const saveObj = saveById.get(id);
                
                // Check if the object type changed (different item in same slot)
                // Use normalized comparison for paired types (open/closed doors, switch states)
                const baseObjId = baseObj.object_id !== undefined ? baseObj.object_id : 0;
                const saveObjId = saveObj.object_id !== undefined ? saveObj.object_id : 0;
                
                // Debug: log switch/button comparisons
                if ((baseObjId >= 0x170 && baseObjId <= 0x17F) || (saveObjId >= 0x170 && saveObjId <= 0x17F)) {
                    console.log(`Switch comparison: base=0x${baseObjId.toString(16)}, save=0x${saveObjId.toString(16)}, ` +
                                `normalized: ${this._normalizeObjectId(baseObjId).toString(16)} vs ${this._normalizeObjectId(saveObjId).toString(16)}, ` +
                                `same=${this._areSameObjectType(baseObjId, saveObjId)}`);
                }
                
                if (!this._areSameObjectType(baseObjId, saveObjId)) {
                    // Object was replaced with a different type - treat as removed + added
                    this.changes[levelNum].removed.push({
                        change_type: ChangeType.REMOVED,
                        object_id: baseObj.object_id || 0,
                        level: levelNum,
                        base_data: baseObj,
                        save_data: null,
                        base_index: id,
                        save_index: null,
                        is_npc: isNpc,
                        changed_properties: [{
                            property: 'object_id',
                            displayName: 'Object Type',
                            from: baseObj.object_id,
                            to: saveObj.object_id,
                            description: `Slot now contains different object type`
                        }]
                    });
                    this.changes[levelNum].added.push({
                        change_type: ChangeType.ADDED,
                        object_id: saveObj.object_id || 0,
                        level: levelNum,
                        base_data: null,
                        save_data: saveObj,
                        base_index: null,
                        save_index: id,
                        is_npc: isNpc,
                        changed_properties: [{
                            property: 'object_id',
                            displayName: 'Object Type',
                            from: baseObj.object_id,
                            to: saveObj.object_id,
                            description: `Replaced object in slot`
                        }]
                    });
                    continue;
                }
                
                // Same object type (or paired type like open/closed door)
                // Check for position and property changes
                const positionChange = this._getPositionChange(baseObj, saveObj);
                const propertyChanges = this._getChangedProperties(baseObj, saveObj);
                
                // If object_id changed (e.g., door opened/closed), add that as a state change
                if (baseObj.object_id !== saveObj.object_id) {
                    propertyChanges.push({
                        property: 'state',
                        displayName: 'State',
                        from: this._getObjectStateName(baseObj.object_id),
                        to: this._getObjectStateName(saveObj.object_id)
                    });
                }
                
                if (positionChange) {
                    // Object moved
                    this.changes[levelNum].moved.push({
                        change_type: ChangeType.MOVED,
                        object_id: baseObj.object_id || 0,
                        level: levelNum,
                        base_data: baseObj,
                        save_data: saveObj,
                        base_index: id,
                        save_index: id,
                        is_npc: isNpc,
                        position_change: positionChange,
                        changed_properties: propertyChanges  // May also have property changes
                    });
                } else if (propertyChanges.length > 0) {
                    // Object modified (properties changed but not position)
                    this.changes[levelNum].modified.push({
                        change_type: ChangeType.MODIFIED,
                        object_id: baseObj.object_id || 0,
                        level: levelNum,
                        base_data: baseObj,
                        save_data: saveObj,
                        base_index: id,
                        save_index: id,
                        is_npc: isNpc,
                        changed_properties: propertyChanges
                    });
                } else {
                    // Object unchanged
                    this.changes[levelNum].unchanged.push({
                        change_type: ChangeType.UNCHANGED,
                        object_id: baseObj.object_id || 0,
                        level: levelNum,
                        base_data: baseObj,
                        save_data: saveObj,
                        base_index: id,
                        save_index: id,
                        is_npc: isNpc,
                        changed_properties: []
                    });
                }
            } else {
                // Object removed (exists in base but not in save)
                this.changes[levelNum].removed.push({
                    change_type: ChangeType.REMOVED,
                    object_id: baseObj.object_id || 0,
                    level: levelNum,
                    base_data: baseObj,
                    save_data: null,
                    base_index: id,
                    save_index: null,
                    is_npc: isNpc,
                    changed_properties: []
                });
            }
        }
        
        // Find added objects (in save but not in base)
        for (const [id, saveObj] of saveById) {
            if (!baseById.has(id)) {
                this.changes[levelNum].added.push({
                    change_type: ChangeType.ADDED,
                    object_id: saveObj.object_id || 0,
                    level: levelNum,
                    base_data: null,
                    save_data: saveObj,
                    base_index: null,
                    save_index: id,
                    is_npc: isNpc,
                    changed_properties: []
                });
            }
        }
    }
    
    /**
     * Compare base and save game data to identify changes
     * @returns {Object} - Dictionary mapping level numbers to change lists
     */
    compare() {
        // Get levels from both datasets
        const baseLevels = this.baseData.levels || [];
        const saveLevels = this.saveData.levels || [];
        
        // Create level maps
        const baseLevelMap = {};
        const saveLevelMap = {};
        
        for (let i = 0; i < baseLevels.length; i++) {
            const level = baseLevels[i];
            baseLevelMap[level.level !== undefined ? level.level : i] = level;
        }
        
        for (let i = 0; i < saveLevels.length; i++) {
            const level = saveLevels[i];
            saveLevelMap[level.level !== undefined ? level.level : i] = level;
        }
        
        // Compare each level
        for (let levelNum = 0; levelNum < 9; levelNum++) {
            const baseLevel = baseLevelMap[levelNum] || {};
            const saveLevel = saveLevelMap[levelNum] || {};
            
            const baseObjects = baseLevel.objects || [];
            const baseNpcs = baseLevel.npcs || [];
            const saveObjects = saveLevel.objects || [];
            const saveNpcs = saveLevel.npcs || [];
            
            // Compare objects
            this._compareObjectLists(levelNum, baseObjects, saveObjects, false);
            
            // Compare NPCs
            this._compareObjectLists(levelNum, baseNpcs, saveNpcs, true);
        }
        
        return this.changes;
    }
    
    /**
     * Get a summary of changes across all levels
     * @returns {Object} - Dictionary with counts of each change type
     */
    getChangesSummary() {
        const summary = {
            removed: 0,
            added: 0,
            moved: 0,
            modified: 0,
            unchanged: 0
        };
        
        for (const levelChanges of Object.values(this.changes)) {
            for (const [changeType, changes] of Object.entries(levelChanges)) {
                summary[changeType] += changes.length;
            }
        }
        
        return summary;
    }
    
    /**
     * Apply change metadata to save data objects
     * @returns {Object} - Save data with change metadata added
     */
    applyChangesToSaveData() {
        const result = { ...this.saveData };
        result.levels = [];
        
        for (let levelNum = 0; levelNum < 9; levelNum++) {
            const levelChanges = this.changes[levelNum];
            const saveLevel = this.saveData.levels?.find(l => l.level === levelNum) || {
                level: levelNum,
                objects: [],
                npcs: []
            };
            
            // Create change lookup maps by save_index
            const addedMap = new Map();
            const movedMap = new Map();
            const modifiedMap = new Map();
            
            for (const change of levelChanges.added) {
                if (change.save_index !== null) {
                    addedMap.set(change.save_index, change);
                }
            }
            for (const change of levelChanges.moved) {
                if (change.save_index !== null) {
                    movedMap.set(change.save_index, change);
                }
            }
            for (const change of levelChanges.modified) {
                if (change.save_index !== null) {
                    modifiedMap.set(change.save_index, change);
                }
            }
            
            // Add change metadata to objects
            const objectsWithChanges = [];
            for (const obj of (saveLevel.objects || [])) {
                const objCopy = { ...obj };
                const objId = obj.id;
                
                if (addedMap.has(objId)) {
                    const change = addedMap.get(objId);
                    objCopy.change_type = ChangeType.ADDED;
                    objCopy.changed_properties = change.changed_properties || [];
                } else if (movedMap.has(objId)) {
                    const change = movedMap.get(objId);
                    objCopy.change_type = ChangeType.MOVED;
                    objCopy.position_change = change.position_change;
                    objCopy.changed_properties = change.changed_properties || [];
                    objCopy.base_data = change.base_data;
                } else if (modifiedMap.has(objId)) {
                    const change = modifiedMap.get(objId);
                    objCopy.change_type = ChangeType.MODIFIED;
                    objCopy.changed_properties = change.changed_properties || [];
                    objCopy.base_data = change.base_data;
                } else {
                    objCopy.change_type = ChangeType.UNCHANGED;
                    objCopy.changed_properties = [];
                }
                
                objectsWithChanges.push(objCopy);
            }
            
            // Add change metadata to NPCs
            const npcsWithChanges = [];
            for (const npc of (saveLevel.npcs || [])) {
                const npcCopy = { ...npc };
                const npcId = npc.id;
                
                if (addedMap.has(npcId)) {
                    const change = addedMap.get(npcId);
                    npcCopy.change_type = ChangeType.ADDED;
                    npcCopy.changed_properties = change.changed_properties || [];
                } else if (movedMap.has(npcId)) {
                    const change = movedMap.get(npcId);
                    npcCopy.change_type = ChangeType.MOVED;
                    npcCopy.position_change = change.position_change;
                    npcCopy.changed_properties = change.changed_properties || [];
                    npcCopy.base_data = change.base_data;
                } else if (modifiedMap.has(npcId)) {
                    const change = modifiedMap.get(npcId);
                    npcCopy.change_type = ChangeType.MODIFIED;
                    npcCopy.changed_properties = change.changed_properties || [];
                    npcCopy.base_data = change.base_data;
                } else {
                    npcCopy.change_type = ChangeType.UNCHANGED;
                    npcCopy.changed_properties = [];
                }
                
                npcsWithChanges.push(npcCopy);
            }
            
            result.levels.push({
                level: levelNum,
                name: saveLevel.name || `Level ${levelNum + 1}`,
                objects: objectsWithChanges,
                npcs: npcsWithChanges
            });
        }
        
        return result;
    }
}

/**
 * Compare save game data with base game data
 * @param {Object} baseData - Base game data (web_map_data.json format)
 * @param {Object} saveData - Save game data (from save-parser.js)
 * @returns {Object} - Result with save_data, changes, and summary
 */
function compareSaveGame(baseData, saveData) {
    const comparator = new SaveGameComparator(baseData, saveData);
    const changes = comparator.compare();
    const saveDataWithChanges = comparator.applyChangesToSaveData();
    const summary = comparator.getChangesSummary();
    
    // Format changes for compatibility with existing code
    const formattedChanges = {};
    for (const [level, levelChanges] of Object.entries(changes)) {
        formattedChanges[level] = {};
        for (const [changeType, changeList] of Object.entries(levelChanges)) {
            formattedChanges[level][changeType] = changeList.map(c => ({
                change_type: c.change_type,
                object_id: c.object_id,
                level: c.level,
                base_data: c.base_data,
                save_data: c.save_data,
                is_npc: c.is_npc,
                changed_properties: c.changed_properties || [],
                position_change: c.position_change || null
            }));
        }
    }
    
    return {
        success: true,
        save_data: saveDataWithChanges,
        changes: formattedChanges,
        summary: summary
    };
}

/**
 * Format a change description for display
 * @param {Object} item - Item with change_type and changed_properties
 * @returns {string} - Human-readable change description
 */
function formatChangeDescription(item) {
    if (!item || !item.change_type) {
        return '';
    }
    
    switch (item.change_type) {
        case ChangeType.ADDED:
            return 'New object (not in base game)';
        case ChangeType.REMOVED:
            return 'Removed (was in base game)';
        case ChangeType.MOVED:
            if (item.position_change) {
                const from = item.position_change.from;
                const to = item.position_change.to;
                let desc = `Moved from (${from.x}, ${from.y}) to (${to.x}, ${to.y})`;
                if (from.z !== to.z) {
                    desc += ` Z: ${from.z} → ${to.z}`;
                }
                return desc;
            }
            return 'Position changed';
        case ChangeType.MODIFIED:
            if (item.changed_properties && item.changed_properties.length > 0) {
                return item.changed_properties.map(p => {
                    const fromVal = p.from !== undefined ? p.from : 'none';
                    const toVal = p.to !== undefined ? p.to : 'none';
                    return `${p.displayName || p.property}: ${fromVal} → ${toVal}`;
                }).join(', ');
            }
            return 'Properties changed';
        case ChangeType.UNCHANGED:
            return 'Unchanged from base game';
        default:
            return '';
    }
}

/**
 * Get a short label for change type
 * @param {string} changeType - The change type
 * @returns {string} - Short label
 */
function getChangeTypeLabel(changeType) {
    switch (changeType) {
        case ChangeType.ADDED: return 'Added';
        case ChangeType.REMOVED: return 'Removed';
        case ChangeType.MOVED: return 'Moved';
        case ChangeType.MODIFIED: return 'Modified';
        case ChangeType.UNCHANGED: return 'Unchanged';
        default: return '';
    }
}

/**
 * Get icon for change type
 * @param {string} changeType - The change type
 * @returns {string} - Emoji icon
 */
function getChangeTypeIcon(changeType) {
    switch (changeType) {
        case ChangeType.ADDED: return '➕';
        case ChangeType.REMOVED: return '➖';
        case ChangeType.MOVED: return '↔️';
        case ChangeType.MODIFIED: return '✏️';
        case ChangeType.UNCHANGED: return '•';
        default: return '';
    }
}

/**
 * Get color for change type
 * @param {string} changeType - The change type
 * @returns {string} - CSS color
 */
function getChangeTypeColor(changeType) {
    switch (changeType) {
        case ChangeType.ADDED: return '#69db7c';     // Green
        case ChangeType.REMOVED: return '#ff4444';   // Red
        case ChangeType.MOVED: return '#ffa94d';     // Orange
        case ChangeType.MODIFIED: return '#748ffc';  // Blue
        case ChangeType.UNCHANGED: return '#868e96'; // Gray
        default: return '#868e96';
    }
}

// Export for use in app.js
window.SaveComparator = {
    SaveGameComparator,
    compareSaveGame,
    formatChangeDescription,
    getChangeTypeLabel,
    getChangeTypeIcon,
    getChangeTypeColor,
    ChangeType,
    PropertyDisplayNames
};
