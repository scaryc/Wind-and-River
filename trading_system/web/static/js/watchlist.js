/**
 * Watchlist Management JavaScript
 * Handles adding, removing, and moving symbols between watchlists
 */

// Global state for drag and drop
let draggedItem = null;

// ============================================================================
// WATCHLIST LOADING AND RENDERING
// ============================================================================

async function loadWatchlists() {
    try {
        const response = await fetch('/api/watchlists');
        const data = await response.json();

        // Render each watchlist
        renderWatchlist('wind_catcher', '8h', data.wind_catcher['8h']);
        renderWatchlist('wind_catcher', '1h', data.wind_catcher['1h']);
        renderWatchlist('wind_catcher', '15m', data.wind_catcher['15m']);
        renderWatchlist('river_turn', '8h', data.river_turn['8h']);
        renderWatchlist('river_turn', '1h', data.river_turn['1h']);
        renderWatchlist('river_turn', '15m', data.river_turn['15m']);

    } catch (error) {
        console.error('Error loading watchlists:', error);
    }
}

function renderWatchlist(direction, timeframe, symbols) {
    const listId = direction === 'wind_catcher' ? 'wind' : 'river';
    const container = document.getElementById(`${listId}-${timeframe}`);

    if (!container) return;

    container.innerHTML = '';

    symbols.forEach(symbol => {
        const item = createPairItem(symbol, timeframe, direction);
        container.appendChild(item);
    });
}

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

    // Drag and drop event listeners
    li.addEventListener('dragstart', handleDragStart);
    li.addEventListener('dragend', handleDragEnd);

    return li;
}

// ============================================================================
// WATCHLIST MODIFICATIONS
// ============================================================================

async function addToWatchlist(symbol, timeframe, direction) {
    try {
        const response = await fetch('/api/watchlist/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol, timeframe, direction })
        });

        const data = await response.json();

        if (data.success) {
            loadWatchlists(); // Reload to show new item
        } else {
            console.log('Symbol already in watchlist');
        }

    } catch (error) {
        console.error('Error adding to watchlist:', error);
    }
}

async function removePair(symbol, timeframe, direction) {
    try {
        const response = await fetch('/api/watchlist/remove', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol, timeframe, direction })
        });

        const data = await response.json();

        if (data.success) {
            loadWatchlists(); // Reload to reflect removal
        }

    } catch (error) {
        console.error('Error removing from watchlist:', error);
    }
}

// ============================================================================
// DRAG AND DROP
// ============================================================================

function handleDragStart(e) {
    draggedItem = {
        symbol: e.target.dataset.symbol,
        timeframe: e.target.dataset.timeframe,
        direction: e.target.dataset.direction
    };

    e.target.classList.add('dragging');
}

function handleDragEnd(e) {
    e.target.classList.remove('dragging');
}

function handleDragOver(e) {
    e.preventDefault();
    e.currentTarget.classList.add('drag-over');
}

function handleDragLeave(e) {
    e.currentTarget.classList.remove('drag-over');
}

async function handleDrop(e) {
    e.preventDefault();
    e.currentTarget.classList.remove('drag-over');

    const dropTarget = e.currentTarget;
    const toTimeframe = dropTarget.parentElement.dataset.timeframe;
    const toDirection = dropTarget.parentElement.dataset.direction;

    // Don't move if dropped in same location
    if (draggedItem.timeframe === toTimeframe && draggedItem.direction === toDirection) {
        return;
    }

    try {
        // API call to move
        const response = await fetch('/api/watchlist/move', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                symbol: draggedItem.symbol,
                from: {
                    timeframe: draggedItem.timeframe,
                    direction: draggedItem.direction
                },
                to: {
                    timeframe: toTimeframe,
                    direction: toDirection
                }
            })
        });

        const data = await response.json();

        if (data.success) {
            loadWatchlists(); // Reload to show new position
        }

    } catch (error) {
        console.error('Error moving symbol:', error);
    }
}

// ============================================================================
// MODAL FOR ADDING SYMBOLS
// ============================================================================

function showAddSymbolModal(timeframe, direction) {
    const modalContainer = document.getElementById('modal-container');

    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.id = 'add-symbol-modal';
    modal.innerHTML = `
        <div class="modal-content">
            <h3>Add Symbol to Watchlist</h3>
            <p style="color: var(--text-secondary); margin-bottom: 1rem;">
                ${direction === 'wind_catcher' ? '🌪️ Wind Catcher' : '🌊 River Turn'} - ${timeframe}
            </p>
            <input
                type="text"
                id="symbol-input"
                placeholder="Enter symbol (e.g., BTC/USDT)"
                list="symbol-suggestions"
                autocomplete="off"
            />
            <datalist id="symbol-suggestions">
                <!-- Populated from API -->
            </datalist>
            <div class="modal-actions">
                <button onclick="closeModal()">Cancel</button>
                <button onclick="confirmAddSymbol('${timeframe}', '${direction}')">Add</button>
            </div>
        </div>
    `;

    modalContainer.innerHTML = '';
    modalContainer.appendChild(modal);

    // Load available symbols for autocomplete
    loadAvailableSymbols();

    // Focus input
    setTimeout(() => {
        document.getElementById('symbol-input').focus();
    }, 100);

    // Close on background click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeModal();
        }
    });

    // Close on Escape key
    document.addEventListener('keydown', handleEscapeKey);
}

async function loadAvailableSymbols() {
    try {
        const response = await fetch('/api/system/pairs');
        const data = await response.json();

        const datalist = document.getElementById('symbol-suggestions');
        if (!datalist) return;

        data.pairs.forEach(pair => {
            const option = document.createElement('option');
            option.value = pair;
            datalist.appendChild(option);
        });

    } catch (error) {
        console.error('Error loading available symbols:', error);
    }
}

async function confirmAddSymbol(timeframe, direction) {
    const input = document.getElementById('symbol-input');
    const symbol = input.value.trim().toUpperCase();

    if (symbol) {
        await addToWatchlist(symbol, timeframe, direction);
        closeModal();
    }
}

function closeModal() {
    const modalContainer = document.getElementById('modal-container');
    modalContainer.innerHTML = '';
    document.removeEventListener('keydown', handleEscapeKey);
}

function handleEscapeKey(e) {
    if (e.key === 'Escape') {
        closeModal();
    }
}

// ============================================================================
// INITIALIZATION
// ============================================================================

// Load watchlists on page load
document.addEventListener('DOMContentLoaded', () => {
    loadWatchlists();

    // Reload every 60 seconds
    setInterval(loadWatchlists, 60000);
});
