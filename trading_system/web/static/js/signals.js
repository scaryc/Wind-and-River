/**
 * Signal Feed for Wind Catcher & River Turn
 * Handles real-time signal updates via polling
 */

// Global state
let latestTimestamp = 0;
let signalCount = 0;

/**
 * Load recent signals from API
 */
async function loadSignals() {
    try {
        const url = `/api/signals/recent?limit=50&since=${latestTimestamp}`;
        const response = await fetch(url);
        const data = await response.json();

        if (data.error) {
            console.error('Error loading signals:', data.error);
            return;
        }

        // If we have new signals, add them to the feed
        if (data.signals && data.signals.length > 0) {
            data.signals.reverse().forEach(signal => {
                appendSignal(signal);
            });

            latestTimestamp = data.latest_timestamp;
            signalCount += data.signals.length;

            // Auto-scroll to bottom to show latest
            const terminal = document.getElementById('signal-terminal');
            terminal.scrollTop = terminal.scrollHeight;
        }

    } catch (error) {
        console.error('Failed to load signals:', error);
    }
}

/**
 * Append a signal to the terminal feed
 */
function appendSignal(signal) {
    const terminal = document.getElementById('signal-terminal');

    // Remove welcome message if it exists
    const welcome = terminal.querySelector('.terminal-welcome');
    if (welcome) {
        welcome.remove();
    }

    // Create signal entry
    const entry = document.createElement('div');
    entry.className = 'signal-entry';

    // Add classification class for border color
    const classLower = signal.confluence_class.toLowerCase().replace(' ', '-');
    entry.classList.add(classLower);

    // Direction class for title color
    const directionClass = signal.direction === 'wind_catcher' ? 'wind-catcher' : 'river-turn';
    const directionText = signal.direction === 'wind_catcher' ? 'BULLISH' : 'BEARISH';

    // Build HTML
    entry.innerHTML = `
        <div class="signal-header">
            <span class="signal-timestamp">[${signal.datetime}]</span>
            <span class="signal-title ${directionClass}">
                ${signal.emoji} ${signal.system_emoji} ${signal.confluence_class}
            </span>
        </div>
        <div class="signal-body">
            <div class="signal-detail">
                <strong>${signal.symbol}</strong> @
                <span class="signal-price">$${signal.price.toFixed(2)}</span> |
                Score: <strong>${signal.confluence_score.toFixed(2)}</strong> |
                ${signal.timeframe} | ${directionText}
            </div>
            <div class="signal-detail">
                Indicators: ${signal.indicators_summary}
            </div>
            <div class="signal-detail">
                Volume: <strong>${signal.volume_level}</strong> (${signal.volume_ratio ? signal.volume_ratio.toFixed(1) : '1.0'}x)
            </div>
        </div>
    `;

    // Add to terminal
    terminal.appendChild(entry);

    // Limit to 100 signals to prevent memory issues
    const allEntries = terminal.querySelectorAll('.signal-entry');
    if (allEntries.length > 100) {
        allEntries[0].remove();
    }
}

/**
 * Load signal statistics
 */
async function loadSignalStats() {
    try {
        const response = await fetch('/api/signals/stats');
        const data = await response.json();

        if (data.error) {
            console.error('Error loading stats:', data.error);
            return;
        }

        // Update signal count display
        const countElement = document.getElementById('signal-count');
        if (countElement) {
            const total = data.total_today || 0;
            const perfect = data.perfect_count || 0;
            const excellent = data.excellent_count || 0;

            countElement.textContent = `${total} signals today (⭐${perfect} 🌟${excellent})`;
        }

    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

/**
 * Initialize signal feed
 */
function initSignals() {
    console.log('Initializing signal feed...');

    // Load initial signals
    loadSignals();
    loadSignalStats();

    // Poll for new signals every 60 seconds
    setInterval(loadSignals, 60000);

    // Update stats every 5 minutes
    setInterval(loadSignalStats, 300000);

    console.log('Signal feed initialized');
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSignals);
} else {
    initSignals();
}
