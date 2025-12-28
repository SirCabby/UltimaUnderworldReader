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
    
    // Marker settings
    marker: {
        radius: 4,
        strokeWidth: 1.5,
    },
    
    // Paths
    paths: {
        data: 'data/web_map_data.json',
        maps: 'maps/level{n}.png',  // Using PNG for better quality
    }
};

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
    filters: {
        categories: new Set(),  // Active category filters
        search: '',
        enchantedOnly: false,   // Show only enchanted items
    },
    selectedMarker: null,
};

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
    categoryFilters: null,
    searchInput: null,
    tooltip: null,
    objectDetails: null,
    locationObjects: null,
    loadingOverlay: null,
    zoomLevel: null,
    statObjects: null,
    statNpcs: null,
    statVisible: null,
    coordDisplay: null,
    coordValue: null,
    enchantedFilter: null,
    enchantedCount: null,
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
    
    // Load data
    try {
        await loadData();
        
        // Initialize UI
        renderLevelTabs();
        renderCategoryFilters();
        
        // Load first level and immediately update counts
        selectLevel(0);
        updateCategoryCounts();
        
        // Hide loading overlay
        elements.loadingOverlay.classList.add('hidden');
    } catch (error) {
        console.error('Failed to initialize:', error);
        elements.loadingOverlay.innerHTML = `
            <p style="color: #ff6b6b;">Error loading data</p>
            <p style="font-size: 0.9rem; color: var(--text-muted);">${error.message}</p>
        `;
    }
}

function cacheElements() {
    elements.mapContainer = document.getElementById('map-container');
    elements.mapWrapper = document.getElementById('map-wrapper');
    elements.mapImage = document.getElementById('map-image');
    elements.markersLayer = document.getElementById('markers-layer');
    elements.tileHighlight = document.getElementById('tile-highlight');
    elements.levelTabs = document.getElementById('level-tabs');
    elements.categoryFilters = document.getElementById('category-filters');
    elements.searchInput = document.getElementById('search-input');
    elements.tooltip = document.getElementById('tooltip');
    elements.objectDetails = document.getElementById('object-details');
    elements.locationObjects = document.getElementById('location-objects');
    elements.loadingOverlay = document.getElementById('loading-overlay');
    elements.zoomLevel = document.getElementById('zoom-level');
    elements.statObjects = document.getElementById('stat-objects');
    elements.statNpcs = document.getElementById('stat-npcs');
    elements.statVisible = document.getElementById('stat-visible');
    elements.coordDisplay = document.getElementById('coord-display');
    elements.coordValue = document.getElementById('coord-value');
    elements.enchantedFilter = document.getElementById('enchanted-filter');
    elements.enchantedCount = document.getElementById('enchanted-count');
}

async function loadData() {
    const response = await fetch(CONFIG.paths.data);
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    state.data = await response.json();
    
    // Initialize filters with all categories enabled
    state.data.categories.forEach(cat => {
        state.filters.categories.add(cat.id);
    });
    // Also add NPCs category
    state.filters.categories.add('npcs');
}

// ============================================================================
// Event Listeners
// ============================================================================

function setupEventListeners() {
    // Zoom controls
    document.getElementById('zoom-in').addEventListener('click', () => adjustZoom(CONFIG.zoom.step));
    document.getElementById('zoom-out').addEventListener('click', () => adjustZoom(-CONFIG.zoom.step));
    document.getElementById('zoom-reset').addEventListener('click', resetView);
    
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
    document.getElementById('select-all-categories').addEventListener('click', selectAllCategories);
    document.getElementById('deselect-all-categories').addEventListener('click', deselectAllCategories);
    
    // Enchanted filter
    elements.enchantedFilter.addEventListener('change', handleEnchantedFilter);
    
    // Keyboard shortcuts
    document.addEventListener('keydown', handleKeyboard);
}

function handleEnchantedFilter(e) {
    state.filters.enchantedOnly = e.target.checked;
    renderMarkers();
    updateStats();
}

function handleWheel(e) {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -CONFIG.zoom.step : CONFIG.zoom.step;
    adjustZoom(delta);
}

function handlePanStart(e) {
    if (e.button !== 0) return;
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

function selectLevel(levelNum) {
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
    }
    
    elements.mapImage.onload = () => {
        // Render markers after image loads
        renderMarkers();
        updateStats();
        updateCategoryCounts();
    };
    
    // Reset view
    resetView();
    clearSelection();
}

// ============================================================================
// Category Filters
// ============================================================================

function renderCategoryFilters() {
    elements.categoryFilters.innerHTML = '';
    
    // Add NPC filter first (not included in data.categories)
    const npcFilter = createCategoryFilter({
        id: 'npcs',
        name: 'NPCs',
        color: '#ff6b6b'
    });
    elements.categoryFilters.appendChild(npcFilter);
    
    // Add other categories (skip if it's 'npcs' to avoid duplicate)
    state.data.categories.forEach(cat => {
        if (cat.id === 'npcs') return;  // Already added above
        const filter = createCategoryFilter(cat);
        elements.categoryFilters.appendChild(filter);
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
    
    // Update NPC count
    const npcCountEl = document.querySelector('.category-count[data-category-id="npcs"]');
    if (npcCountEl) {
        npcCountEl.textContent = level.npcs.length;
    }
    
    // Update object category counts
    const categoryCounts = {};
    level.objects.forEach(obj => {
        categoryCounts[obj.category] = (categoryCounts[obj.category] || 0) + 1;
    });
    
    state.data.categories.forEach(cat => {
        // Skip npcs category - it's handled separately above
        if (cat.id === 'npcs') return;
        
        const countEl = document.querySelector(`.category-count[data-category-id="${cat.id}"]`);
        if (countEl) {
            countEl.textContent = categoryCounts[cat.id] || 0;
        }
    });
    
    // Update enchanted item count
    updateEnchantedCount();
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

function selectAllCategories() {
    // Add all categories to the filter set
    state.filters.categories.add('npcs');
    state.data.categories.forEach(cat => {
        state.filters.categories.add(cat.id);
    });
    
    // Update all checkboxes
    document.querySelectorAll('.category-filter input[type="checkbox"]').forEach(cb => {
        cb.checked = true;
    });
    
    renderMarkers();
    updateStats();
}

function deselectAllCategories() {
    // Clear all categories from the filter set
    state.filters.categories.clear();
    
    // Update all checkboxes
    document.querySelectorAll('.category-filter input[type="checkbox"]').forEach(cb => {
        cb.checked = false;
    });
    
    renderMarkers();
    updateStats();
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
    
    // Render NPCs
    if (state.filters.categories.has('npcs')) {
        level.npcs.forEach(npc => {
            if (shouldShowItem(npc)) {
                const marker = createMarker(npc, '#ff6b6b', pxPerTileX, pxPerTileY, true);
                elements.markersLayer.appendChild(marker);
                visibleCount++;
            }
        });
    }
    
    // Render objects
    level.objects.forEach(obj => {
        if (state.filters.categories.has(obj.category) && shouldShowItem(obj)) {
            const color = getCategoryColor(obj.category);
            const marker = createMarker(obj, color, pxPerTileX, pxPerTileY, false);
            elements.markersLayer.appendChild(marker);
            visibleCount++;
        }
    });
    
    elements.statVisible.textContent = visibleCount;
}

function shouldShowItem(item) {
    // Check enchanted filter first
    if (state.filters.enchantedOnly) {
        if (!isEnchanted(item)) return false;
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
 * Check if an effect string represents a true magical enchantment
 * Excludes: keys ("Opens lock #X"), books/scrolls ("Text #X")
 */
function isMagicalEffect(effect) {
    if (!effect) return false;
    
    // Exclude keys that open locks
    if (effect.startsWith('Opens lock')) return false;
    
    // Exclude books/scrolls with text
    if (effect.startsWith('Text #')) return false;
    
    // Everything else with an effect is considered enchanted
    return true;
}

/**
 * Check if an item is enchanted (has an effect field with magical properties)
 * Also recursively checks container contents and NPC inventory
 */
function isEnchanted(item) {
    // Check if item itself has a magical effect (not just text or lock info)
    if (isMagicalEffect(item.effect)) return true;
    
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
 * Recursively check if any content item is enchanted
 */
function hasEnchantedContent(contents) {
    for (const contentItem of contents) {
        if (isMagicalEffect(contentItem.effect)) return true;
        
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
    // Convert tile coordinates to pixel position
    // Note: Y is flipped because game coords have Y=0 at south (bottom)
    // but image has Y=0 at top
    const px = CONFIG.mapArea.offsetX + (item.tile_x + 0.5) * pxPerTileX;
    const py = CONFIG.mapArea.offsetY + (CONFIG.mapArea.gridSize - item.tile_y - 0.5) * pxPerTileY;
    
    const marker = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    marker.setAttribute('cx', px);
    marker.setAttribute('cy', py);
    marker.setAttribute('r', isNpc ? CONFIG.marker.radius + 1 : CONFIG.marker.radius);
    marker.setAttribute('fill', color);
    marker.setAttribute('stroke', isNpc ? '#fff' : 'rgba(0,0,0,0.5)');
    marker.setAttribute('stroke-width', CONFIG.marker.strokeWidth);
    marker.classList.add('marker');
    
    // Store item data
    marker.dataset.id = item.id;
    marker.dataset.isNpc = isNpc;
    marker.dataset.tileX = item.tile_x;
    marker.dataset.tileY = item.tile_y;
    
    // Store original radius for hover effect
    const originalRadius = isNpc ? CONFIG.marker.radius + 1 : CONFIG.marker.radius;
    marker.dataset.originalRadius = originalRadius;
    
    // Event listeners
    marker.addEventListener('mouseenter', (e) => {
        // Increase radius on hover (instead of transform which causes flickering)
        marker.setAttribute('r', originalRadius * 1.5);
        showTooltip(e, item, isNpc);
    });
    marker.addEventListener('mouseleave', () => {
        // Restore original radius unless selected
        if (!marker.classList.contains('selected')) {
            marker.setAttribute('r', originalRadius);
        }
        hideTooltip();
    });
    marker.addEventListener('click', () => selectItem(item, isNpc, marker));
    
    return marker;
}

function getCategoryColor(categoryId) {
    const cat = state.data.categories.find(c => c.id === categoryId);
    return cat ? cat.color : '#868e96';
}

// ============================================================================
// Tooltip
// ============================================================================

function showTooltip(e, item, isNpc) {
    const tooltip = elements.tooltip;
    
    let html = `<div class="tooltip-name">${item.name || (isNpc ? 'Unknown NPC' : 'Unknown Object')}</div>`;
    
    if (isNpc) {
        // Show creature type if different from name
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
        // Show effect preview in tooltip only for truly magical effects
        if (isMagicalEffect(item.effect)) {
            html += `<div class="tooltip-info" style="color: #9775fa; font-size: 0.8rem;">✨ ${escapeHtml(truncateText(item.effect, 50))}</div>`;
        }
        // Show description preview (truncated) for books/scrolls/keys
        if (item.description && item.description.length > 0) {
            html += `<div class="tooltip-info" style="color: var(--text-accent); font-size: 0.8rem;">${escapeHtml(truncateText(item.description, 60))}</div>`;
        }
        // Show container count
        if (item.contents && item.contents.length > 0) {
            html += `<div class="tooltip-info" style="color: var(--text-accent);">📦 ${item.contents.length} item${item.contents.length > 1 ? 's' : ''} inside</div>`;
        }
    }
    
    html += `<div class="tooltip-position">Tile: (${item.tile_x}, ${item.tile_y})</div>`;
    
    tooltip.innerHTML = html;
    tooltip.classList.add('visible');
    
    // Position tooltip
    updateTooltipPosition(e);
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
    elements.tooltip.classList.remove('visible');
}

// ============================================================================
// Selection & Details
// ============================================================================

function selectItem(item, isNpc, markerElement) {
    // Clear previous selection and restore original radius
    document.querySelectorAll('.marker.selected').forEach(m => {
        m.classList.remove('selected');
        const origR = parseFloat(m.dataset.originalRadius) || CONFIG.marker.radius;
        m.setAttribute('r', origR);
    });
    
    // Mark new selection and increase radius
    markerElement.classList.add('selected');
    const origR = parseFloat(markerElement.dataset.originalRadius) || CONFIG.marker.radius;
    markerElement.setAttribute('r', origR * 1.8);
    state.selectedMarker = markerElement;
    
    // Update details panel
    renderObjectDetails(item, isNpc);
    
    // Find all items at same tile, passing the selected item id
    renderLocationObjects(item.tile_x, item.tile_y, item.id);
}

function clearSelection() {
    document.querySelectorAll('.marker.selected').forEach(m => {
        m.classList.remove('selected');
        const origR = parseFloat(m.dataset.originalRadius) || CONFIG.marker.radius;
        m.setAttribute('r', origR);
    });
    state.selectedMarker = null;
    elements.objectDetails.innerHTML = '<p class="no-selection">Hover over a marker to see details</p>';
    elements.locationObjects.innerHTML = '<p class="no-selection">Click a marker to see all objects at that tile</p>';
}

function renderObjectDetails(item, isNpc) {
    let html = '<div class="detail-card">';
    html += `<div class="detail-name">${item.name || (isNpc ? 'Unknown NPC' : 'Unknown Object')}</div>`;
    
    if (isNpc) {
        html += `
            <div class="detail-row">
                <span class="detail-label">Type</span>
                <span class="detail-category" style="background: rgba(255,107,107,0.2); color: #ff6b6b;">NPC</span>
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
        html += `
            <div class="detail-row">
                <span class="detail-label">Category</span>
                <span class="detail-category" style="background: ${catColor}22; color: ${catColor};">${formatCategory(item.category)}</span>
            </div>
        `;
        
        // Show type-specific details based on category/object_id
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
        const qty = item.quantity > 1 ? ` (×${item.quantity})` : '';
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
        nameDiv.textContent = `${item.name || 'Unknown'}${qty}${hasEffect}${hasContents ? ' 📦' : ''}`;
        
        // Build info line with category and optional effect preview (only for magical effects)
        let infoText = formatCategory(item.category);
        if (isMagicalEffect(item.effect)) {
            infoText += ` • ${truncateText(item.effect, 30)}`;
        }
        
        const infoDiv = document.createElement('div');
        infoDiv.style.cssText = 'color: var(--text-muted); font-size: 0.75rem;';
        infoDiv.textContent = infoText;
        
        contentItem.appendChild(nameDiv);
        contentItem.appendChild(infoDiv);
        
        // Show description preview for readable items (books, scrolls)
        if (item.description && item.description.length > 0) {
            const descDiv = document.createElement('div');
            descDiv.style.cssText = 'color: var(--text-accent); font-size: 0.7rem; margin-top: 2px; font-style: italic;';
            descDiv.textContent = truncateText(item.description, 50);
            contentItem.appendChild(descDiv);
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
        const qty = item.quantity > 1 ? ` (×${item.quantity})` : '';
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
        nameDiv.textContent = `${item.name || 'Unknown'}${qty}${hasEffect}${hasContents ? ' 📦' : ''}`;
        
        // Build info line with category and optional effect preview (only for magical effects)
        let infoText = formatCategory(item.category);
        if (isMagicalEffect(item.effect)) {
            infoText += ` • ${truncateText(item.effect, 30)}`;
        }
        
        const infoDiv = document.createElement('div');
        infoDiv.style.cssText = 'color: var(--text-muted); font-size: 0.75rem;';
        infoDiv.textContent = infoText;
        
        inventoryItem.appendChild(nameDiv);
        inventoryItem.appendChild(infoDiv);
        
        // Show description preview for readable items (books, scrolls)
        if (item.description && item.description.length > 0) {
            const descDiv = document.createElement('div');
            descDiv.style.cssText = 'color: var(--text-accent); font-size: 0.7rem; margin-top: 2px; font-style: italic;';
            descDiv.textContent = truncateText(item.description, 50);
            inventoryItem.appendChild(descDiv);
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
    html += `<div class="detail-name">${item.name || 'Unknown Object'}</div>`;
    
    const catColor = getCategoryColor(item.category);
    html += `
        <div class="detail-row">
            <span class="detail-label">Category</span>
            <span class="detail-category" style="background: ${catColor}22; color: ${catColor};">${formatCategory(item.category)}</span>
        </div>
    `;
    
    // Show quantity only if > 1 (stackable items)
    if (item.quantity && item.quantity > 1) {
        html += `
            <div class="detail-row">
                <span class="detail-label">Quantity</span>
                <span class="detail-value">${item.quantity}</span>
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
    html += `<div class="detail-name">${item.name || 'Unknown Object'}</div>`;
    
    const catColor = getCategoryColor(item.category);
    html += `
        <div class="detail-row">
            <span class="detail-label">Category</span>
            <span class="detail-category" style="background: ${catColor}22; color: ${catColor};">${formatCategory(item.category)}</span>
        </div>
    `;
    
    // Show quantity only if > 1 (stackable items)
    if (item.quantity && item.quantity > 1) {
        html += `
            <div class="detail-row">
                <span class="detail-label">Quantity</span>
                <span class="detail-value">${item.quantity}</span>
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
    
    // Find all items at this tile
    const npcsAtTile = level.npcs.filter(n => n.tile_x === tileX && n.tile_y === tileY);
    const objectsAtTile = level.objects.filter(o => o.tile_x === tileX && o.tile_y === tileY);
    
    if (npcsAtTile.length === 0 && objectsAtTile.length === 0) {
        elements.locationObjects.innerHTML = '<p class="no-selection">No objects at this location</p>';
        return;
    }
    
    // Clear container and build with DOM elements for click handlers
    elements.locationObjects.innerHTML = '';
    
    const header = document.createElement('p');
    header.style.cssText = 'color: var(--text-muted); margin-bottom: 8px;';
    header.textContent = `Tile (${tileX}, ${tileY}) - ${npcsAtTile.length + objectsAtTile.length} items`;
    elements.locationObjects.appendChild(header);
    
    // Render NPCs
    npcsAtTile.forEach(npc => {
        const card = document.createElement('div');
        card.className = 'detail-card location-item';
        card.style.cssText = `border-left: 3px solid #ff6b6b; cursor: pointer;`;
        if (selectedItemId === npc.id) {
            card.classList.add('selected-location-item');
        }
        
        // Show creature type if different from name
        const creatureInfo = (npc.creature_type && npc.creature_type !== npc.name) 
            ? ` (${npc.creature_type})` 
            : '';
        
        const hasInventory = npc.inventory && npc.inventory.length > 0;
        
        card.innerHTML = `
            <div class="detail-name" style="font-size: 0.9rem;">${npc.name || 'Unknown NPC'}${creatureInfo}${hasInventory ? ' 🎒' : ''}</div>
            <div style="font-size: 0.8rem; color: var(--text-muted);">NPC - HP: ${npc.hp}</div>
            ${hasInventory ? `<div style="font-size: 0.75rem; color: var(--text-accent); margin-top: 4px;">${npc.inventory.length} item${npc.inventory.length > 1 ? 's' : ''} carried</div>` : ''}
        `;
        
        card.addEventListener('click', () => selectLocationItem(npc, true, tileX, tileY));
        elements.locationObjects.appendChild(card);
    });
    
    // Render objects
    objectsAtTile.forEach(obj => {
        const color = getCategoryColor(obj.category);
        const hasContents = obj.contents && obj.contents.length > 0;
        
        const card = document.createElement('div');
        card.className = 'detail-card location-item';
        card.style.cssText = `border-left: 3px solid ${color}; cursor: pointer;`;
        if (selectedItemId === obj.id) {
            card.classList.add('selected-location-item');
        }
        
        card.innerHTML = `
            <div class="detail-name" style="font-size: 0.9rem;">${obj.name || 'Unknown'}${hasContents ? ' 📦' : ''}</div>
            <div style="font-size: 0.8rem; color: var(--text-muted);">${formatCategory(obj.category)}</div>
            ${hasContents ? `<div style="font-size: 0.75rem; color: var(--text-accent); margin-top: 4px;">${obj.contents.length} item${obj.contents.length > 1 ? 's' : ''} inside</div>` : ''}
        `;
        
        card.addEventListener('click', () => selectLocationItem(obj, false, tileX, tileY));
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
    
    // Clear previous marker selection
    document.querySelectorAll('.marker.selected').forEach(m => {
        m.classList.remove('selected');
        const origR = parseFloat(m.dataset.originalRadius) || CONFIG.marker.radius;
        m.setAttribute('r', origR);
    });
    
    // If marker exists, select it visually
    if (markerElement) {
        markerElement.classList.add('selected');
        const origR = parseFloat(markerElement.dataset.originalRadius) || CONFIG.marker.radius;
        markerElement.setAttribute('r', origR * 1.8);
        state.selectedMarker = markerElement;
    } else {
        state.selectedMarker = null;
    }
    
    // Update details panel
    renderObjectDetails(item, isNpc);
    
    // Re-render location objects to show selection
    renderLocationObjects(tileX, tileY, item.id);
}

// ============================================================================
// Zoom & Pan
// ============================================================================

function adjustZoom(delta) {
    state.zoom = Math.max(CONFIG.zoom.min, Math.min(CONFIG.zoom.max, state.zoom + delta));
    updateMapTransform();
    elements.zoomLevel.textContent = `${Math.round(state.zoom * 100)}%`;
}

function resetView() {
    state.zoom = CONFIG.zoom.default;
    state.pan = { x: 0, y: 0 };
    updateMapTransform();
    elements.zoomLevel.textContent = `${Math.round(state.zoom * 100)}%`;
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
    
    elements.statObjects.textContent = level.object_count;
    elements.statNpcs.textContent = level.npc_count;
}

// ============================================================================
// Utilities
// ============================================================================

function formatCategory(categoryId) {
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
    
    // Weapons (0x00-0x1F) - show effect if enchanted, otherwise minimal info
    if (objId <= 0x1F) {
        // Only show enchantment info if there's an actual effect
        // The effect field already contains the meaningful enchantment text
        return html;
    }
    
    // Armor (0x20-0x3F) - show effect if enchanted
    if (objId >= 0x20 && objId <= 0x3F) {
        // Only show enchantment info if there's an actual effect
        return html;
    }
    
    // Containers (0x80-0x8F) - no special fields needed
    if (objId >= 0x80 && objId <= 0x8F) {
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
    
    // Food and Potions (0xB0-0xBF) - effect shows potion type
    if (objId >= 0xB0 && objId <= 0xBF) {
        return html;
    }
    
    // Scenery (0xC0-0xDF) - no fields needed
    if (objId >= 0xC0 && objId <= 0xDF) {
        return html;
    }
    
    // Runes (0xE0-0xFF) - no special fields
    if (objId >= 0xE0 && objId <= 0xFF) {
        return html;
    }
    
    // Keys (0x100-0x10E) - description shows what lock it opens
    if (objId >= 0x100 && objId <= 0x10E) {
        return html;
    }
    
    // Books and Scrolls (0x130-0x13F) - description shows content
    if (objId >= 0x130 && objId <= 0x13F) {
        return html;
    }
    
    // Doors (0x140-0x17F) - no special fields for now
    if (objId >= 0x140 && objId <= 0x17F) {
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

