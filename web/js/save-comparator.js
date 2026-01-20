/**
 * Save Game Comparator for Ultima Underworld
 * 
 * Compares save game data with base game data to identify changes:
 * - Removed: Objects present in base but missing in save
 * - Added: Objects present in save but missing in base
 * - Moved: Objects with same ID but different position
 * - Modified: Objects with same position but different properties
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
     * Create a unique key for an object for comparison
     * @param {Object} obj - Object dictionary
     * @param {boolean} includePosition - Whether to include position in the key
     * @returns {string} - Key string
     */
    _createObjectKey(obj, includePosition = true) {
        if (includePosition) {
            return `${obj.object_id || 0}_${obj.tile_x || 0}_${obj.tile_y || 0}_${obj.z || 0}`;
        }
        return `${obj.object_id || 0}`;
    }
    
    /**
     * Check if object properties changed
     * @param {Object} baseObj - Base game object
     * @param {Object} saveObj - Save game object
     * @returns {boolean} - True if properties changed
     */
    _objectPropertiesChanged(baseObj, saveObj) {
        const propsToCheck = [
            'quality', 'owner', 'is_enchanted', 'quantity',
            'hp', 'level', 'attitude'  // For NPCs
        ];
        
        for (const prop of propsToCheck) {
            const baseVal = baseObj[prop];
            const saveVal = saveObj[prop];
            if (baseVal !== saveVal) {
                return true;
            }
        }
        
        return false;
    }
    
    /**
     * Check if object position changed significantly
     * @param {Object} baseObj - Base game object
     * @param {Object} saveObj - Save game object
     * @returns {boolean} - True if position changed significantly
     */
    _objectPositionChanged(baseObj, saveObj) {
        const baseX = baseObj.tile_x || 0;
        const baseY = baseObj.tile_y || 0;
        const baseZ = baseObj.z || 0;
        
        const saveX = saveObj.tile_x || 0;
        const saveY = saveObj.tile_y || 0;
        const saveZ = saveObj.z || 0;
        
        // Consider it moved if position changed by more than 1 tile
        return (
            Math.abs(baseX - saveX) > 1 ||
            Math.abs(baseY - saveY) > 1 ||
            Math.abs(baseZ - saveZ) > 10
        );
    }
    
    /**
     * Compare two lists of objects and identify changes
     * @param {number} levelNum - Level number
     * @param {Array} baseList - Base game objects
     * @param {Array} saveList - Save game objects
     * @param {boolean} isNpc - Whether these are NPC objects
     */
    _compareObjectLists(levelNum, baseList, saveList, isNpc = false) {
        // Create maps for efficient lookup
        const baseMap = new Map();
        const saveMap = new Map();
        
        for (const obj of baseList) {
            let key;
            if (isNpc) {
                key = `${obj.object_id || 0}_${obj.id || 0}`;
            } else {
                key = this._createObjectKey(obj, true);
            }
            baseMap.set(key, obj);
        }
        
        for (const obj of saveList) {
            let key;
            if (isNpc) {
                key = `${obj.object_id || 0}_${obj.id || 0}`;
            } else {
                key = this._createObjectKey(obj, true);
            }
            saveMap.set(key, obj);
        }
        
        // Find removed objects (in base but not in save)
        for (const [key, baseObj] of baseMap) {
            if (!saveMap.has(key)) {
                this.changes[levelNum].removed.push({
                    change_type: ChangeType.REMOVED,
                    object_id: baseObj.object_id || 0,
                    level: levelNum,
                    base_data: baseObj,
                    save_data: null,
                    base_index: baseObj.id || 0,
                    save_index: null
                });
            }
        }
        
        // Find added objects (in save but not in base)
        for (const [key, saveObj] of saveMap) {
            if (!baseMap.has(key)) {
                this.changes[levelNum].added.push({
                    change_type: ChangeType.ADDED,
                    object_id: saveObj.object_id || 0,
                    level: levelNum,
                    base_data: null,
                    save_data: saveObj,
                    base_index: null,
                    save_index: saveObj.id || 0
                });
            }
        }
        
        // Find moved/modified objects (in both but different)
        for (const [key, baseObj] of baseMap) {
            if (saveMap.has(key)) {
                const saveObj = saveMap.get(key);
                
                // Check if position changed significantly
                if (this._objectPositionChanged(baseObj, saveObj)) {
                    this.changes[levelNum].moved.push({
                        change_type: ChangeType.MOVED,
                        object_id: baseObj.object_id || 0,
                        level: levelNum,
                        base_data: baseObj,
                        save_data: saveObj,
                        base_index: baseObj.id || 0,
                        save_index: saveObj.id || 0
                    });
                }
                // Check if properties changed
                else if (this._objectPropertiesChanged(baseObj, saveObj)) {
                    this.changes[levelNum].modified.push({
                        change_type: ChangeType.MODIFIED,
                        object_id: baseObj.object_id || 0,
                        level: levelNum,
                        base_data: baseObj,
                        save_data: saveObj,
                        base_index: baseObj.id || 0,
                        save_index: saveObj.id || 0
                    });
                }
                else {
                    // Object unchanged
                    this.changes[levelNum].unchanged.push({
                        change_type: ChangeType.UNCHANGED,
                        object_id: baseObj.object_id || 0,
                        level: levelNum,
                        base_data: baseObj,
                        save_data: saveObj,
                        base_index: baseObj.id || 0,
                        save_index: saveObj.id || 0
                    });
                }
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
                const objId = obj.id || 0;
                
                if (addedMap.has(objId)) {
                    objCopy.change_type = ChangeType.ADDED;
                } else if (movedMap.has(objId)) {
                    objCopy.change_type = ChangeType.MOVED;
                } else if (modifiedMap.has(objId)) {
                    objCopy.change_type = ChangeType.MODIFIED;
                } else {
                    objCopy.change_type = ChangeType.UNCHANGED;
                }
                
                objectsWithChanges.push(objCopy);
            }
            
            // Add change metadata to NPCs
            const npcsWithChanges = [];
            for (const npc of (saveLevel.npcs || [])) {
                const npcCopy = { ...npc };
                const npcId = npc.id || 0;
                
                if (addedMap.has(npcId)) {
                    npcCopy.change_type = ChangeType.ADDED;
                } else if (movedMap.has(npcId)) {
                    npcCopy.change_type = ChangeType.MOVED;
                } else if (modifiedMap.has(npcId)) {
                    npcCopy.change_type = ChangeType.MODIFIED;
                } else {
                    npcCopy.change_type = ChangeType.UNCHANGED;
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
                save_data: c.save_data
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

// Export for use in app.js
window.SaveComparator = {
    SaveGameComparator,
    compareSaveGame,
    ChangeType
};
