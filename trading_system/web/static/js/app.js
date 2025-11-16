/**
 * Main Application JavaScript for Wind Catcher & River Turn
 * Handles system status, initialization, and general utilities
 */

/**
 * Update system status in header
 */
async function updateSystemStatus() {
    try {
        const response = await fetch('/api/system/status');
        const data = await response.json();

        if (data.error) {
            console.error('Error fetching system status:', data.error);
            setSystemStatus('error', 'Error');
            return;
        }

        // Update status indicator
        setSystemStatus('ok', 'System Active');

        // Could add more detailed status info here if needed
        console.log('System status:', data);

    } catch (error) {
        console.error('Failed to fetch system status:', error);
        setSystemStatus('error', 'Offline');
    }
}

/**
 * Set system status in UI
 */
function setSystemStatus(status, text) {
    const indicator = document.getElementById('status-indicator');
    const statusText = document.getElementById('status-text');

    if (!indicator || !statusText) return;

    statusText.textContent = text;

    // Update indicator color based on status
    if (status === 'ok') {
        indicator.style.color = 'var(--accent-success)';
    } else if (status === 'warning') {
        indicator.style.color = 'var(--accent-warning)';
    } else if (status === 'error') {
        indicator.style.color = 'var(--accent-river)';
    }
}

/**
 * Check API health
 */
async function checkHealth() {
    try {
        const response = await fetch('/health');
        const data = await response.json();

        if (data.status === 'ok') {
            console.log('✅ API health check passed');
            return true;
        }
    } catch (error) {
        console.error('❌ API health check failed:', error);
        return false;
    }
}

/**
 * Initialize application
 */
async function initApp() {
    console.log('🚀 Initializing Wind Catcher & River Turn Web Interface');

    // Check API health
    const healthy = await checkHealth();

    if (!healthy) {
        setSystemStatus('error', 'API Offline');
        alert('Warning: Backend API is not responding. Please ensure the Flask server is running.');
        return;
    }

    // Update system status
    await updateSystemStatus();

    // Refresh system status every 5 minutes
    setInterval(updateSystemStatus, 300000);

    console.log('✅ Application initialized successfully');
}

/**
 * Format timestamp to readable string
 */
function formatTimestamp(timestamp) {
    const date = new Date(timestamp * 1000);
    return date.toLocaleString();
}

/**
 * Show notification (could be extended to use browser notifications)
 */
function showNotification(message, type = 'info') {
    console.log(`[${type.toUpperCase()}] ${message}`);
    // Could add toast notifications here
}

/**
 * Utility: Debounce function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Handle keyboard shortcuts
 */
function initKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Ctrl/Cmd + R: Refresh watchlists and signals
        if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
            e.preventDefault();
            console.log('Refreshing all data...');
            if (typeof loadWatchlists === 'function') loadWatchlists();
            if (typeof loadSignals === 'function') loadSignals();
            if (typeof loadSignalStats === 'function') loadSignalStats();
        }

        // Escape: Close modal
        if (e.key === 'Escape') {
            if (typeof closeAddSymbolModal === 'function') {
                closeAddSymbolModal();
            }
        }
    });
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        initApp();
        initKeyboardShortcuts();
    });
} else {
    initApp();
    initKeyboardShortcuts();
}

// Log when all scripts are loaded
console.log('📜 All scripts loaded');
