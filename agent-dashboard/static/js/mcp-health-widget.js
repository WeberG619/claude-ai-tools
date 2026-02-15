/**
 * MCP Health Widget
 * =================
 * Real-time MCP server health monitoring widget.
 *
 * Features:
 * - Grid layout showing all MCP servers
 * - Green/red/yellow status indicators
 * - Auto-refresh every 60 seconds
 * - Click to expand for details
 * - Parses data from /api/mcp-health endpoint
 *
 * Author: Weber Gouin
 * Created: 2026-02-03
 */

const mcpHealth = (function() {
    'use strict';

    // Configuration
    const CONFIG = {
        refreshInterval: 60000,  // 60 seconds
        apiEndpoint: '/api/mcp-health',
        selectors: {
            panel: '#mcpHealthPanel',
            grid: '#mcpServerGrid',
            summary: '#mcpHealthSummary',
            lastCheck: '#mcpLastCheck',
            modal: '#mcpDetailModal',
            detailName: '#mcpDetailName',
            detailBody: '#mcpDetailBody',
            refreshBtn: '.mcp-health-panel .refresh-btn',
            autoRefreshIndicator: '#mcpAutoRefreshIndicator'
        }
    };

    // State
    let state = {
        data: null,
        refreshTimer: null,
        isLoading: false,
        lastFetch: null
    };

    /**
     * Initialize the widget
     */
    function init() {
        console.log('[MCP Health] Initializing widget...');

        // Initial fetch
        refresh();

        // Set up auto-refresh
        startAutoRefresh();

        // Keyboard listener for modal close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                closeDetail();
            }
        });

        console.log('[MCP Health] Widget initialized');
    }

    /**
     * Fetch health data from API
     */
    async function fetchHealthData() {
        try {
            const response = await fetch(CONFIG.apiEndpoint);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.error('[MCP Health] Fetch error:', error);
            return {
                error: error.message,
                generated_at: null,
                total_servers: 0,
                summary: { healthy: 0, failing: 0, disabled: 0, error: 0 },
                servers: []
            };
        }
    }

    /**
     * Refresh the health data
     */
    async function refresh() {
        if (state.isLoading) return;

        state.isLoading = true;
        setLoadingState(true);

        try {
            state.data = await fetchHealthData();
            state.lastFetch = new Date();
            render();
        } catch (error) {
            console.error('[MCP Health] Refresh error:', error);
            renderError(error.message);
        } finally {
            state.isLoading = false;
            setLoadingState(false);
        }
    }

    /**
     * Start auto-refresh timer
     */
    function startAutoRefresh() {
        if (state.refreshTimer) {
            clearInterval(state.refreshTimer);
        }
        state.refreshTimer = setInterval(refresh, CONFIG.refreshInterval);
    }

    /**
     * Set loading state on UI
     */
    function setLoadingState(isLoading) {
        const refreshBtn = document.querySelector(CONFIG.selectors.refreshBtn);
        if (refreshBtn) {
            if (isLoading) {
                refreshBtn.classList.add('loading');
            } else {
                refreshBtn.classList.remove('loading');
            }
        }
    }

    /**
     * Main render function
     */
    function render() {
        if (!state.data) return;

        renderSummary();
        renderLastCheck();
        renderServerGrid();
    }

    /**
     * Render the summary badge
     */
    function renderSummary() {
        const summaryEl = document.querySelector(CONFIG.selectors.summary);
        if (!summaryEl || !state.data) return;

        const { summary, total_servers } = state.data;
        const hasIssues = summary.failing > 0 || summary.error > 0;

        let text;
        if (state.data.error) {
            text = 'Error';
            summaryEl.className = 'badge health-summary has-issues';
        } else if (hasIssues) {
            text = `${summary.healthy}/${total_servers} Healthy`;
            summaryEl.className = 'badge health-summary has-issues';
        } else {
            text = `${summary.healthy} Healthy | ${summary.disabled} Disabled`;
            summaryEl.className = 'badge health-summary all-healthy';
        }

        summaryEl.textContent = text;
    }

    /**
     * Render last check timestamp
     */
    function renderLastCheck() {
        const lastCheckEl = document.querySelector(CONFIG.selectors.lastCheck);
        if (!lastCheckEl || !state.data) return;

        if (state.data.generated_at) {
            lastCheckEl.textContent = formatTimestamp(state.data.generated_at);
        } else if (state.lastFetch) {
            lastCheckEl.textContent = formatTimestamp(state.lastFetch.toISOString());
        } else {
            lastCheckEl.textContent = '--';
        }
    }

    /**
     * Render the server grid
     */
    function renderServerGrid() {
        const gridEl = document.querySelector(CONFIG.selectors.grid);
        if (!gridEl || !state.data) return;

        const { servers, error } = state.data;

        if (error && servers.length === 0) {
            gridEl.innerHTML = `
                <div class="empty-state">
                    <div style="font-size: 40px; margin-bottom: 10px; opacity: 0.5;">⚠️</div>
                    <div>Failed to load MCP health data</div>
                    <div style="font-size: 12px; margin-top: 8px;">${escapeHtml(error)}</div>
                </div>
            `;
            return;
        }

        if (servers.length === 0) {
            gridEl.innerHTML = `
                <div class="empty-state">
                    <div style="font-size: 40px; margin-bottom: 10px; opacity: 0.5;">🔌</div>
                    <div>No MCP servers found</div>
                </div>
            `;
            return;
        }

        // Sort servers: healthy first, then by name
        const sortedServers = [...servers].sort((a, b) => {
            const statusOrder = { healthy: 0, failing: 1, error: 2, disabled: 3 };
            const orderA = statusOrder[a.status] ?? 4;
            const orderB = statusOrder[b.status] ?? 4;
            if (orderA !== orderB) return orderA - orderB;
            return a.name.localeCompare(b.name);
        });

        gridEl.innerHTML = sortedServers.map(server => renderServerCard(server)).join('');
    }

    /**
     * Render a single server card
     */
    function renderServerCard(server) {
        const statusClass = getStatusClass(server.status);
        const serverData = escapeHtml(JSON.stringify(server));

        return `
            <div class="mcp-server-card" onclick='mcpHealth.showDetail(${serverData})'>
                <div class="status-indicator ${statusClass}" title="${capitalize(server.status)}"></div>
                <div class="server-name">${escapeHtml(server.name)}</div>
                <span class="server-command">${escapeHtml(server.command || 'N/A')}</span>
                <div class="server-source">${escapeHtml(server.source || '')}</div>
            </div>
        `;
    }

    /**
     * Show server detail modal
     */
    function showDetail(server) {
        const modal = document.querySelector(CONFIG.selectors.modal);
        const nameEl = document.querySelector(CONFIG.selectors.detailName);
        const bodyEl = document.querySelector(CONFIG.selectors.detailBody);

        if (!modal || !nameEl || !bodyEl) return;

        // Set name with status indicator
        const statusClass = getStatusClass(server.status);
        nameEl.innerHTML = `
            <span class="status-indicator ${statusClass}" style="position: static; width: 12px; height: 12px;"></span>
            ${escapeHtml(server.name)}
        `;

        // Build detail content
        let detailHtml = `
            <div class="detail-row">
                <span class="detail-label">Status</span>
                <span class="detail-value">
                    <span class="status-badge ${statusClass}">
                        ${getStatusIcon(server.status)} ${capitalize(server.status)}
                    </span>
                </span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Command</span>
                <span class="detail-value code">${escapeHtml(server.command || 'N/A')}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Config Source</span>
                <span class="detail-value">${escapeHtml(server.source || 'Unknown')}</span>
            </div>
        `;

        if (server.purpose) {
            detailHtml += `
                <div class="detail-row">
                    <span class="detail-label">Purpose</span>
                    <span class="detail-value">${escapeHtml(server.purpose)}</span>
                </div>
            `;
        }

        if (server.script_path) {
            detailHtml += `
                <div class="detail-row">
                    <span class="detail-label">Script Path</span>
                    <span class="detail-value code" style="font-size: 10px;">${escapeHtml(server.script_path)}</span>
                </div>
            `;
        }

        if (server.error_message) {
            detailHtml += `
                <div class="error-box">
                    <div class="error-title">Error Details</div>
                    <div class="error-message">${escapeHtml(server.error_message)}</div>
                </div>
            `;
        }

        bodyEl.innerHTML = detailHtml;
        modal.style.display = 'block';
    }

    /**
     * Close the detail modal
     */
    function closeDetail() {
        const modal = document.querySelector(CONFIG.selectors.modal);
        if (modal) {
            modal.style.display = 'none';
        }
    }

    /**
     * Render error state
     */
    function renderError(message) {
        const gridEl = document.querySelector(CONFIG.selectors.grid);
        if (gridEl) {
            gridEl.innerHTML = `
                <div class="empty-state">
                    <div style="font-size: 40px; margin-bottom: 10px; opacity: 0.5;">❌</div>
                    <div>Error loading MCP health data</div>
                    <div style="font-size: 12px; margin-top: 8px; color: var(--accent-red);">
                        ${escapeHtml(message)}
                    </div>
                </div>
            `;
        }

        const summaryEl = document.querySelector(CONFIG.selectors.summary);
        if (summaryEl) {
            summaryEl.textContent = 'Error';
            summaryEl.className = 'badge health-summary has-issues';
        }
    }

    // =====================================
    // Helper Functions
    // =====================================

    function getStatusClass(status) {
        const classes = {
            healthy: 'healthy',
            failing: 'failing',
            disabled: 'disabled',
            error: 'error'
        };
        return classes[status] || 'error';
    }

    function getStatusIcon(status) {
        const icons = {
            healthy: '✓',
            failing: '✗',
            disabled: '○',
            error: '!'
        };
        return icons[status] || '?';
    }

    function formatTimestamp(isoString) {
        if (!isoString) return '--';

        try {
            // Handle both ISO format and the report format "2026-02-03 13:51:35"
            const date = new Date(isoString.replace(' ', 'T'));
            if (isNaN(date.getTime())) {
                return isoString;  // Return as-is if parsing fails
            }

            const now = new Date();
            const diffMs = now - date;
            const diffMins = Math.floor(diffMs / 60000);

            if (diffMins < 1) return 'Just now';
            if (diffMins < 60) return `${diffMins}m ago`;

            const diffHours = Math.floor(diffMins / 60);
            if (diffHours < 24) return `${diffHours}h ago`;

            return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        } catch (e) {
            return isoString;
        }
    }

    function capitalize(str) {
        if (!str) return '';
        return str.charAt(0).toUpperCase() + str.slice(1);
    }

    function escapeHtml(unsafe) {
        if (typeof unsafe !== 'string') {
            unsafe = String(unsafe);
        }
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // =====================================
    // Public API
    // =====================================
    return {
        init,
        refresh,
        showDetail,
        closeDetail,
        getState: () => state.data
    };
})();

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mcpHealth.init);
} else {
    mcpHealth.init();
}
