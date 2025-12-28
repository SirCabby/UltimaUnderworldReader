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
    
    // Keyboard shortcuts
    document.addEventListener('keydown', handleKeyboard);
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
    if (!state.filters.search) return true;
    const name = (item.name || '').toLowerCase();
    return name.includes(state.filters.search);
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
    } else {
        html += `<div class="tooltip-info">${formatCategory(item.category)}</div>`;
        if (item.is_enchanted) {
            html += `<div class="tooltip-info" style="color: #9775fa;">✨ Enchanted</div>`;
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
    } else {
        const catColor = getCategoryColor(item.category);
        html += `
            <div class="detail-row">
                <span class="detail-label">Category</span>
                <span class="detail-category" style="background: ${catColor}22; color: ${catColor};">${formatCategory(item.category)}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Object ID</span>
                <span class="detail-value">0x${item.object_id.toString(16).toUpperCase().padStart(3, '0')}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Quality</span>
                <span class="detail-value">${item.quality}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Enchanted</span>
                <span class="detail-value">${item.is_enchanted ? '✨ Yes' : 'No'}</span>
            </div>
        `;
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
    
    // Add container contents if this is a container
    if (item.contents && item.contents.length > 0) {
        html += renderContainerContents(item.contents);
    }
    
    elements.objectDetails.innerHTML = html;
}

/**
 * Render container contents as a nested list
 */
function renderContainerContents(contents, depth = 0) {
    if (!contents || contents.length === 0) return '';
    
    const indent = depth * 12;
    let html = `<div class="container-contents" style="margin-left: ${indent}px; margin-top: 8px;">`;
    html += `<div class="contents-header" style="color: var(--text-accent); font-size: 0.85rem; margin-bottom: 6px;">
        ${depth === 0 ? '📦 Contains:' : '↳ Contains:'}
    </div>`;
    
    contents.forEach(item => {
        const catColor = getCategoryColor(item.category);
        const qty = item.quantity > 1 ? ` (×${item.quantity})` : '';
        const enchanted = item.is_enchanted ? ' ✨' : '';
        
        html += `
            <div class="content-item" style="
                background: var(--bg-tertiary); 
                border-left: 3px solid ${catColor};
                padding: 6px 8px;
                margin-bottom: 4px;
                border-radius: 0 4px 4px 0;
                font-size: 0.85rem;
            ">
                <div style="color: var(--text-primary);">${item.name || 'Unknown'}${qty}${enchanted}</div>
                <div style="color: var(--text-muted); font-size: 0.75rem;">
                    ${formatCategory(item.category)}
                    ${item.quality > 0 ? ` • Quality: ${item.quality}` : ''}
                </div>
            </div>
        `;
        
        // Recursively render nested container contents
        if (item.contents && item.contents.length > 0) {
            html += renderContainerContents(item.contents, depth + 1);
        }
    });
    
    html += '</div>';
    return html;
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
        
        card.innerHTML = `
            <div class="detail-name" style="font-size: 0.9rem;">${npc.name || 'Unknown NPC'}${creatureInfo}</div>
            <div style="font-size: 0.8rem; color: var(--text-muted);">NPC - HP: ${npc.hp}</div>
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

function debounce(fn, delay) {
    let timeoutId;
    return function(...args) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => fn.apply(this, args), delay);
    };
}

