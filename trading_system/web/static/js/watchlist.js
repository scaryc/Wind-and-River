/**
 * Watchlist Management for Wind Catcher & River Turn
 * Handles loading, adding, removing, and drag-drop of symbols
 */

// Global state
let currentModalTimeframe = null;
let currentModalDirection = null;
let draggedItem = null;

/**
 * Load all watchlists from API and render them
 */
async function loadWatchlists() {
    try {
        const response = await fetch('/api/watchlists');
        const data = await response.json();

        if (data.error) {
            console.error('Error loading watchlists:', data.error);
            return;
        }

        // Render Wind Catcher watchlists
        renderWatchlist('wind', '8h', data.wind_catcher['8h'] || []);
        renderWatchlist('wind', '1h', data.wind_catcher['1h'] || []);
        renderWatchlist('wind', '15m', data.wind_catcher['15m'] || []);

        // Render River Turn watchlists
        renderWatchlist('river', '8h', data.river_turn['8h'] || []);
        renderWatchlist('river', '1h', data.river_turn['1h'] || []);
        renderWatchlist('river', '15m', data.river_turn['15m'] || []);

    } catch (error) {
        console.error('Failed to load watchlists:', error);
    }
}

/**
 * Render a single watchlist
 */
function renderWatchlist(prefix, timeframe, symbols) {
    const listId = `${prefix}-${timeframe}`;
    const container = document.getElementById(listId);

    if (!container) {
        console.warn(`Container not found: ${listId}`);
        return;
    }

    // Clear existing items
    container.innerHTML = '';

    // Add symbols
    symbols.forEach(symbol => {
        const direction = prefix === 'wind' ? 'wind_catcher' : 'river_turn';
        const item = createPairItem(symbol, timeframe, direction);
        container.appendChild(item);
    });

    // If empty, show placeholder
    if (symbols.length === 0) {
        const placeholder = document.createElement('li');
        placeholder.className = 'pair-item-placeholder';
        placeholder.textContent = 'Drag symbols here or click + to add';
        placeholder.style.cssText = 'text-align: center; padding: 1rem; color: var(--text-muted); font-size: 0.875rem;';
        container.appendChild(placeholder);
    }
}

/**
 * Create a draggable pair item element
 */
function createPairItem(symbol, timeframe, direction) {
    const li = document.createElement('li');
    li.className = 'pair-item';
    li.draggable = true;
    li.dataset.symbol = symbol;
    li.dataset.timeframe = timeframe;
    li.dataset.direction = direction;

    li.innerHTML = `
        <span class="pair-name">${symbol}</span>
        <span class="remove-btn" onclick="removePair('${symbol}', '${timeframe}', '${direction}')">×</span>
    `;

    // Drag event listeners
    li.addEventListener('dragstart', handleDragStart);
    li.addEventListener('dragend', handleDragEnd);

    return li;
}

/**
 * Handle drag start
 */
function handleDragStart(e) {
    draggedItem = {
        symbol: e.target.dataset.symbol,
        timeframe: e.target.dataset.timeframe,
        direction: e.target.dataset.direction
    };

    e.target.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/html', e.target.innerHTML);
}

/**
 * Handle drag end
 */
function handleDragEnd(e) {
    e.target.classList.remove('dragging');
}

/**
 * Initialize drag-and-drop on all pair lists
 */
function setupDragAndDrop() {
    const lists = document.querySelectorAll('.pair-list');

    lists.forEach(list => {
        list.addEventListener('dragover', handleDragOver);
        list.addEventListener('dragleave', handleDragLeave);
        list.addEventListener('drop', handleDrop);
    });
}

/**
 * Handle drag over (allow drop)
 */
function handleDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';

    const list = e.currentTarget;
    list.classList.add('drag-over');
}

/**
 * Handle drag leave
 */
function handleDragLeave(e) {
    const list = e.currentTarget;

    // Only remove class if actually leaving the list
    if (e.relatedTarget && !list.contains(e.relatedTarget)) {
        list.classList.remove('drag-over');
    }
}

/**
 * Handle drop
 */
async function handleDrop(e) {
    e.preventDefault();
    const list = e.currentTarget;
    list.classList.remove('drag-over');

    if (!draggedItem) return;

    // Get target watchlist info from parent
    const watchlist = list.closest('.watchlist');
    const toTimeframe = watchlist.dataset.timeframe;
    const toDirection = watchlist.dataset.direction;

    // Don't do anything if dropped in same location
    if (draggedItem.timeframe === toTimeframe && draggedItem.direction === toDirection) {
        return;
    }

    // Move the item
    await moveWatchlistEntry(
        draggedItem.symbol,
        draggedItem.timeframe,
        draggedItem.direction,
        toTimeframe,
        toDirection
    );

    draggedItem = null;
}

/**
 * Add a symbol to a watchlist via API
 */
async function addToWatchlist(symbol, timeframe, direction) {
    try {
        const response = await fetch('/api/watchlist/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol, timeframe, direction })
        });

        const result = await response.json();

        if (result.error) {
            alert(`Error: ${result.error}`);
            return false;
        }

        // Reload watchlists to show new item
        await loadWatchlists();
        return true;

    } catch (error) {
        console.error('Failed to add to watchlist:', error);
        alert('Failed to add symbol. Check console for details.');
        return false;
    }
}

/**
 * Remove a symbol from a watchlist via API
 */
async function removePair(symbol, timeframe, direction) {
    if (!confirm(`Remove ${symbol} from ${direction} ${timeframe}?`)) {
        return;
    }

    try {
        const response = await fetch('/api/watchlist/remove', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol, timeframe, direction })
        });

        const result = await response.json();

        if (result.error) {
            alert(`Error: ${result.error}`);
            return;
        }

        // Reload watchlists
        await loadWatchlists();

    } catch (error) {
        console.error('Failed to remove from watchlist:', error);
        alert('Failed to remove symbol. Check console for details.');
    }
}

/**
 * Move a symbol from one watchlist to another via API
 */
async function moveWatchlistEntry(symbol, fromTimeframe, fromDirection, toTimeframe, toDirection) {
    try {
        const response = await fetch('/api/watchlist/move', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                symbol: symbol,
                from: { timeframe: fromTimeframe, direction: fromDirection },
                to: { timeframe: toTimeframe, direction: toDirection }
            })
        });

        const result = await response.json();

        if (result.error) {
            alert(`Error: ${result.error}`);
            return;
        }

        // Reload watchlists to show changes
        await loadWatchlists();

    } catch (error) {
        console.error('Failed to move watchlist entry:', error);
        alert('Failed to move symbol. Check console for details.');
    }
}

/**
 * Show modal for adding a symbol
 */
function showAddSymbolModal(timeframe, direction) {
    currentModalTimeframe = timeframe;
    currentModalDirection = direction;

    const modal = document.getElementById('add-symbol-modal');
    const directionLabel = document.getElementById('modal-direction-label');
    const timeframeLabel = document.getElementById('modal-timeframe-label');
    const input = document.getElementById('symbol-input');

    // Update labels
    const directionText = direction === 'wind_catcher' ? '🌪️ Wind Catcher (Bullish)' : '🌊 River Turn (Bearish)';
    directionLabel.textContent = directionText;
    timeframeLabel.textContent = `${timeframe} Timeframe`;

    // Show modal
    modal.style.display = 'flex';
    input.value = '';
    input.focus();

    // Handle Enter key
    input.onkeyup = function(event) {
        if (event.key === 'Enter') {
            confirmAddSymbol();
        } else if (event.key === 'Escape') {
            closeAddSymbolModal();
        }
    };
}

/**
 * Close add symbol modal
 */
function closeAddSymbolModal() {
    const modal = document.getElementById('add-symbol-modal');
    modal.style.display = 'none';
    currentModalTimeframe = null;
    currentModalDirection = null;
}

/**
 * Confirm adding a symbol from modal
 */
async function confirmAddSymbol() {
    const input = document.getElementById('symbol-input');
    const symbol = input.value.trim().toUpperCase();

    if (!symbol) {
        alert('Please enter a symbol');
        return;
    }

    // Basic validation (alphanumeric only)
    if (!/^[A-Z0-9]+$/.test(symbol)) {
        alert('Symbol should only contain letters and numbers');
        return;
    }

    const success = await addToWatchlist(symbol, currentModalTimeframe, currentModalDirection);

    if (success) {
        closeAddSymbolModal();
    }
}

/**
 * Initialize watchlist module
 */
function initWatchlists() {
    console.log('Initializing watchlists...');

    // Load initial watchlists
    loadWatchlists();

    // Set up drag and drop
    setupDragAndDrop();

    // Reload watchlists every 60 seconds
    setInterval(loadWatchlists, 60000);

    console.log('Watchlists initialized');
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initWatchlists);
} else {
    initWatchlists();
}
