/**
 * Main Application JavaScript
 * Handles system status and general app coordination
 */

// ============================================================================
// SYSTEM STATUS
// ============================================================================

async function loadSystemStatus() {
    try {
        const response = await fetch('/api/system/status');
        const data = await response.json();

        // Update status indicator
        const statusIndicator = document.getElementById('status-indicator');
        const statusText = document.getElementById('status-text');

        if (data.status === 'ok') {
            statusIndicator.style.color = 'var(--accent-success)';
            statusText.textContent = 'System Active';
        } else {
            statusIndicator.style.color = 'var(--accent-warning)';
            statusText.textContent = 'System Warning';
        }

    } catch (error) {
        console.error('Error loading system status:', error);

        const statusIndicator = document.getElementById('status-indicator');
        const statusText = document.getElementById('status-text');

        statusIndicator.style.color = 'var(--accent-river)';
        statusText.textContent = 'Connection Error';
    }
}

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('🌪️ Wind Catcher & River Turn Trading System');
    console.log('Dashboard loaded successfully');

    // Load system status
    loadSystemStatus();

    // Refresh system status every minute
    setInterval(loadSystemStatus, 60000);

    // Log initialization
    console.log('✅ All systems initialized');
});

// ============================================================================
// GLOBAL ERROR HANDLING
// ============================================================================

window.addEventListener('error', (e) => {
    console.error('Global error:', e.message);
});

window.addEventListener('unhandledrejection', (e) => {
    console.error('Unhandled promise rejection:', e.reason);
});
