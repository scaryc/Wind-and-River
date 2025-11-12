/**
 * Signal Feed JavaScript
 * Handles loading and displaying signals in terminal format
 */

let latestTimestamp = 0;

// ============================================================================
// SIGNAL LOADING
// ============================================================================

async function loadSignals() {
    try {
        const response = await fetch(`/api/signals/recent?since=${latestTimestamp}&limit=50`);
        const data = await response.json();

        if (data.signals && data.signals.length > 0) {
            // Append new signals
            data.signals.forEach(signal => {
                appendSignal(signal);
            });

            latestTimestamp = data.latest_timestamp;

            // Auto-scroll to bottom
            const terminal = document.getElementById('signal-terminal');
            terminal.scrollTop = terminal.scrollHeight;

            // Remove welcome message if present
            const welcomeMsg = document.querySelector('.welcome-message');
            if (welcomeMsg) {
                welcomeMsg.remove();
            }
        }

        // Update signal statistics
        loadSignalStats();

    } catch (error) {
        console.error('Error loading signals:', error);
    }
}

async function loadSignalStats() {
    try {
        const response = await fetch('/api/signals/stats');
        const data = await response.json();

        // Update stats display
        document.getElementById('signals-today').textContent = data.total_today || 0;
        document.getElementById('perfect-count').textContent = data.perfect_count || 0;
        document.getElementById('excellent-count').textContent = data.excellent_count || 0;

    } catch (error) {
        console.error('Error loading signal stats:', error);
    }
}

// ============================================================================
// SIGNAL RENDERING
// ============================================================================

function appendSignal(signal) {
    const terminal = document.getElementById('signal-terminal');

    const entry = document.createElement('div');
    entry.className = 'signal-entry';

    const directionClass = signal.system === 'wind_catcher' ? 'wind_catcher' : 'river_turn';
    const systemEmoji = signal.system_emoji || (signal.system === 'wind_catcher' ? '🌪️' : '🌊');
    const confluenceEmoji = signal.emoji || getConfluenceEmoji(signal.confluence_class);

    entry.innerHTML = `
        <div class="signal-header">
            <span class="signal-timestamp">[${formatTime(signal.datetime)}]</span>
            <span class="signal-title ${directionClass}">
                ${confluenceEmoji} ${systemEmoji} ${signal.confluence_class} Signal
            </span>
        </div>
        <div class="signal-body">
            <div class="signal-detail">
                <strong>${signal.symbol}</strong> @
                <span class="signal-price">$${formatPrice(signal.price)}</span> |
                Score: ${signal.confluence_score.toFixed(1)} |
                ${signal.timeframe}
            </div>
            <div class="signal-detail">
                Indicators: ${signal.indicators_summary || 'None'}
            </div>
            ${signal.volume_level ? `
            <div class="signal-detail">
                Volume: ${getVolumeEmoji(signal.volume_level)} ${signal.volume_level}
                ${signal.volume_ratio ? ` (${signal.volume_ratio.toFixed(1)}x)` : ''}
            </div>
            ` : ''}
        </div>
    `;

    terminal.appendChild(entry);
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

function formatTime(datetime) {
    // Extract time from datetime string (YYYY-MM-DD HH:MM:SS)
    const parts = datetime.split(' ');
    if (parts.length === 2) {
        return parts[1]; // HH:MM:SS
    }
    return datetime;
}

function formatPrice(price) {
    if (price >= 1000) {
        return price.toFixed(2);
    } else if (price >= 1) {
        return price.toFixed(4);
    } else {
        return price.toFixed(6);
    }
}

function getConfluenceEmoji(confluenceClass) {
    const emojiMap = {
        'PERFECT': '⭐',
        'EXCELLENT': '🌟',
        'VERY GOOD': '✨',
        'GOOD': '💫',
        'INTERESTING': '💡'
    };

    return emojiMap[confluenceClass] || '❓';
}

function getVolumeEmoji(volumeLevel) {
    const emojiMap = {
        'CLIMAX': '🔥',
        'HOT': '🌡️',
        'WARMING': '📈',
        'NORMAL': '📊'
    };

    return emojiMap[volumeLevel] || '📊';
}

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    // Load initial signals
    loadSignals();

    // Poll for new signals every 60 seconds
    setInterval(loadSignals, 60000);
});
