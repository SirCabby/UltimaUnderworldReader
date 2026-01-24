/**
 * Ultima Underworld Interactive Map Viewer
 * Main application module
 */

// ============================================================================
// Configuration & Constants
// ============================================================================

const CONFIG = {
    // Map calibration - for our generated 640x640 clean maps
    // The map is exactly 64x64 tiles at 10 pixels each, no borders
    mapArea: {
        offsetX: 0,       // No left offset - map starts at edge
        offsetY: 0,       // No top offset - map starts at edge
        width: 640,       // Full image width (64 tiles * 10px)
        height: 640,      // Full image height (64 tiles * 10px)
        gridSize: 64,     // Game uses 64x64 tile grid
    },
    
    // Zoom settings
    zoom: {
        min: 0.5,
        max: 3,
        step: 0.25,
        default: 1.0,     // Start at 100% since maps are now clean
    },
    
    // Marker settings - sized to fit within 10px tiles
    marker: {
        radius: 3,
        strokeWidth: 1,
    },
    
    // Bridge settings
    bridge: {
        objectId: 356,           // Object ID for bridge (0x164)
        color: '#8B5A2B',        // Wooden brown color (SaddleBrown-like)
        strokeColor: '#5D3A1A',  // Darker brown for border
    },
    
    // Stairs settings
    stairs: {
        downImage: 'images/static/stairs/stairs_down.png',
        upImage: 'images/static/stairs/stairs_up.png',
    },
    
    // Paths
    paths: {
        data: 'data/web_map_data.json',
        maps: 'maps/level{n}.png',  // Using PNG for better quality
    }
};

/**
 * Category groups for organizing categories into sections
 */
const CATEGORY_GROUPS = {
    npcs: ['npcs_named', 'npcs_friendly', 'npcs_hostile'],
    items: ['quest', 'runes', 'weapons', 'armor', 'keys', 'containers', 'spell_scrolls', 'potions', 'wands', 'food', 'treasure', 'light', 'misc', 'books_scrolls', 'useless_item'],
    world: ['stairs', 'shrines', 'secret_doors', 'doors_locked', 'doors_unlocked', 'storage', 'switches', 'traps', 'triggers', 'boulders', 'illusory_walls', 'writings', 'gravestones', 'bridges', 'furniture', 'scenery', 'texture_objects', 'animations']
};

/**
 * Check if an item is a bridge object
 */
function isBridge(item) {
    return item && item.object_id === CONFIG.bridge.objectId;
}

/**
 * Check if an item is a stairs object (move trigger that changes level)
 */
function isStairs(item) {
    return item && item.category === 'stairs';
}

/**
 * Create a stairs icon using the extracted image files
 * Returns a group element with the stairs image
 * 
 * @param {number} x - X coordinate (left edge)
 * @param {number} y - Y coordinate (top edge)
 * @param {number} width - Tile width in pixels
 * @param {number} height - Tile height in pixels
 * @param {string} imagePath - Path to stairs image (up or down)
 */
function createStairsIcon(x, y, width, height, imagePath) {
    const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    
    // Create SVG image element
    const img = document.createElementNS('http://www.w3.org/2000/svg', 'image');
    img.setAttributeNS('http://www.w3.org/1999/xlink', 'href', imagePath);
    img.setAttribute('x', x);
    img.setAttribute('y', y);
    img.setAttribute('width', width);
    img.setAttribute('height', height);
    img.setAttribute('preserveAspectRatio', 'none');
    img.style.imageRendering = 'pixelated';
    
    group.appendChild(img);
    return group;
}

// ============================================================================
// Application State
// ============================================================================

const state = {
    data: null,
    currentLevel: 0,
    zoom: 1.0,  // Will be set from CONFIG on init
    pan: { x: 0, y: 0 },
    isDragging: false,
    dragStart: { x: 0, y: 0 },
    viewLocked: false,  // Lock zoom and pan to prevent changes
    filters: {
        categories: new Set(),  // Active category filters
        search: '',
        enchantedOnly: false,   // Show only enchanted items
        ownedFilter: null,      // null = all, "only" = owned only, "exclude" = exclude owned
        changeTypes: new Set(['added', 'removed', 'moved', 'modified', 'unchanged']),  // Selected change types to show (when save game loaded)
    },
    selectedMarker: null,
    pendingSelection: null,    // For restoring selection after page load
    tooltipHideTimeout: null,  // For delayed tooltip hiding
    isTooltipHovered: false,   // Track if tooltip is being hovered
    collapsedCategories: new Set(),  // Tracks which categories are collapsed in visible objects list
    saveGame: {
        currentSaveName: null,  // null = base game, string = save folder name
        saves: {},              // { folderName: { saveData, changes } }
        baseData: null,         // Original base game data (backup)
    },
};

// ============================================================================
// State Persistence
// ============================================================================

const STORAGE_KEY = 'uw_map_filters';

/**
 * Serialize navigation state to URL hash
 */
function serializeUrlState() {
    const params = new URLSearchParams();
    params.set('level', (state.currentLevel || 0) + 1);
    // Explicitly do NOT save zoom - always reset to default on page load
    // Explicitly do NOT save pan - always reset to center on page load
    // Store selected marker as "id:isNpc" (e.g., "123:true" or "456:false")
    if (state.selectedMarker && state.selectedMarker.dataset) {
        const id = state.selectedMarker.dataset.id;
        const isNpc = state.selectedMarker.dataset.isNpc;
        if (id) {
            params.set('selected', `${id}:${isNpc}`);
        }
    }
    // Ensure pan and zoom are never in the URL (remove them if somehow present)
    params.delete('pan');
    params.delete('zoom');
    return params.toString();
}

/**
 * Update the URL hash with current navigation state
 */
function updateUrlHash() {
    const hash = serializeUrlState();
    history.replaceState(null, '', '#' + hash);
}

/**
 * Save filter preferences to localStorage
 */
function saveFiltersToStorage() {
    const filters = {
        categories: Array.from(state.filters.categories),
        search: state.filters.search,
        enchantedOnly: state.filters.enchantedOnly,
        ownedFilter: state.filters.ownedFilter,
        changeTypes: Array.from(state.filters.changeTypes),
        collapsedCategories: Array.from(state.collapsedCategories),
        viewLocked: state.viewLocked,
        zoom: state.zoom  // Persist zoom level
    };
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(filters));
    } catch (e) {
        console.warn('Failed to save filters to localStorage:', e);
    }
}

/**
 * Load filter preferences from localStorage
 */
function loadFiltersFromStorage() {
    try {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (stored) {
            return JSON.parse(stored);
        }
    } catch (e) {
        console.warn('Failed to load filters from localStorage:', e);
    }
    return null;
}

/**
 * Parse navigation state from URL hash
 */
function parseUrlState() {
    const hash = window.location.hash.slice(1);
    if (!hash) return null;
    
    const params = new URLSearchParams(hash);
    const result = {};
    
    // Parse level (1-9 in URL, 0-8 internally)
    if (params.has('level')) {
        const level = parseInt(params.get('level'), 10);
        if (!isNaN(level) && level >= 1 && level <= 9) {
            result.level = level - 1;
        }
    }
    
    // Don't parse zoom - always reset to default on page load
    // Don't parse pan - always reset to center on page load
    
    // Parse selected marker (format: "id:isNpc")
    if (params.has('selected')) {
        const selectedParts = params.get('selected').split(':');
        if (selectedParts.length === 2) {
            result.selectedId = selectedParts[0];
            result.selectedIsNpc = selectedParts[1];
        }
    }
    
    return Object.keys(result).length > 0 ? result : null;
}

/**
 * Restore state from URL hash and localStorage
 * Call this after data is loaded but before UI is rendered
 */
function restoreState() {
    // Restore filters from localStorage
    const storedFilters = loadFiltersFromStorage();
    if (storedFilters) {
        // Restore categories (validate they exist in data)
        if (storedFilters.categories && Array.isArray(storedFilters.categories)) {
            state.filters.categories.clear();
            
            // Build set of valid category IDs
            const validCategoryIds = new Set();
            if (state.data && state.data.categories) {
                state.data.categories.forEach(cat => {
                    validCategoryIds.add(cat.id);
                });
            }
            // Add special NPC categories
            validCategoryIds.add('npcs_hostile');
            validCategoryIds.add('npcs_friendly');
            validCategoryIds.add('npcs_named');
            
            // Only restore categories that are valid
            storedFilters.categories.forEach(catId => {
                if (validCategoryIds.has(catId)) {
                    state.filters.categories.add(catId);
                }
            });
            
            // If no valid categories were restored, enable all categories as fallback
            if (state.filters.categories.size === 0 && state.data && state.data.categories) {
                state.data.categories.forEach(cat => {
                    state.filters.categories.add(cat.id);
                });
                state.filters.categories.add('npcs_hostile');
                state.filters.categories.add('npcs_friendly');
                state.filters.categories.add('npcs_named');
            }
        }
        
        // Restore search
        if (typeof storedFilters.search === 'string') {
            state.filters.search = storedFilters.search;
        }
        
        // Restore enchanted filter
        if (typeof storedFilters.enchantedOnly === 'boolean') {
            state.filters.enchantedOnly = storedFilters.enchantedOnly;
        }
        
        // Restore owned filter
        if (storedFilters.ownedFilter === null || storedFilters.ownedFilter === 'only' || storedFilters.ownedFilter === 'exclude') {
            state.filters.ownedFilter = storedFilters.ownedFilter;
        }
        
        // Restore change types filter
        if (storedFilters.changeTypes && Array.isArray(storedFilters.changeTypes)) {
            state.filters.changeTypes = new Set(storedFilters.changeTypes);
        }
        
        // Restore collapsed categories (validate they exist)
        if (storedFilters.collapsedCategories && Array.isArray(storedFilters.collapsedCategories)) {
            state.collapsedCategories.clear();
            
            // Build set of valid category IDs for collapsed categories
            const validCategoryIds = new Set();
            if (state.data && state.data.categories) {
                state.data.categories.forEach(cat => {
                    validCategoryIds.add(cat.id);
                });
            }
            validCategoryIds.add('npcs_hostile');
            validCategoryIds.add('npcs_friendly');
            validCategoryIds.add('npcs_named');
            
            storedFilters.collapsedCategories.forEach(catId => {
                if (validCategoryIds.has(catId)) {
                    state.collapsedCategories.add(catId);
                }
            });
        }
        
        // Restore view lock state
        if (typeof storedFilters.viewLocked === 'boolean') {
            state.viewLocked = storedFilters.viewLocked;
        }
        
        // Restore zoom from localStorage if present and valid
        if (typeof storedFilters.zoom === 'number' && 
            !isNaN(storedFilters.zoom) && 
            storedFilters.zoom >= CONFIG.zoom.min && 
            storedFilters.zoom <= CONFIG.zoom.max) {
            state.zoom = storedFilters.zoom;
        }
    }
    
    // Restore navigation from URL hash
    const urlState = parseUrlState();
    if (urlState) {
        if (typeof urlState.level === 'number') {
            state.currentLevel = urlState.level;
        }
        // Zoom is restored from localStorage above, or defaults if not found
        // Always reset pan to center (don't restore pan position)
        state.pan = { x: 0, y: 0 };
        // Store pending selection to restore after markers render
        if (urlState.selectedId) {
            state.pendingSelection = {
                id: String(urlState.selectedId),  // Ensure it's a string for comparison
                isNpc: String(urlState.selectedIsNpc)  // Ensure it's a string for comparison
            };
        }
    } else {
        // No URL state - ensure defaults are set (zoom already restored from localStorage if available)
        if (typeof state.zoom !== 'number' || isNaN(state.zoom)) {
            state.zoom = CONFIG.zoom.default;
        }
        state.pan = { x: 0, y: 0 };
    }
}

/**
 * Restore a pending selection after markers have been rendered
 * Call this after renderMarkers() completes
 */
function restorePendingSelection() {
    if (!state.pendingSelection) {
        // No selection to restore - make sure visible objects pane is shown
        renderVisibleObjectsPane();
        return;
    }
    
    const { id, isNpc } = state.pendingSelection;
    state.pendingSelection = null;
    
    // Normalize values to strings for comparison
    const normalizedId = String(id);
    const normalizedIsNpc = String(isNpc);
    
    // Find the marker with matching id and isNpc
    // Check both regular markers and markers within groups (for stacked markers)
    const markers = document.querySelectorAll('.marker');
    for (const marker of markers) {
        // Normalize dataset values to strings for comparison
        const markerId = String(marker.dataset.id || '');
        const markerIsNpc = String(marker.dataset.isNpc || '');
        
        if (markerId === normalizedId && markerIsNpc === normalizedIsNpc) {
            // Find the item data
            const level = state.data.levels[state.currentLevel];
            if (!level) return;
            
            let item = null;
            let itemIsNpc = normalizedIsNpc === 'true';
            
            if (itemIsNpc) {
                item = level.npcs.find(npc => String(npc.id) === normalizedId);
            } else {
                item = level.objects.find(obj => String(obj.id) === normalizedId);
            }
            
            if (item) {
                // Select the item (reusing existing selection logic)
                selectItem(item, itemIsNpc, marker);
            }
            return;
        }
    }
    
    // Also check for stacked marker groups
    const groups = document.querySelectorAll('.stacked-marker-group');
    for (const group of groups) {
        const markersInGroup = group.querySelectorAll('.marker');
        for (const marker of markersInGroup) {
            const markerId = String(marker.dataset.id || '');
            const markerIsNpc = String(marker.dataset.isNpc || '');
            
            if (markerId === normalizedId && markerIsNpc === normalizedIsNpc) {
                const level = state.data.levels[state.currentLevel];
                if (!level) return;
                
                let item = null;
                let itemIsNpc = normalizedIsNpc === 'true';
                
                if (itemIsNpc) {
                    item = level.npcs.find(npc => String(npc.id) === normalizedId);
                } else {
                    item = level.objects.find(obj => String(obj.id) === normalizedId);
                }
                
                if (item) {
                    selectItem(item, itemIsNpc, group);  // Select the group for stacked markers
                }
                return;
            }
        }
    }
}

/**
 * Apply restored state to UI elements
 * Call this after cacheElements and before rendering
 */
function applyRestoredStateToUI() {
    // Apply search text to input
    if (state.filters.search && elements.searchInput) {
        elements.searchInput.value = state.filters.search;
    }
    
    // Apply enchanted filter checkbox
    if (elements.enchantedFilter) {
        elements.enchantedFilter.checked = state.filters.enchantedOnly;
    }
    
    // Apply owned items filter dropdown state
    updateOwnedItemsFilterUI();
    
    // Apply change types filter checkboxes
    updateChangeTypesFilterUI();

    // Apply zoom level display
    if (elements.zoomLevel) {
        elements.zoomLevel.textContent = `${Math.round(state.zoom * 100)}%`;
    }
    
    // Apply view lock button state
    updateViewLockButton();
}

// ============================================================================
// DOM Elements
// ============================================================================

const elements = {
    mapContainer: null,
    mapWrapper: null,
    mapImage: null,
    markersLayer: null,
    tileHighlight: null,
    levelTabs: null,
    npcFilters: null,
    itemFilters: null,
    worldFilters: null,
    searchInput: null,
    tooltip: null,
    detailsSidebar: null,
    objectDetails: null,
    locationObjects: null,
    loadingOverlay: null,
    zoomLevel: null,
    statObjects: null,
    statVisible: null,
    coordDisplay: null,
    coordValue: null,
    enchantedFilter: null,
    enchantedCount: null,
    ownedItemsFilter: null,
    ownedItemsHeader: null,
    ownedItemsLabel: null,
    ownedItemsDropdown: null,
    changeTypesFilter: null,
    changeTypesDropdown: null,
    changeTypesCheckboxes: {},  // Map of change type to checkbox element
    saveGameInput: null,
    loadSaveBtn: null,
    saveGameSelector: null,
};

// ============================================================================
// Initialization
// ============================================================================

document.addEventListener('DOMContentLoaded', init);

async function init() {
    // Cache DOM elements
    cacheElements();
    
    // Set up event listeners
    setupEventListeners();
    
    // Set up tooltip hover tracking for interactive tooltips
    setupTooltipHoverTracking();
    
    // Load data
    try {
        await loadData();
        
        // Restore state from URL hash and localStorage
        restoreState();
        
        // Apply restored state to UI elements (search input, checkboxes, etc.)
        applyRestoredStateToUI();
        
        // Initialize UI
        renderLevelTabs();
        renderNpcFilters();
        renderItemFilters();
        renderWorldFilters();
        setupOwnedItemsFilter();
        setupChangeTypesFilter();
        updateSaveGameUI();
        
        // Load the restored level (or first level if none saved)
        selectLevel(state.currentLevel, true);
        // Update zoom level display after restoring from localStorage
        if (elements.zoomLevel) {
            elements.zoomLevel.textContent = `${Math.round(state.zoom * 100)}%`;
        }
        updateCategoryCounts();
        
        // Set initial URL hash if not already set
        if (!window.location.hash) {
            updateUrlHash();
        }
        
        // Hide loading overlay
        elements.loadingOverlay.classList.add('hidden');
    } catch (error) {
        console.error('Failed to initialize:', error);
        if (elements.loadingOverlay) {
            elements.loadingOverlay.innerHTML = `
                <p style="color: #ff6b6b;">Error loading data</p>
                <p style="font-size: 0.9rem; color: var(--text-muted);">${error.message}</p>
            `;
        }
    }
}

function cacheElements() {
    elements.mapContainer = document.getElementById('map-container');
    elements.mapWrapper = document.getElementById('map-wrapper');
    elements.mapImage = document.getElementById('map-image');
    elements.markersLayer = document.getElementById('markers-layer');
    elements.tileHighlight = document.getElementById('tile-highlight');
    elements.levelTabs = document.getElementById('level-tabs');
    elements.npcFilters = document.getElementById('npc-filters');
    elements.itemFilters = document.getElementById('item-filters');
    elements.worldFilters = document.getElementById('world-filters');
    elements.searchInput = document.getElementById('search-input');
    elements.tooltip = document.getElementById('tooltip');
    elements.detailsSidebar = document.getElementById('details-sidebar');
    elements.loadingOverlay = document.getElementById('loading-overlay');
    elements.zoomLevel = document.getElementById('zoom-level');
    elements.statObjects = document.getElementById('stat-objects');
    elements.statVisible = document.getElementById('stat-visible');
    elements.coordDisplay = document.getElementById('coord-display');
    elements.coordValue = document.getElementById('coord-value');
    elements.enchantedFilter = document.getElementById('enchanted-filter');
    elements.enchantedCount = document.getElementById('enchanted-count');
    elements.ownedItemsFilter = document.getElementById('owned-items-filter');
    elements.ownedItemsHeader = document.getElementById('owned-items-header');
    elements.ownedItemsLabel = document.getElementById('owned-items-label');
    elements.ownedItemsDropdown = document.getElementById('owned-items-dropdown');
    elements.changeTypesFilter = document.getElementById('change-types-filter');
    elements.changeTypesDropdown = document.getElementById('change-types-dropdown');
    // Change type and owned items checkboxes will be populated after DOM creation
    elements.saveGameInput = document.getElementById('save-game-input');
    elements.loadSaveBtn = document.getElementById('load-save-btn');
    elements.saveGameSelector = document.getElementById('save-game-selector');
}

async function loadData() {
    const response = await fetch(CONFIG.paths.data);
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    state.data = await response.json();
    
    // Validate data structure
    if (!state.data || !state.data.categories || !Array.isArray(state.data.categories)) {
        throw new Error('Invalid data format: missing or invalid categories array');
    }
    
    // Store base data backup
    state.saveGame.baseData = JSON.parse(JSON.stringify(state.data));
    
    // Initialize filters with all categories enabled (will be overridden by restoreState if saved filters exist)
    state.filters.categories.clear();
    state.data.categories.forEach(cat => {
        state.filters.categories.add(cat.id);
    });
    // Also add NPC categories (split by hostility and named status)
    state.filters.categories.add('npcs_hostile');
    state.filters.categories.add('npcs_friendly');
    state.filters.categories.add('npcs_named');
}

// ============================================================================
// Save Game Loading
// ============================================================================

/**
 * Load save game from uploaded directory
 * Uses client-side parsing for static hosting compatibility (GitHub Pages)
 */
async function loadSaveGame(files) {
    if (!files || files.length === 0) {
        alert('Please select a save game directory');
        return;
    }
    
    try {
        // Show loading state
        elements.loadSaveBtn.disabled = true;
        elements.loadSaveBtn.textContent = 'Loading...';
        
        // Check if client-side parser is available
        if (!window.SaveParser || !window.SaveComparator) {
            throw new Error('Save game parser not loaded. Please refresh the page.');
        }
        
        // Find lev.ark file in the uploaded files
        const levArkFile = window.SaveParser.findLevArkFile(files);
        if (!levArkFile) {
            throw new Error('lev.ark file not found in uploaded directory');
        }
        
        // Extract save folder name
        const saveFolderName = window.SaveParser.extractSaveFolderName(files);
        
        // Try to extract save game name from DESC file
        let saveGameName = null;
        const descFile = window.SaveParser.findDescFile(files);
        console.log('Looking for DESC file, found:', descFile ? descFile.name : 'not found');
        if (descFile) {
            saveGameName = await window.SaveParser.parseSaveGameName(descFile);
            console.log('Parsed save game name:', saveGameName);
        }
        
        // Parse the save game using client-side parser
        // Pass the base game data for category and name lookup
        const baseData = state.saveGame.baseData || state.data;
        const saveData = await window.SaveParser.parseLevArk(levArkFile, baseData);
        
        // Compare save game with base game
        const result = window.SaveComparator.compareSaveGame(baseData, saveData);
        
        if (!result.success) {
            throw new Error(result.error || 'Failed to load save game');
        }
        
        // Store save game data in the saves object
        state.saveGame.saves[saveFolderName] = {
            saveData: result.save_data,
            changes: result.changes,
            saveGameName: saveGameName  // Save game name from DESC file (may be null)
        };
        
        // Switch to the newly loaded save
        switchSaveGame(saveFolderName);
        
        // Show success message
        const summary = result.summary;
        console.log('Save game loaded:', summary);
        
    } catch (error) {
        console.error('Error loading save game:', error);
        alert(`Error loading save game: ${error.message}`);
    } finally {
        elements.loadSaveBtn.disabled = false;
        elements.loadSaveBtn.textContent = '📁 Load Save';
    }
}

/**
 * Switch between saves or base game
 * @param {string|null} saveName - Save folder name, or null/empty string for base game
 */
function switchSaveGame(saveName) {
    if (!saveName || saveName === '') {
        // Switch to base game
        if (!state.saveGame.baseData) {
            console.warn('No base data to switch to');
            return;
        }
        
        // Restore base data
        state.data = JSON.parse(JSON.stringify(state.saveGame.baseData));
        state.saveGame.currentSaveName = null;
    } else {
        // Switch to a specific save
        const save = state.saveGame.saves[saveName];
        if (!save) {
            console.warn(`Save "${saveName}" not found`);
            return;
        }
        
        if (!state.saveGame.baseData) {
            console.warn('No base data available');
            return;
        }
        
        // Merge save data into state.data (replace levels with save game levels)
        // Keep categories and metadata from base
        state.data.levels = save.saveData.levels.map(level => ({
            ...level,
            // Preserve secrets from base game if they exist
            secrets: state.saveGame.baseData.levels[level.level]?.secrets || []
        }));
        state.saveGame.currentSaveName = saveName;
    }
    
    // Update UI (this will also reset changesOnly filter if switching to base)
    updateSaveGameUI();
    renderMarkers();
    updateStats();
    updateCategoryCounts();
    refreshVisibleObjectsIfNoSelection();
}

/**
 * Update save game UI elements
 */
function updateSaveGameUI() {
    if (!elements.saveGameSelector) {
        return;
    }
    
    // Clear existing options except "Base Game"
    elements.saveGameSelector.innerHTML = '<option value="">Base Game</option>';
    
    // Add all loaded saves to the dropdown
    const saveNames = Object.keys(state.saveGame.saves).sort();
    for (const saveName of saveNames) {
        const save = state.saveGame.saves[saveName];
        const option = document.createElement('option');
        option.value = saveName;
        // Display save game name from DESC file if available, otherwise folder name
        option.textContent = save.saveGameName || saveName;
        elements.saveGameSelector.appendChild(option);
    }
    
    // Set the selected option based on currentSaveName
    if (state.saveGame.currentSaveName) {
        elements.saveGameSelector.value = state.saveGame.currentSaveName;
        elements.saveGameSelector.classList.add('loaded');
        // Show change types filter when save game is loaded
        if (elements.changeTypesFilter) {
            elements.changeTypesFilter.style.display = '';
        }
    } else {
        elements.saveGameSelector.value = '';
        elements.saveGameSelector.classList.remove('loaded');
        // Hide change types filter when no save game is loaded
        if (elements.changeTypesFilter) {
            elements.changeTypesFilter.style.display = 'none';
        }
        // Reset change types filter state when switching to base game
        state.filters.changeTypes = new Set(['added', 'removed', 'moved', 'modified', 'unchanged']);
        updateChangeTypesFilterUI();
    }
}

/**
 * Get change type for an object
 */
function getObjectChangeType(item) {
    if (!state.saveGame.currentSaveName || !item) {
        return null;
    }
    
    // Get current save
    const currentSave = state.saveGame.saves[state.saveGame.currentSaveName];
    if (!currentSave) {
        return null;
    }
    
    // Check if item has change_type property (from save data)
    if (item.change_type) {
        return item.change_type;
    }
    
    // Check changes metadata
    if (currentSave.changes && currentSave.changes[state.currentLevel]) {
        const levelChanges = currentSave.changes[state.currentLevel];
        
        // Check removed objects
        for (const change of levelChanges.removed || []) {
            if (change.base_data && change.base_data.id === item.id) {
                return 'removed';
            }
        }
    }
    
    return null;
}

/**
 * Check if object should be shown based on change types filter
 */
function shouldShowBasedOnChanges(item) {
    if (!state.saveGame.currentSaveName) {
        return true; // Show all when no save game loaded
    }
    
    const changeType = getObjectChangeType(item);
    if (!changeType) {
        // No change info - treat as unchanged
        return state.filters.changeTypes.has('unchanged');
    }
    
    // Show if the change type is selected in the filter
    return state.filters.changeTypes.has(changeType);
}

// ============================================================================
// Event Listeners
// ============================================================================

function setupEventListeners() {
    // Zoom controls
    document.getElementById('zoom-in').addEventListener('click', () => adjustZoom(CONFIG.zoom.step));
    document.getElementById('zoom-out').addEventListener('click', () => adjustZoom(-CONFIG.zoom.step));
    document.getElementById('zoom-reset').addEventListener('click', resetView);
    document.getElementById('zoom-lock').addEventListener('click', toggleViewLock);
    
    // Mouse wheel zoom
    elements.mapContainer.addEventListener('wheel', handleWheel, { passive: false });
    
    // Pan controls
    elements.mapWrapper.addEventListener('mousedown', handlePanStart);
    document.addEventListener('mousemove', handlePanMove);
    document.addEventListener('mouseup', handlePanEnd);
    
    // Coordinate tracking
    elements.mapContainer.addEventListener('mousemove', handleCoordinateTracking);
    elements.mapContainer.addEventListener('mouseleave', handleCoordinateLeave);
    
    // Search
    elements.searchInput.addEventListener('input', debounce(handleSearch, 200));
    
    // Category toggle buttons
    document.getElementById('select-all-npcs').addEventListener('click', selectAllNpcs);
    document.getElementById('deselect-all-npcs').addEventListener('click', deselectAllNpcs);
    document.getElementById('select-all-items').addEventListener('click', selectAllItems);
    document.getElementById('deselect-all-items').addEventListener('click', deselectAllItems);
    document.getElementById('select-all-world').addEventListener('click', selectAllWorld);
    document.getElementById('deselect-all-world').addEventListener('click', deselectAllWorld);
    
    // Enchanted filter
    elements.enchantedFilter.addEventListener('change', handleEnchantedFilter);
    
    // Owned items filter - setup happens in setupOwnedItemsFilter()
    
    // Change types filter - setup happens in setupChangeTypesFilter()
    
    // Save game controls
    if (elements.loadSaveBtn) {
        elements.loadSaveBtn.addEventListener('click', () => {
            elements.saveGameInput?.click();
        });
    }
    if (elements.saveGameInput) {
        elements.saveGameInput.addEventListener('change', (e) => {
            if (e.target.files && e.target.files.length > 0) {
                loadSaveGame(e.target.files);
            }
        });
    }
    if (elements.saveGameSelector) {
        elements.saveGameSelector.addEventListener('change', (e) => {
            const selectedValue = e.target.value;
            switchSaveGame(selectedValue || null);
        });
    }
    
    // Keyboard shortcuts
    document.addEventListener('keydown', handleKeyboard);
}

function handleEnchantedFilter(e) {
    state.filters.enchantedOnly = e.target.checked;
    renderMarkers();
    updateStats();
    refreshVisibleObjectsIfNoSelection();
    saveFiltersToStorage();
}

/**
 * Handle change type filter checkbox toggle
 */
function handleChangeTypeFilter(changeType, checked) {
    if (checked) {
        state.filters.changeTypes.add(changeType);
    } else {
        state.filters.changeTypes.delete(changeType);
    }
    renderMarkers();
    updateStats();
    refreshVisibleObjectsIfNoSelection();
    saveFiltersToStorage();
}

/**
 * Update the change types filter UI checkboxes
 */
function updateChangeTypesFilterUI() {
    for (const [changeType, checkbox] of Object.entries(elements.changeTypesCheckboxes)) {
        if (checkbox) {
            checkbox.checked = state.filters.changeTypes.has(changeType);
        }
    }
    updateChangeTypesDropdownLabel();
}

/**
 * Update the dropdown label to show current selection
 */
function updateChangeTypesDropdownLabel() {
    const label = document.getElementById('change-types-label');
    if (!label) return;
    
    const selected = Array.from(state.filters.changeTypes);
    const allTypes = ['added', 'removed', 'moved', 'modified', 'unchanged'];
    
    if (selected.length === 0) {
        label.textContent = 'None Selected';
    } else if (selected.length === allTypes.length) {
        label.textContent = 'All Changes';
    } else if (selected.length === 1) {
        label.textContent = selected[0].charAt(0).toUpperCase() + selected[0].slice(1) + ' Only';
    } else {
        // Show count of selected types
        label.textContent = `${selected.length} Types`;
    }
}

/**
 * Setup the owned items filter dropdown
 */
function setupOwnedItemsFilter() {
    const container = elements.ownedItemsDropdown;
    const header = elements.ownedItemsHeader;
    const filterDiv = elements.ownedItemsFilter;
    if (!container || !header || !filterDiv) return;
    
    // Add click handler to toggle dropdown
    header.addEventListener('click', () => {
        container.classList.toggle('collapsed');
        filterDiv.classList.toggle('expanded');
    });
    
    const options = [
        { value: null, label: 'All Items', icon: '📦' },
        { value: 'only', label: 'Owned Only', icon: '🔒' },
        { value: 'exclude', label: 'Exclude Owned', icon: '🔓' }
    ];
    
    options.forEach(option => {
        const div = document.createElement('div');
        div.className = 'owned-item-option';
        div.dataset.value = option.value === null ? 'all' : option.value;
        div.innerHTML = `
            <span class="option-indicator"></span>
            <span class="option-icon">${option.icon}</span>
            <span class="option-label">${option.label}</span>
        `;
        container.appendChild(div);
        
        div.addEventListener('click', (e) => {
            e.stopPropagation();
            selectOwnedFilterOption(option.value);
            // Collapse dropdown after selection
            container.classList.add('collapsed');
            filterDiv.classList.remove('expanded');
        });
    });
    
    // Update initial state
    updateOwnedItemsFilterUI();
}

/**
 * Select an owned filter option
 */
function selectOwnedFilterOption(value) {
    state.filters.ownedFilter = value;
    updateOwnedItemsFilterUI();
    renderMarkers();
    updateStats();
    refreshVisibleObjectsIfNoSelection();
    saveFiltersToStorage();
}

/**
 * Update the owned items filter UI
 */
function updateOwnedItemsFilterUI() {
    if (!elements.ownedItemsFilter || !elements.ownedItemsLabel || !elements.ownedItemsDropdown) return;
    
    // Remove all state classes
    elements.ownedItemsFilter.classList.remove('owned-filter-only', 'owned-filter-exclude');
    
    // Update label and add state class
    if (state.filters.ownedFilter === 'only') {
        elements.ownedItemsLabel.textContent = 'Owned Only';
        elements.ownedItemsFilter.classList.add('owned-filter-only');
    } else if (state.filters.ownedFilter === 'exclude') {
        elements.ownedItemsLabel.textContent = 'Exclude Owned';
        elements.ownedItemsFilter.classList.add('owned-filter-exclude');
    } else {
        elements.ownedItemsLabel.textContent = 'All Items';
    }
    
    // Update selected state on options
    const options = elements.ownedItemsDropdown.querySelectorAll('.owned-item-option');
    options.forEach(opt => {
        const optValue = opt.dataset.value === 'all' ? null : opt.dataset.value;
        if (optValue === state.filters.ownedFilter) {
            opt.classList.add('selected');
        } else {
            opt.classList.remove('selected');
        }
    });
}

/**
 * Setup the change types filter dropdown
 */
function setupChangeTypesFilter() {
    const container = document.getElementById('change-types-dropdown');
    const header = document.getElementById('change-types-header');
    const filterDiv = document.getElementById('change-types-filter');
    if (!container) return;
    
    // Add click handler to toggle dropdown
    if (header) {
        header.addEventListener('click', () => {
            container.classList.toggle('collapsed');
            filterDiv?.classList.toggle('expanded');
        });
    }
    
    const changeTypes = [
        { id: 'added', label: 'Added', icon: '➕', color: '#69db7c' },
        { id: 'removed', label: 'Removed', icon: '➖', color: '#ff4444' },
        { id: 'moved', label: 'Moved', icon: '↔️', color: '#ffa94d' },
        { id: 'modified', label: 'Modified', icon: '✏️', color: '#748ffc' },
        { id: 'unchanged', label: 'Unchanged', icon: '•', color: '#868e96' }
    ];
    
    changeTypes.forEach(type => {
        const label = document.createElement('label');
        label.className = 'change-type-option';
        label.innerHTML = `
            <input type="checkbox" id="change-type-${type.id}" value="${type.id}" checked>
            <span class="change-type-icon" style="color: ${type.color};">${type.icon}</span>
            <span class="change-type-label">${type.label}</span>
        `;
        container.appendChild(label);
        
        const checkbox = label.querySelector('input');
        elements.changeTypesCheckboxes[type.id] = checkbox;
        
        checkbox.addEventListener('change', (e) => {
            handleChangeTypeFilter(type.id, e.target.checked);
        });
    });
    
    // Add quick select buttons
    const quickButtons = document.createElement('div');
    quickButtons.className = 'change-type-quick-btns';
    quickButtons.innerHTML = `
        <button type="button" class="quick-btn" id="select-all-changes">All</button>
        <button type="button" class="quick-btn" id="select-none-changes">None</button>
    `;
    container.appendChild(quickButtons);
    
    document.getElementById('select-all-changes')?.addEventListener('click', () => {
        state.filters.changeTypes = new Set(['added', 'removed', 'moved', 'modified', 'unchanged']);
        updateChangeTypesFilterUI();
        renderMarkers();
        updateStats();
        refreshVisibleObjectsIfNoSelection();
        saveFiltersToStorage();
    });
    
    document.getElementById('select-none-changes')?.addEventListener('click', () => {
        state.filters.changeTypes = new Set();
        updateChangeTypesFilterUI();
        renderMarkers();
        updateStats();
        refreshVisibleObjectsIfNoSelection();
        saveFiltersToStorage();
    });
    
    // Update initial state
    updateChangeTypesFilterUI();
}


function handleWheel(e) {
    if (state.viewLocked) return;
    e.preventDefault();
    const delta = e.deltaY > 0 ? -CONFIG.zoom.step : CONFIG.zoom.step;
    adjustZoom(delta);
}

function handlePanStart(e) {
    if (e.button !== 0) return;
    if (state.viewLocked) return;
    state.isDragging = true;
    state.dragStart = { x: e.clientX - state.pan.x, y: e.clientY - state.pan.y };
    elements.mapWrapper.style.cursor = 'grabbing';
}

function handlePanMove(e) {
    if (!state.isDragging) return;
    state.pan.x = e.clientX - state.dragStart.x;
    state.pan.y = e.clientY - state.dragStart.y;
    updateMapTransform();
}

function handlePanEnd() {
    state.isDragging = false;
    elements.mapWrapper.style.cursor = 'grab';
    updateUrlHash();
}

function handleCoordinateTracking(e) {
    // Get the map wrapper's bounding rect and current transform
    const wrapperRect = elements.mapWrapper.getBoundingClientRect();
    
    // Calculate mouse position relative to the map wrapper (accounting for zoom and pan)
    const mouseX = (e.clientX - wrapperRect.left) / state.zoom;
    const mouseY = (e.clientY - wrapperRect.top) / state.zoom;
    
    // Convert pixel position to tile coordinates
    const pxPerTile = CONFIG.mapArea.width / CONFIG.mapArea.gridSize;
    const tileX = Math.floor((mouseX - CONFIG.mapArea.offsetX) / pxPerTile);
    // Y is flipped: image Y=0 is top, but game Y=0 is south (bottom)
    const tileY = CONFIG.mapArea.gridSize - 1 - Math.floor((mouseY - CONFIG.mapArea.offsetY) / pxPerTile);
    
    // Check if coordinates are within valid range
    if (tileX >= 0 && tileX < CONFIG.mapArea.gridSize && 
        tileY >= 0 && tileY < CONFIG.mapArea.gridSize) {
        elements.coordValue.textContent = `(${tileX}, ${tileY})`;
        elements.coordDisplay.classList.remove('hidden');
        
        // Position the tile highlight
        // Convert tile coordinates back to pixel position for the highlight
        const highlightX = CONFIG.mapArea.offsetX + tileX * pxPerTile;
        // Flip Y back: convert game Y to image Y
        const highlightY = CONFIG.mapArea.offsetY + (CONFIG.mapArea.gridSize - 1 - tileY) * pxPerTile;
        
        elements.tileHighlight.style.left = `${highlightX}px`;
        elements.tileHighlight.style.top = `${highlightY}px`;
        elements.tileHighlight.style.width = `${pxPerTile}px`;
        elements.tileHighlight.style.height = `${pxPerTile}px`;
        elements.tileHighlight.classList.add('visible');
    } else {
        elements.coordValue.textContent = '—';
        elements.coordDisplay.classList.add('hidden');
        elements.tileHighlight.classList.remove('visible');
    }
}

function handleCoordinateLeave() {
    elements.coordValue.textContent = '—';
    elements.coordDisplay.classList.add('hidden');
    elements.tileHighlight.classList.remove('visible');
}

function handleSearch(e) {
    state.filters.search = e.target.value.toLowerCase();
    renderMarkers();
    refreshVisibleObjectsIfNoSelection();
    saveFiltersToStorage();
}

function handleKeyboard(e) {
    // Number keys 1-9 for level selection
    if (e.key >= '1' && e.key <= '9') {
        const level = parseInt(e.key) - 1;
        if (level < 9) selectLevel(level);
    }
    // Escape to clear selection
    if (e.key === 'Escape') {
        clearSelection();
    }
}

// ============================================================================
// Level Selection
// ============================================================================

function renderLevelTabs() {
    elements.levelTabs.innerHTML = '';
    
    for (let i = 0; i < 9; i++) {
        const tab = document.createElement('button');
        tab.className = 'level-tab';
        tab.textContent = i + 1;
        tab.title = state.data.levels[i]?.name || `Level ${i + 1}`;
        tab.addEventListener('click', () => selectLevel(i));
        elements.levelTabs.appendChild(tab);
    }
}

function selectLevel(levelNum, preservePan = false) {
    state.currentLevel = levelNum;
    
    // Update tab states
    document.querySelectorAll('.level-tab').forEach((tab, i) => {
        tab.classList.toggle('active', i === levelNum);
    });
    
    // Load map image
    const mapPath = CONFIG.paths.maps.replace('{n}', levelNum + 1);
    elements.mapImage.src = mapPath;
    
    // Wait a bit for image to load if already cached
    if (elements.mapImage.complete) {
        renderMarkers();
        updateStats();
        updateCategoryCounts();
        restorePendingSelection();
    }
    
    elements.mapImage.onload = () => {
        // Render markers after image loads
        renderMarkers();
        updateStats();
        updateCategoryCounts();
        restorePendingSelection();
    };
    
    // Always reset pan to center (we don't preserve pan position anymore)
    state.pan = { x: 0, y: 0 };
    if (!preservePan) {
        clearSelection();
    }
    updateMapTransform();
    updateUrlHash();
}

// ============================================================================
// Category Filters
// ============================================================================

/**
 * Get category object by ID (includes hardcoded NPC categories)
 */
function getCategoryById(categoryId) {
    // Check hardcoded NPC categories first
    if (categoryId === 'npcs_named') {
        return { id: 'npcs_named', name: 'Named NPCs', color: '#ffd43b' };
    }
    if (categoryId === 'npcs_friendly') {
        return { id: 'npcs_friendly', name: 'Friendly NPCs', color: '#69db7c' };
    }
    if (categoryId === 'npcs_hostile') {
        return { id: 'npcs_hostile', name: 'Hostile NPCs', color: '#ff4444' };
    }
    // Look up in data categories
    if (state.data && state.data.categories) {
        return state.data.categories.find(c => c.id === categoryId);
    }
    return null;
}

function renderNpcFilters() {
    if (!elements.npcFilters) return;
    elements.npcFilters.innerHTML = '';
    
    // Safety check: ensure data is loaded
    if (!state.data || !state.data.categories || !Array.isArray(state.data.categories)) {
        console.error('Cannot render NPC filters: data not loaded');
        return;
    }
    
    // Render NPC categories in specified order: npcs_named, npcs_friendly, npcs_hostile
    CATEGORY_GROUPS.npcs.forEach(categoryId => {
        const cat = getCategoryById(categoryId);
        if (cat) {
            const filter = createCategoryFilter(cat);
            elements.npcFilters.appendChild(filter);
        }
    });
}

function renderItemFilters() {
    if (!elements.itemFilters) return;
    elements.itemFilters.innerHTML = '';
    
    // Safety check: ensure data is loaded
    if (!state.data || !state.data.categories || !Array.isArray(state.data.categories)) {
        console.error('Cannot render Item filters: data not loaded');
        return;
    }
    
    // Render Item categories in specified order
    CATEGORY_GROUPS.items.forEach(categoryId => {
        const cat = getCategoryById(categoryId);
        if (cat) {
            const filter = createCategoryFilter(cat);
            elements.itemFilters.appendChild(filter);
        }
    });
}

function renderWorldFilters() {
    if (!elements.worldFilters) return;
    elements.worldFilters.innerHTML = '';
    
    // Safety check: ensure data is loaded
    if (!state.data || !state.data.categories || !Array.isArray(state.data.categories)) {
        console.error('Cannot render World filters: data not loaded');
        return;
    }
    
    // Render World categories in specified order
    CATEGORY_GROUPS.world.forEach(categoryId => {
        const cat = getCategoryById(categoryId);
        if (cat) {
            const filter = createCategoryFilter(cat);
            elements.worldFilters.appendChild(filter);
        }
    });
}

function createCategoryFilter(cat) {
    const label = document.createElement('label');
    label.className = 'category-filter';
    label.dataset.categoryId = cat.id;
    label.style.setProperty('--category-color', cat.color);
    
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.checked = state.filters.categories.has(cat.id);
    checkbox.addEventListener('change', () => {
        if (checkbox.checked) {
            state.filters.categories.add(cat.id);
        } else {
            state.filters.categories.delete(cat.id);
        }
        renderMarkers();
        updateStats();
        refreshVisibleObjectsIfNoSelection();
        saveFiltersToStorage();
    });
    
    const colorDot = document.createElement('span');
    colorDot.className = 'category-color-dot';
    colorDot.style.backgroundColor = cat.color;
    
    const labelText = document.createElement('span');
    labelText.className = 'category-label';
    labelText.textContent = cat.name;
    
    const countSpan = document.createElement('span');
    countSpan.className = 'category-count';
    countSpan.dataset.categoryId = cat.id;
    countSpan.textContent = '0';
    
    label.appendChild(checkbox);
    label.appendChild(colorDot);
    label.appendChild(labelText);
    label.appendChild(countSpan);
    
    return label;
}

function updateCategoryCounts() {
    const level = state.data.levels[state.currentLevel];
    if (!level) return;
    
    // Count NPCs by category
    let hostileCount = 0;
    let friendlyCount = 0;
    let namedCount = 0;
    
    level.npcs.forEach(npc => {
        const npcCat = getNpcCategory(npc);
        if (npcCat === 'npcs_hostile') hostileCount++;
        else if (npcCat === 'npcs_friendly') friendlyCount++;
        else if (npcCat === 'npcs_named') namedCount++;
    });
    
    // Update NPC category counts
    const hostileCountEl = document.querySelector('.category-count[data-category-id="npcs_hostile"]');
    if (hostileCountEl) hostileCountEl.textContent = hostileCount;
    
    const friendlyCountEl = document.querySelector('.category-count[data-category-id="npcs_friendly"]');
    if (friendlyCountEl) friendlyCountEl.textContent = friendlyCount;
    
    const namedCountEl = document.querySelector('.category-count[data-category-id="npcs_named"]');
    if (namedCountEl) namedCountEl.textContent = namedCount;
    
    // Update illusory walls count
    const illusoryCountEl = document.querySelector('.category-count[data-category-id="illusory_walls"]');
    if (illusoryCountEl && level.secrets) {
        const count = level.secrets.filter(s => s.category === 'illusory_walls').length;
        illusoryCountEl.textContent = count;
    }
    
    // Update secret doors count (from secrets array)
    const secretDoorsCountEl = document.querySelector('.category-count[data-category-id="secret_doors"]');
    if (secretDoorsCountEl && level.secrets) {
        const count = level.secrets.filter(s => s.category === 'secret_doors').length;
        secretDoorsCountEl.textContent = count;
    }
    
    // Update object category counts - including items inside containers and NPC inventories
    const categoryCounts = {};
    
    // Count top-level objects and their contents recursively
    level.objects.forEach(obj => {
        categoryCounts[obj.category] = (categoryCounts[obj.category] || 0) + 1;
        // Count items inside containers
        if (obj.contents && obj.contents.length > 0) {
            countItemsByCategory(obj.contents, categoryCounts);
        }
    });
    
    // Count items in NPC inventories
    level.npcs.forEach(npc => {
        if (npc.inventory && npc.inventory.length > 0) {
            countItemsByCategory(npc.inventory, categoryCounts);
        }
    });
    
    state.data.categories.forEach(cat => {
        // Skip npcs - handled separately; illusory_walls and secret_doors are counted from secrets array
        if (cat.id === 'npcs' || cat.id === 'illusory_walls' || cat.id === 'secret_doors') return;
        
        const countEl = document.querySelector(`.category-count[data-category-id="${cat.id}"]`);
        if (countEl) {
            countEl.textContent = categoryCounts[cat.id] || 0;
        }
    });
    
    // Update enchanted item count
    updateEnchantedCount();
}

/**
 * Recursively count items by category, including nested container contents
 */
function countItemsByCategory(items, categoryCounts) {
    if (!items || items.length === 0) return;
    
    items.forEach(item => {
        categoryCounts[item.category] = (categoryCounts[item.category] || 0) + 1;
        
        // Recursively count nested container contents
        if (item.contents && item.contents.length > 0) {
            countItemsByCategory(item.contents, categoryCounts);
        }
    });
}

/**
 * Count and display the number of enchanted items on the current level
 */
function updateEnchantedCount() {
    const level = state.data.levels[state.currentLevel];
    if (!level || !elements.enchantedCount) return;
    
    let enchantedCount = 0;
    
    // Count enchanted objects
    level.objects.forEach(obj => {
        if (isEnchanted(obj)) enchantedCount++;
    });
    
    // Count NPCs with enchanted items in inventory
    level.npcs.forEach(npc => {
        if (isEnchanted(npc)) enchantedCount++;
    });
    
    elements.enchantedCount.textContent = enchantedCount;
}

function selectAllNpcs() {
    // Add all NPC categories to the filter set
    CATEGORY_GROUPS.npcs.forEach(categoryId => {
        state.filters.categories.add(categoryId);
    });

    // Update NPC category checkboxes
    elements.npcFilters.querySelectorAll('.category-filter input[type="checkbox"]').forEach(cb => {
        cb.checked = true;
    });

    renderMarkers();
    updateStats();
    refreshVisibleObjectsIfNoSelection();
    saveFiltersToStorage();
}

function deselectAllNpcs() {
    // Remove all NPC categories from the filter set
    CATEGORY_GROUPS.npcs.forEach(categoryId => {
        state.filters.categories.delete(categoryId);
    });

    // Update NPC category checkboxes
    elements.npcFilters.querySelectorAll('.category-filter input[type="checkbox"]').forEach(cb => {
        cb.checked = false;
    });

    renderMarkers();
    updateStats();
    refreshVisibleObjectsIfNoSelection();
    saveFiltersToStorage();
}

function selectAllItems() {
    // Add all Item categories to the filter set
    CATEGORY_GROUPS.items.forEach(categoryId => {
        state.filters.categories.add(categoryId);
    });

    // Update Item category checkboxes
    elements.itemFilters.querySelectorAll('.category-filter input[type="checkbox"]').forEach(cb => {
        cb.checked = true;
    });

    renderMarkers();
    updateStats();
    refreshVisibleObjectsIfNoSelection();
    saveFiltersToStorage();
}

function deselectAllItems() {
    // Remove all Item categories from the filter set
    CATEGORY_GROUPS.items.forEach(categoryId => {
        state.filters.categories.delete(categoryId);
    });

    // Update Item category checkboxes
    elements.itemFilters.querySelectorAll('.category-filter input[type="checkbox"]').forEach(cb => {
        cb.checked = false;
    });

    renderMarkers();
    updateStats();
    refreshVisibleObjectsIfNoSelection();
    saveFiltersToStorage();
}

function selectAllWorld() {
    // Add all World categories to the filter set
    CATEGORY_GROUPS.world.forEach(categoryId => {
        state.filters.categories.add(categoryId);
    });

    // Update World category checkboxes
    elements.worldFilters.querySelectorAll('.category-filter input[type="checkbox"]').forEach(cb => {
        cb.checked = true;
    });

    renderMarkers();
    updateStats();
    refreshVisibleObjectsIfNoSelection();
    saveFiltersToStorage();
}

function deselectAllWorld() {
    // Remove all World categories from the filter set
    CATEGORY_GROUPS.world.forEach(categoryId => {
        state.filters.categories.delete(categoryId);
    });

    // Update World category checkboxes
    elements.worldFilters.querySelectorAll('.category-filter input[type="checkbox"]').forEach(cb => {
        cb.checked = false;
    });

    renderMarkers();
    updateStats();
    refreshVisibleObjectsIfNoSelection();
    saveFiltersToStorage();
}


// ============================================================================
// Marker Rendering
// ============================================================================

function renderMarkers() {
    const level = state.data.levels[state.currentLevel];
    if (!level) return;
    
    // Clear existing markers
    elements.markersLayer.innerHTML = '';
    
    // Get image dimensions
    const imgWidth = elements.mapImage.naturalWidth || 800;
    const imgHeight = elements.mapImage.naturalHeight || 500;
    
    // Set SVG viewBox to match image
    elements.markersLayer.setAttribute('viewBox', `0 0 ${imgWidth} ${imgHeight}`);
    
    // Calculate pixels per tile
    const pxPerTileX = CONFIG.mapArea.width / CONFIG.mapArea.gridSize;
    const pxPerTileY = CONFIG.mapArea.height / CONFIG.mapArea.gridSize;
    
    let visibleCount = 0;
    
    // Collect all visible items grouped by tile
    const tileGroups = new Map(); // key: "x,y" -> array of {item, color, isNpc}
    
    // Collect NPCs - show if matching NPC category is selected OR if they carry items matching selected categories
    level.npcs.forEach(npc => {
        const npcCategory = getNpcCategory(npc);
        const npcCategoryMatch = state.filters.categories.has(npcCategory);
        const hasMatchingInventory = hasContentMatchingCategory(npc.inventory);
        
        if ((npcCategoryMatch || hasMatchingInventory) && shouldShowItem(npc) && shouldShowBasedOnChanges(npc)) {
            const key = `${npc.tile_x},${npc.tile_y}`;
            if (!tileGroups.has(key)) {
                tileGroups.set(key, []);
            }
            // Use category-specific colors
            const npcColor = npcCategory === 'npcs_hostile' ? '#ff4444' :
                            npcCategory === 'npcs_named' ? '#ffd43b' : '#69db7c';
            tileGroups.get(key).push({ item: npc, color: npcColor, isNpc: true });
            visibleCount++;
        }
    });
    
    // Collect objects - show if category matches OR if container holds items matching selected categories
    level.objects.forEach(obj => {
        // Skip secret doors that match base secrets (they're shown as secrets, not objects)
        if (isSecretDoorMatchingBaseSecret(obj, level)) {
            return;
        }
        
        const objCategoryMatch = state.filters.categories.has(obj.category);
        const hasMatchingContents = hasContentMatchingCategory(obj.contents);
        
        if ((objCategoryMatch || hasMatchingContents) && shouldShowItem(obj) && shouldShowBasedOnChanges(obj)) {
            const key = `${obj.tile_x},${obj.tile_y}`;
            if (!tileGroups.has(key)) {
                tileGroups.set(key, []);
            }
            tileGroups.get(key).push({ item: obj, color: getCategoryColor(obj.category), isNpc: false });
            visibleCount++;
        }
    });
    
    // Collect removed objects when a save game is loaded and 'removed' filter is active
    if (state.saveGame.currentSaveName && state.filters.changeTypes.has('removed')) {
        const currentSave = state.saveGame.saves[state.saveGame.currentSaveName];
        if (currentSave && currentSave.changes && currentSave.changes[state.currentLevel]) {
            const levelChanges = currentSave.changes[state.currentLevel];
            const removedItems = levelChanges.removed || [];
            
            removedItems.forEach(change => {
                const baseObj = change.base_data;
                if (!baseObj) return;
                
                // Create a display object from the base data with removed marker
                const removedObj = {
                    ...baseObj,
                    change_type: 'removed',
                    changed_properties: change.changed_properties || []
                };
                
                // Check category filter
                const isNpc = change.is_npc;
                let categoryMatch = false;
                
                if (isNpc) {
                    const npcCategory = getNpcCategory(removedObj);
                    categoryMatch = state.filters.categories.has(npcCategory);
                } else {
                    categoryMatch = state.filters.categories.has(removedObj.category);
                }
                
                if (categoryMatch && shouldShowItem(removedObj)) {
                    const key = `${removedObj.tile_x},${removedObj.tile_y}`;
                    if (!tileGroups.has(key)) {
                        tileGroups.set(key, []);
                    }
                    
                    // Use red color for removed items, but slightly faded
                    const color = '#ff4444';
                    if (isNpc) {
                        tileGroups.get(key).push({ item: removedObj, color: color, isNpc: true, isRemoved: true });
                    } else {
                        tileGroups.get(key).push({ item: removedObj, color: color, isNpc: false, isRemoved: true });
                    }
                    visibleCount++;
                }
            });
        }
    }
    
    // Collect secrets (illusory walls and secret doors) - show based on their category
    // Note: Secrets are never "enchanted" in the magical sense, so they're hidden when enchanted filter is on
    // Note: Secrets can never be owned, so they're hidden when owned filter is set to "only"
    // Note: Secrets are static base game data - hide them when change filter excludes 'unchanged'
    const showSecrets = level.secrets && 
                        !state.filters.enchantedOnly && 
                        state.filters.ownedFilter !== 'only' &&
                        // If save game is loaded and change filter is active, only show secrets if 'unchanged' is selected
                        (!state.saveGame || state.filters.changeTypes.has('unchanged'));
    
    if (showSecrets) {
        level.secrets.forEach(secret => {
            // Check if this secret's category is enabled
            if (!state.filters.categories.has(secret.category)) {
                return;
            }
            
            // Apply search filter to secrets
            if (state.filters.search) {
                const desc = (secret.description || '').toLowerCase();
                const type = (secret.type || '').toLowerCase();
                if (!desc.includes(state.filters.search) && !type.includes(state.filters.search)) {
                    return;
                }
            }
            
            const key = `${secret.tile_x},${secret.tile_y}`;
            if (!tileGroups.has(key)) {
                tileGroups.set(key, []);
            }
            
            // Use different colors based on type
            const color = secret.category === 'illusory_walls' ? '#ff00ff' : '#ffd43b';
            
            tileGroups.get(key).push({ 
                item: secret, 
                color: color, 
                isNpc: false, 
                isSecret: true 
            });
            visibleCount++;
        });
    }
    
    // Render markers for each tile group
    tileGroups.forEach((items, key) => {
        const [tileX, tileY] = key.split(',').map(Number);
        
        if (items.length === 1) {
            // Single item - render normally
            const { item, color, isNpc, isSecret } = items[0];
            if (isSecret) {
                const marker = createSecretMarker(item, color, pxPerTileX, pxPerTileY);
                elements.markersLayer.appendChild(marker);
            } else {
                const marker = createMarker(item, color, pxPerTileX, pxPerTileY, isNpc);
                elements.markersLayer.appendChild(marker);
            }
        } else {
            // Multiple items - render with stacking and count indicator
            renderStackedMarkers(items, tileX, tileY, pxPerTileX, pxPerTileY);
        }
    });
    
    elements.statVisible.textContent = visibleCount;
}

/**
 * Render stacked markers for tiles with multiple items
 * Shows a single count badge that replaces individual markers
 * The entire tile area is hoverable for better UX
 * Bridges are rendered as a full-tile background with other items on top
 */
function renderStackedMarkers(items, tileX, tileY, pxPerTileX, pxPerTileY) {
    // Tile boundaries (top-left corner of tile in pixel coordinates)
    const tileLeft = CONFIG.mapArea.offsetX + tileX * pxPerTileX;
    const tileTop = CONFIG.mapArea.offsetY + (CONFIG.mapArea.gridSize - tileY - 1) * pxPerTileY;
    
    // Center of tile
    const centerX = tileLeft + pxPerTileX / 2;
    const centerY = tileTop + pxPerTileY / 2;
    
    // Separate bridges and stairs from other items
    const bridges = items.filter(itemData => isBridge(itemData.item));
    const stairs = items.filter(itemData => isStairs(itemData.item));
    const nonBridgeStairsItems = items.filter(itemData => !isBridge(itemData.item) && !isStairs(itemData.item));
    
    // Create a group for the stacked marker
    const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    group.classList.add('marker-stack');
    if (bridges.length > 0) group.classList.add('has-bridge');
    if (stairs.length > 0) group.classList.add('has-stairs');
    
    // Check for change types in stacked items
    const changeTypes = new Set();
    items.forEach(itemData => {
        const changeType = getObjectChangeType(itemData.item);
        if (changeType && changeType !== 'unchanged') {
            changeTypes.add(changeType);
        }
    });
    // Add change indicator classes (prioritize added > moved > modified > removed)
    if (changeTypes.has('added')) {
        group.classList.add('marker-added');
    } else if (changeTypes.has('moved')) {
        group.classList.add('marker-moved');
    } else if (changeTypes.has('modified')) {
        group.classList.add('marker-modified');
    } else if (changeTypes.has('removed')) {
        group.classList.add('marker-removed');
    }
    
    group.dataset.tileX = tileX;
    group.dataset.tileY = tileY;
    group.dataset.count = items.length;
    
    // Render stairs first as background layer (under bridges if both exist)
    if (stairs.length > 0) {
        // Use first stairs item to determine direction (stairs in same tile should have same direction)
        const firstStairs = stairs[0].item;
        const destLevel = firstStairs.stairs_dest_level; // 1-indexed destination level
        const currentLevel1Idx = state.currentLevel + 1; // Convert to 1-indexed (state.currentLevel is 0-indexed)
        // If destination level is higher number (deeper), use stairs_down, otherwise stairs_up
        // Level 1 is surface (highest), Level 9 is deepest
        const stairsImage = (destLevel > currentLevel1Idx) ? CONFIG.stairs.downImage : CONFIG.stairs.upImage;
        const stairsRect = createStairsIcon(tileLeft, tileTop, pxPerTileX, pxPerTileY, stairsImage);
        stairsRect.classList.add('stairs-rect', 'stairs-background');
        stairsRect.style.pointerEvents = 'none';
        group.appendChild(stairsRect);
    }
    
    // Render bridge(s) next as background layer
    if (bridges.length > 0) {
        const bridgeRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        bridgeRect.setAttribute('x', tileLeft);
        bridgeRect.setAttribute('y', tileTop);
        bridgeRect.setAttribute('width', pxPerTileX);
        bridgeRect.setAttribute('height', pxPerTileY);
        bridgeRect.setAttribute('fill', CONFIG.bridge.color);
        bridgeRect.setAttribute('stroke', CONFIG.bridge.strokeColor);
        bridgeRect.setAttribute('stroke-width', '0.5');
        bridgeRect.classList.add('bridge-rect', 'bridge-background');
        bridgeRect.style.pointerEvents = 'none';
        group.appendChild(bridgeRect);
    }
    
    // Sort non-bridge/stairs items: NPCs first, then by category for consistent ordering
    nonBridgeStairsItems.sort((a, b) => {
        if (a.isNpc !== b.isNpc) return a.isNpc ? -1 : 1;
        return 0;
    });
    
    // Create invisible tile-sized hover area (added after bridge so it captures events)
    const hoverArea = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    hoverArea.setAttribute('x', tileLeft);
    hoverArea.setAttribute('y', tileTop);
    hoverArea.setAttribute('width', pxPerTileX);
    hoverArea.setAttribute('height', pxPerTileY);
    hoverArea.setAttribute('fill', 'transparent');
    hoverArea.classList.add('tile-hover-area');
    
    group.appendChild(hoverArea);
    
    // If there are non-bridge/stairs items, show a count badge for them
    if (nonBridgeStairsItems.length > 0) {
        // Special case: if there's exactly 1 non-bridge item, show it as a normal marker instead of a count badge
        if (nonBridgeStairsItems.length === 1) {
            const singleItem = nonBridgeStairsItems[0];
            const { item, color, isNpc } = singleItem;
            
            // Calculate marker position (center of tile)
            const px = centerX;
            const py = centerY;
            const radius = isNpc ? CONFIG.marker.radius + 0.5 : CONFIG.marker.radius;
            const isNamedNpc = isNpc && hasUniqueName(item);
            
            // Create the marker visual element
            let marker;
            if (isNamedNpc) {
                // Create star-shaped marker for named NPCs
                marker = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                const starPath = createStarPath(px, py, radius * 1.2);
                marker.setAttribute('d', starPath);
                marker.setAttribute('fill', color);
                marker.setAttribute('stroke', '#fff');
                marker.setAttribute('stroke-width', CONFIG.marker.strokeWidth);
                marker.classList.add('marker', 'star-marker');
                marker.style.transformOrigin = `${px}px ${py}px`;
            } else {
                // Create circle marker for regular items/NPCs
                marker = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                marker.setAttribute('cx', px);
                marker.setAttribute('cy', py);
                marker.setAttribute('r', radius);
                marker.setAttribute('fill', color);
                marker.setAttribute('stroke', isNpc ? '#fff' : 'rgba(0,0,0,0.5)');
                marker.setAttribute('stroke-width', CONFIG.marker.strokeWidth);
                marker.classList.add('marker');
            }
            marker.style.pointerEvents = 'none'; // Visual only
            
            // Store item data on marker
            marker.dataset.id = item.id;
            marker.dataset.isNpc = isNpc;
            marker.dataset.tileX = item.tile_x;
            marker.dataset.tileY = item.tile_y;
            marker.dataset.originalRadius = radius;
            marker.dataset.isStarMarker = isNamedNpc;
            marker.dataset.centerX = px;
            marker.dataset.centerY = py;
            
            group.appendChild(marker);
            
            // Set up hover events to show normal tooltip for the single item
            const hoverRadius = Math.min(radius * 1.3, 4);
            hoverArea.addEventListener('mouseenter', (e) => {
                if (!marker.classList.contains('selected')) {
                    if (isNamedNpc) {
                        marker.style.transform = 'scale(1.3)';
                    } else {
                        marker.setAttribute('r', hoverRadius);
                    }
                }
                showTooltip(e, item, isNpc);
            });
            hoverArea.addEventListener('mouseleave', () => {
                if (!marker.classList.contains('selected')) {
                    if (isNamedNpc) {
                        marker.style.transform = 'scale(1)';
                    } else {
                        marker.setAttribute('r', radius);
                    }
                }
                hideTooltip();
            });
            hoverArea.addEventListener('mousemove', (e) => {
                updateTooltipPosition(e);
            });
            hoverArea.addEventListener('click', () => {
                hideTooltip();
                if (singleItem.isSecret) {
                    selectSecret(item);
                } else {
                    selectStackedItem(item, isNpc, tileX, tileY);
                }
            });
        } else {
            // Multiple non-bridge items - show count badge
            const badge = createCountBadge(centerX, centerY, nonBridgeStairsItems.length, tileX, tileY, nonBridgeStairsItems);
            group.appendChild(badge);
            
            // Add hover events for stacked items (count badge)
            hoverArea.addEventListener('mouseenter', (e) => {
                showStackedTooltip(e, items, tileX, tileY);
            });
            hoverArea.addEventListener('mouseleave', () => {
                scheduleHideTooltip();
            });
            hoverArea.addEventListener('mousemove', (e) => {
                updateTooltipPosition(e);
            });
            hoverArea.addEventListener('click', () => {
                hideTooltip();
                // Select the first non-bridge/stairs item if available, otherwise first item
                const firstItem = nonBridgeStairsItems.length > 0 ? nonBridgeStairsItems[0] : items[0];
                if (firstItem.isSecret) {
                    selectSecret(firstItem.item);
                } else {
                    selectStackedItem(firstItem.item, firstItem.isNpc, tileX, tileY);
                }
            });
        }
    } else if (stairs.length > 1) {
        // If only stairs, show count for multiple stairs
        const badge = createCountBadge(centerX, centerY, stairs.length, tileX, tileY, stairs);
        group.appendChild(badge);
        
        // Add hover events for stacked stairs
        hoverArea.addEventListener('mouseenter', (e) => {
            showStackedTooltip(e, items, tileX, tileY);
        });
        hoverArea.addEventListener('mouseleave', () => {
            scheduleHideTooltip();
        });
        hoverArea.addEventListener('mousemove', (e) => {
            updateTooltipPosition(e);
        });
        hoverArea.addEventListener('click', () => {
            hideTooltip();
            selectStackedItem(items[0].item, items[0].isNpc, tileX, tileY);
        });
    } else {
        // Only bridges (single or multiple) and no other items - add hover events for bridges
        hoverArea.addEventListener('mouseenter', (e) => {
            showStackedTooltip(e, items, tileX, tileY);
        });
        hoverArea.addEventListener('mouseleave', () => {
            scheduleHideTooltip();
        });
        hoverArea.addEventListener('mousemove', (e) => {
            updateTooltipPosition(e);
        });
        hoverArea.addEventListener('click', () => {
            hideTooltip();
            selectStackedItem(items[0].item, items[0].isNpc, tileX, tileY);
        });
    }
    // If only bridges (single or multiple) and no other items, the rect is enough (no badge needed)
    
    elements.markersLayer.appendChild(group);
}

/**
 * Create a single marker for stacked display
 */
function createStackedMarker(item, color, px, py, isNpc, isPrimary) {
    const baseRadius = isNpc ? CONFIG.marker.radius + 0.5 : CONFIG.marker.radius;
    // Make non-primary markers slightly smaller
    const radius = isPrimary ? baseRadius : baseRadius * 0.8;
    
    // Check if this is a named NPC (should use star shape)
    const isNamedNpc = isNpc && hasUniqueName(item);
    
    let marker;
    if (isNamedNpc) {
        // Create star-shaped marker for named NPCs
        marker = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        const starPath = createStarPath(px, py, radius * 1.2);
        marker.setAttribute('d', starPath);
        marker.setAttribute('fill', color);
        marker.setAttribute('stroke', '#fff');
        marker.setAttribute('stroke-width', CONFIG.marker.strokeWidth);
        marker.classList.add('marker', 'star-marker');
        // Store original transform origin for scaling
        marker.style.transformOrigin = `${px}px ${py}px`;
    } else {
        // Create circle marker for regular items/NPCs
        marker = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        marker.setAttribute('cx', px);
        marker.setAttribute('cy', py);
        marker.setAttribute('r', radius);
        marker.setAttribute('fill', color);
        marker.setAttribute('stroke', isNpc ? '#fff' : 'rgba(0,0,0,0.5)');
        marker.setAttribute('stroke-width', CONFIG.marker.strokeWidth);
        marker.classList.add('marker');
    }
    
    if (!isPrimary) {
        marker.classList.add('stacked-marker');
    }
    
    // Store item data
    marker.dataset.id = item.id;
    marker.dataset.isNpc = isNpc;
    marker.dataset.tileX = item.tile_x;
    marker.dataset.tileY = item.tile_y;
    marker.dataset.originalRadius = radius;
    marker.dataset.isStarMarker = isNamedNpc;
    marker.dataset.centerX = px;
    marker.dataset.centerY = py;
    
    // Event listeners - limit hover expansion to stay within tile
    const hoverRadius = Math.min(radius * 1.3, 4);
    marker.addEventListener('mouseenter', (e) => {
        // Don't shrink if already selected (selected = 1.8x, hover = 1.3x)
        if (!marker.classList.contains('selected')) {
            if (isNamedNpc) {
                marker.style.transform = 'scale(1.3)';
            } else {
                marker.setAttribute('r', hoverRadius);
            }
        }
        showTooltip(e, item, isNpc);
    });
    marker.addEventListener('mouseleave', () => {
        if (!marker.classList.contains('selected')) {
            if (isNamedNpc) {
                marker.style.transform = 'scale(1)';
            } else {
                marker.setAttribute('r', radius);
            }
        }
        hideTooltip();
    });
    marker.addEventListener('click', () => selectItem(item, isNpc, marker));
    
    return marker;
}

/**
 * Create a count badge showing number of items at a tile
 * Badge is centered in the tile and replaces individual markers
 */
function createCountBadge(centerX, centerY, count, tileX, tileY, items) {
    const badgeGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    badgeGroup.classList.add('count-badge');
    
    // Badge is centered in the tile
    const badgeRadius = 4;
    
    const bgCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    bgCircle.setAttribute('cx', centerX);
    bgCircle.setAttribute('cy', centerY);
    bgCircle.setAttribute('r', badgeRadius);
    bgCircle.setAttribute('fill', '#d4a855');
    bgCircle.setAttribute('stroke', '#0d0d0f');
    bgCircle.setAttribute('stroke-width', '0.5');
    
    // Badge text
    const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    text.setAttribute('x', centerX);
    text.setAttribute('y', centerY);
    text.setAttribute('text-anchor', 'middle');
    text.setAttribute('dominant-baseline', 'central');
    text.setAttribute('fill', '#0d0d0f');
    text.setAttribute('font-family', 'var(--font-mono), monospace');
    text.setAttribute('font-size', '6');
    text.setAttribute('font-weight', 'bold');
    text.textContent = count > 9 ? '+' : count;
    
    badgeGroup.appendChild(bgCircle);
    badgeGroup.appendChild(text);
    
    // Badge is visual only - the tile hover area handles all events
    badgeGroup.style.pointerEvents = 'none';
    
    return badgeGroup;
}

/**
 * Show interactive tooltip for stacked items badge
 * Items are clickable to select them
 */
function showStackedTooltip(e, items, tileX, tileY) {
    // Cancel any pending tooltip hide from a previous hover area
    if (state.tooltipHideTimeout) {
        clearTimeout(state.tooltipHideTimeout);
        state.tooltipHideTimeout = null;
    }
    
    const tooltip = elements.tooltip;
    
    // Clear previous content
    tooltip.innerHTML = '';
    
    // Header
    const header = document.createElement('div');
    header.className = 'tooltip-name';
    header.style.color = 'var(--text-accent)';
    header.textContent = `📍 ${items.length} items at this tile`;
    tooltip.appendChild(header);
    
    const position = document.createElement('div');
    position.className = 'tooltip-position';
    position.style.marginBottom = '6px';
    position.textContent = `Tile: (${tileX}, ${tileY})`;
    tooltip.appendChild(position);
    
    // Clickable item list
    const itemList = document.createElement('div');
    itemList.className = 'tooltip-item-list';
    
    items.forEach(({ item, color, isNpc, isSecret }, index) => {
        const itemEl = document.createElement('div');
        itemEl.className = 'tooltip-item-entry';
        itemEl.style.cssText = `
            padding: 4px 8px;
            margin: 2px 0;
            border-left: 3px solid ${color};
            cursor: pointer;
            border-radius: 0 3px 3px 0;
            transition: background 0.1s ease;
        `;
        
        // Build item display with icons based on type
        let icon, displayName;
        if (isSecret) {
            icon = item.type === 'illusory_wall' ? '🔮' : '🚪';
            displayName = item.type === 'illusory_wall' ? 'Illusory Wall' : 'Secret Door';
        } else if (isNpc) {
            icon = '👤';
            displayName = item.name || 'Unknown';
        } else {
            icon = '•';
            displayName = getItemDisplayName(item);
        }
        const enchantIcon = (!isSecret && isEnchanted(item)) ? ' ✨' : '';
        
        // Create name line
        const nameSpan = document.createElement('span');
        nameSpan.textContent = `${icon} ${displayName}${enchantIcon}`;
        itemEl.appendChild(nameSpan);
        
        // Show quantity for stackable items (only if > 1)
        if (!isSecret && !isNpc && item.quantity && item.quantity > 1) {
            const qtyDiv = document.createElement('div');
            qtyDiv.style.cssText = 'font-size: 0.7rem; color: #fcc419; margin-top: 2px;';
            qtyDiv.textContent = `📦 Qty: ${item.quantity}`;
            itemEl.appendChild(qtyDiv);
        }
        
        // Show owner information for items (item belongs to an NPC - taking it is stealing)
        if (!isSecret && !isNpc && isOwned(item)) {
            const ownerDiv = document.createElement('div');
            ownerDiv.style.cssText = 'font-size: 0.7rem; color: #fab005; margin-top: 2px;';
            const ownerName = item.owner_name || `NPC #${item.owner}`;
            ownerDiv.textContent = `⚠️ Owned by ${ownerName}`;
            itemEl.appendChild(ownerDiv);
        }
        
        // Add stats line for non-secret items (weapons/armor)
        if (!isSecret && !isNpc) {
            const objId = item.object_id || 0;
            
            // Show enchantment effect for enchanted items (spell scrolls, enchanted weapons, etc.)
            if (isEnchanted(item) && item.effect && isMagicalEffect(item.effect)) {
                const effectDiv = document.createElement('div');
                effectDiv.style.cssText = `font-size: 0.7rem; color: #da77f2; margin-top: 2px;`;
                effectDiv.textContent = `⚡ ${item.effect}`;
                itemEl.appendChild(effectDiv);
            }
            
            // Weapon damage
            if (objId <= 0x0F && (item.slash_damage !== undefined || item.bash_damage !== undefined || item.stab_damage !== undefined)) {
                const damageDiv = document.createElement('div');
                damageDiv.style.cssText = `font-size: 0.7rem; font-family: var(--font-mono); color: #e03131; margin-top: 2px;`;
                damageDiv.textContent = formatDamage(item);
                itemEl.appendChild(damageDiv);
            }
            
            // Weapon durability (melee and ranged)
            if (objId <= 0x1F && item.max_durability !== undefined) {
                const durDiv = document.createElement('div');
                durDiv.style.cssText = `font-size: 0.7rem; font-family: var(--font-mono); color: #fab005; margin-top: 2px;`;
                durDiv.textContent = formatDurability(item);
                itemEl.appendChild(durDiv);
            }
            
            // Armor stats
            if (isArmor(item) && (item.protection !== undefined || item.max_durability !== undefined)) {
                const armorDiv = document.createElement('div');
                armorDiv.style.cssText = `font-size: 0.7rem; font-family: var(--font-mono); color: #5c7cfa; margin-top: 2px;`;
                armorDiv.textContent = formatArmor(item);
                itemEl.appendChild(armorDiv);
            }
            
            // Container capacity
            if (item.capacity !== undefined) {
                const capDiv = document.createElement('div');
                capDiv.style.cssText = `font-size: 0.7rem; color: var(--text-accent); margin-top: 2px;`;
                let capText = `📦 ${item.capacity} stone${item.capacity !== 1 ? 's' : ''}`;
                if (item.accepts && item.accepts !== 'any') {
                    capText += ` (${item.accepts})`;
                }
                capDiv.textContent = capText;
                itemEl.appendChild(capDiv);
            }
            
            // Show book/scroll/writing/gravestone content for readable items
            // Books/scrolls: 0x130-0x13F (excluding 0x13B map) = 304-319 (excluding 315)
            // Gravestones: 0x165 = 357, Writings: 0x166 = 358
            const objIdNumStack = Number(objId);
            const isBookOrScroll = (objIdNumStack >= 304 && objIdNumStack <= 319 && objIdNumStack !== 315);
            const isStationaryWriting = (objIdNumStack === 357 || objIdNumStack === 358);
            const isStackedReadable = isBookOrScroll || isStationaryWriting;
            const hasDescStack = item.description && String(item.description).trim().length > 0;
            if (isStackedReadable && hasDescStack) {
                const descDiv = document.createElement('div');
                const maxLen = 60;
                const displayText = item.description.length > maxLen 
                    ? item.description.substring(0, maxLen) + '...' 
                    : item.description;
                const icon = (objIdNumStack === 357) ? '🪦' : (objIdNumStack === 358) ? '📝' : '📜';
                descDiv.style.cssText = `font-size: 0.7rem; color: #e8d4b8; margin-top: 4px; padding: 3px 5px; background: rgba(232, 212, 184, 0.1); border-left: 2px solid #e8d4b8; border-radius: 2px; font-style: italic; line-height: 1.3;`;
                descDiv.textContent = `${icon} "${displayText}"`;
                itemEl.appendChild(descDiv);
            }
        }
        
        // Show change information when a save game is loaded
        if (state.saveGame.currentSaveName && item.change_type && item.change_type !== 'unchanged') {
            const changeColor = window.SaveComparator?.getChangeTypeColor(item.change_type) || '#868e96';
            const changeIcon = window.SaveComparator?.getChangeTypeIcon(item.change_type) || '';
            const changeLabel = window.SaveComparator?.getChangeTypeLabel(item.change_type) || '';
            
            const changeDiv = document.createElement('div');
            changeDiv.style.cssText = `font-size: 0.7rem; color: ${changeColor}; margin-top: 4px; font-weight: 500;`;
            changeDiv.textContent = `${changeIcon} ${changeLabel}`;
            itemEl.appendChild(changeDiv);
        }
        
        // Hover effect
        itemEl.addEventListener('mouseenter', () => {
            itemEl.style.background = 'var(--bg-elevated)';
        });
        itemEl.addEventListener('mouseleave', () => {
            itemEl.style.background = 'transparent';
        });
        
        // Click to select this item
        itemEl.addEventListener('click', (clickEvent) => {
            clickEvent.stopPropagation();
            hideTooltip();
            
            // Select this item based on type
            if (isSecret) {
                selectSecret(item);
            } else {
                selectStackedItem(item, isNpc, tileX, tileY);
            }
        });
        
        itemList.appendChild(itemEl);
    });
    
    tooltip.appendChild(itemList);
    
    // Footer hint
    const hint = document.createElement('div');
    hint.className = 'tooltip-info';
    hint.style.cssText = 'margin-top: 6px; color: var(--text-muted); font-size: 0.75rem; text-align: center;';
    hint.textContent = 'Click an item to select it';
    tooltip.appendChild(hint);
    
    // Mark tooltip as interactive
    tooltip.classList.add('visible', 'interactive');
    
    updateTooltipPosition(e);
}

/**
 * Select an item from a stacked badge (no visible marker)
 */
function selectStackedItem(item, isNpc, tileX, tileY) {
    // Clear previous selection (individual markers)
    document.querySelectorAll('.marker.selected').forEach(m => {
        m.classList.remove('selected');
        if (m.dataset.isStarMarker === 'true') {
            m.style.transform = 'scale(1)';
        } else {
            const origR = parseFloat(m.dataset.originalRadius) || CONFIG.marker.radius;
            m.setAttribute('r', origR);
        }
    });
    
    // Clear previous selection (stacked marker groups) - also reset inline styles
    document.querySelectorAll('.marker-stack.selected').forEach(g => {
        g.classList.remove('selected');
        clearStackedMarkerStyles(g);
    });
    
    // Clear secret marker groups
    document.querySelectorAll('.secret-marker.selected').forEach(g => {
        g.classList.remove('selected');
        // Reset transform
        const visualGroup = g.querySelector('.secret-visual');
        if (visualGroup) {
            visualGroup.setAttribute('transform', `translate(${visualGroup.dataset.centerX}, ${visualGroup.dataset.centerY})`);
        }
        // Reset stroke widths
        const lines = g.querySelectorAll('.secret-x');
        lines.forEach(line => line.setAttribute('stroke-width', '2'));
        const diamonds = g.querySelectorAll('.secret-diamond');
        diamonds.forEach(diamond => diamond.setAttribute('stroke-width', '1'));
    });
    
    state.selectedMarker = null;
    
    // First try to find an individual marker (for single-item tiles)
    const markers = document.querySelectorAll('.marker');
    let foundMarker = false;
    for (const marker of markers) {
        if (marker.dataset.id === String(item.id) && 
            marker.dataset.isNpc === String(isNpc)) {
            marker.classList.add('selected');
            if (marker.dataset.isStarMarker === 'true') {
                marker.style.transform = 'scale(1.8)';
            } else {
                const origR = parseFloat(marker.dataset.originalRadius) || CONFIG.marker.radius;
                marker.setAttribute('r', origR * 1.8);
            }
            state.selectedMarker = marker;
            foundMarker = true;
            break;
        }
    }
    
    // If no individual marker found, look for the stacked marker group at this tile
    if (!foundMarker) {
        const stackedGroups = document.querySelectorAll('.marker-stack');
        for (const group of stackedGroups) {
            if (group.dataset.tileX === String(tileX) && 
                group.dataset.tileY === String(tileY)) {
                group.classList.add('selected');
                // Apply inline styles for selection (more reliable than CSS for SVG)
                applyStackedMarkerSelectionStyles(group);
                state.selectedMarker = group;
                break;
            }
        }
    }
    
    // Ensure selection pane layout is rendered
    renderSelectionPane();
    
    // Update details panel
    renderObjectDetails(item, isNpc);
    
    // Show all items at this location
    renderLocationObjects(tileX, tileY, item.id);
    
    updateUrlHash();
}

/**
 * Check if any item in contents (recursively) matches the currently selected category filters
 */
function hasContentMatchingCategory(contents) {
    if (!contents || contents.length === 0) return false;
    
    for (const item of contents) {
        // Check if this item's category matches any selected filter
        if (state.filters.categories.has(item.category)) {
            return true;
        }
        
        // Recursively check nested containers
        if (item.contents && item.contents.length > 0) {
            if (hasContentMatchingCategory(item.contents)) {
                return true;
            }
        }
    }
    
    return false;
}

/**
 * Check if an object is a secret door that matches a secret in the base game
 * If so, it should be hidden from the objects list (since it's shown as a secret)
 * @param {Object} obj - Object to check
 * @param {Object} level - Level data containing secrets
 * @returns {boolean} - True if object should be hidden (matches a secret)
 */
function isSecretDoorMatchingBaseSecret(obj, level) {
    if (!obj || !level || !level.secrets) {
        return false;
    }
    
    const objId = obj.object_id !== undefined ? obj.object_id : 0;
    
    // Check if this is a secret door object ID
    const isSecretDoor = objId === 0x147 || objId === 0x14F || 
                        (objId >= 0x150 && objId <= 0x15F);
    
    if (!isSecretDoor) {
        return false;
    }
    
    const objX = obj.tile_x !== undefined ? obj.tile_x : 0;
    const objY = obj.tile_y !== undefined ? obj.tile_y : 0;
    
    // Check if there's a matching secret at the same tile position
    for (const secret of level.secrets) {
        const secretX = secret.tile_x !== undefined ? secret.tile_x : 0;
        const secretY = secret.tile_y !== undefined ? secret.tile_y : 0;
        
        if (secretX === objX && secretY === objY) {
            // Check if it's a secret door type
            const isSecretDoorType = secret.type === 'secret_door' || 
                                    secret.category === 'secret_doors' ||
                                    secret.category === 'secret_door';
            
            if (isSecretDoorType) {
                return true; // This object matches a secret, hide it
            }
        }
    }
    
    return false;
}

function shouldShowItem(item) {
    // Check enchanted filter first
    if (state.filters.enchantedOnly) {
        if (!isEnchanted(item)) return false;
    }
    
    // Check owned filter
    if (state.filters.ownedFilter === 'only') {
        if (!isOwned(item)) return false;
    } else if (state.filters.ownedFilter === 'exclude') {
        if (isOwned(item)) return false;
    }
    
    // Then apply search filter
    if (!state.filters.search) return true;
    const searchTerm = state.filters.search;
    
    // Check the item's own name
    const name = (item.name || '').toLowerCase();
    if (name.includes(searchTerm)) return true;
    
    // Check contents recursively (for containers)
    if (item.contents && item.contents.length > 0) {
        if (hasMatchingContent(item.contents, searchTerm)) return true;
    }
    
    // Check inventory recursively (for NPCs)
    if (item.inventory && item.inventory.length > 0) {
        if (hasMatchingContent(item.inventory, searchTerm)) return true;
    }
    
    return false;
}

/**
 * Categories that are inherently magical (always show with enchanted filter)
 */
const MAGICAL_CATEGORIES = new Set([
    'wands',          // Magic wands (cast spells)
    'potions',        // Potions (magical effects)
    'spell_scrolls',  // Spell scrolls (cast spells when used)
]);

/**
 * Check if an effect string represents a true magical enchantment
 * Excludes: keys ("Opens lock #X"), regular books/scrolls ("Text #X")
 */
function isMagicalEffect(effect) {
    if (!effect) return false;
    
    // Exclude keys that open locks
    if (effect.startsWith('Opens lock')) return false;
    
    // Exclude regular books/scrolls with text (spell scrolls handled by category)
    if (effect.startsWith('Text #')) return false;
    
    // Everything else with an effect is considered enchanted
    return true;
}

/**
 * Check if an item is enchanted (has an effect field with magical properties)
 * Also recursively checks container contents and NPC inventory
 */
function isEnchanted(item) {
    // Check if item's category is inherently magical
    if (MAGICAL_CATEGORIES.has(item.category)) return true;
    
    // Check if item itself has a magical effect (not just text or lock info)
    if (isMagicalEffect(item.effect)) return true;
    
    // Check extra_info for spell-related properties
    if (item.extra_info) {
        if (item.extra_info.spell_index !== undefined) return true;
        if (item.extra_info.spell_link !== undefined) return true;
    }
    
    // Check container contents recursively
    if (item.contents && item.contents.length > 0) {
        if (hasEnchantedContent(item.contents)) return true;
    }
    
    // Check NPC inventory recursively
    if (item.inventory && item.inventory.length > 0) {
        if (hasEnchantedContent(item.inventory)) return true;
    }
    
    return false;
}

/**
 * Check if an item is owned (has an owner > 0)
 * Excludes types that can never have owners: traps, triggers, secret doors, stairs, useless items, and item 0x1ca
 */
function isOwned(item) {
    // Centralized ownership semantics live in js/ownership.js
    if (window.Ownership && typeof window.Ownership.isOwned === 'function') {
        return window.Ownership.isOwned(item);
    }

    // Items that can never have owners (even if owner field is set)
    if (!item) return false;
    
    // Check if this is a secret (secrets have a type property and can never be owned)
    if (item.type === 'secret_door' || item.type === 'illusory_wall') {
        return false;
    }
    
    const objectId = item.object_id;
    if (objectId === undefined || objectId === null) {
        // If no object_id, fall back to category check
        const category = item.category;
        if (category === 'trap' || 
            category === 'traps' ||
            category === 'trigger' || 
            category === 'triggers' ||
            category === 'secret_door' || 
            category === 'secret_doors' || 
            category === 'stairs' || 
            category === 'useless_item' ||
            category === 'animation' ||
            category === 'animations' ||
            category === 'writings') {
            return false;
        }
        // If no object_id and category doesn't exclude it, check owner
        return item.owner && item.owner > 0;
    }
    
    // Check object ID ranges for types that can never have owners
    // Traps: 0x180-0x19F (384-415)
    if (objectId >= 0x180 && objectId <= 0x19F) {
        return false;
    }
    
    // Triggers: 0x1A0-0x1BF (416-447)
    if (objectId >= 0x1A0 && objectId <= 0x1BF) {
        return false;
    }
    
    // Secret doors: 0x147 (closed), 0x14F (open)
    if (objectId === 0x147 || objectId === 0x14F) {
        return false;
    }
    
    // Writings: 0x166 (358)
    if (objectId === 0x166 || objectId === 358) {
        return false;
    }
    
    // Animations: 0x1C0-0x1C9 (448-457) and 0x1CB-0x1CF (459-463)
    // Note: 0x1CA is a quest_item, not an animation
    if ((objectId >= 0x1C0 && objectId <= 0x1C9) || (objectId >= 0x1CB && objectId <= 0x1CF)) {
        return false;
    }
    
    // Stairs are identified by category, but also check if it's a move trigger
    // Move triggers that change level are stairs (object_id in trigger range but with special properties)
    // For now, rely on category check for stairs
    
    // Specific item exclusion: 0x1ca (458)
    if (objectId === 0x1ca || objectId === 458) {
        return false;
    }
    
    // Check category exclusions (for items where category might be more reliable)
    const category = item.category;
    if (category === 'trap' || 
        category === 'traps' ||
        category === 'trigger' || 
        category === 'triggers' ||
        category === 'secret_door' || 
        category === 'secret_doors' || 
        category === 'stairs' || 
        category === 'useless_item' ||
        category === 'animation' ||
        category === 'animations' ||
        category === 'writings') {
        return false;
    }
    
    // For all other items, check if owner field is set
    return item.owner && item.owner > 0;
}

/**
 * Check if an NPC has a unique name (different from their creature type)
 * Named NPCs are ones that have dialogue and personal identities
 * Generic descriptors like "bandit" don't count as unique names
 */
function hasUniqueName(npc) {
    if (!npc || !npc.name) return false;
    
    const nameLower = npc.name.toLowerCase();
    
    // Exclude exact generic aliases (not compound names like "head bandit")
    // "bandit" alone is generic, but "head bandit" is a specific character
    const genericAliases = ['bandit', 'guard'];
    if (genericAliases.includes(nameLower)) return false;
    
    // Exclude ethereal creatures from Level 9 (names like "a_bizarre fish", "an_eyeball")
    // These start with "a_" or "an_" and are generic enemy types, not named characters
    if (nameLower.startsWith('a_') || nameLower.startsWith('an_')) return false;
    
    // If creature_type is empty/missing, check if it looks like a proper name
    // "the Slasher of Veils" and "Tyball" are proper names (capital letters after articles)
    if (!npc.creature_type) {
        // Check if name has at least one capital letter (proper name indicator)
        // This distinguishes "the Slasher of Veils" from generic lowercase descriptors
        return /[A-Z]/.test(npc.name);
    }
    
    // Name must be different from creature type
    if (nameLower === npc.creature_type.toLowerCase()) return false;
    
    return true;
}

/**
 * Check if an NPC is hostile based on their attitude
 * Only "hostile" attitude is considered hostile; "upset" and "mellow" are friendly
 */
function isHostile(npc) {
    if (!npc) return false;
    const attitude = (npc.attitude || '').toLowerCase();
    return attitude === 'hostile';
}

/**
 * Generate an SVG path for a 5-pointed star centered at (cx, cy) with given outer radius
 * @param {number} cx - Center X coordinate
 * @param {number} cy - Center Y coordinate
 * @param {number} outerRadius - Radius to the outer points of the star
 * @param {number} innerRadius - Radius to the inner points (usually outerRadius * 0.4)
 * @returns {string} SVG path data for the star
 */
function createStarPath(cx, cy, outerRadius, innerRadius = null) {
    if (innerRadius === null) innerRadius = outerRadius * 0.4;
    const points = 5;
    const angleOffset = -Math.PI / 2; // Start from top point
    let path = '';
    
    for (let i = 0; i < points * 2; i++) {
        const radius = i % 2 === 0 ? outerRadius : innerRadius;
        const angle = angleOffset + (i * Math.PI) / points;
        const x = cx + radius * Math.cos(angle);
        const y = cy + radius * Math.sin(angle);
        path += (i === 0 ? 'M' : 'L') + x.toFixed(2) + ',' + y.toFixed(2);
    }
    path += 'Z';
    return path;
}

/**
 * Get the NPC category based on hostility and unique name
 * Returns: 'npcs_hostile', 'npcs_friendly', or 'npcs_named'
 */
function getNpcCategory(npc) {
    if (isHostile(npc)) {
        return 'npcs_hostile';
    } else if (hasUniqueName(npc)) {
        return 'npcs_named';
    } else {
        return 'npcs_friendly';
    }
}

/**
 * Recursively check if any content item is enchanted
 */
function hasEnchantedContent(contents) {
    for (const contentItem of contents) {
        // Check if category is inherently magical
        if (MAGICAL_CATEGORIES.has(contentItem.category)) return true;
        
        // Check if has magical effect
        if (isMagicalEffect(contentItem.effect)) return true;
        
        // Check extra_info for spell-related properties
        if (contentItem.extra_info) {
            if (contentItem.extra_info.spell_index !== undefined) return true;
            if (contentItem.extra_info.spell_link !== undefined) return true;
        }
        
        // Check nested containers
        if (contentItem.contents && contentItem.contents.length > 0) {
            if (hasEnchantedContent(contentItem.contents)) return true;
        }
    }
    return false;
}

/**
 * Recursively search container contents for matching item names
 */
function hasMatchingContent(contents, searchTerm) {
    for (const contentItem of contents) {
        const name = (contentItem.name || '').toLowerCase();
        if (name.includes(searchTerm)) return true;
        
        // Check nested containers
        if (contentItem.contents && contentItem.contents.length > 0) {
            if (hasMatchingContent(contentItem.contents, searchTerm)) return true;
        }
    }
    return false;
}

function createMarker(item, color, pxPerTileX, pxPerTileY, isNpc) {
    // Tile boundaries (top-left corner of tile in pixel coordinates)
    const tileLeft = CONFIG.mapArea.offsetX + item.tile_x * pxPerTileX;
    const tileTop = CONFIG.mapArea.offsetY + (CONFIG.mapArea.gridSize - item.tile_y - 1) * pxPerTileY;
    
    // Center of tile
    const px = tileLeft + pxPerTileX / 2;
    const py = tileTop + pxPerTileY / 2;
    
    // Use smaller radius for NPCs to fit within tile
    const radius = isNpc ? CONFIG.marker.radius + 0.5 : CONFIG.marker.radius;
    
    // Check if this is a named NPC (should use star shape)
    const isNamedNpc = isNpc && hasUniqueName(item);
    
    // Check if this is a bridge or stairs
    const itemIsBridge = isBridge(item);
    const itemIsStairs = isStairs(item);
    
    // Get change type for save game visualization
    const changeType = getObjectChangeType(item);
    
    // Create a group to hold both hover area and marker
    const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    group.classList.add('marker-group');
    if (itemIsBridge) group.classList.add('bridge-marker');
    if (itemIsStairs) group.classList.add('stairs-marker');
    
    // Add change indicator classes
    if (changeType) {
        group.classList.add(`marker-${changeType}`);
    }
    
    group.dataset.id = item.id;
    group.dataset.isNpc = isNpc;
    group.dataset.isBridge = itemIsBridge;
    group.dataset.isStairs = itemIsStairs;
    group.dataset.tileX = item.tile_x;
    group.dataset.tileY = item.tile_y;
    if (changeType) {
        group.dataset.changeType = changeType;
    }
    
    // Create invisible tile-sized hover area (added first so marker renders on top)
    const hoverArea = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    hoverArea.setAttribute('x', tileLeft);
    hoverArea.setAttribute('y', tileTop);
    hoverArea.setAttribute('width', pxPerTileX);
    hoverArea.setAttribute('height', pxPerTileY);
    hoverArea.setAttribute('fill', 'transparent');
    hoverArea.classList.add('tile-hover-area');
    
    // Check if this is a removed item (needs special X marker)
    const isRemoved = changeType === 'removed' || item.change_type === 'removed';
    
    // Create the visual marker
    let marker;
    let isXMarker = false;
    
    if (isRemoved && !itemIsStairs && !itemIsBridge) {
        // Create X marker for removed items (similar to illusory wall style)
        isXMarker = true;
        const size = 4;
        marker = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        marker.classList.add('marker', 'removed-x-marker');
        marker.setAttribute('transform', `translate(${px}, ${py})`);
        marker.dataset.centerX = px;
        marker.dataset.centerY = py;
        
        const line1 = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line1.setAttribute('x1', -size);
        line1.setAttribute('y1', -size);
        line1.setAttribute('x2', size);
        line1.setAttribute('y2', size);
        line1.setAttribute('stroke', '#ff4444');
        line1.setAttribute('stroke-width', '2');
        line1.classList.add('removed-x');
        line1.style.pointerEvents = 'none';
        
        const line2 = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line2.setAttribute('x1', size);
        line2.setAttribute('y1', -size);
        line2.setAttribute('x2', -size);
        line2.setAttribute('y2', size);
        line2.setAttribute('stroke', '#ff4444');
        line2.setAttribute('stroke-width', '2');
        line2.classList.add('removed-x');
        line2.style.pointerEvents = 'none';
        
        marker.appendChild(line1);
        marker.appendChild(line2);
    } else if (itemIsStairs) {
        // Create stairs icon for stairs - determine up vs down based on destination level
        const destLevel = item.stairs_dest_level; // 1-indexed destination level
        const currentLevel1Idx = state.currentLevel + 1; // Convert to 1-indexed (state.currentLevel is 0-indexed)
        // If destination level is higher number (deeper), use stairs_down, otherwise stairs_up
        const stairsImage = (destLevel > currentLevel1Idx) ? CONFIG.stairs.downImage : CONFIG.stairs.upImage;
        marker = createStairsIcon(tileLeft, tileTop, pxPerTileX, pxPerTileY, stairsImage);
        marker.classList.add('marker', 'stairs-rect');
    } else if (itemIsBridge) {
        // Create full-tile rectangle for bridges
        marker = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        marker.setAttribute('x', tileLeft);
        marker.setAttribute('y', tileTop);
        marker.setAttribute('width', pxPerTileX);
        marker.setAttribute('height', pxPerTileY);
        marker.setAttribute('fill', CONFIG.bridge.color);
        marker.setAttribute('stroke', CONFIG.bridge.strokeColor);
        marker.setAttribute('stroke-width', '0.5');
        marker.classList.add('marker', 'bridge-rect');
    } else if (isNamedNpc) {
        // Create star-shaped marker for named NPCs
        marker = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        const starPath = createStarPath(px, py, radius * 1.2);
        marker.setAttribute('d', starPath);
        marker.setAttribute('fill', color);
        marker.setAttribute('stroke', '#fff');
        marker.setAttribute('stroke-width', CONFIG.marker.strokeWidth);
        marker.classList.add('marker', 'star-marker');
        marker.style.transformOrigin = `${px}px ${py}px`;
    } else {
        // Create circle marker for regular items/NPCs
        marker = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        marker.setAttribute('cx', px);
        marker.setAttribute('cy', py);
        marker.setAttribute('r', radius);
        marker.setAttribute('fill', color);
        marker.setAttribute('stroke', isNpc ? '#fff' : 'rgba(0,0,0,0.5)');
        marker.setAttribute('stroke-width', CONFIG.marker.strokeWidth);
        marker.classList.add('marker');
    }
    marker.style.pointerEvents = 'none'; // Visual only
    
    // Store item data on marker for selection
    marker.dataset.id = item.id;
    marker.dataset.isNpc = isNpc;
    marker.dataset.isBridge = itemIsBridge;
    marker.dataset.isStairs = itemIsStairs;
    marker.dataset.tileX = item.tile_x;
    marker.dataset.tileY = item.tile_y;
    marker.dataset.isXMarker = isXMarker;
    if (!itemIsStairs && !itemIsBridge && !isXMarker) {
        marker.dataset.originalRadius = radius;
        marker.dataset.isStarMarker = isNamedNpc;
        marker.dataset.centerX = px;
        marker.dataset.centerY = py;
    }
    
    // Hover radius for visual feedback (not used for bridges, stairs, or X markers)
    const hoverRadius = Math.min(radius * 1.3, 4);
    
    // Event listeners on the tile hover area
    hoverArea.addEventListener('mouseenter', (e) => {
        // Don't shrink if already selected (selected = 1.8x, hover = 1.3x)
        if (!marker.classList.contains('selected') && !itemIsBridge && !itemIsStairs) {
            if (isXMarker) {
                // Scale the X marker group
                marker.setAttribute('transform', `translate(${px}, ${py}) scale(1.3)`);
            } else if (isNamedNpc) {
                marker.style.transform = 'scale(1.3)';
            } else {
                marker.setAttribute('r', hoverRadius);
            }
        }
        showTooltip(e, item, isNpc);
    });
    hoverArea.addEventListener('mouseleave', () => {
        if (!marker.classList.contains('selected') && !itemIsBridge && !itemIsStairs) {
            if (isXMarker) {
                // Reset the X marker scale
                marker.setAttribute('transform', `translate(${px}, ${py})`);
            } else if (isNamedNpc) {
                marker.style.transform = 'scale(1)';
            } else {
                marker.setAttribute('r', radius);
            }
        }
        hideTooltip();
    });
    hoverArea.addEventListener('mousemove', (e) => {
        updateTooltipPosition(e);
    });
    hoverArea.addEventListener('click', () => selectItem(item, isNpc, marker));
    
    group.appendChild(hoverArea);
    group.appendChild(marker);
    
    return group;
}

/**
 * Create a special marker for secrets (illusory walls, secret doors)
 * Uses distinct shapes: X for illusory walls, diamond for secret doors
 */
function createSecretMarker(secret, color, pxPerTileX, pxPerTileY) {
    // Tile boundaries
    const tileLeft = CONFIG.mapArea.offsetX + secret.tile_x * pxPerTileX;
    const tileTop = CONFIG.mapArea.offsetY + (CONFIG.mapArea.gridSize - secret.tile_y - 1) * pxPerTileY;
    
    // Center of tile
    const px = tileLeft + pxPerTileX / 2;
    const py = tileTop + pxPerTileY / 2;
    
    // Create a group to hold the marker
    const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    group.classList.add('marker-group', 'secret-marker');
    group.dataset.id = secret.id;
    group.dataset.isSecret = true;
    group.dataset.secretType = secret.type;
    group.dataset.tileX = secret.tile_x;
    group.dataset.tileY = secret.tile_y;
    
    // Create invisible tile-sized hover area
    const hoverArea = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    hoverArea.setAttribute('x', tileLeft);
    hoverArea.setAttribute('y', tileTop);
    hoverArea.setAttribute('width', pxPerTileX);
    hoverArea.setAttribute('height', pxPerTileY);
    hoverArea.setAttribute('fill', 'transparent');
    hoverArea.classList.add('tile-hover-area');
    
    // Create visual marker based on secret type
    const size = 4;
    
    // Create a transform group for the visual marker (for scaling when selected)
    const visualGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    visualGroup.classList.add('secret-visual');
    visualGroup.setAttribute('transform', `translate(${px}, ${py})`);
    visualGroup.dataset.centerX = px;
    visualGroup.dataset.centerY = py;
    
    if (secret.type === 'illusory_wall') {
        // Draw an X for illusory walls (bright magenta)
        const line1 = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line1.setAttribute('x1', -size);
        line1.setAttribute('y1', -size);
        line1.setAttribute('x2', size);
        line1.setAttribute('y2', size);
        line1.setAttribute('stroke', '#ff00ff');
        line1.setAttribute('stroke-width', '2');
        line1.classList.add('marker', 'secret-x');
        line1.style.pointerEvents = 'none';
        
        const line2 = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line2.setAttribute('x1', size);
        line2.setAttribute('y1', -size);
        line2.setAttribute('x2', -size);
        line2.setAttribute('y2', size);
        line2.setAttribute('stroke', '#ff00ff');
        line2.setAttribute('stroke-width', '2');
        line2.classList.add('marker', 'secret-x');
        line2.style.pointerEvents = 'none';
        
        visualGroup.appendChild(line1);
        visualGroup.appendChild(line2);
    } else if (secret.type === 'secret_door') {
        // Draw a diamond for secret doors (bright yellow)
        const diamond = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
        const points = `0,${-size} ${size},0 0,${size} ${-size},0`;
        diamond.setAttribute('points', points);
        diamond.setAttribute('fill', '#ffff00');
        diamond.setAttribute('stroke', '#ffffff');
        diamond.setAttribute('stroke-width', '1');
        diamond.classList.add('marker', 'secret-diamond');
        diamond.style.pointerEvents = 'none';
        
        visualGroup.appendChild(diamond);
    } else {
        // Default: circle marker
        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('cx', 0);
        circle.setAttribute('cy', 0);
        circle.setAttribute('r', size);
        circle.setAttribute('fill', color);
        circle.setAttribute('stroke', '#ffffff');
        circle.setAttribute('stroke-width', '1');
        circle.classList.add('marker');
        circle.style.pointerEvents = 'none';
        
        visualGroup.appendChild(circle);
    }
    
    group.appendChild(hoverArea);
    group.appendChild(visualGroup);
    
    // Event listeners
    hoverArea.addEventListener('mouseenter', (e) => {
        showSecretTooltip(e, secret);
    });
    hoverArea.addEventListener('mouseleave', () => {
        hideTooltip();
    });
    hoverArea.addEventListener('mousemove', (e) => {
        updateTooltipPosition(e);
    });
    hoverArea.addEventListener('click', () => selectSecret(secret));
    
    return group;
}

/**
 * Show tooltip for a secret
 */
function showSecretTooltip(e, secret) {
    // Cancel any pending tooltip hide from a previous hover area
    if (state.tooltipHideTimeout) {
        clearTimeout(state.tooltipHideTimeout);
        state.tooltipHideTimeout = null;
    }
    
    const tooltip = elements.tooltip;
    
    const typeLabel = secret.type === 'illusory_wall' ? '🔮 Illusory Wall' : '🚪 Secret Door';
    const typeColor = secret.type === 'illusory_wall' ? '#ff00ff' : '#ffff00';
    
    let html = `<div class="tooltip-name" style="color: ${typeColor};">${typeLabel}</div>`;
    html += `<div class="tooltip-info">${secret.description || 'Hidden passage'}</div>`;
    
    if (secret.details) {
        if (secret.details.new_tile_type) {
            html += `<div class="tooltip-info" style="font-size: 0.8rem; color: var(--text-muted);">Reveals: ${secret.details.new_tile_type}</div>`;
        }
        // Show lock information for locked secret doors
        if (secret.details.is_locked) {
            const lockId = secret.details.lock_id;
            const lockType = secret.details.lock_type;
            const isPickable = secret.details.is_pickable;
            let lockText = '';
            if (lockType === 'special') {
                lockText = '🔒 Special Lock (trigger-opened)';
            } else {
                lockText = `🔒 Locked (lock #${lockId})`;
                if (isPickable) {
                    lockText += ' - ⛏️ Pickable';
                }
            }
            html += `<div class="tooltip-info" style="color: #ff6b6b; font-size: 0.85rem;">${lockText}</div>`;
        }
        // Show health for secret doors (they can be broken down)
        if (secret.type === 'secret_door' && secret.details.door_health !== undefined) {
            const doorHealth = secret.details.door_health;
            const doorMax = secret.details.door_max_health !== undefined ? secret.details.door_max_health : 40;
            const healthText = `${doorHealth}/${doorMax}`;
            html += `<div class="tooltip-info" style="font-family: var(--font-mono); font-size: 0.8rem; color: var(--text-accent);">Health: ${healthText}</div>`;
        }
    }
    
    html += `<div class="tooltip-position">Tile: (${secret.tile_x}, ${secret.tile_y})</div>`;
    
    tooltip.innerHTML = html;
    tooltip.classList.add('visible');
    
    updateTooltipPosition(e);
}

/**
 * Select a secret and show its details
 */
function selectSecret(secret) {
    // Clear previous selection (individual markers)
    document.querySelectorAll('.marker.selected').forEach(m => {
        m.classList.remove('selected');
    });
    
    // Clear stacked marker groups (also reset inline styles)
    document.querySelectorAll('.marker-stack.selected').forEach(g => {
        g.classList.remove('selected');
        clearStackedMarkerStyles(g);
    });
    
    // Clear secret marker groups
    document.querySelectorAll('.secret-marker.selected').forEach(g => {
        g.classList.remove('selected');
        // Reset transform
        const visualGroup = g.querySelector('.secret-visual');
        if (visualGroup) {
            visualGroup.setAttribute('transform', `translate(${visualGroup.dataset.centerX}, ${visualGroup.dataset.centerY})`);
        }
        // Reset stroke widths
        const lines = g.querySelectorAll('.secret-x');
        lines.forEach(line => line.setAttribute('stroke-width', '2'));
        const diamonds = g.querySelectorAll('.secret-diamond');
        diamonds.forEach(diamond => diamond.setAttribute('stroke-width', '1'));
    });
    
    state.selectedMarker = null;
    
    // Find and select the secret marker group
    const markerGroups = document.querySelectorAll('.secret-marker');
    for (const group of markerGroups) {
        if (group.dataset.id === secret.id) {
            group.classList.add('selected');
            // Apply transform to the visual group
            const visualGroup = group.querySelector('.secret-visual');
            if (visualGroup) {
                visualGroup.setAttribute('transform', `translate(${visualGroup.dataset.centerX}, ${visualGroup.dataset.centerY}) scale(1.8)`);
            }
            // Update stroke widths for better visibility
            const lines = group.querySelectorAll('.secret-x');
            lines.forEach(line => line.setAttribute('stroke-width', '3'));
            const diamonds = group.querySelectorAll('.secret-diamond');
            diamonds.forEach(diamond => diamond.setAttribute('stroke-width', '2'));
            state.selectedMarker = group;
            break;
        }
    }
    
    // Ensure selection pane layout is rendered
    renderSelectionPane();
    
    // Update details panel
    renderSecretDetails(secret);
    
    // Show location info
    renderLocationObjects(secret.tile_x, secret.tile_y, secret.id);
    
    updateUrlHash();
}

/**
 * Get the reveal method text for an illusory wall based on its trigger
 */
function getIllusoryWallRevealMethod(triggerString) {
    if (!triggerString) {
        return 'Cast the <strong>Reveal</strong> spell (ORT LOR)';
    }
    
    // Extract trigger type from string (e.g., "move trigger at (8, 34)" -> "move trigger")
    const triggerMatch = triggerString.match(/^([^a]+trigger)/i);
    if (!triggerMatch) {
        return 'Cast the <strong>Reveal</strong> spell (ORT LOR)';
    }
    
    const triggerType = triggerMatch[1].trim().toLowerCase();
    
    if (triggerType.includes('look')) {
        return 'Search';
    } else if (triggerType.includes('move')) {
        return 'Walk through';
    } else if (triggerType.includes('use')) {
        return 'Use';
    } else {
        // Fallback for other trigger types
        return `Activate (${triggerType})`;
    }
}

/**
 * Render secret details in the details panel
 */
function renderSecretDetails(secret) {
    const typeLabel = secret.type === 'illusory_wall' ? '🔮 Illusory Wall' : '🚪 Secret Door';
    const typeColor = secret.type === 'illusory_wall' ? '#ff00ff' : '#ffff00';
    
    let html = '<div class="detail-card">';
    html += `<div class="detail-name" style="color: ${typeColor};">${typeLabel}</div>`;
    
    html += `
        <div class="detail-row">
            <span class="detail-label">Type</span>
            <span class="detail-category" style="background: ${typeColor}22; color: ${typeColor};">Secret</span>
        </div>
    `;
    
    // For illusory walls, skip the redundant description if it's just "Illusory wall -> {type}"
    // since we show "Reveals" separately below
    const isRedundantDescription = secret.type === 'illusory_wall' && 
                                    secret.description && 
                                    secret.description.startsWith('Illusory wall ->');
    
    if (!isRedundantDescription) {
        html += `
            <div class="detail-row">
                <span class="detail-label">Description</span>
                <span class="detail-value">${secret.description || 'Hidden passage'}</span>
            </div>
        `;
    }
    
    if (secret.details) {
        if (secret.details.new_tile_type) {
            html += `
                <div class="detail-row">
                    <span class="detail-label">Reveals</span>
                    <span class="detail-value">${secret.details.new_tile_type}</span>
                </div>
            `;
        }
        if (secret.details.new_floor_height !== undefined) {
            html += `
                <div class="detail-row">
                    <span class="detail-label">Floor Height</span>
                    <span class="detail-value">${secret.details.new_floor_height}</span>
                </div>
            `;
        }
        // Show lock information for locked secret doors
        if (secret.details.is_locked) {
            const lockId = secret.details.lock_id;
            const lockType = secret.details.lock_type;
            const isPickable = secret.details.is_pickable;
            let lockText = '';
            if (lockType === 'special') {
                lockText = '🔒 Special Lock (trigger-opened)';
            } else {
                lockText = `🔒 Locked (lock #${lockId})`;
                if (isPickable) {
                    lockText += ' - ⛏️ Pickable';
                }
            }
            html += `
                <div class="detail-row">
                    <span class="detail-label">Lock Status</span>
                    <span class="detail-value" style="color: #ff6b6b;">${lockText}</span>
                </div>
            `;
        }
        // Show health for secret doors (they can be broken down)
        if (secret.type === 'secret_door' && secret.details.door_health !== undefined) {
            const doorHealth = secret.details.door_health;
            const doorMax = secret.details.door_max_health !== undefined ? secret.details.door_max_health : 40;
            html += `
                <div class="detail-row">
                    <span class="detail-label">Health</span>
                    <span class="detail-value" style="font-family: var(--font-mono);">${doorHealth}/${doorMax}</span>
                </div>
            `;
        }
    }
    
    html += `
        <div class="detail-row">
            <span class="detail-label">Position</span>
            <span class="detail-value">(${secret.tile_x}, ${secret.tile_y})</span>
        </div>
    `;
    
    // Add hint about how to reveal
    if (secret.type === 'illusory_wall') {
        const triggerString = secret.details && secret.details.trigger;
        const revealMethod = getIllusoryWallRevealMethod(triggerString);
        html += `
            <div class="detail-description" style="margin-top: 12px;">
                <div class="detail-label" style="margin-bottom: 4px;">How to Reveal</div>
                <div class="description-text" style="color: var(--text-accent);">${revealMethod}</div>
            </div>
        `;
    }
    
    html += '</div>';
    
    elements.objectDetails.innerHTML = html;
}

function getCategoryColor(categoryId) {
    // Check hardcoded NPC categories first
    if (categoryId === 'npcs_named') return '#ffd43b';
    if (categoryId === 'npcs_friendly') return '#69db7c';
    if (categoryId === 'npcs_hostile') return '#ff4444';
    // Look up in data categories
    const cat = state.data.categories.find(c => c.id === categoryId);
    return cat ? cat.color : '#868e96';
}

// ============================================================================
// Tooltip
// ============================================================================

function showTooltip(e, item, isNpc) {
    // Cancel any pending tooltip hide from a previous hover area
    if (state.tooltipHideTimeout) {
        clearTimeout(state.tooltipHideTimeout);
        state.tooltipHideTimeout = null;
    }
    
    const tooltip = elements.tooltip;
    
    const uniqueIndicator = isNpc && hasUniqueName(item) ? '⭐ ' : '';
    const displayName = isNpc ? (item.name || 'Unknown NPC') : getItemDisplayName(item);
    let html = `<div class="tooltip-name">${uniqueIndicator}${displayName}</div>`;
    
    if (isNpc) {
        // Show creature type if different from name (already indicated by ⭐ but add context)
        if (item.creature_type && item.creature_type !== item.name) {
            html += `<div class="tooltip-info" style="color: var(--text-muted); font-style: italic;">${item.creature_type}</div>`;
        }
        html += `<div class="tooltip-info">HP: ${item.hp} | Level: ${item.level}</div>`;
        if (item.attitude) {
            html += `<div class="tooltip-info">Attitude: ${item.attitude}</div>`;
        }
        // Show inventory count for NPCs
        if (item.inventory && item.inventory.length > 0) {
            html += `<div class="tooltip-info" style="color: var(--text-accent);">🎒 ${item.inventory.length} item${item.inventory.length > 1 ? 's' : ''} carried</div>`;
        }
    } else {
        html += `<div class="tooltip-info">${formatCategory(item.category)}</div>`;
        // Show owner information (item belongs to an NPC - taking it is stealing)
        if (isOwned(item)) {
            const ownerName = item.owner_name || `NPC #${item.owner}`;
            html += `<div class="tooltip-info" style="color: #fab005; font-size: 0.85rem;">⚠️ Owned by ${escapeHtml(ownerName)}</div>`;
        }
        // Show damage values for melee weapons
        const objId = item.object_id || 0;
        if (objId <= 0x0F && (item.slash_damage !== undefined || item.bash_damage !== undefined || item.stab_damage !== undefined)) {
            html += `<div class="tooltip-info" style="font-family: var(--font-mono); font-size: 0.8rem; color: #e03131;">${formatDamage(item)}</div>`;
        }
        // Show durability for weapons (melee 0x00-0x0F and ranged 0x10-0x1F)
        if (objId <= 0x1F && item.max_durability !== undefined) {
            html += `<div class="tooltip-info" style="font-family: var(--font-mono); font-size: 0.8rem; color: #fab005;">${formatDurability(item)}</div>`;
        }
        // Show protection/durability for armor
        if (isArmor(item) && (item.protection !== undefined || item.max_durability !== undefined)) {
            html += `<div class="tooltip-info" style="font-family: var(--font-mono); font-size: 0.8rem; color: #5c7cfa;">${formatArmor(item)}</div>`;
        }
        // Show weight for items that have it
        if (item.weight !== undefined && item.weight > 0) {
            html += `<div class="tooltip-info" style="font-size: 0.8rem; color: var(--text-muted);">⚖️ ${formatWeight(item.weight)}</div>`;
        }
        // Show nutrition for food items (0xB0-0xB9, 0xBD water)
        if (item.nutrition !== undefined) {
            const nutritionColor = item.nutrition >= 40 ? '#69db7c' : 
                                   item.nutrition >= 20 ? '#a9e34b' : 
                                   item.nutrition > 0 ? '#fcc419' : '#ff6b6b';
            html += `<div class="tooltip-info" style="font-size: 0.8rem; color: ${nutritionColor};">🍖 Nutrition: ${item.nutrition}${item.nutrition === 0 ? ' (none!)' : ''}</div>`;
        }
        // Show intoxication for alcoholic drinks (ale 0xBA, port 0xBE, wine 0xBF)
        if (item.intoxication !== undefined && item.intoxication > 0) {
            const intoxColor = item.intoxication >= 100 ? '#ff6b6b' : 
                               item.intoxication >= 50 ? '#ffa94d' : '#fcc419';
            html += `<div class="tooltip-info" style="font-size: 0.8rem; color: ${intoxColor};">🍺 Intoxication: ${item.intoxication}</div>`;
        }
        // Show lock information for locked doors
        if (item.extra_info && item.extra_info.is_locked) {
            const lockId = item.extra_info.lock_id;
            const lockType = item.extra_info.lock_type;
            const isPickable = item.extra_info.is_pickable;
            let lockText = '';
            if (lockType === 'special') {
                lockText = '🔒 Special Lock (trigger-opened)';
            } else {
                lockText = `🔒 Locked (lock #${lockId})`;
                if (isPickable) {
                    lockText += ' - ⛏️ Pickable';
                }
            }
            html += `<div class="tooltip-info" style="color: #ff6b6b; font-size: 0.85rem;">${lockText}</div>`;
        }
        // Doors: show type + health/condition
        if (objId >= 0x140 && objId <= 0x14F && item.extra_info) {
            const doorVariant = item.extra_info.door_variant || '';
            const doorHealth = item.extra_info.door_health;
            const doorMax = item.extra_info.door_max_health !== undefined ? item.extra_info.door_max_health : 40;
            const doorCond = item.extra_info.door_condition || '';
            
            const variantText = doorVariant ? ` • ${escapeHtml(String(doorVariant).replace(/_/g, ' '))}` : '';
            
            const condDisplay = doorCond;
            html += `<div class="tooltip-info" style="font-size: 0.8rem; color: var(--text-muted);">Status: ${escapeHtml(condDisplay)}${variantText}</div>`;
            if (doorHealth !== undefined) {
                const healthText = (doorCond === 'massive') ? 'unbreakable' : `${doorHealth}/${doorMax}`;
                html += `<div class="tooltip-info" style="font-family: var(--font-mono); font-size: 0.8rem; color: var(--text-accent);">Health: ${healthText}</div>`;
            }
        }
        // Show lock number for keys (0x100-0x10E)
        if (objId >= 0x100 && objId <= 0x10E && item.effect) {
            const lockMatch = item.effect.match(/lock #(\d+)/i);
            if (lockMatch) {
                html += `<div class="tooltip-info" style="color: #fab005; font-size: 0.85rem;">🔑 Opens lock #${lockMatch[1]}</div>`;
            }
        }
        // Show effect preview in tooltip only for truly magical effects
        if (isMagicalEffect(item.effect)) {
            html += `<div class="tooltip-info" style="color: #9775fa; font-size: 0.8rem;">✨ ${escapeHtml(truncateText(item.effect, 50))}</div>`;
        }
        // Show description for books/scrolls/writing/gravestones with enhanced formatting
        // Books/scrolls: 0x130-0x13F (excluding 0x13B map) = 304-319 (excluding 315)
        // Gravestones: 0x165 = 357, Writings: 0x166 = 358
        const objIdNum = Number(objId);
        const isBookOrScroll = (objIdNum >= 304 && objIdNum <= 319 && objIdNum !== 315);
        const isStationaryWriting = (objIdNum === 357 || objIdNum === 358);
        const isReadable = isBookOrScroll || isStationaryWriting;
        const hasDescDetail = item.description && String(item.description).trim().length > 0;
        if (hasDescDetail) {
            if (isReadable) {
                // For readable items, show longer text with book styling
                const maxLen = 200;
                const displayText = item.description.length > maxLen 
                    ? item.description.substring(0, maxLen) + '...' 
                    : item.description;
                const icon = (objIdNum === 357) ? '🪦' : (objIdNum === 358) ? '📝' : '📜';
                html += `<div class="tooltip-book-content" style="color: #e8d4b8; font-size: 0.8rem; margin-top: 6px; padding: 6px 8px; background: rgba(232, 212, 184, 0.08); border-left: 2px solid #e8d4b8; border-radius: 2px; font-style: italic; white-space: pre-wrap; max-width: 250px; line-height: 1.4;">${icon} "${escapeHtml(displayText)}"</div>`;
            } else {
                // For other items (keys, etc.) show short preview
                html += `<div class="tooltip-info" style="color: var(--text-accent); font-size: 0.8rem;">${escapeHtml(truncateText(item.description, 60))}</div>`;
            }
        }
        // Show container capacity and weight for containers
        if (item.capacity !== undefined) {
            let containerInfo = `📦 Capacity: ${item.capacity} stone${item.capacity !== 1 ? 's' : ''}`;
            if (item.accepts && item.accepts !== 'any') {
                containerInfo += ` (${item.accepts} only)`;
            }
            html += `<div class="tooltip-info" style="color: var(--text-accent);">${containerInfo}</div>`;
        }
        // Show container count
        if (item.contents && item.contents.length > 0) {
            html += `<div class="tooltip-info" style="color: var(--text-accent);">📦 ${item.contents.length} item${item.contents.length > 1 ? 's' : ''} inside</div>`;
        }
    }
    
    // Check if there are multiple items at this tile
    const otherItemsAtTile = countOtherItemsAtTile(item.tile_x, item.tile_y, item.id);
    if (otherItemsAtTile > 0) {
        html += `<div class="tooltip-stacked" style="color: var(--text-accent); font-size: 0.8rem; margin-top: 4px; padding-top: 4px; border-top: 1px dashed var(--border-color);">📍 +${otherItemsAtTile} more item${otherItemsAtTile > 1 ? 's' : ''} here</div>`;
    }
    
    html += `<div class="tooltip-position">Tile: (${item.tile_x}, ${item.tile_y})</div>`;
    
    // Show change information when a save game is loaded
    if (state.saveGame.currentSaveName && item.change_type) {
        const changeColor = window.SaveComparator?.getChangeTypeColor(item.change_type) || '#868e96';
        const changeIcon = window.SaveComparator?.getChangeTypeIcon(item.change_type) || '';
        const changeLabel = window.SaveComparator?.getChangeTypeLabel(item.change_type) || item.change_type;
        const changeDesc = window.SaveComparator?.formatChangeDescription(item) || '';
        
        html += `<div class="tooltip-change" style="margin-top: 6px; padding-top: 6px; border-top: 1px solid var(--border-color);">`;
        html += `<div style="color: ${changeColor}; font-weight: 500;">${changeIcon} ${changeLabel}</div>`;
        if (changeDesc && item.change_type !== 'unchanged') {
            html += `<div style="color: var(--text-secondary); font-size: 0.75rem; margin-top: 2px;">${escapeHtml(changeDesc)}</div>`;
        }
        html += `</div>`;
    }
    
    tooltip.innerHTML = html;
    tooltip.classList.add('visible');
    
    // Position tooltip
    updateTooltipPosition(e);
}

/**
 * Count how many other visible items are at the same tile (excluding the current item)
 */
function countOtherItemsAtTile(tileX, tileY, excludeId) {
    const level = state.data.levels[state.currentLevel];
    if (!level) return 0;
    
    let count = 0;
    
    // Count NPCs at this tile
    level.npcs.forEach(npc => {
        if (npc.tile_x === tileX && npc.tile_y === tileY && npc.id !== excludeId) {
            const npcCategory = getNpcCategory(npc);
            const npcCategoryMatch = state.filters.categories.has(npcCategory);
            const hasMatchingInventory = hasContentMatchingCategory(npc.inventory);
            if ((npcCategoryMatch || hasMatchingInventory) && shouldShowItem(npc)) {
                count++;
            }
        }
    });
    
    // Count objects at this tile
    level.objects.forEach(obj => {
        if (obj.tile_x === tileX && obj.tile_y === tileY && obj.id !== excludeId) {
            const objCategoryMatch = state.filters.categories.has(obj.category);
            const hasMatchingContents = hasContentMatchingCategory(obj.contents);
            if ((objCategoryMatch || hasMatchingContents) && shouldShowItem(obj)) {
                count++;
            }
        }
    });
    
    return count;
}

function updateTooltipPosition(e) {
    const tooltip = elements.tooltip;
    const rect = tooltip.getBoundingClientRect();
    
    let x = e.clientX + 15;
    let y = e.clientY + 15;
    
    // Keep tooltip on screen
    if (x + rect.width > window.innerWidth) {
        x = e.clientX - rect.width - 15;
    }
    if (y + rect.height > window.innerHeight) {
        y = e.clientY - rect.height - 15;
    }
    
    tooltip.style.left = `${x}px`;
    tooltip.style.top = `${y}px`;
}

function hideTooltip() {
    // Clear any pending hide timeout
    if (state.tooltipHideTimeout) {
        clearTimeout(state.tooltipHideTimeout);
        state.tooltipHideTimeout = null;
    }
    elements.tooltip.classList.remove('visible');
    elements.tooltip.classList.remove('interactive');
}

/**
 * Schedule tooltip to hide after a delay (allows moving mouse to tooltip)
 */
function scheduleHideTooltip() {
    // Clear any existing timeout
    if (state.tooltipHideTimeout) {
        clearTimeout(state.tooltipHideTimeout);
    }
    
    // Delay hiding to allow mouse to move to tooltip
    state.tooltipHideTimeout = setTimeout(() => {
        if (!state.isTooltipHovered) {
            hideTooltip();
        }
    }, 150);
}

/**
 * Set up tooltip hover tracking (called once during init)
 */
function setupTooltipHoverTracking() {
    elements.tooltip.addEventListener('mouseenter', () => {
        state.isTooltipHovered = true;
        // Cancel any pending hide
        if (state.tooltipHideTimeout) {
            clearTimeout(state.tooltipHideTimeout);
            state.tooltipHideTimeout = null;
        }
    });
    
    elements.tooltip.addEventListener('mouseleave', () => {
        state.isTooltipHovered = false;
        hideTooltip();
    });
}

// ============================================================================
// Selection & Details
// ============================================================================

function selectItem(item, isNpc, markerElement) {
    // Clear previous selection and restore original size (individual markers)
    document.querySelectorAll('.marker.selected').forEach(m => {
        m.classList.remove('selected');
        if (m.dataset.isStarMarker === 'true') {
            m.style.transform = 'scale(1)';
        } else {
            const origR = parseFloat(m.dataset.originalRadius) || CONFIG.marker.radius;
            m.setAttribute('r', origR);
        }
    });
    
    // Clear stacked marker groups (also reset inline styles)
    document.querySelectorAll('.marker-stack.selected').forEach(g => {
        g.classList.remove('selected');
        clearStackedMarkerStyles(g);
    });
    
    // Clear secret marker groups
    document.querySelectorAll('.secret-marker.selected').forEach(g => {
        g.classList.remove('selected');
        // Reset transform
        const visualGroup = g.querySelector('.secret-visual');
        if (visualGroup) {
            visualGroup.setAttribute('transform', `translate(${visualGroup.dataset.centerX}, ${visualGroup.dataset.centerY})`);
        }
        // Reset stroke widths
        const lines = g.querySelectorAll('.secret-x');
        lines.forEach(line => line.setAttribute('stroke-width', '2'));
        const diamonds = g.querySelectorAll('.secret-diamond');
        diamonds.forEach(diamond => diamond.setAttribute('stroke-width', '1'));
    });
    
    // Mark new selection and increase size
    markerElement.classList.add('selected');
    if (markerElement.dataset.isStarMarker === 'true') {
        markerElement.style.transform = 'scale(1.8)';
    } else {
        const origR = parseFloat(markerElement.dataset.originalRadius) || CONFIG.marker.radius;
        markerElement.setAttribute('r', origR * 1.8);
    }
    state.selectedMarker = markerElement;
    
    // Ensure selection pane layout is rendered
    renderSelectionPane();
    
    // Update details panel
    renderObjectDetails(item, isNpc);
    
    // Find all items at same tile, passing the selected item id
    renderLocationObjects(item.tile_x, item.tile_y, item.id);
    
    updateUrlHash();
}

/**
 * Apply visual selection styles to a stacked marker group
 * Matches the style of individual marker selection (enlarge + glow)
 */
function applyStackedMarkerSelectionStyles(group) {
    const countBadge = group.querySelector('.count-badge');
    
    if (countBadge) {
        const circle = countBadge.querySelector('circle');
        const text = countBadge.querySelector('text');
        
        if (circle) {
            // Store original radius if not already stored
            if (!circle.dataset.originalRadius) {
                circle.dataset.originalRadius = circle.getAttribute('r');
            }
            // Scale up radius by 1.8x (matching individual markers)
            const origR = parseFloat(circle.dataset.originalRadius);
            circle.setAttribute('r', origR * 1.8);
            // Apply glow filter to the circle
            circle.style.filter = 'brightness(1.4) drop-shadow(0 0 8px rgba(212, 168, 85, 0.9))';
        }
        
        if (text) {
            // Store original font size if not already stored
            if (!text.dataset.originalFontSize) {
                text.dataset.originalFontSize = text.getAttribute('font-size');
            }
            // Scale up font size by 1.8x
            const origSize = parseFloat(text.dataset.originalFontSize);
            text.setAttribute('font-size', origSize * 1.8);
        }
    }
}

/**
 * Clear visual selection styles from a stacked marker group
 */
function clearStackedMarkerStyles(group) {
    const countBadge = group.querySelector('.count-badge');
    
    if (countBadge) {
        const circle = countBadge.querySelector('circle');
        const text = countBadge.querySelector('text');
        
        if (circle && circle.dataset.originalRadius) {
            // Restore original radius
            circle.setAttribute('r', circle.dataset.originalRadius);
            circle.style.filter = '';
        }
        
        if (text && text.dataset.originalFontSize) {
            // Restore original font size
            text.setAttribute('font-size', text.dataset.originalFontSize);
        }
    }
}

/**
 * Apply hover scale effect to a marker (same as selection scale 1.8x)
 * Used when hovering over items in the visible objects list
 */
function applyMarkerHoverEffect(markerElement) {
    if (!markerElement) return;
    
    // Don't apply hover effect if already selected
    if (markerElement.classList.contains('selected')) return;
    
    // Mark as hovered
    markerElement.classList.add('hovered-from-list');
    
    if (markerElement.dataset.isStarMarker === 'true') {
        markerElement.style.transform = 'scale(1.8)';
    } else if (markerElement.tagName === 'circle') {
        const origR = parseFloat(markerElement.dataset.originalRadius) || CONFIG.marker.radius;
        markerElement.setAttribute('r', origR * 1.8);
    }
}

/**
 * Remove hover scale effect from a marker
 */
function removeMarkerHoverEffect(markerElement) {
    if (!markerElement) return;
    
    // Only remove if we're the one that applied the hover effect
    if (!markerElement.classList.contains('hovered-from-list')) return;
    
    // Don't remove if selected
    if (markerElement.classList.contains('selected')) {
        markerElement.classList.remove('hovered-from-list');
        return;
    }
    
    markerElement.classList.remove('hovered-from-list');
    
    if (markerElement.dataset.isStarMarker === 'true') {
        markerElement.style.transform = 'scale(1)';
    } else if (markerElement.tagName === 'circle') {
        const origR = parseFloat(markerElement.dataset.originalRadius) || CONFIG.marker.radius;
        markerElement.setAttribute('r', origR);
    }
}

/**
 * Apply hover scale effect to a stacked marker group
 */
function applyStackedMarkerHoverEffect(group) {
    if (!group) return;
    
    // Don't apply hover effect if already selected
    if (group.classList.contains('selected')) return;
    
    // Mark as hovered
    group.classList.add('hovered-from-list');
    
    const countBadge = group.querySelector('.count-badge');
    if (countBadge) {
        const circle = countBadge.querySelector('circle');
        const text = countBadge.querySelector('text');
        
        if (circle) {
            // Store original radius if not already stored
            if (!circle.dataset.originalRadius) {
                circle.dataset.originalRadius = circle.getAttribute('r');
            }
            // Scale up radius by 1.8x (matching selection)
            const origR = parseFloat(circle.dataset.originalRadius);
            circle.setAttribute('r', origR * 1.8);
        }
        
        if (text) {
            // Store original font size if not already stored
            if (!text.dataset.originalFontSize) {
                text.dataset.originalFontSize = text.getAttribute('font-size');
            }
            // Scale up font size by 1.8x
            const origSize = parseFloat(text.dataset.originalFontSize);
            text.setAttribute('font-size', origSize * 1.8);
        }
    }
}

/**
 * Remove hover scale effect from a stacked marker group
 */
function removeStackedMarkerHoverEffect(group) {
    if (!group) return;
    
    // Only remove if we're the one that applied the hover effect
    if (!group.classList.contains('hovered-from-list')) return;
    
    // Don't remove if selected
    if (group.classList.contains('selected')) {
        group.classList.remove('hovered-from-list');
        return;
    }
    
    group.classList.remove('hovered-from-list');
    clearStackedMarkerStyles(group);
}

/**
 * Apply hover scale effect to a secret marker group
 */
function applySecretMarkerHoverEffect(group) {
    if (!group) return;
    
    // Don't apply hover effect if already selected
    if (group.classList.contains('selected')) return;
    
    // Mark as hovered
    group.classList.add('hovered-from-list');
    
    const visualGroup = group.querySelector('.secret-visual');
    if (visualGroup && visualGroup.dataset.centerX && visualGroup.dataset.centerY) {
        visualGroup.setAttribute('transform', `translate(${visualGroup.dataset.centerX}, ${visualGroup.dataset.centerY}) scale(1.8)`);
    }
}

/**
 * Remove hover scale effect from a secret marker group
 */
function removeSecretMarkerHoverEffect(group) {
    if (!group) return;
    
    // Only remove if we're the one that applied the hover effect
    if (!group.classList.contains('hovered-from-list')) return;
    
    // Don't remove if selected
    if (group.classList.contains('selected')) {
        group.classList.remove('hovered-from-list');
        return;
    }
    
    group.classList.remove('hovered-from-list');
    
    const visualGroup = group.querySelector('.secret-visual');
    if (visualGroup && visualGroup.dataset.centerX && visualGroup.dataset.centerY) {
        visualGroup.setAttribute('transform', `translate(${visualGroup.dataset.centerX}, ${visualGroup.dataset.centerY})`);
    }
}

/**
 * Find and apply hover effect to marker(s) on the map for a given item
 */
function applyHoverEffectToMapMarker(item, isNpc, isSecret) {
    if (isSecret) {
        // Find secret marker by ID
        const secretGroups = document.querySelectorAll('.secret-marker');
        for (const group of secretGroups) {
            if (group.dataset.id === String(item.id)) {
                applySecretMarkerHoverEffect(group);
                break;
            }
        }
    } else {
        // First try to find an individual marker
        const markers = document.querySelectorAll('.marker');
        let foundMarker = false;
        for (const marker of markers) {
            if (marker.dataset.id === String(item.id) && 
                marker.dataset.isNpc === String(isNpc)) {
                applyMarkerHoverEffect(marker);
                foundMarker = true;
                break;
            }
        }
        
        // If no individual marker found, look for stacked marker group
        if (!foundMarker) {
            const stackedGroups = document.querySelectorAll('.marker-stack');
            for (const group of stackedGroups) {
                if (group.dataset.tileX === String(item.tile_x) && 
                    group.dataset.tileY === String(item.tile_y)) {
                    applyStackedMarkerHoverEffect(group);
                    break;
                }
            }
        }
    }
}

/**
 * Find and remove hover effect from marker(s) on the map for a given item
 */
function removeHoverEffectFromMapMarker(item, isNpc, isSecret) {
    if (isSecret) {
        // Find secret marker by ID
        const secretGroups = document.querySelectorAll('.secret-marker');
        for (const group of secretGroups) {
            if (group.dataset.id === String(item.id)) {
                removeSecretMarkerHoverEffect(group);
                break;
            }
        }
    } else {
        // First try to find an individual marker
        const markers = document.querySelectorAll('.marker');
        let foundMarker = false;
        for (const marker of markers) {
            if (marker.dataset.id === String(item.id) && 
                marker.dataset.isNpc === String(isNpc)) {
                removeMarkerHoverEffect(marker);
                foundMarker = true;
                break;
            }
        }
        
        // If no individual marker found, look for stacked marker group
        if (!foundMarker) {
            const stackedGroups = document.querySelectorAll('.marker-stack');
            for (const group of stackedGroups) {
                if (group.dataset.tileX === String(item.tile_x) && 
                    group.dataset.tileY === String(item.tile_y)) {
                    removeStackedMarkerHoverEffect(group);
                    break;
                }
            }
        }
    }
}

function clearSelection() {
    // Clear individual markers
    document.querySelectorAll('.marker.selected').forEach(m => {
        m.classList.remove('selected');
        if (m.dataset.isStarMarker === 'true') {
            m.style.transform = 'scale(1)';
        } else {
            const origR = parseFloat(m.dataset.originalRadius) || CONFIG.marker.radius;
            m.setAttribute('r', origR);
        }
    });
    
    // Clear stacked marker groups (also reset inline styles)
    document.querySelectorAll('.marker-stack.selected').forEach(g => {
        g.classList.remove('selected');
        clearStackedMarkerStyles(g);
    });
    
    // Clear secret marker groups
    document.querySelectorAll('.secret-marker.selected').forEach(g => {
        g.classList.remove('selected');
        // Reset transform
        const visualGroup = g.querySelector('.secret-visual');
        if (visualGroup) {
            visualGroup.setAttribute('transform', `translate(${visualGroup.dataset.centerX}, ${visualGroup.dataset.centerY})`);
        }
        // Reset stroke widths
        const lines = g.querySelectorAll('.secret-x');
        lines.forEach(line => line.setAttribute('stroke-width', '2'));
        const diamonds = g.querySelectorAll('.secret-diamond');
        diamonds.forEach(diamond => diamond.setAttribute('stroke-width', '1'));
    });
    
    state.selectedMarker = null;
    
    // Show all visible objects list view
    renderVisibleObjectsPane();
    updateUrlHash();
}

/**
 * Refresh the visible objects list only if no object is currently selected
 * Called after filter changes to update the list
 */
function refreshVisibleObjectsIfNoSelection() {
    if (state.selectedMarker === null) {
        renderVisibleObjectsPane();
    }
}

/**
 * Render the selection view with two sections: Selected Object and Objects at Location
 */
function renderSelectionPane() {
    elements.detailsSidebar.innerHTML = `
        <div class="sidebar-section">
            <div class="section-header">
                <h3 class="section-title">Selected Object</h3>
                <button class="close-selection-btn" id="close-selection-btn" title="Close and return to visible objects">✕</button>
            </div>
            <div class="object-details" id="object-details">
                <p class="no-selection">Loading...</p>
            </div>
        </div>
        <div class="sidebar-section">
            <h3 class="section-title">Objects at Location</h3>
            <div class="location-objects" id="location-objects">
                <p class="no-selection">Click a marker to see all objects at that tile</p>
            </div>
        </div>
    `;
    // Update element references
    elements.objectDetails = document.getElementById('object-details');
    elements.locationObjects = document.getElementById('location-objects');
    
    // Add close button handler
    document.getElementById('close-selection-btn').addEventListener('click', clearSelection);
}

/**
 * Render the visible objects list as the entire right pane
 * This is shown when no specific object is selected
 */
function renderVisibleObjectsPane() {
    const level = state.data?.levels[state.currentLevel];
    if (!level) {
        elements.detailsSidebar.innerHTML = `
            <div class="sidebar-section" style="flex: 1;">
                <h3 class="section-title">Visible Objects</h3>
                <p class="no-selection">No level data</p>
            </div>
        `;
        return;
    }
    
    // Collect all visible items based on current filters
    const visibleItems = [];
    
    // Collect NPCs
    level.npcs.forEach(npc => {
        const npcCategory = getNpcCategory(npc);
        const npcCategoryMatch = state.filters.categories.has(npcCategory);
        const hasMatchingInventory = hasContentMatchingCategory(npc.inventory);
        
        if ((npcCategoryMatch || hasMatchingInventory) && shouldShowItem(npc) && shouldShowBasedOnChanges(npc)) {
            visibleItems.push({ item: npc, isNpc: true, isSecret: false });
        }
    });
    
    // Collect objects
    level.objects.forEach(obj => {
        // Skip secret doors that match base secrets (they're shown as secrets, not objects)
        if (isSecretDoorMatchingBaseSecret(obj, level)) {
            return;
        }
        
        const objCategoryMatch = state.filters.categories.has(obj.category);
        const hasMatchingContents = hasContentMatchingCategory(obj.contents);
        
        if ((objCategoryMatch || hasMatchingContents) && shouldShowItem(obj) && shouldShowBasedOnChanges(obj)) {
            visibleItems.push({ item: obj, isNpc: false, isSecret: false });
        }
    });
    
    // Collect removed objects when a save game is loaded and 'removed' filter is active
    if (state.saveGame.currentSaveName && state.filters.changeTypes.has('removed')) {
        const currentSave = state.saveGame.saves[state.saveGame.currentSaveName];
        if (currentSave && currentSave.changes && currentSave.changes[state.currentLevel]) {
            const levelChanges = currentSave.changes[state.currentLevel];
            const removedItems = levelChanges.removed || [];
            
            removedItems.forEach(change => {
                const baseObj = change.base_data;
                if (!baseObj) return;
                
                // Create a display object from the base data with removed marker
                const removedObj = {
                    ...baseObj,
                    change_type: 'removed',
                    changed_properties: change.changed_properties || []
                };
                
                // Check category filter
                const isNpc = change.is_npc;
                let categoryMatch = false;
                
                if (isNpc) {
                    const npcCategory = getNpcCategory(removedObj);
                    categoryMatch = state.filters.categories.has(npcCategory);
                } else {
                    categoryMatch = state.filters.categories.has(removedObj.category);
                }
                
                if (categoryMatch && shouldShowItem(removedObj)) {
                    visibleItems.push({ item: removedObj, isNpc: isNpc, isSecret: false });
                }
            });
        }
    }
    
    // Collect secrets (not shown when enchanted filter is on)
    // Note: Secrets can never be owned, so they're hidden when owned filter is set to "only"
    // Note: Secrets are static base game data - hide them when change filter excludes 'unchanged'
    const showSecretsInList = level.secrets && 
                              !state.filters.enchantedOnly && 
                              state.filters.ownedFilter !== 'only' &&
                              (!state.saveGame || state.filters.changeTypes.has('unchanged'));
    
    if (showSecretsInList) {
        level.secrets.forEach(secret => {
            if (!state.filters.categories.has(secret.category)) return;
            
            // Apply search filter
            if (state.filters.search) {
                const desc = (secret.description || '').toLowerCase();
                const type = (secret.type || '').toLowerCase();
                if (!desc.includes(state.filters.search) && !type.includes(state.filters.search)) {
                    return;
                }
            }
            
            visibleItems.push({ item: secret, isNpc: false, isSecret: true });
        });
    }
    
    // Build category order map to match sidebar order:
    // 1. NPCs categories first (named, friendly, hostile)
    // 2. Items categories
    // 3. World categories
    const categoryOrder = new Map();
    let orderIndex = 0;
    
    // NPCs section
    CATEGORY_GROUPS.npcs.forEach(categoryId => {
        categoryOrder.set(categoryId, orderIndex++);
    });
    
    // Items section
    CATEGORY_GROUPS.items.forEach(categoryId => {
        categoryOrder.set(categoryId, orderIndex++);
    });
    
    // World section
    CATEGORY_GROUPS.world.forEach(categoryId => {
        categoryOrder.set(categoryId, orderIndex++);
    });
    
    function getCategoryOrderIndex(categoryId) {
        return categoryOrder.has(categoryId) ? categoryOrder.get(categoryId) : 9999;
    }
    
    // Sort by category (matching sidebar order), then by name
    visibleItems.sort((a, b) => {
        // Get category for each item
        const catA = a.isNpc ? getNpcCategory(a.item) : a.item.category;
        const catB = b.isNpc ? getNpcCategory(b.item) : b.item.category;
        // Sort by sidebar order
        const orderA = getCategoryOrderIndex(catA);
        const orderB = getCategoryOrderIndex(catB);
        if (orderA !== orderB) return orderA - orderB;
        // Then by name
        const nameA = a.item.name || '';
        const nameB = b.item.name || '';
        return nameA.localeCompare(nameB);
    });
    
    // Build the sidebar content
    elements.detailsSidebar.innerHTML = '';
    
    // Single section that fills the pane
    const section = document.createElement('div');
    section.className = 'sidebar-section visible-objects-pane';
    section.style.cssText = 'flex: 1; display: flex; flex-direction: column; overflow: hidden;';
    
    // Header
    const header = document.createElement('div');
    header.className = 'visible-objects-header';
    header.style.cssText = `
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
        flex-shrink: 0;
        gap: 8px;
    `;
    header.innerHTML = `
        <h3 class="section-title" style="margin-bottom: 0; flex: 1;">Visible Objects</h3>
        <div class="collapse-toggle-btns" style="display: flex; gap: 4px;">
            <button class="toggle-btn" id="expand-all-categories" title="Expand All">▼</button>
            <button class="toggle-btn" id="collapse-all-categories" title="Collapse All">▲</button>
        </div>
        <span style="color: var(--text-accent); font-family: var(--font-mono); font-size: 0.9rem; background: var(--bg-tertiary); padding: 4px 10px; border-radius: 12px;">${visibleItems.length}</span>
    `;
    section.appendChild(header);
    
    if (visibleItems.length === 0) {
        const empty = document.createElement('p');
        empty.className = 'no-selection';
        empty.textContent = 'No visible objects match filters';
        section.appendChild(empty);
        elements.detailsSidebar.appendChild(section);
        return;
    }
    
    // Scrollable list container
    const listContainer = document.createElement('div');
    listContainer.className = 'visible-objects-list';
    listContainer.style.cssText = `
        flex: 1;
        overflow-y: auto;
        margin: 0 -16px;
        padding: 0 16px;
    `;
    
    // Group items by category for better organization
    const groupedItems = new Map();
    visibleItems.forEach(({ item, isNpc, isSecret }) => {
        let category;
        if (isNpc) category = getNpcCategory(item);  // Use specific NPC category
        else if (isSecret) category = item.category;
        else category = item.category;
        
        if (!groupedItems.has(category)) {
            groupedItems.set(category, []);
        }
        groupedItems.get(category).push({ item, isNpc, isSecret });
    });
    
    // Add expand/collapse all button handlers (now that groupedItems exists)
    header.querySelector('#expand-all-categories').addEventListener('click', () => {
        state.collapsedCategories.clear();
        renderVisibleObjectsPane();
        saveFiltersToStorage();
    });
    header.querySelector('#collapse-all-categories').addEventListener('click', () => {
        // Collapse ALL possible categories, not just those on the current level
        // This ensures consistent collapsed state when switching levels
        categoryOrder.forEach((_, categoryId) => {
            state.collapsedCategories.add(categoryId);
        });
        renderVisibleObjectsPane();
        saveFiltersToStorage();
    });
    
    // Render each category group
    groupedItems.forEach((items, categoryId) => {
        const isCollapsed = state.collapsedCategories.has(categoryId);
        
        // Category header (clickable to toggle)
        const categoryHeader = document.createElement('div');
        categoryHeader.className = 'category-group-header collapsible-header' + (isCollapsed ? ' collapsed' : '');
        const catColor = categoryId === 'npcs_hostile' ? '#ff4444' :
                         categoryId === 'npcs_friendly' ? '#69db7c' :
                         categoryId === 'npcs_named' ? '#ffd43b' :
                         categoryId === 'illusory_walls' ? '#ff00ff' :
                         categoryId === 'secret_doors' ? '#ffff00' :
                         getCategoryColor(categoryId);
        const catName = categoryId === 'npcs_hostile' ? 'Hostile NPCs' :
                        categoryId === 'npcs_friendly' ? 'Friendly NPCs' :
                        categoryId === 'npcs_named' ? 'Named NPCs' :
                        formatCategory(categoryId);
        categoryHeader.style.cssText = `
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 0 4px 0;
            margin-top: 4px;
            color: ${catColor};
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 1px solid var(--border-color);
            position: sticky;
            top: 0;
            background: var(--bg-secondary);
            z-index: 1;
            cursor: pointer;
            user-select: none;
            transition: background 0.15s ease;
        `;
        categoryHeader.innerHTML = `
            <span class="collapse-chevron" style="font-size: 0.65rem; transition: transform 0.2s ease; transform: rotate(${isCollapsed ? '-90deg' : '0deg'});">▼</span>
            <span style="width: 8px; height: 8px; background: ${catColor}; border-radius: 50%; flex-shrink: 0;"></span>
            <span style="flex: 1;">${catName}</span>
            <span style="color: var(--text-muted); font-weight: normal;">${items.length}</span>
        `;
        
        // Toggle collapse on click
        categoryHeader.addEventListener('click', () => {
            if (state.collapsedCategories.has(categoryId)) {
                state.collapsedCategories.delete(categoryId);
            } else {
                state.collapsedCategories.add(categoryId);
            }
            renderVisibleObjectsPane();
            saveFiltersToStorage();
        });
        
        // Hover effect
        categoryHeader.addEventListener('mouseenter', () => {
            categoryHeader.style.background = 'var(--bg-tertiary)';
        });
        categoryHeader.addEventListener('mouseleave', () => {
            categoryHeader.style.background = 'var(--bg-secondary)';
        });
        
        listContainer.appendChild(categoryHeader);
        
        // Create collapsible container for items
        const itemsContainer = document.createElement('div');
        itemsContainer.className = 'category-items-container' + (isCollapsed ? ' collapsed' : '');
        itemsContainer.style.cssText = isCollapsed ? 'display: none;' : '';
        
        // Render items in this category
        items.forEach(({ item, isNpc, isSecret }) => {
            const itemEl = document.createElement('div');
            itemEl.className = 'visible-object-item';
            itemEl.style.cssText = `
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 8px 10px;
                margin: 2px 0;
                background: var(--bg-tertiary);
                border-left: 3px solid ${catColor};
                border-radius: 0 4px 4px 0;
                cursor: pointer;
                transition: background 0.15s ease, transform 0.1s ease;
                font-size: 0.85rem;
            `;
            
            // Build item content
            let icon, displayName, subtitle, enchantLine = '';
            if (isSecret) {
                icon = item.type === 'illusory_wall' ? '🔮' : '🚪';
                displayName = item.type === 'illusory_wall' ? 'Illusory Wall' : 'Secret Door';
                subtitle = `(${item.tile_x}, ${item.tile_y})`;
                // Show "Reveals" info and reveal method for illusory walls
                if (item.type === 'illusory_wall' && item.details) {
                    let revealInfo = '';
                    if (item.details.new_tile_type) {
                        revealInfo = `Reveals: ${escapeHtml(item.details.new_tile_type)}`;
                    }
                    // Show reveal method
                    const triggerString = item.details.trigger;
                    const revealMethod = getIllusoryWallRevealMethod(triggerString);
                    // Remove HTML tags for the list view
                    const revealMethodText = revealMethod.replace(/<[^>]*>/g, '');
                    revealInfo += revealInfo ? '<br>' : '';
                    if (triggerString) {
                        revealInfo += revealMethodText;
                    } else {
                        revealInfo += `✨ ${revealMethodText}`;
                    }
                    if (revealInfo) {
                        enchantLine = `<div style="color: var(--text-accent); font-size: 0.7rem; margin-top: 2px;">${revealInfo}</div>`;
                    }
                }
                // Show lock info for locked secret doors
                if (item.type === 'secret_door' && item.details && item.details.is_locked) {
                    const lockId = item.details.lock_id;
                    const lockType = item.details.lock_type;
                    const isPickable = item.details.is_pickable;
                    let lockText = '';
                    if (lockType === 'special') {
                        lockText = '🔒 Special Lock';
                    } else if (lockId !== undefined) {
                        lockText = `🔒 Lock #${lockId}`;
                        if (isPickable) {
                            lockText += ' ⛏️';  // Can be picked
                        }
                    } else {
                        lockText = '🔒 Locked';
                    }
                    enchantLine = `<div style="color: #ff6b6b; font-size: 0.7rem; margin-top: 2px;">${lockText}</div>`;
                }
                // Show health for secret doors (they can be broken down)
                if (item.type === 'secret_door' && item.details && item.details.door_health !== undefined) {
                    const doorHealth = item.details.door_health;
                    const doorMax = item.details.door_max_health !== undefined ? item.details.door_max_health : 40;
                    enchantLine += `<div style="color: var(--text-accent); font-size: 0.7rem; font-family: var(--font-mono); margin-top: 2px;">Health: ${doorHealth}/${doorMax}</div>`;
                }
            } else if (isNpc) {
                const isUnique = hasUniqueName(item);
                icon = isUnique ? '⭐' : '👤';
                displayName = item.name || 'Unknown NPC';
                subtitle = `HP ${item.hp} • (${item.tile_x}, ${item.tile_y})`;
            } else {
                const itemEnchanted = isEnchanted(item);
                icon = itemEnchanted ? '✨' : '•';
                displayName = getItemDisplayName(item);
                subtitle = `(${item.tile_x}, ${item.tile_y})`;
                // Show enchantment effect for enchanted items (including spell scrolls)
                // Also show effect for spell_scrolls category directly (they always have spell effects)
                if (item.category === 'spell_scrolls' && item.effect) {
                    enchantLine = `<div style="color: #da77f2; font-size: 0.7rem; margin-top: 2px;">⚡ ${escapeHtml(item.effect)}</div>`;
                } else if (itemEnchanted && item.effect && isMagicalEffect(item.effect)) {
                    // Use gold for other enchantments
                    enchantLine = `<div style="color: var(--text-accent); font-size: 0.7rem; margin-top: 2px;">⚡ ${escapeHtml(item.effect)}</div>`;
                }
                // Show lock info for doors
                const isLocked = item.extra_info && item.extra_info.is_locked;
                const lockId = item.extra_info && item.extra_info.lock_id;
                const lockType = item.extra_info && item.extra_info.lock_type;
                const isPickable = item.extra_info && item.extra_info.is_pickable;
                if (isLocked) {
                    let lockText = '';
                    if (lockType === 'special') {
                        lockText = '🔒 Special Lock';
                    } else if (lockId !== undefined) {
                        lockText = `🔒 Lock #${lockId}`;
                        if (isPickable) {
                            lockText += ' ⛏️';  // Can be picked
                        }
                    } else {
                        lockText = '🔒 Locked';
                    }
                    enchantLine = `<div style="color: #ff6b6b; font-size: 0.7rem; margin-top: 2px;">${lockText}</div>`;
                }
                // Show health for doors (0x140-0x14F)
                const objId = item.object_id || 0;
                const isDoorObj = (objId >= 0x140 && objId <= 0x14F);
                if (isDoorObj && item.extra_info && item.extra_info.door_health !== undefined) {
                    const doorCond = item.extra_info.door_condition || '';
                    const doorMax = item.extra_info.door_max_health !== undefined ? item.extra_info.door_max_health : 40;
                    const healthText = (doorCond === 'massive') ? 'massive' : `${item.extra_info.door_health}/${doorMax}`;
                    enchantLine += `<div style="color: var(--text-accent); font-size: 0.7rem; font-family: var(--font-mono); margin-top: 2px;">Health: ${healthText}</div>`;
                }
                // Show lock info for keys (0x100-0x10E) - they have "Opens lock #N" in effect field
                if (objId >= 0x100 && objId <= 0x10E) {
                    const effectText = item.effect || '';
                    const match = effectText.match(/lock #(\d+)/i);
                    if (match) {
                        enchantLine = `<div style="color: #fab005; font-size: 0.7rem; margin-top: 2px;">🔑 Opens Lock #${match[1]}</div>`;
                    }
                }
                // Show damage info for melee weapons
                if (objId <= 0x0F && (item.slash_damage !== undefined || item.bash_damage !== undefined || item.stab_damage !== undefined)) {
                    enchantLine += `<div style="color: #e03131; font-size: 0.7rem; font-family: var(--font-mono); margin-top: 2px;">${formatDamage(item)}</div>`;
                }
                // Show durability for weapons (melee and ranged)
                if (objId <= 0x1F && item.max_durability !== undefined) {
                    enchantLine += `<div style="color: #fab005; font-size: 0.7rem; font-family: var(--font-mono); margin-top: 2px;">${formatDurability(item)}</div>`;
                }
                // Show protection/durability for armor
                if (isArmor(item) && (item.protection !== undefined || item.max_durability !== undefined)) {
                    enchantLine += `<div style="color: #5c7cfa; font-size: 0.7rem; font-family: var(--font-mono); margin-top: 2px;">${formatArmor(item)}</div>`;
                }
                // Show weight for items that have it
                if (item.weight !== undefined && item.weight > 0) {
                    enchantLine += `<div style="color: var(--text-muted); font-size: 0.7rem; margin-top: 2px;">⚖️ ${formatWeight(item.weight)}</div>`;
                }
                // Show nutrition for food items (0xB0-0xB9, 0xBD water)
                if (item.nutrition !== undefined) {
                    const nutritionColor = item.nutrition >= 40 ? '#69db7c' : 
                                           item.nutrition >= 20 ? '#a9e34b' : 
                                           item.nutrition > 0 ? '#fcc419' : '#ff6b6b';
                    enchantLine += `<div style="color: ${nutritionColor}; font-size: 0.7rem; margin-top: 2px;">🍖 Nutrition: ${item.nutrition}${item.nutrition === 0 ? ' (none!)' : ''}</div>`;
                }
                // Show intoxication for alcoholic drinks
                if (item.intoxication !== undefined && item.intoxication > 0) {
                    const intoxColor = item.intoxication >= 100 ? '#ff6b6b' : 
                                       item.intoxication >= 50 ? '#ffa94d' : '#fcc419';
                    enchantLine += `<div style="color: ${intoxColor}; font-size: 0.7rem; margin-top: 2px;">🍺 Intoxication: ${item.intoxication}</div>`;
                }
                // Show container capacity
                if (item.capacity !== undefined) {
                    let capacityText = `📦 ${item.capacity} stone${item.capacity !== 1 ? 's' : ''}`;
                    if (item.accepts && item.accepts !== 'any') {
                        capacityText += ` (${item.accepts})`;
                    }
                    enchantLine += `<div style="color: var(--text-accent); font-size: 0.7rem; margin-top: 2px;">${capacityText}</div>`;
                }
                // Show book/scroll/writing/gravestone content for readable items
                // Books/scrolls: 0x130-0x13F (excluding 0x13B map) = 304-319 (excluding 315)
                // Gravestones: 0x165 = 357, Writings: 0x166 = 358
                const objIdNum = Number(objId);
                const isBookOrScroll = (objIdNum >= 304 && objIdNum <= 319 && objIdNum !== 315);
                const isStationaryWriting = (objIdNum === 357 || objIdNum === 358); // 0x165 = 357, 0x166 = 358
                const isReadableItem = isBookOrScroll || isStationaryWriting;
                // Check for description - must exist and be non-empty
                const hasDescription = item.description && String(item.description).trim().length > 0;
                if (isReadableItem && hasDescription) {
                    const maxLen = 100;
                    const displayText = item.description.length > maxLen 
                        ? item.description.substring(0, maxLen) + '...' 
                        : item.description;
                    // Use appropriate icon: 🪦 for gravestone (357), 📝 for writing (358), 📜 for books/scrolls
                    const icon = (objIdNum === 357) ? '🪦' : (objIdNum === 358) ? '📝' : '📜';
                    enchantLine += `<div style="color: #e8d4b8; font-size: 0.7rem; margin-top: 4px; padding: 4px 6px; background: rgba(232, 212, 184, 0.1); border-left: 2px solid #e8d4b8; border-radius: 2px; font-style: italic; line-height: 1.3; white-space: pre-wrap;">${icon} "${escapeHtml(displayText)}"</div>`;
                }
                // Show effect for switches, traps, and triggers (including lever 0x161)
                const isSwitchTrapTrigger = (objIdNum >= 0x170 && objIdNum <= 0x17F) || objIdNum === 0x161 || (objIdNum >= 0x180 && objIdNum <= 0x1BF);
                if (isSwitchTrapTrigger && item.description && item.description.length > 0) {
                    enchantLine += `<div style="color: #ffa94d; font-size: 0.7rem; margin-top: 4px; padding: 4px 6px; background: rgba(255, 169, 77, 0.1); border-left: 2px solid #ffa94d; border-radius: 2px; line-height: 1.3;">⚙️ ${escapeHtml(item.description)}</div>`;
                }
                // Show quantity for stackable items (only if > 1)
                if (item.quantity && item.quantity > 1) {
                    enchantLine += `<div style="color: #fcc419; font-size: 0.7rem; margin-top: 2px;">📦 Qty: ${item.quantity}</div>`;
                }
                // Show ownership information
                if (isOwned(item)) {
                    const ownerName = item.owner_name || `NPC #${item.owner}`;
                    enchantLine += `<div style="color: #fab005; font-size: 0.7rem; margin-top: 2px;">⚠️ Owned by ${escapeHtml(ownerName)}</div>`;
                }
            }
            
            // Show container/inventory indicators
            const hasContents = !isSecret && !isNpc && item.contents && item.contents.length > 0;
            const hasInventory = isNpc && item.inventory && item.inventory.length > 0;
            const extraIcon = hasContents ? ' 📦' : (hasInventory ? ' 🎒' : '');
            
            // Add image thumbnail for non-secret items (objects only, not NPCs)
            // Exclude images for writings, doors, and texture map objects
            let imageHtml = '';
            if (!isSecret && !isNpc && item.image_path) {
                // Object images - exclude writings, doors, and texture map objects
                const objId = item.object_id || 0;
                const isWriting = objId === 0x166;
                const isDoor = (objId >= 0x140 && objId <= 0x14F);
                const isTextureMap = (objId >= 0x16E && objId <= 0x16F);

                if (!isWriting && !isDoor && !isTextureMap) {
                    imageHtml = `
                        <div class="list-item-image-container" style="flex-shrink: 0; width: 32px; height: 32px; margin-right: 8px;">
                            <img src="${escapeHtml(item.image_path)}" alt="${escapeHtml(displayName)}"
                                 class="list-item-image"
                                 style="width: 100%; height: 100%; object-fit: contain; image-rendering: pixelated; image-rendering: -moz-crisp-edges; image-rendering: crisp-edges;"
                                 onerror="this.style.display='none';">
                        </div>
                    `;
                }
            }
            
            // Build change badge if save game is loaded
            let changeBadgeHtml = '';
            if (state.saveGame.currentSaveName && item.change_type && item.change_type !== 'unchanged') {
                const changeColor = window.SaveComparator?.getChangeTypeColor(item.change_type) || '#868e96';
                const changeIcon = window.SaveComparator?.getChangeTypeIcon(item.change_type) || '';
                const changeLabel = window.SaveComparator?.getChangeTypeLabel(item.change_type) || '';
                changeBadgeHtml = `<span class="change-badge change-${item.change_type}" style="margin-left: 6px;">${changeIcon} ${changeLabel}</span>`;
            }
            
            itemEl.innerHTML = `
                ${imageHtml ? imageHtml : `<span style="flex-shrink: 0;">${icon}</span>`}
                <div style="flex: 1; min-width: 0;">
                    <div style="color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: flex; align-items: center;">
                        <span style="overflow: hidden; text-overflow: ellipsis;">${escapeHtml(displayName)}${extraIcon}</span>
                        ${changeBadgeHtml}
                    </div>
                    <div style="color: var(--text-muted); font-size: 0.75rem;">${subtitle}</div>
                    ${enchantLine}
                </div>
            `;
            
            // Hover effects
            itemEl.addEventListener('mouseenter', () => {
                itemEl.style.background = 'var(--bg-elevated)';
                itemEl.style.transform = 'translateX(2px)';
                // Apply hover effect to corresponding map marker
                applyHoverEffectToMapMarker(item, isNpc, isSecret);
            });
            itemEl.addEventListener('mouseleave', () => {
                itemEl.style.background = 'var(--bg-tertiary)';
                itemEl.style.transform = 'translateX(0)';
                // Remove hover effect from corresponding map marker
                removeHoverEffectFromMapMarker(item, isNpc, isSecret);
            });
            
            // Click to select
            itemEl.addEventListener('click', () => {
                if (isSecret) {
                    selectSecret(item);
                } else {
                    selectStackedItem(item, isNpc, item.tile_x, item.tile_y);
                }
            });
            
            itemsContainer.appendChild(itemEl);
        });
        
        listContainer.appendChild(itemsContainer);
    });
    
    section.appendChild(listContainer);
    
    // Hint at bottom
    const hint = document.createElement('div');
    hint.style.cssText = `
        flex-shrink: 0;
        padding: 10px 0 0 0;
        margin-top: 8px;
        border-top: 1px solid var(--border-color);
        color: var(--text-muted);
        font-size: 0.75rem;
        text-align: center;
    `;
    hint.textContent = 'Click an item to view details';
    section.appendChild(hint);
    
    elements.detailsSidebar.appendChild(section);
}

function renderObjectDetails(item, isNpc) {
    let html = '<div class="detail-card">';
    const uniqueIndicator = isNpc && hasUniqueName(item) ? '⭐ ' : '';
    const displayName = isNpc ? (item.name || 'Unknown NPC') : getItemDisplayName(item);
    html += `<div class="detail-name">${uniqueIndicator}${displayName}</div>`;
    
    // Display image if available (for objects only, not NPCs)
    // Exclude images for writings, doors, and texture map objects
    if (!isNpc && item.image_path) {
        // Object images - exclude writings, doors, and texture map objects
        const objId = item.object_id || 0;
        const isWriting = objId === 0x166;
        const isDoor = (objId >= 0x140 && objId <= 0x14F);
        const isTextureMap = (objId >= 0x16E && objId <= 0x16F);
        
        if (!isWriting && !isDoor && !isTextureMap) {
            html += `
                <div class="detail-image-container">
                    <img src="${item.image_path}" alt="${displayName}" class="detail-image" 
                         onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                    <div class="detail-image-placeholder" style="display: none;">
                        <span class="image-placeholder-icon">🖼️</span>
                        <span class="image-placeholder-text">No image available</span>
                    </div>
                </div>
            `;
        }
    }
    
    if (isNpc) {
        const npcCategory = getNpcCategory(item);
        const npcColor = npcCategory === 'npcs_hostile' ? '#ff4444' :
                        npcCategory === 'npcs_named' ? '#ffd43b' : '#69db7c';
        const npcLabel = npcCategory === 'npcs_hostile' ? 'Hostile NPC' :
                        npcCategory === 'npcs_named' ? 'Named NPC' : 'Friendly NPC';
        const npcColorBg = npcCategory === 'npcs_hostile' ? 'rgba(255,68,68,0.2)' :
                          npcCategory === 'npcs_named' ? 'rgba(255,212,59,0.2)' : 'rgba(105,219,124,0.2)';
        
        html += `
            <div class="detail-row">
                <span class="detail-label">Type</span>
                <span class="detail-category" style="background: ${npcColorBg}; color: ${npcColor};">${npcLabel}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Object ID</span>
                <span class="detail-value" style="font-family: var(--font-mono);">${item.object_id} (0x${(item.object_id || 0).toString(16).toUpperCase().padStart(3, '0')})</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Creature</span>
                <span class="detail-value">${item.creature_type || 'Unknown'}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">HP</span>
                <span class="detail-value">${item.hp}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Level</span>
                <span class="detail-value">${item.level}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Attitude</span>
                <span class="detail-value">${item.attitude || 'Unknown'}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Has Dialogue</span>
                <span class="detail-value">${item.has_conversation ? 'Yes' : 'No'}</span>
            </div>
        `;
        
        // Show inventory count if NPC has items
        if (item.inventory && item.inventory.length > 0) {
            html += `
            <div class="detail-row">
                <span class="detail-label">Carrying</span>
                <span class="detail-value" style="color: var(--text-accent);">${item.inventory.length} item${item.inventory.length > 1 ? 's' : ''}</span>
            </div>
            `;
        }
    } else {
        const catColor = getCategoryColor(item.category);
        // Try to get object_id from multiple possible sources - ALWAYS display Object ID
        let objId = item.object_id;
        
        // Check if object_id exists and is valid
        if (objId === undefined || objId === null || objId === '') {
            // Try to get from object_id_hex if available
            if (item.object_id_hex) {
                objId = parseInt(item.object_id_hex, 16);
            } else if (item.id !== undefined) {
                // Last resort: try to use id if it's a valid object ID (0-511)
                // But only if it looks like an object ID, not an index
                const testId = Number(item.id);
                if (!isNaN(testId) && testId >= 0 && testId <= 511) {
                    objId = testId;
                } else {
                    objId = 0;
                }
            } else {
                // Fallback to 0 if not found
                objId = 0;
            }
        }
        
        // Handle string hex values (e.g., "0x0AA" or "0AA")
        if (typeof objId === 'string') {
            if (objId.startsWith('0x') || objId.startsWith('0X')) {
                objId = parseInt(objId, 16);
            } else if (/^[0-9A-Fa-f]+$/.test(objId)) {
                objId = parseInt(objId, 16);
            } else {
                objId = parseInt(objId, 10);
            }
        }
        
        // Ensure it's a valid number (0-511 for object IDs)
        objId = Number(objId);
        if (isNaN(objId) || objId < 0 || objId > 511) {
            objId = 0;
        }
        
        // ALWAYS display Object ID - this should never be skipped
        html += `
            <div class="detail-row">
                <span class="detail-label">Category</span>
                <span class="detail-category" style="background: ${catColor}22; color: ${catColor};">${formatCategory(item.category)}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Object ID</span>
                <span class="detail-value" style="font-family: var(--font-mono);">${objId} (0x${objId.toString(16).toUpperCase().padStart(3, '0')})</span>
            </div>
        `;
        
        // Show quantity for stackable items (always show in selected object view, even if 1)
        // Items that can have quantity: emeralds, rubies, sapphires, tiny blue gems, red gems, resilient spears
        const quantityItems = [0x0A2, 0x0A3, 0x0A4, 0x0A6, 0x0A7]; // Ruby (162), Red gem (163), Small blue gem (164), Sapphire (166), Emerald (167)
        const canHaveQuantity = quantityItems.includes(objId);
        
        // Convert quantity to number, defaulting to 0 if not present
        let quantity = 0;
        if (item.quantity !== undefined && item.quantity !== null) {
            quantity = typeof item.quantity === 'number' ? item.quantity : parseInt(item.quantity, 10);
            if (isNaN(quantity)) quantity = 0;
        }
        
        // Show quantity if:
        // 1. Quantity is >= 1 (for all items), OR
        // 2. Item can have quantity (always show quantity field for these items in selected view, even if 0)
        if (quantity >= 1 || canHaveQuantity) {
            html += `
                <div class="detail-row">
                    <span class="detail-label">Quantity</span>
                    <span class="detail-value" style="color: #fcc419;">${quantity}</span>
                </div>
            `;
        }
        
        // Show type-specific details based on category/object_id
        html += getTypeSpecificDetails(item);
        
        // Show contents indicator for storage items in the stats section
        if (item.category === 'storage') {
            if (item.contents && item.contents.length > 0) {
                html += `
                    <div class="detail-row">
                        <span class="detail-label">Contents</span>
                        <span class="detail-value" style="color: var(--text-accent);">📦 ${item.contents.length} item${item.contents.length > 1 ? 's' : ''}</span>
                    </div>
                `;
            } else {
                html += `
                    <div class="detail-row">
                        <span class="detail-label">Contents</span>
                        <span class="detail-value" style="color: var(--text-muted);">Empty</span>
                    </div>
                `;
            }
        }
        
        // Show description if available (books, scrolls, keys, potions, etc.)
        // For switches, triggers and traps, show the effect description inline without extra section
        if (item.description) {
            const objId = item.object_id || 0;
            const isSwitchTrapOrTrigger = (objId >= 0x170 && objId <= 0x17F) || objId === 0x161 || (objId >= 0x180 && objId <= 0x1BF);
            
            if (isSwitchTrapOrTrigger) {
                // Show switch/trap/trigger effect in a styled block
                html += `
                    <div class="detail-effect" style="margin-top: 12px;">
                        <div class="detail-label" style="margin-bottom: 4px;">Effect</div>
                        <div style="font-size: 0.85rem; color: var(--color-switches); padding: 8px 10px; background: rgba(255, 169, 77, 0.1); border-radius: 4px; border-left: 3px solid var(--color-switches);">⚙️ ${escapeHtml(item.description)}</div>
                    </div>
                `;
            } else {
                // Show description in a separate section for books/scrolls/etc
                html += `
                    <div class="detail-description">
                        <div class="detail-label" style="margin-bottom: 4px;">Description</div>
                        <div class="description-text">${escapeHtml(item.description)}</div>
                    </div>
                `;
            }
        }
        
        // Show effect/enchantment only for truly magical effects
        if (isMagicalEffect(item.effect)) {
            html += `
                <div class="detail-effect">
                    <div class="detail-label" style="margin-bottom: 4px;">✨ Enchantment</div>
                    <div class="effect-text">${escapeHtml(item.effect)}</div>
                </div>
            `;
        }
        
        // Show owner information (item belongs to an NPC - taking it is stealing)
        if (isOwned(item)) {
            const ownerName = item.owner_name || `NPC #${item.owner}`;
            html += `
                <div class="detail-row">
                    <span class="detail-label">Owned By</span>
                    <span class="detail-value" style="color: #fab005;">⚠️ ${escapeHtml(ownerName)}</span>
                </div>
            `;
        }
    }
    
    html += `
        <div class="detail-row">
            <span class="detail-label">Position</span>
            <span class="detail-value">(${item.tile_x}, ${item.tile_y})</span>
        </div>
        <div class="detail-row">
            <span class="detail-label">Z Height</span>
            <span class="detail-value">${item.z}</span>
        </div>
    `;
    
    // Show change information when a save game is loaded
    if (state.saveGame.currentSaveName && item.change_type) {
        const changeColor = window.SaveComparator?.getChangeTypeColor(item.change_type) || '#868e96';
        const changeIcon = window.SaveComparator?.getChangeTypeIcon(item.change_type) || '';
        const changeLabel = window.SaveComparator?.getChangeTypeLabel(item.change_type) || item.change_type;
        const changeDesc = window.SaveComparator?.formatChangeDescription(item) || '';
        
        html += `
            <div class="detail-change" style="margin-top: 12px; padding: 10px; background: ${changeColor}15; border-left: 3px solid ${changeColor}; border-radius: 4px;">
                <div class="detail-row" style="margin-bottom: 0;">
                    <span class="detail-label">Save Status</span>
                    <span class="detail-value" style="color: ${changeColor}; font-weight: 500;">${changeIcon} ${changeLabel}</span>
                </div>
        `;
        
        if (changeDesc && item.change_type !== 'unchanged') {
            html += `
                <div style="color: var(--text-secondary); font-size: 0.85rem; margin-top: 6px;">
                    ${escapeHtml(changeDesc)}
                </div>
            `;
        }
        
        html += `</div>`;
    }
    
    html += '</div>';
    
    // Set the HTML first
    elements.objectDetails.innerHTML = html;
    
    // Add container contents if this is a container (using DOM elements for click handling)
    if (item.contents && item.contents.length > 0) {
        const contentsEl = renderContainerContents(item.contents, 0, item);
        if (contentsEl) {
            elements.objectDetails.appendChild(contentsEl);
        }
    }
    
    // Add NPC inventory if this is an NPC with items (using DOM elements for click handling)
    if (isNpc && item.inventory && item.inventory.length > 0) {
        const inventoryEl = renderNpcInventory(item.inventory, item);
        if (inventoryEl) {
            elements.objectDetails.appendChild(inventoryEl);
        }
    }
}

/**
 * Render container contents as a nested list with clickable items
 * Returns a DOM element instead of HTML string for click handling
 */
function renderContainerContents(contents, depth = 0, parentContainer = null) {
    if (!contents || contents.length === 0) return null;
    
    const indent = depth * 12;
    const container = document.createElement('div');
    container.className = 'container-contents';
    container.style.marginLeft = `${indent}px`;
    container.style.marginTop = '8px';
    
    const header = document.createElement('div');
    header.className = 'contents-header';
    header.style.cssText = 'color: var(--text-accent); font-size: 0.85rem; margin-bottom: 6px;';
    header.textContent = depth === 0 ? '📦 Contains:' : '↳ Contains:';
    container.appendChild(header);
    
    contents.forEach(item => {
        const catColor = getCategoryColor(item.category);
        const hasEffect = isMagicalEffect(item.effect) ? ' ✨' : '';
        const hasContents = item.contents && item.contents.length > 0;
        
        const contentItem = document.createElement('div');
        contentItem.className = 'content-item selectable-content';
        contentItem.dataset.itemId = item.id || '';
        contentItem.style.cssText = `
            background: var(--bg-tertiary); 
            border-left: 3px solid ${catColor};
            padding: 6px 8px;
            margin-bottom: 4px;
            border-radius: 0 4px 4px 0;
            font-size: 0.85rem;
            cursor: pointer;
            transition: background 0.15s ease, transform 0.1s ease;
        `;
        
        const nameDiv = document.createElement('div');
        nameDiv.style.color = 'var(--text-primary)';
        nameDiv.textContent = `${getItemDisplayName(item)}${hasEffect}${hasContents ? ' 📦' : ''}`;
        
        // Build info line with category, quantity (only if > 1), and optional effect preview
        let infoText = formatCategory(item.category);
        if (item.quantity && item.quantity > 1) {
            infoText += ` • Qty: ${item.quantity}`;
        }
        if (isMagicalEffect(item.effect)) {
            infoText += ` • ${truncateText(item.effect, 30)}`;
        }
        
        const infoDiv = document.createElement('div');
        infoDiv.style.cssText = 'color: var(--text-muted); font-size: 0.75rem;';
        infoDiv.textContent = infoText;
        
        contentItem.appendChild(nameDiv);
        contentItem.appendChild(infoDiv);
        
        // Show description preview for readable items (books, scrolls)
        const contObjId = item.object_id || 0;
        const isContainerReadable = (contObjId >= 0x130 && contObjId <= 0x13F && contObjId !== 0x13B);
        if (item.description && item.description.length > 0) {
            const descDiv = document.createElement('div');
            if (isContainerReadable) {
                // Enhanced book/scroll styling
                const maxLen = 80;
                const displayText = item.description.length > maxLen 
                    ? item.description.substring(0, maxLen) + '...' 
                    : item.description;
                descDiv.style.cssText = 'color: #e8d4b8; font-size: 0.7rem; margin-top: 4px; padding: 4px 6px; background: rgba(232, 212, 184, 0.1); border-left: 2px solid #e8d4b8; border-radius: 2px; font-style: italic; line-height: 1.3; white-space: pre-wrap;';
                descDiv.textContent = `📜 "${displayText}"`;
            } else {
                descDiv.style.cssText = 'color: var(--text-accent); font-size: 0.7rem; margin-top: 2px; font-style: italic;';
                descDiv.textContent = truncateText(item.description, 50);
            }
            contentItem.appendChild(descDiv);
        }
        
        // Show weight if available
        if (item.weight !== undefined && item.weight > 0) {
            const weightDiv = document.createElement('div');
            weightDiv.style.cssText = 'color: var(--text-muted); font-size: 0.7rem; margin-top: 2px;';
            weightDiv.textContent = `⚖️ ${formatWeight(item.weight)}`;
            contentItem.appendChild(weightDiv);
        }
        
        // Show nutrition for food items (0xB0-0xB9, 0xBD water)
        if (item.nutrition !== undefined) {
            const nutritionDiv = document.createElement('div');
            const nutritionColor = item.nutrition >= 40 ? '#69db7c' : 
                                   item.nutrition >= 20 ? '#a9e34b' : 
                                   item.nutrition > 0 ? '#fcc419' : '#ff6b6b';
            nutritionDiv.style.cssText = `color: ${nutritionColor}; font-size: 0.7rem; margin-top: 2px;`;
            nutritionDiv.textContent = `🍖 Nutrition: ${item.nutrition}${item.nutrition === 0 ? ' (none!)' : ''}`;
            contentItem.appendChild(nutritionDiv);
        }
        
        // Show intoxication for alcoholic drinks
        if (item.intoxication !== undefined && item.intoxication > 0) {
            const intoxDiv = document.createElement('div');
            const intoxColor = item.intoxication >= 100 ? '#ff6b6b' : 
                               item.intoxication >= 50 ? '#ffa94d' : '#fcc419';
            intoxDiv.style.cssText = `color: ${intoxColor}; font-size: 0.7rem; margin-top: 2px;`;
            intoxDiv.textContent = `🍺 Intoxication: ${item.intoxication}`;
            contentItem.appendChild(intoxDiv);
        }
        
        // Show container capacity for nested containers
        if (item.capacity !== undefined) {
            const capDiv = document.createElement('div');
            capDiv.style.cssText = 'color: var(--text-accent); font-size: 0.7rem; margin-top: 2px;';
            let capText = `📦 Capacity: ${item.capacity} stone${item.capacity !== 1 ? 's' : ''}`;
            if (item.accepts && item.accepts !== 'any') {
                capText += ` (${item.accepts} only)`;
            }
            capDiv.textContent = capText;
            contentItem.appendChild(capDiv);
        }
        
        // Show owner information (item belongs to an NPC - taking it is stealing)
        if (isOwned(item)) {
            const ownerDiv = document.createElement('div');
            ownerDiv.style.cssText = 'color: #fab005; font-size: 0.7rem; margin-top: 2px;';
            const ownerName = item.owner_name || `NPC #${item.owner}`;
            ownerDiv.textContent = `⚠️ Owned by: ${ownerName}`;
            contentItem.appendChild(ownerDiv);
        }
        
        // Add hover effects
        contentItem.addEventListener('mouseenter', () => {
            contentItem.style.background = 'var(--bg-elevated)';
            contentItem.style.transform = 'translateX(2px)';
        });
        contentItem.addEventListener('mouseleave', () => {
            if (!contentItem.classList.contains('selected-content')) {
                contentItem.style.background = 'var(--bg-tertiary)';
            }
            contentItem.style.transform = 'translateX(0)';
        });
        
        // Add click handler to select this item
        contentItem.addEventListener('click', (e) => {
            e.stopPropagation();
            selectContainerItem(item, parentContainer);
        });
        
        container.appendChild(contentItem);
        
        // Recursively render nested container contents
        if (hasContents) {
            const nestedContents = renderContainerContents(item.contents, depth + 1, item);
            if (nestedContents) {
                container.appendChild(nestedContents);
            }
        }
    });
    
    return container;
}

/**
 * Render NPC inventory as a list with clickable items
 * Returns a DOM element for click handling
 */
function renderNpcInventory(inventory, parentNpc = null) {
    if (!inventory || inventory.length === 0) return null;
    
    const container = document.createElement('div');
    container.className = 'npc-inventory';
    container.style.marginTop = '12px';
    
    const header = document.createElement('div');
    header.className = 'inventory-header';
    header.style.cssText = 'color: var(--text-accent); font-size: 0.85rem; margin-bottom: 6px;';
    header.textContent = '🎒 Inventory:';
    container.appendChild(header);
    
    inventory.forEach(item => {
        const catColor = getCategoryColor(item.category);
        const hasEffect = isMagicalEffect(item.effect) ? ' ✨' : '';
        const hasContents = item.contents && item.contents.length > 0;
        
        const inventoryItem = document.createElement('div');
        inventoryItem.className = 'inventory-item selectable-content';
        inventoryItem.dataset.itemId = item.id || item.object_id || '';
        inventoryItem.style.cssText = `
            background: var(--bg-tertiary); 
            border-left: 3px solid ${catColor};
            padding: 6px 8px;
            margin-bottom: 4px;
            border-radius: 0 4px 4px 0;
            font-size: 0.85rem;
            cursor: pointer;
            transition: background 0.15s ease, transform 0.1s ease;
        `;
        
        const nameDiv = document.createElement('div');
        nameDiv.style.color = 'var(--text-primary)';
        nameDiv.textContent = `${getItemDisplayName(item)}${hasEffect}${hasContents ? ' 📦' : ''}`;
        
        // Build info line with category, quantity (only if > 1), and optional effect preview
        let infoText = formatCategory(item.category);
        if (item.quantity && item.quantity > 1) {
            infoText += ` • Qty: ${item.quantity}`;
        }
        if (isMagicalEffect(item.effect)) {
            infoText += ` • ${truncateText(item.effect, 30)}`;
        }
        
        const infoDiv = document.createElement('div');
        infoDiv.style.cssText = 'color: var(--text-muted); font-size: 0.75rem;';
        infoDiv.textContent = infoText;
        
        inventoryItem.appendChild(nameDiv);
        inventoryItem.appendChild(infoDiv);
        
        // Show description preview for readable items (books, scrolls)
        const invObjId = item.object_id || 0;
        const isInvReadable = (invObjId >= 0x130 && invObjId <= 0x13F && invObjId !== 0x13B);
        if (item.description && item.description.length > 0) {
            const descDiv = document.createElement('div');
            if (isInvReadable) {
                // Enhanced book/scroll styling
                const maxLen = 80;
                const displayText = item.description.length > maxLen 
                    ? item.description.substring(0, maxLen) + '...' 
                    : item.description;
                descDiv.style.cssText = 'color: #e8d4b8; font-size: 0.7rem; margin-top: 4px; padding: 4px 6px; background: rgba(232, 212, 184, 0.1); border-left: 2px solid #e8d4b8; border-radius: 2px; font-style: italic; line-height: 1.3; white-space: pre-wrap;';
                descDiv.textContent = `📜 "${displayText}"`;
            } else {
                descDiv.style.cssText = 'color: var(--text-accent); font-size: 0.7rem; margin-top: 2px; font-style: italic;';
                descDiv.textContent = truncateText(item.description, 50);
            }
            inventoryItem.appendChild(descDiv);
        }
        
        // Show weight if available
        if (item.weight !== undefined && item.weight > 0) {
            const weightDiv = document.createElement('div');
            weightDiv.style.cssText = 'color: var(--text-muted); font-size: 0.7rem; margin-top: 2px;';
            weightDiv.textContent = `⚖️ ${formatWeight(item.weight)}`;
            inventoryItem.appendChild(weightDiv);
        }
        
        // Show nutrition for food items (0xB0-0xB9, 0xBD water)
        if (item.nutrition !== undefined) {
            const nutritionDiv = document.createElement('div');
            const nutritionColor = item.nutrition >= 40 ? '#69db7c' : 
                                   item.nutrition >= 20 ? '#a9e34b' : 
                                   item.nutrition > 0 ? '#fcc419' : '#ff6b6b';
            nutritionDiv.style.cssText = `color: ${nutritionColor}; font-size: 0.7rem; margin-top: 2px;`;
            nutritionDiv.textContent = `🍖 Nutrition: ${item.nutrition}${item.nutrition === 0 ? ' (none!)' : ''}`;
            inventoryItem.appendChild(nutritionDiv);
        }
        
        // Show intoxication for alcoholic drinks
        if (item.intoxication !== undefined && item.intoxication > 0) {
            const intoxDiv = document.createElement('div');
            const intoxColor = item.intoxication >= 100 ? '#ff6b6b' : 
                               item.intoxication >= 50 ? '#ffa94d' : '#fcc419';
            intoxDiv.style.cssText = `color: ${intoxColor}; font-size: 0.7rem; margin-top: 2px;`;
            intoxDiv.textContent = `🍺 Intoxication: ${item.intoxication}`;
            inventoryItem.appendChild(intoxDiv);
        }
        
        // Show container capacity
        if (item.capacity !== undefined) {
            const capDiv = document.createElement('div');
            capDiv.style.cssText = 'color: var(--text-accent); font-size: 0.7rem; margin-top: 2px;';
            let capText = `📦 Capacity: ${item.capacity} stone${item.capacity !== 1 ? 's' : ''}`;
            if (item.accepts && item.accepts !== 'any') {
                capText += ` (${item.accepts} only)`;
            }
            capDiv.textContent = capText;
            inventoryItem.appendChild(capDiv);
        }
        
        // Show owner information (item belongs to an NPC - taking it is stealing)
        if (isOwned(item)) {
            const ownerDiv = document.createElement('div');
            ownerDiv.style.cssText = 'color: #fab005; font-size: 0.7rem; margin-top: 2px;';
            const ownerName = item.owner_name || `NPC #${item.owner}`;
            ownerDiv.textContent = `⚠️ Owned by: ${ownerName}`;
            inventoryItem.appendChild(ownerDiv);
        }
        
        // Add hover effects
        inventoryItem.addEventListener('mouseenter', () => {
            inventoryItem.style.background = 'var(--bg-elevated)';
            inventoryItem.style.transform = 'translateX(2px)';
        });
        inventoryItem.addEventListener('mouseleave', () => {
            if (!inventoryItem.classList.contains('selected-content')) {
                inventoryItem.style.background = 'var(--bg-tertiary)';
            }
            inventoryItem.style.transform = 'translateX(0)';
        });
        
        // Add click handler to select this item
        inventoryItem.addEventListener('click', (e) => {
            e.stopPropagation();
            selectInventoryItem(item, parentNpc);
        });
        
        container.appendChild(inventoryItem);
        
        // Recursively render nested container contents within inventory
        if (hasContents) {
            const nestedContents = renderContainerContents(item.contents, 1, item);
            if (nestedContents) {
                container.appendChild(nestedContents);
            }
        }
    });
    
    return container;
}

/**
 * Select an item from within an NPC's inventory
 */
function selectInventoryItem(item, parentNpc = null) {
    // Clear any previous content selection highlighting
    document.querySelectorAll('.selectable-content.selected-content').forEach(el => {
        el.classList.remove('selected-content');
        el.style.background = 'var(--bg-tertiary)';
        el.style.borderColor = '';
    });
    
    // Build details for the selected inventory item
    let html = '<div class="detail-card">';
    const displayName = getItemDisplayName(item);
    html += `<div class="detail-name">${displayName}</div>`;
    
    // Display image if available (for objects only, not NPCs)
    // Exclude images for writings, doors, and texture map objects
    if (item.image_path) {
        // Object images - exclude writings, doors, and texture map objects
        const objId = item.object_id || 0;
        // Handle string hex values (e.g., "0x0AA" or "0AA")
        let imageObjId = typeof objId === 'string' ? 
            (objId.startsWith('0x') || objId.startsWith('0X') ? parseInt(objId, 16) : 
             /^[0-9A-Fa-f]+$/.test(objId) ? parseInt(objId, 16) : parseInt(objId, 10)) : 
            (objId || 0);
        imageObjId = Number(imageObjId) || 0;
        
        const isWriting = imageObjId === 0x166;
        const isDoor = (imageObjId >= 0x140 && imageObjId <= 0x14F);
        const isTextureMap = (imageObjId >= 0x16E && imageObjId <= 0x16F);
        
        if (!isWriting && !isDoor && !isTextureMap) {
            html += `
                <div class="detail-image-container">
                    <img src="${item.image_path}" alt="${displayName}" class="detail-image" 
                         onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                    <div class="detail-image-placeholder" style="display: none;">
                        <span class="image-placeholder-icon">🖼️</span>
                        <span class="image-placeholder-text">No image available</span>
                    </div>
                </div>
            `;
        }
    }
    
    const catColor = getCategoryColor(item.category);
    html += `
        <div class="detail-row">
            <span class="detail-label">Category</span>
            <span class="detail-category" style="background: ${catColor}22; color: ${catColor};">${formatCategory(item.category)}</span>
        </div>
    `;
    
    // Show quantity for stackable items (always show in selected object view, even if 1)
    // Items that can have quantity: emeralds, rubies, sapphires, tiny blue gems, red gems, resilient spears
    const objId = typeof item.object_id === 'string' ? parseInt(item.object_id, 16) : (item.object_id || 0);
    const quantityItems = [0x0A2, 0x0A3, 0x0A4, 0x0A6, 0x0A7]; // Ruby (162), Red gem (163), Small blue gem (164), Sapphire (166), Emerald (167)
    const canHaveQuantity = quantityItems.includes(objId);
    
    // Convert quantity to number, defaulting to 0 if not present
    let quantity = 0;
    if (item.quantity !== undefined && item.quantity !== null) {
        quantity = typeof item.quantity === 'number' ? item.quantity : parseInt(item.quantity, 10);
        if (isNaN(quantity)) quantity = 0;
    }
    
    // Show quantity if:
    // 1. Quantity is >= 1 (for all items), OR
    // 2. Item can have quantity (always show quantity field for these items in selected view, even if 0)
    if (quantity >= 1 || canHaveQuantity) {
        html += `
            <div class="detail-row">
                <span class="detail-label">Quantity</span>
                <span class="detail-value" style="color: #fcc419;">${quantity}</span>
            </div>
        `;
    }
    
    // Show type-specific details
    html += getTypeSpecificDetails(item);
    
    // Show description if available (books, scrolls, keys, potions, etc.)
    if (item.description) {
        html += `
            <div class="detail-description">
                <div class="detail-label" style="margin-bottom: 4px;">Description</div>
                <div class="description-text">${escapeHtml(item.description)}</div>
            </div>
        `;
    }
    
    // Show effect/enchantment only for truly magical effects
    if (isMagicalEffect(item.effect)) {
        html += `
            <div class="detail-effect">
                <div class="detail-label" style="margin-bottom: 4px;">✨ Enchantment</div>
                <div class="effect-text">${escapeHtml(item.effect)}</div>
            </div>
        `;
    }
    
    // Show owner information (item belongs to an NPC - taking it is stealing)
    if (isOwned(item)) {
        const ownerName = item.owner_name || `NPC #${item.owner}`;
        html += `
            <div class="detail-row">
                <span class="detail-label">Owned By</span>
                <span class="detail-value" style="color: #fab005;">⚠️ ${escapeHtml(ownerName)}</span>
            </div>
        `;
    }
    
    // Show parent NPC info
    if (parentNpc) {
        html += `
            <div class="detail-row">
                <span class="detail-label">Carried by</span>
                <span class="detail-value" style="color: #ff6b6b;">${parentNpc.name || 'NPC'}</span>
            </div>
        `;
    }
    
    html += '</div>';
    
    // Add nested container contents if this item is also a container
    elements.objectDetails.innerHTML = html;
    
    if (item.contents && item.contents.length > 0) {
        const contentsEl = renderContainerContents(item.contents, 0, item);
        if (contentsEl) {
            elements.objectDetails.appendChild(contentsEl);
        }
    }
    
    // Add a "back to NPC" button if there's a parent NPC
    if (parentNpc) {
        const backBtn = document.createElement('button');
        backBtn.className = 'back-to-parent-btn';
        backBtn.innerHTML = '← Back to ' + (parentNpc.name || 'NPC');
        backBtn.style.cssText = `
            margin-top: 12px;
            padding: 8px 12px;
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: 4px;
            color: var(--text-secondary);
            font-family: var(--font-body);
            font-size: 0.85rem;
            cursor: pointer;
            width: 100%;
            transition: all 0.15s ease;
        `;
        backBtn.addEventListener('mouseenter', () => {
            backBtn.style.background = 'var(--bg-elevated)';
            backBtn.style.borderColor = '#ff6b6b';
            backBtn.style.color = '#ff6b6b';
        });
        backBtn.addEventListener('mouseleave', () => {
            backBtn.style.background = 'var(--bg-tertiary)';
            backBtn.style.borderColor = 'var(--border-color)';
            backBtn.style.color = 'var(--text-secondary)';
        });
        backBtn.addEventListener('click', () => {
            renderObjectDetails(parentNpc, true);
        });
        elements.objectDetails.appendChild(backBtn);
    }
    
    // Highlight the selected inventory item
    const selectedEl = document.querySelector(`.selectable-content[data-item-id="${item.id || item.object_id}"]`);
    if (selectedEl) {
        selectedEl.classList.add('selected-content');
        selectedEl.style.background = 'var(--bg-elevated)';
    }
}

/**
 * Select an item from within a container
 */
function selectContainerItem(item, parentContainer = null) {
    // Clear any previous content selection highlighting
    document.querySelectorAll('.selectable-content.selected-content').forEach(el => {
        el.classList.remove('selected-content');
        el.style.background = 'var(--bg-tertiary)';
        el.style.borderColor = '';
    });
    
    // Build details for the selected container item
    let html = '<div class="detail-card">';
    const displayName = getItemDisplayName(item);
    html += `<div class="detail-name">${displayName}</div>`;
    
    // Display image if available (for objects only, not NPCs)
    // Exclude images for writings, doors, and texture map objects
    if (item.image_path) {
        // Object images - exclude writings, doors, and texture map objects
        let imageObjId = item.object_id;
        if (imageObjId === undefined || imageObjId === null || imageObjId === '') {
            if (item.object_id_hex) {
                imageObjId = parseInt(item.object_id_hex, 16);
            } else {
                imageObjId = 0;
            }
        }
        if (typeof imageObjId === 'string') {
            if (imageObjId.startsWith('0x') || imageObjId.startsWith('0X')) {
                imageObjId = parseInt(imageObjId, 16);
            } else if (/^[0-9A-Fa-f]+$/.test(imageObjId)) {
                imageObjId = parseInt(imageObjId, 16);
            } else {
                imageObjId = parseInt(imageObjId, 10);
            }
        }
        imageObjId = Number(imageObjId) || 0;
        
        const isWriting = imageObjId === 0x166;
        const isDoor = (imageObjId >= 0x140 && imageObjId <= 0x14F);
        const isTextureMap = (imageObjId >= 0x16E && imageObjId <= 0x16F);
        
        if (!isWriting && !isDoor && !isTextureMap) {
            html += `
                <div class="detail-image-container">
                    <img src="${item.image_path}" alt="${displayName}" class="detail-image" 
                         onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                    <div class="detail-image-placeholder" style="display: none;">
                        <span class="image-placeholder-icon">🖼️</span>
                        <span class="image-placeholder-text">No image available</span>
                    </div>
                </div>
            `;
        }
    }
    
    const catColor = getCategoryColor(item.category);
    
    // Get object_id - try multiple sources
    let objId = item.object_id;
    if (objId === undefined || objId === null || objId === '') {
        if (item.object_id_hex) {
            objId = parseInt(item.object_id_hex, 16);
        } else {
            objId = 0;
        }
    }
    if (typeof objId === 'string') {
        if (objId.startsWith('0x') || objId.startsWith('0X')) {
            objId = parseInt(objId, 16);
        } else if (/^[0-9A-Fa-f]+$/.test(objId)) {
            objId = parseInt(objId, 16);
        } else {
            objId = parseInt(objId, 10);
        }
    }
    objId = Number(objId) || 0;
    
    html += `
        <div class="detail-row">
            <span class="detail-label">Category</span>
            <span class="detail-category" style="background: ${catColor}22; color: ${catColor};">${formatCategory(item.category)}</span>
        </div>
        <div class="detail-row">
            <span class="detail-label">Object ID</span>
            <span class="detail-value" style="font-family: var(--font-mono);">${objId} (0x${objId.toString(16).toUpperCase().padStart(3, '0')})</span>
        </div>
    `;
    
    // Show quantity for stackable items (always show in selected object view, even if 1)
    // Items that can have quantity: emeralds, rubies, sapphires, tiny blue gems, red gems, resilient spears
    const quantityItems = [0x0A2, 0x0A3, 0x0A4, 0x0A6, 0x0A7]; // Ruby (162), Red gem (163), Small blue gem (164), Sapphire (166), Emerald (167)
    const canHaveQuantity = quantityItems.includes(objId);
    
    // Convert quantity to number, defaulting to 0 if not present
    let quantity = 0;
    if (item.quantity !== undefined && item.quantity !== null) {
        quantity = typeof item.quantity === 'number' ? item.quantity : parseInt(item.quantity, 10);
        if (isNaN(quantity)) quantity = 0;
    }
    
    // Show quantity if:
    // 1. Quantity is >= 1 (for all items), OR
    // 2. Item can have quantity (always show quantity field for these items in selected view, even if 0)
    if (quantity >= 1 || canHaveQuantity) {
        html += `
            <div class="detail-row">
                <span class="detail-label">Quantity</span>
                <span class="detail-value" style="color: #fcc419;">${quantity}</span>
            </div>
        `;
    }
    
    // Show type-specific details
    html += getTypeSpecificDetails(item);
    
    // Show description if available (books, scrolls, keys, potions, etc.)
    if (item.description) {
        html += `
            <div class="detail-description">
                <div class="detail-label" style="margin-bottom: 4px;">Description</div>
                <div class="description-text">${escapeHtml(item.description)}</div>
            </div>
        `;
    }
    
    // Show effect/enchantment only for truly magical effects
    if (isMagicalEffect(item.effect)) {
        html += `
            <div class="detail-effect">
                <div class="detail-label" style="margin-bottom: 4px;">✨ Enchantment</div>
                <div class="effect-text">${escapeHtml(item.effect)}</div>
            </div>
        `;
    }
    
    // Show owner information (item belongs to an NPC - taking it is stealing)
    if (isOwned(item)) {
        const ownerName = item.owner_name || `NPC #${item.owner}`;
        html += `
            <div class="detail-row">
                <span class="detail-label">Owned By</span>
                <span class="detail-value" style="color: #fab005;">⚠️ ${escapeHtml(ownerName)}</span>
            </div>
        `;
    }
    
    // Show parent container info
    if (parentContainer) {
        html += `
            <div class="detail-row">
                <span class="detail-label">Inside</span>
                <span class="detail-value" style="color: var(--text-accent);">${parentContainer.name || 'Container'}</span>
            </div>
        `;
    }
    
    html += '</div>';
    
    // Add nested container contents if this item is also a container
    elements.objectDetails.innerHTML = html;
    
    if (item.contents && item.contents.length > 0) {
        const contentsEl = renderContainerContents(item.contents, 0, item);
        if (contentsEl) {
            elements.objectDetails.appendChild(contentsEl);
        }
    }
    
    // Add a "back to parent" button if there's a parent
    if (parentContainer) {
        const backBtn = document.createElement('button');
        backBtn.className = 'back-to-parent-btn';
        backBtn.innerHTML = '← Back to ' + (parentContainer.name || 'Container');
        backBtn.style.cssText = `
            margin-top: 12px;
            padding: 8px 12px;
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: 4px;
            color: var(--text-secondary);
            font-family: var(--font-body);
            font-size: 0.85rem;
            cursor: pointer;
            width: 100%;
            transition: all 0.15s ease;
        `;
        backBtn.addEventListener('mouseenter', () => {
            backBtn.style.background = 'var(--bg-elevated)';
            backBtn.style.borderColor = 'var(--text-accent)';
            backBtn.style.color = 'var(--text-accent)';
        });
        backBtn.addEventListener('mouseleave', () => {
            backBtn.style.background = 'var(--bg-tertiary)';
            backBtn.style.borderColor = 'var(--border-color)';
            backBtn.style.color = 'var(--text-secondary)';
        });
        backBtn.addEventListener('click', () => {
            renderObjectDetails(parentContainer, false);
        });
        elements.objectDetails.appendChild(backBtn);
    }
    
    // Highlight the selected content item
    const selectedEl = document.querySelector(`.selectable-content[data-item-id="${item.id}"]`);
    if (selectedEl) {
        selectedEl.classList.add('selected-content');
        selectedEl.style.background = 'var(--bg-elevated)';
    }
}

function renderLocationObjects(tileX, tileY, selectedItemId = null) {
    const level = state.data.levels[state.currentLevel];
    if (!level) return;
    
    // Find all items at this tile (respecting enchanted and owned filters)
    const npcsAtTile = level.npcs.filter(n => {
        if (n.tile_x !== tileX || n.tile_y !== tileY) return false;
        if (state.filters.enchantedOnly && !isEnchanted(n)) return false;
        if (state.filters.ownedFilter === 'only' && !isOwned(n)) return false;
        if (state.filters.ownedFilter === 'exclude' && isOwned(n)) return false;
        return true;
    });
    const objectsAtTile = level.objects.filter(o => {
        if (o.tile_x !== tileX || o.tile_y !== tileY) return false;
        // Skip secret doors that match base secrets (they're shown as secrets, not objects)
        if (isSecretDoorMatchingBaseSecret(o, level)) return false;
        if (state.filters.enchantedOnly && !isEnchanted(o)) return false;
        if (state.filters.ownedFilter === 'only' && !isOwned(o)) return false;
        if (state.filters.ownedFilter === 'exclude' && isOwned(o)) return false;
        return true;
    });
    // Don't show secrets when enchanted filter is on (secrets aren't magical)
    // Note: Secrets can never be owned, so they're hidden when owned filter is set to "only"
    const secretsAtTile = (level.secrets && !state.filters.enchantedOnly && state.filters.ownedFilter !== 'only') 
        ? level.secrets.filter(s => s.tile_x === tileX && s.tile_y === tileY) 
        : [];
    
    const totalItems = npcsAtTile.length + objectsAtTile.length + secretsAtTile.length;
    
    if (totalItems === 0) {
        elements.locationObjects.innerHTML = '<p class="no-selection">No objects at this location</p>';
        return;
    }
    
    // Clear container and build with DOM elements for click handlers
    elements.locationObjects.innerHTML = '';
    
    const header = document.createElement('p');
    header.style.cssText = 'color: var(--text-muted); margin-bottom: 8px;';
    header.textContent = `Tile (${tileX}, ${tileY}) - ${totalItems} items`;
    elements.locationObjects.appendChild(header);
    
    // Render NPCs
    npcsAtTile.forEach(npc => {
        const npcCategory = getNpcCategory(npc);
        const npcColor = npcCategory === 'npcs_hostile' ? '#ff4444' :
                        npcCategory === 'npcs_named' ? '#ffd43b' : '#69db7c';
        const npcLabel = npcCategory === 'npcs_hostile' ? 'Hostile NPC' :
                        npcCategory === 'npcs_named' ? 'Named NPC' : 'Friendly NPC';
        
        const card = document.createElement('div');
        card.className = 'detail-card location-item';
        card.style.cssText = `border-left: 3px solid ${npcColor}; cursor: pointer;`;
        if (selectedItemId === npc.id) {
            card.classList.add('selected-location-item');
        }
        
        // Show creature type if different from name
        const creatureInfo = (npc.creature_type && npc.creature_type !== npc.name) 
            ? ` (${npc.creature_type})` 
            : '';
        
        const hasInventory = npc.inventory && npc.inventory.length > 0;
        const isUnique = hasUniqueName(npc);
        const uniqueIndicator = isUnique ? '⭐ ' : '';

        // Build change badge if save game is loaded
        let npcChangeBadge = '';
        if (state.saveGame.currentSaveName && npc.change_type && npc.change_type !== 'unchanged') {
            const changeColor = window.SaveComparator?.getChangeTypeColor(npc.change_type) || '#868e96';
            const changeIcon = window.SaveComparator?.getChangeTypeIcon(npc.change_type) || '';
            const changeLabel = window.SaveComparator?.getChangeTypeLabel(npc.change_type) || '';
            npcChangeBadge = `<span class="change-badge change-${npc.change_type}" style="margin-left: 6px;">${changeIcon} ${changeLabel}</span>`;
        }

        // NPC images disabled for now
        card.innerHTML = `
            <div class="detail-name" style="font-size: 0.9rem; display: flex; align-items: center; flex-wrap: wrap;">${uniqueIndicator}${npc.name || 'Unknown NPC'}${creatureInfo}${hasInventory ? ' 🎒' : ''}${npcChangeBadge}</div>
            <div style="font-size: 0.8rem; color: var(--text-muted);">${npcLabel} - HP: ${npc.hp}</div>
            ${hasInventory ? `<div style="font-size: 0.75rem; color: var(--text-accent); margin-top: 4px;">${npc.inventory.length} item${npc.inventory.length > 1 ? 's' : ''} carried</div>` : ''}
        `;
        
        card.addEventListener('click', () => selectLocationItem(npc, true, tileX, tileY));
        elements.locationObjects.appendChild(card);
    });
    
    // Render objects
    objectsAtTile.forEach(obj => {
        const color = getCategoryColor(obj.category);
        const hasContents = obj.contents && obj.contents.length > 0;
        
        // Check for lock info (doors)
        const isLocked = obj.extra_info && obj.extra_info.is_locked;
        const lockId = obj.extra_info && obj.extra_info.lock_id;
        const lockType = obj.extra_info && obj.extra_info.lock_type;
        const isPickable = obj.extra_info && obj.extra_info.is_pickable;
        let lockInfo = '';
        if (isLocked) {
            if (lockType === 'special') {
                lockInfo = '🔒 Special';
            } else if (lockId !== undefined) {
                lockInfo = `🔒 Lock #${lockId}`;
                if (isPickable) {
                    lockInfo += ' ⛏️';  // Can be picked
                }
            } else {
                lockInfo = '🔒 Locked';
            }
        }
        // Check for lock info (keys 0x100-0x10E) - they have "Opens lock #N" in effect field
        const objId = obj.object_id || 0;
        if (objId >= 0x100 && objId <= 0x10E) {
            const effectText = obj.effect || '';
            const match = effectText.match(/lock #(\d+)/i);
            if (match) {
                lockInfo = `🔑 Lock #${match[1]}`;
            }
        }
        
        const card = document.createElement('div');
        card.className = 'detail-card location-item';
        card.style.cssText = `border-left: 3px solid ${color}; cursor: pointer;`;
        if (selectedItemId === obj.id) {
            card.classList.add('selected-location-item');
        }
        
        // Build damage/armor/weight info line
        let statsLine = '';
        // Doors: show condition + health
        const isDoorObj = (objId >= 0x140 && objId <= 0x14F);
        if (isDoorObj && obj.extra_info && obj.extra_info.door_health !== undefined) {
            const rawCond = obj.extra_info.door_condition || '';
            const condDisplay = rawCond;
            statsLine += `<div style="font-size: 0.75rem; color: var(--text-muted);">Status: ${escapeHtml(condDisplay)}</div>`;
            const doorMax = (obj.extra_info.door_max_health !== undefined) ? obj.extra_info.door_max_health : 40;
            const healthText = (rawCond === 'massive') ? 'unbreakable' : `${obj.extra_info.door_health}/${doorMax}`;
            statsLine += `<div style="font-size: 0.75rem; color: var(--text-accent); font-family: var(--font-mono);">Health: ${healthText}</div>`;
        }
        if (objId <= 0x0F && (obj.slash_damage !== undefined || obj.bash_damage !== undefined || obj.stab_damage !== undefined)) {
            statsLine = `<div style="font-size: 0.75rem; color: #e03131; font-family: var(--font-mono);">${formatDamage(obj)}</div>`;
        }
        // Show durability for weapons (melee and ranged)
        if (objId <= 0x1F && obj.max_durability !== undefined) {
            statsLine += `<div style="font-size: 0.75rem; color: #fab005; font-family: var(--font-mono);">${formatDurability(obj)}</div>`;
        }
        if (isArmor(obj) && (obj.protection !== undefined || obj.max_durability !== undefined)) {
            statsLine += `<div style="font-size: 0.75rem; color: #5c7cfa; font-family: var(--font-mono);">${formatArmor(obj)}</div>`;
        }
        // Don't show weight for scenery items (0xC0-0xDF), campfire (0x12A), fountain (0x12E), or storage items
        const isStorage = obj.category === 'storage';
        // Exclude weight for storage items - they should never show weight
        if (obj.weight !== undefined && obj.weight > 0 && !isStorage && !(objId >= 0xC0 && objId <= 0xDF) && objId !== 0x12A && objId !== 0x12E) {
            statsLine += `<div style="font-size: 0.75rem; color: var(--text-muted);">⚖️ ${formatWeight(obj.weight)}</div>`;
        }
        // Show nutrition for food items (0xB0-0xB9, 0xBD water)
        if (obj.nutrition !== undefined) {
            const nutritionColor = obj.nutrition >= 40 ? '#69db7c' : 
                                   obj.nutrition >= 20 ? '#a9e34b' : 
                                   obj.nutrition > 0 ? '#fcc419' : '#ff6b6b';
            statsLine += `<div style="font-size: 0.75rem; color: ${nutritionColor};">🍖 Nutrition: ${obj.nutrition}${obj.nutrition === 0 ? ' (none!)' : ''}</div>`;
        }
        // Show intoxication for alcoholic drinks
        if (obj.intoxication !== undefined && obj.intoxication > 0) {
            const intoxColor = obj.intoxication >= 100 ? '#ff6b6b' : 
                               obj.intoxication >= 50 ? '#ffa94d' : '#fcc419';
            statsLine += `<div style="font-size: 0.75rem; color: ${intoxColor};">🍺 Intoxication: ${obj.intoxication}</div>`;
        }
        // Show container capacity (but not for storage items - they should never show capacity)
        if (!isStorage && obj.capacity !== undefined && obj.capacity !== null) {
            let capacityText = `📦 Capacity: ${obj.capacity} stone${obj.capacity !== 1 ? 's' : ''}`;
            if (obj.accepts && obj.accepts !== 'any') {
                capacityText += ` (${obj.accepts} only)`;
            }
            statsLine += `<div style="font-size: 0.75rem; color: var(--text-accent);">${capacityText}</div>`;
        }
        // Show spell effect for spell scrolls
        if (obj.category === 'spell_scrolls' && obj.effect) {
            statsLine += `<div style="font-size: 0.75rem; color: #da77f2;">⚡ ${escapeHtml(obj.effect)}</div>`;
        }
        // Show enchantment effect for other enchanted items
        else if (isEnchanted(obj) && obj.effect && isMagicalEffect(obj.effect)) {
            statsLine += `<div style="font-size: 0.75rem; color: var(--text-accent);">⚡ ${escapeHtml(obj.effect)}</div>`;
        }
        // Show description/effect for switches, traps, and triggers (including lever 0x161)
        const isSwitchTrapTrigger = (objId >= 0x170 && objId <= 0x17F) || objId === 0x161 || (objId >= 0x180 && objId <= 0x1BF);
        if (isSwitchTrapTrigger && obj.description) {
            statsLine += `<div style="font-size: 0.75rem; color: #ffa94d; margin-top: 2px;">⚙️ ${escapeHtml(obj.description)}</div>`;
        }
        // Show quantity for stackable items (only if > 1)
        if (obj.quantity && obj.quantity > 1) {
            statsLine += `<div style="font-size: 0.75rem; color: #fcc419;">📦 Qty: ${obj.quantity}</div>`;
        }
        // Show ownership information
        if (isOwned(obj)) {
            const ownerName = obj.owner_name || `NPC #${obj.owner}`;
            statsLine += `<div style="font-size: 0.75rem; color: #fab005;">⚠️ Owned by ${escapeHtml(ownerName)}</div>`;
        }
        
        // For storage items, always show contents count (even if empty)
        let contentsInfo = '';
        if (isStorage) {
            if (hasContents) {
                contentsInfo = `<div style="font-size: 0.75rem; color: var(--text-accent); margin-top: 4px;">📦 ${obj.contents.length} item${obj.contents.length > 1 ? 's' : ''} inside</div>`;
            } else {
                contentsInfo = `<div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 4px;">📦 Empty</div>`;
            }
        } else if (hasContents) {
            contentsInfo = `<div style="font-size: 0.75rem; color: var(--text-accent); margin-top: 4px;">${obj.contents.length} item${obj.contents.length > 1 ? 's' : ''} inside</div>`;
        }
        
        // Show description for writing/gravestones in location cards
        // Books/scrolls: 0x130-0x13F (excluding 0x13B map) = 304-319 (excluding 315)
        // Gravestones: 0x165 = 357, Writings: 0x166 = 358
        let descriptionHtml = '';
        const objIdNum = Number(objId);
        const isBookOrScroll = (objIdNum >= 304 && objIdNum <= 319 && objIdNum !== 315);
        const isStationaryWriting = (objIdNum === 357 || objIdNum === 358); // 0x165 = 357, 0x166 = 358
        const isReadable = isBookOrScroll || isStationaryWriting;
        const hasDescLoc = obj.description && String(obj.description).trim().length > 0;
        if (isReadable && hasDescLoc) {
            const maxLen = 80;
            const displayText = obj.description.length > maxLen 
                ? obj.description.substring(0, maxLen) + '...' 
                : obj.description;
            const icon = (objIdNum === 357) ? '🪦' : (objIdNum === 358) ? '📝' : '📜';
            descriptionHtml = `<div style="font-size: 0.75rem; color: #e8d4b8; margin-top: 4px; padding: 4px 6px; background: rgba(232, 212, 184, 0.1); border-left: 2px solid #e8d4b8; border-radius: 2px; font-style: italic; line-height: 1.3;">${icon} "${escapeHtml(displayText)}"</div>`;
        }
        
        // Add image thumbnail if available
        // Exclude images for writings, doors, and texture map objects
        let locationImageHtml = '';
        if (obj.image_path) {
            const objId = obj.object_id || 0;
            // Exclude: writings (0x166), doors (0x140-0x14F), texture map objects (0x16E-0x16F)
            const isWriting = objId === 0x166;
            const isDoor = (objId >= 0x140 && objId <= 0x14F);
            const isTextureMap = (objId >= 0x16E && objId <= 0x16F);
            
            if (!isWriting && !isDoor && !isTextureMap) {
                locationImageHtml = `
                    <div class="location-item-image-container" style="float: right; width: 40px; height: 40px; margin-left: 8px; margin-bottom: 4px;">
                        <img src="${escapeHtml(obj.image_path)}" alt="${escapeHtml(getItemDisplayName(obj))}" 
                             class="location-item-image" 
                             style="width: 100%; height: 100%; object-fit: contain; image-rendering: pixelated; image-rendering: -moz-crisp-edges; image-rendering: crisp-edges;"
                             onerror="this.style.display='none';">
                    </div>
                `;
            }
        }
        
        // Build change badge if save game is loaded
        let objChangeBadge = '';
        if (state.saveGame.currentSaveName && obj.change_type && obj.change_type !== 'unchanged') {
            const changeColor = window.SaveComparator?.getChangeTypeColor(obj.change_type) || '#868e96';
            const changeIcon = window.SaveComparator?.getChangeTypeIcon(obj.change_type) || '';
            const changeLabel = window.SaveComparator?.getChangeTypeLabel(obj.change_type) || '';
            objChangeBadge = `<span class="change-badge change-${obj.change_type}" style="margin-left: 6px;">${changeIcon} ${changeLabel}</span>`;
        }

        card.innerHTML = `
            ${locationImageHtml}
            <div class="detail-name" style="font-size: 0.9rem; display: flex; align-items: center; flex-wrap: wrap;">${getItemDisplayName(obj)}${hasContents ? ' 📦' : ''}${lockInfo ? ` <span style="color: #ff6b6b;">${lockInfo}</span>` : ''}${objChangeBadge}</div>
            <div style="font-size: 0.8rem; color: var(--text-muted);">${formatCategory(obj.category)}</div>
            <div style="font-size: 0.75rem; color: var(--text-muted); font-family: var(--font-mono);">ID: ${objId} (0x${objId.toString(16).toUpperCase().padStart(3, '0')})</div>
            ${statsLine}
            ${contentsInfo}
            ${descriptionHtml}
        `;
        
        card.addEventListener('click', () => selectLocationItem(obj, false, tileX, tileY));
        elements.locationObjects.appendChild(card);
    });
    
    // Render secrets
    secretsAtTile.forEach(secret => {
        const typeLabel = secret.type === 'illusory_wall' ? '🔮 Illusory Wall' : '🚪 Secret Door';
        const typeColor = secret.type === 'illusory_wall' ? '#ff00ff' : '#ffff00';
        
        // Check for lock info (secret doors)
        let lockInfo = '';
        if (secret.type === 'secret_door' && secret.details && secret.details.is_locked) {
            const lockId = secret.details.lock_id;
            const lockType = secret.details.lock_type;
            const isPickable = secret.details.is_pickable;
            if (lockType === 'special') {
                lockInfo = '🔒 Special';
            } else if (lockId !== undefined) {
                lockInfo = `🔒 Lock #${lockId}`;
                if (isPickable) {
                    lockInfo += ' ⛏️';  // Can be picked
                }
            } else {
                lockInfo = '🔒 Locked';
            }
        }
        
        const card = document.createElement('div');
        card.className = 'detail-card location-item';
        card.style.cssText = `border-left: 3px solid ${typeColor}; cursor: pointer;`;
        if (selectedItemId === secret.id) {
            card.classList.add('selected-location-item');
        }
        
        // Build reveal method info for illusory walls
        let revealMethodInfo = '';
        if (secret.type === 'illusory_wall' && secret.details) {
            const triggerString = secret.details.trigger;
            const revealMethod = getIllusoryWallRevealMethod(triggerString);
            // Remove HTML tags for the location view
            const revealMethodText = revealMethod.replace(/<[^>]*>/g, '');
            if (triggerString) {
                revealMethodInfo = `<div style="font-size: 0.75rem; color: var(--text-accent); margin-top: 4px;">${revealMethodText}</div>`;
            } else {
                revealMethodInfo = `<div style="font-size: 0.75rem; color: var(--text-accent); margin-top: 4px;">✨ ${revealMethodText}</div>`;
            }
            // Also show what it reveals
            if (secret.details.new_tile_type) {
                revealMethodInfo = `<div style="font-size: 0.75rem; color: var(--text-accent); margin-top: 4px;">Reveals: ${escapeHtml(secret.details.new_tile_type)}</div>${revealMethodInfo}`;
            }
        }
        
        // For illusory walls, skip the redundant description if it's just "Illusory wall -> {type}"
        // since we show "Reveals" separately below
        const isRedundantDescription = secret.type === 'illusory_wall' && 
                                        secret.description && 
                                        secret.description.startsWith('Illusory wall ->');
        const descriptionHtml = (!isRedundantDescription && secret.description) 
            ? `<div style="font-size: 0.8rem; color: var(--text-muted);">${secret.description}</div>`
            : '';
        
        // Show health for secret doors (they can be broken down)
        let healthInfo = '';
        if (secret.type === 'secret_door' && secret.details && secret.details.door_health !== undefined) {
            const doorHealth = secret.details.door_health;
            const doorMax = secret.details.door_max_health !== undefined ? secret.details.door_max_health : 40;
            healthInfo = `<div style="font-size: 0.75rem; color: var(--text-accent); font-family: var(--font-mono);">Health: ${doorHealth}/${doorMax}</div>`;
        }
        
        card.innerHTML = `
            <div class="detail-name" style="font-size: 0.9rem; color: ${typeColor};">${typeLabel}${lockInfo ? ` <span style="color: #ff6b6b;">${lockInfo}</span>` : ''}</div>
            ${descriptionHtml}
            ${healthInfo}
            ${revealMethodInfo}
        `;
        
        card.addEventListener('click', () => selectSecret(secret));
        elements.locationObjects.appendChild(card);
    });
}

/**
 * Select an item from the location list
 */
function selectLocationItem(item, isNpc, tileX, tileY) {
    // Find the marker for this item if it exists
    const markers = document.querySelectorAll('.marker');
    let markerElement = null;
    
    for (const marker of markers) {
        if (marker.dataset.id === String(item.id) && 
            marker.dataset.isNpc === String(isNpc)) {
            markerElement = marker;
            break;
        }
    }
    
    // Clear previous marker selection (individual markers)
    document.querySelectorAll('.marker.selected').forEach(m => {
        m.classList.remove('selected');
        if (m.dataset.isStarMarker === 'true') {
            m.style.transform = 'scale(1)';
        } else {
            const origR = parseFloat(m.dataset.originalRadius) || CONFIG.marker.radius;
            m.setAttribute('r', origR);
        }
    });
    
    // Clear stacked marker groups (also reset inline styles)
    document.querySelectorAll('.marker-stack.selected').forEach(g => {
        g.classList.remove('selected');
        clearStackedMarkerStyles(g);
    });
    
    // If marker exists, select it visually
    if (markerElement) {
        markerElement.classList.add('selected');
        if (markerElement.dataset.isStarMarker === 'true') {
            markerElement.style.transform = 'scale(1.8)';
        } else {
            const origR = parseFloat(markerElement.dataset.originalRadius) || CONFIG.marker.radius;
            markerElement.setAttribute('r', origR * 1.8);
        }
        state.selectedMarker = markerElement;
    } else {
        // No individual marker found - check for stacked marker group
        const stackedGroups = document.querySelectorAll('.marker-stack');
        let foundStack = false;
        for (const group of stackedGroups) {
            if (group.dataset.tileX === String(tileX) && 
                group.dataset.tileY === String(tileY)) {
                group.classList.add('selected');
                applyStackedMarkerSelectionStyles(group);
                state.selectedMarker = group;
                foundStack = true;
                break;
            }
        }
        if (!foundStack) {
            state.selectedMarker = null;
        }
    }
    
    // Ensure selection pane layout exists (it should, but re-render to be safe)
    if (!elements.objectDetails) {
        renderSelectionPane();
    }
    
    // Update details panel
    renderObjectDetails(item, isNpc);
    
    // Re-render location objects to show selection
    renderLocationObjects(tileX, tileY, item.id);
    
    updateUrlHash();
}

// ============================================================================
// Zoom & Pan
// ============================================================================

function adjustZoom(delta) {
    if (state.viewLocked) return;
    state.zoom = Math.max(CONFIG.zoom.min, Math.min(CONFIG.zoom.max, state.zoom + delta));
    updateMapTransform();
    elements.zoomLevel.textContent = `${Math.round(state.zoom * 100)}%`;
    saveFiltersToStorage();  // Persist zoom to localStorage
    updateUrlHash();
}

function resetView() {
    if (state.viewLocked) return;
    state.zoom = CONFIG.zoom.default;
    state.pan = { x: 0, y: 0 };
    updateMapTransform();
    elements.zoomLevel.textContent = `${Math.round(state.zoom * 100)}%`;
    saveFiltersToStorage();  // Persist zoom to localStorage
    updateUrlHash();
}

function toggleViewLock() {
    state.viewLocked = !state.viewLocked;
    updateViewLockButton();
    saveFiltersToStorage();
}

function updateViewLockButton() {
    const lockBtn = document.getElementById('zoom-lock');
    if (state.viewLocked) {
        lockBtn.classList.add('locked');
        lockBtn.title = 'Unlock View (Zoom & Pan)';
        lockBtn.textContent = '🔓';
    } else {
        lockBtn.classList.remove('locked');
        lockBtn.title = 'Lock View (Zoom & Pan)';
        lockBtn.textContent = '🔒';
    }
}

function updateMapTransform() {
    elements.mapWrapper.style.transform = `translate(${state.pan.x}px, ${state.pan.y}px) scale(${state.zoom})`;
}

// ============================================================================
// Statistics
// ============================================================================

function updateStats() {
    const level = state.data.levels[state.currentLevel];
    if (!level) return;
    
    // Count all items including nested container contents and NPC inventories
    let totalObjects = 0;
    
    // Count objects and their contents
    level.objects.forEach(obj => {
        totalObjects++;
        totalObjects += countNestedItems(obj.contents);
    });
    
    // Count NPCs and their inventories
    level.npcs.forEach(npc => {
        totalObjects++;
        totalObjects += countNestedItems(npc.inventory);
    });
    
    // Count secrets
    if (level.secrets) {
        totalObjects += level.secrets.length;
    }
    
    elements.statObjects.textContent = totalObjects;
}

/**
 * Recursively count all items including nested container contents
 */
function countNestedItems(items) {
    if (!items || items.length === 0) return 0;
    
    let count = items.length;
    items.forEach(item => {
        if (item.contents && item.contents.length > 0) {
            count += countNestedItems(item.contents);
        }
    });
    return count;
}

// ============================================================================
// Utilities
// ============================================================================

function formatCategory(categoryId) {
    // Check hardcoded NPC categories first
    if (categoryId === 'npcs_named') return 'Named NPCs';
    if (categoryId === 'npcs_friendly') return 'Friendly NPCs';
    if (categoryId === 'npcs_hostile') return 'Hostile NPCs';
    // Look up in data categories
    const cat = state.data.categories.find(c => c.id === categoryId);
    return cat ? cat.name : categoryId;
}

/**
 * Get type-specific detail rows based on item category and object_id
 * Only shows relevant information for each type
 */
function getTypeSpecificDetails(item) {
    let html = '';
    const objId = item.object_id;
    
    // Melee Weapons (0x00-0x0F) - show all three damage values, durability, and weight
    if (objId <= 0x0F) {
        const hasDamage = item.slash_damage !== undefined || item.bash_damage !== undefined || item.stab_damage !== undefined;
        if (hasDamage) {
            html += `
                <div class="detail-row">
                    <span class="detail-label">Damage</span>
                    <span class="detail-value" style="font-family: var(--font-mono);">
                        <span title="Slash">⚔️ ${item.slash_damage || 0}</span>
                        <span style="margin-left: 8px;" title="Bash">🔨 ${item.bash_damage || 0}</span>
                        <span style="margin-left: 8px;" title="Stab">🗡️ ${item.stab_damage || 0}</span>
                    </span>
                </div>
            `;
        }
        // Show durability for melee weapons
        if (item.max_durability !== undefined) {
            html += `
                <div class="detail-row">
                    <span class="detail-label">Durability</span>
                    <span class="detail-value" style="font-family: var(--font-mono);">${formatDurability(item)}</span>
                </div>
            `;
        }
        // Show weight for melee weapons
        if (item.weight !== undefined && item.weight > 0) {
            html += `
                <div class="detail-row">
                    <span class="detail-label">Weight</span>
                    <span class="detail-value">${formatWeight(item.weight)}</span>
                </div>
            `;
        }
        return html;
    }
    
    // Ranged Weapons (0x10-0x1F) - show durability and weight
    if (objId >= 0x10 && objId <= 0x1F) {
        // Show durability for ranged weapons
        if (item.max_durability !== undefined) {
            html += `
                <div class="detail-row">
                    <span class="detail-label">Durability</span>
                    <span class="detail-value" style="font-family: var(--font-mono);">${formatDurability(item)}</span>
                </div>
            `;
        }
        if (item.weight !== undefined && item.weight > 0) {
            html += `
                <div class="detail-row">
                    <span class="detail-label">Weight</span>
                    <span class="detail-value">${formatWeight(item.weight)}</span>
                </div>
            `;
        }
        return html;
    }
    
    // Armor (0x20-0x3F) - show protection, durability, and weight
    if (objId >= 0x20 && objId <= 0x3F) {
        if (item.protection !== undefined || item.max_durability !== undefined) {
            const durStr = item.max_durability !== undefined ? formatDurability(item) : '';
            html += `
                <div class="detail-row">
                    <span class="detail-label">Stats</span>
                    <span class="detail-value" style="font-family: var(--font-mono);">
                        <span title="Protection">🛡️ ${item.protection || 0}</span>
                        ${durStr ? `<span style="margin-left: 8px;" title="${getDurabilityTooltip(item)}">${durStr}</span>` : ''}
                    </span>
                </div>
            `;
        }
        if (item.weight !== undefined && item.weight > 0) {
            html += `
                <div class="detail-row">
                    <span class="detail-label">Weight</span>
                    <span class="detail-value">${formatWeight(item.weight)}</span>
                </div>
            `;
        }
        return html;
    }

    // Doors (0x140-0x14F) - show door status and health/condition
    if (objId >= 0x140 && objId <= 0x14F) {
        const extra = item.extra_info || {};
        const condLabel = extra.door_condition || '';
        if (condLabel) {
            const condDisplay = condLabel;
            html += `
                <div class="detail-row">
                    <span class="detail-label">Condition</span>
                    <span class="detail-value">${escapeHtml(condDisplay)}</span>
                </div>
            `;
        }
        
        if (extra.door_health !== undefined) {
            const doorMax = (extra.door_max_health !== undefined) ? extra.door_max_health : 40;
            const healthText = (extra.door_condition === 'massive') ? 'unbreakable' : `${extra.door_health}/${doorMax}`;
            html += `
                <div class="detail-row">
                    <span class="detail-label">Health</span>
                    <span class="detail-value" style="font-family: var(--font-mono);">${healthText}</span>
                </div>
            `;
        }
        
        if (extra.door_variant) {
            html += `
                <div class="detail-row">
                    <span class="detail-label">Variant</span>
                    <span class="detail-value">${escapeHtml(String(extra.door_variant).replace(/_/g, ' '))}</span>
                </div>
            `;
        }
        
        if (extra.door_status) {
            html += `
                <div class="detail-row">
                    <span class="detail-label">Status</span>
                    <span class="detail-value">${escapeHtml(extra.door_status)}</span>
                </div>
            `;
        }
        
        return html;
    }
    
    // Storage items (barrels, chests, cauldron, etc.) - show capacity but not weight
    if (item.category === 'storage') {
        // Show capacity if available
        if (item.capacity !== undefined) {
            html += `
                <div class="detail-row">
                    <span class="detail-label">Capacity</span>
                    <span class="detail-value">${item.capacity} stone${item.capacity !== 1 ? 's' : ''}</span>
                </div>
            `;
        }
        // Show what the container accepts if not "any"
        if (item.accepts && item.accepts !== 'any') {
            html += `
                <div class="detail-row">
                    <span class="detail-label">Accepts</span>
                    <span class="detail-value" style="text-transform: capitalize;">${item.accepts}</span>
                </div>
            `;
        }
        // Storage items don't show weight
        return html;
    }
    
    // Containers (0x80-0x8F) - show capacity and weight
    if (objId >= 0x80 && objId <= 0x8F) {
        // Show capacity if available
        if (item.capacity !== undefined) {
            html += `
                <div class="detail-row">
                    <span class="detail-label">Capacity</span>
                    <span class="detail-value">${item.capacity} stone${item.capacity !== 1 ? 's' : ''}</span>
                </div>
            `;
        }
        // Show what the container accepts if not "any"
        if (item.accepts && item.accepts !== 'any') {
            html += `
                <div class="detail-row">
                    <span class="detail-label">Accepts</span>
                    <span class="detail-value" style="text-transform: capitalize;">${item.accepts}</span>
                </div>
            `;
        }
        // Show weight if available
        if (item.weight !== undefined && item.weight > 0) {
            html += `
                <div class="detail-row">
                    <span class="detail-label">Weight</span>
                    <span class="detail-value">${formatWeight(item.weight)}</span>
                </div>
            `;
        }
        return html;
    }
    
    // Light sources (0x90-0x97) - no special fields
    if (objId >= 0x90 && objId <= 0x97) {
        return html;
    }
    
    // Wands (0x98-0x9B) - effect shows spell and charges
    if (objId >= 0x98 && objId <= 0x9B) {
        // Effect field already contains "Spell Name (X charges)"
        return html;
    }
    
    // Treasure/coins (0xA0-0xAF) - quantity shown in description
    if (objId >= 0xA0 && objId <= 0xAF) {
        return html;
    }
    
    // Food items - use category (from backend) so plants (0xCE, 0xCF), dead rotworm (0xD9), etc. are treated correctly
    if (item.category === 'food') {
        // Show intoxication for alcoholic drinks (ale, port)
        if (item.intoxication !== undefined && item.intoxication > 0) {
            const intoxColor = item.intoxication >= 100 ? '#ff6b6b' : 
                               item.intoxication >= 50 ? '#ffa94d' : '#fcc419';
            html += `
                <div class="detail-row">
                    <span class="detail-label">Intoxication</span>
                    <span class="detail-value" style="color: ${intoxColor}; font-weight: 500;">
                        🍺 ${item.intoxication}
                    </span>
                </div>
            `;
        }
        // Show nutrition (or "no effect" for water)
        if (item.nutrition !== undefined) {
            const nutritionColor = item.nutrition >= 40 ? '#69db7c' : 
                                   item.nutrition >= 20 ? '#a9e34b' : 
                                   item.nutrition > 0 ? '#fcc419' : '#ff6b6b';
            // Special note for water (0xBD) which has no effect; use object_id for this specific ID check
            const objIdNum = Number(item.object_id);
            const noEffectNote = (objIdNum === 0xBD && item.nutrition === 0) ? ' (no effect!)' : 
                                 (item.nutrition === 0) ? ' (no nutrition!)' : '';
            html += `
                <div class="detail-row">
                    <span class="detail-label">Nutrition</span>
                    <span class="detail-value" style="color: ${nutritionColor}; font-weight: 500;">
                        🍖 ${item.nutrition}${noEffectNote}
                    </span>
                </div>
            `;
        }
        // Show weight if available
        if (item.weight !== undefined && item.weight > 0) {
            html += `
                <div class="detail-row">
                    <span class="detail-label">Weight</span>
                    <span class="detail-value">${formatWeight(item.weight)}</span>
                </div>
            `;
        }
        return html;
    }
    
    // Potions (0xBB red mana, 0xBC green health) - effect shows potion type
    if (objId === 0xBB || objId === 0xBC) {
        return html;
    }
    
    // Wine of Compassion (0xBF) - quest item, no consumable stats needed
    if (objId === 0xBF) {
        return html;
    }
    
    // Scenery (0xC0-0xDF), campfire (0x12A), and fountain (0x12E) - no fields needed
    if ((objId >= 0xC0 && objId <= 0xDF) || objId === 0x12A || objId === 0x12E) {
        return html;
    }
    
    // Runes (0xE0-0xFF) - no special fields
    if (objId >= 0xE0 && objId <= 0xFF) {
        return html;
    }
    
    // Keys (0x100-0x10E) - show which lock it opens
    if (objId >= 0x100 && objId <= 0x10E) {
        // Check effect field for "Opens lock #N"
        const effectText = item.effect || item.description || '';
        if (effectText.includes('lock #')) {
            const match = effectText.match(/lock #(\d+)/);
            if (match) {
                html += `
                    <div class="detail-row">
                        <span class="detail-label">Key ID</span>
                        <span class="detail-value" style="color: #fab005;">🔑 ${match[1]}</span>
                    </div>
                `;
            }
        }
        return html;
    }
    
    // Books and Scrolls (0x130-0x13F) - description shows content
    if (objId >= 0x130 && objId <= 0x13F) {
        return html;
    }
    
    // Texture map objects (0x16E-0x16F) - no status needed
    if (objId === 0x16E || objId === 0x16F) {
        return html;
    }
    
    // Doors (0x140-0x14F) - show lock information
    // Only check actual door range, not the broader 0x140-0x17F range that includes furniture, decals, texture maps, and switches
    if (objId >= 0x140 && objId <= 0x14F) {
        if (item.extra_info && item.extra_info.is_locked) {
            const lockId = item.extra_info.lock_id;
            const lockType = item.extra_info.lock_type;
            const isPickable = item.extra_info.is_pickable;
            
            if (lockType === 'special') {
                html += `
                    <div class="detail-row">
                        <span class="detail-label">Lock</span>
                        <span class="detail-value" style="color: #ff6b6b;">🔒 Special (trigger)</span>
                    </div>
                `;
            } else {
                html += `
                    <div class="detail-row">
                        <span class="detail-label">Lock ID</span>
                        <span class="detail-value" style="color: #fab005;">🔒 ${lockId}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Pickable</span>
                        <span class="detail-value" style="color: ${isPickable ? '#69db7c' : '#ff6b6b'};">${isPickable ? '⛏️ Yes' : 'No'}</span>
                    </div>
                `;
            }
        } else if (item.extra_info && item.extra_info.is_open) {
            html += `
                <div class="detail-row">
                    <span class="detail-label">Status</span>
                    <span class="detail-value" style="color: #69db7c;">Open</span>
                </div>
            `;
        } else {
            html += `
                <div class="detail-row">
                    <span class="detail-label">Status</span>
                    <span class="detail-value" style="color: #69db7c;">Unlocked</span>
                </div>
            `;
        }
        return html;
    }
    
    // Traps/Triggers (0x180-0x1BF) - minimal info
    if (objId >= 0x180 && objId <= 0x1BF) {
        return html;
    }
    
    // Default - show nothing extra (description and effect cover it)
    return html;
}

/**
 * Escape HTML special characters to prevent XSS
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Get the display name for an item (just the name, quantity shown separately)
 */
function getItemDisplayName(item) {
    // For keys (0x100-0x10E), construct a more descriptive name from the effect field
    const objId = item.object_id || 0;
    if (objId >= 0x100 && objId <= 0x10E) {
        // Keys have "Opens lock #N" in the effect field - extract the lock number
        if (item.effect) {
            const match = item.effect.match(/lock #(\d+)/i);
            if (match) {
                return `Key #${match[1]}`;
            }
        }
    }
    return item.name || 'Unknown';
}

/**
 * Format quantity display for stackable items
 * Returns empty string if quantity is 1 or not set
 */
function formatQuantity(item) {
    const quantity = item.quantity || 0;
    if (quantity > 1) {
        return `×${quantity}`;
    }
    return '';
}

/**
 * Format weight value in stones
 */
function formatWeight(weight) {
    if (weight === undefined || weight === null) return '';
    // Weight is in stones (already converted from 0.1 stones in the exporter)
    if (weight >= 1) {
        return `${weight.toFixed(1)} stones`;
    } else {
        return `${weight.toFixed(1)} stone`;
    }
}

/**
 * Format weapon damage values as a compact string
 */
function formatDamage(item) {
    if (item.slash_damage === undefined && item.bash_damage === undefined && item.stab_damage === undefined) {
        return '';
    }
    return `⚔️${item.slash_damage || 0} 🔨${item.bash_damage || 0} 🗡️${item.stab_damage || 0}`;
}

/**
 * Format armor stats (protection and durability) as a compact string
 */
function formatArmor(item) {
    if (item.protection === undefined && item.max_durability === undefined) {
        return '';
    }
    const durabilityStr = formatDurability(item);
    return `🛡️${item.protection || 0} ${durabilityStr}`;
}

/**
 * Format durability as current/max
 * 
 * Data sources (from uw-formats.txt documentation):
 * - max_durability: from OBJECTS.DAT - the item type's max durability (e.g., leather vest = 8)
 * - quality: from placed object data, bits 0-5 of word 2 (range 0-63)
 *            This is the item's current condition (0=destroyed, 63=pristine)
 * 
 * The quality is scaled to the item's max durability for display:
 *   current = round((quality / 63) * max_durability)
 * 
 * Items with max_durability=255 are indestructible.
 */
function formatDurability(item) {
    if (item.max_durability === undefined) {
        return '';
    }
    // 255 durability = indestructible
    if (item.max_durability === 255) {
        return '🔧∞';
    }
    const maxDur = item.max_durability;
    if (item.quality !== undefined) {
        // Scale quality (0-63) to the item's actual durability range
        // quality=63 means 100% of max durability, quality=0 means 0%
        const scaledCurrent = Math.round((item.quality / 63) * maxDur);
        return `🔧${scaledCurrent}/${maxDur}`;
    }
    // No quality data, just show max (item assumed to be pristine)
    return `🔧${maxDur}/${maxDur}`;
}

/**
 * Get tooltip text for durability
 */
function getDurabilityTooltip(item) {
    if (item.max_durability === undefined) {
        return 'Durability';
    }
    if (item.max_durability === 255) {
        return 'Indestructible';
    }
    return 'Durability (current/max)';
}

/**
 * Check if an item is armor (object_id 0x20-0x3F)
 */
function isArmor(item) {
    const objId = item.object_id || 0;
    return objId >= 0x20 && objId <= 0x3F;
}

/**
 * Truncate text to a maximum length with ellipsis
 */
function truncateText(text, maxLength = 100) {
    if (!text || text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

function debounce(fn, delay) {
    let timeoutId;
    return function(...args) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => fn.apply(this, args), delay);
    };
}

