/**
 * Admin Dashboard JavaScript
 * Handles inventory display, alerts, and agent trace visualization
 */

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initializeTabs();
    loadStatistics();
    loadInventory();
    loadAlerts();
    loadTraces();

    // Event listeners
    document.getElementById('refreshInventoryBtn').addEventListener('click', loadInventory);
    document.getElementById('refreshAlertsTabBtn').addEventListener('click', loadAlerts);
    document.getElementById('refreshTracesBtn').addEventListener('click', loadTraces);
});

/**
 * Tab switching functionality
 */
function initializeTabs() {
    const tabButtons = document.querySelectorAll('.tab-btn');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            // Remove active class from all buttons and panes
            tabButtons.forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));

            // Add active class to clicked button and corresponding pane
            button.classList.add('active');
            const tabId = button.getAttribute('data-tab');
            document.getElementById(`${tabId}-tab`).classList.add('active');
        });
    });
}

/**
 * Load system statistics
 */
async function loadStatistics() {
    try {
        const response = await fetch('/api/statistics');
        const stats = await response.json();

        document.getElementById('totalMedicines').textContent = stats.inventory.total_medicines;
        document.getElementById('lowStockCount').textContent = stats.inventory.low_stock_count;
        document.getElementById('totalTraces').textContent = stats.total_traces;
        document.getElementById('prescriptionCount').textContent = stats.inventory.prescription_required_count;

    } catch (error) {
        console.error('Error loading statistics:', error);
    }
}

/**
 * Load and display inventory
 */
async function loadInventory() {
    const tableBody = document.getElementById('inventoryTableBody');
    tableBody.innerHTML = '<tr><td colspan="5" class="loading">Loading inventory...</td></tr>';

    try {
        const response = await fetch('/api/inventory');
        const inventory = await response.json();

        displayInventory(inventory);

    } catch (error) {
        tableBody.innerHTML = '<tr><td colspan="5" class="loading">Failed to load inventory</td></tr>';
        console.error('Error loading inventory:', error);
    }
}

/**
 * Display inventory in table
 */
function displayInventory(inventory) {
    const tableBody = document.getElementById('inventoryTableBody');

    if (!inventory || inventory.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="5" class="loading">No medicines in inventory</td></tr>';
        return;
    }

    tableBody.innerHTML = '';

    inventory.forEach(medicine => {
        const row = document.createElement('tr');

        const stockLevel = medicine.stock_level;
        let stockStatus, stockClass;

        if (stockLevel < 20) {
            stockStatus = 'Critical';
            stockClass = 'critical';
        } else if (stockLevel < 50) {
            stockStatus = 'Low';
            stockClass = 'low';
        } else {
            stockStatus = 'Good';
            stockClass = 'good';
        }

        row.innerHTML = `
            <td><strong>${medicine.medicine_name}</strong></td>
            <td>${medicine.unit_type}</td>
            <td>${stockLevel}</td>
            <td>${medicine.prescription_required ? '✅ Yes' : '❌ No'}</td>
            <td><span class="stock-badge ${stockClass}">${stockStatus}</span></td>
        `;

        tableBody.appendChild(row);
    });
}

/**
 * Load alerts (low stock and refills)
 */
async function loadAlerts() {
    await loadLowStockAlerts();
    await loadRefillAlertsAdmin();
}

/**
 * Load low stock alerts
 */
async function loadLowStockAlerts() {
    const container = document.getElementById('lowStockAlerts');
    container.innerHTML = '<p class="loading">Loading...</p>';

    try {
        const response = await fetch('/api/alerts/low-stock');
        const alerts = await response.json();

        if (!alerts || alerts.length === 0) {
            container.innerHTML = '<p class="loading">No low stock items ✅</p>';
            return;
        }

        container.innerHTML = '';

        alerts.forEach(medicine => {
            const card = document.createElement('div');
            card.className = 'alert-card';
            card.innerHTML = `
                <h4>⚠️ ${medicine.medicine_name}</h4>
                <p>Current stock: <strong>${medicine.stock_level}</strong> ${medicine.unit_type}(s)</p>
                <p>Prescription required: ${medicine.prescription_required ? 'Yes' : 'No'}</p>
            `;
            container.appendChild(card);
        });

    } catch (error) {
        container.innerHTML = '<p class="loading">Failed to load alerts</p>';
        console.error('Error loading low stock alerts:', error);
    }
}

/**
 * Load refill alerts for admin
 */
async function loadRefillAlertsAdmin() {
    const container = document.getElementById('refillAlertsAdmin');
    container.innerHTML = '<p class="loading">Loading...</p>';

    try {
        const response = await fetch('/api/alerts/refills');
        const alerts = await response.json();

        if (!alerts || alerts.length === 0) {
            container.innerHTML = '<p class="loading">No refill predictions at this time ✅</p>';
            return;
        }

        container.innerHTML = '';

        alerts.forEach(alert => {
            const card = document.createElement('div');
            card.className = `alert-card priority-${alert.alert_priority.toLowerCase()}`;
            card.innerHTML = `
                <h4>💊 ${alert.medicine_name}</h4>
                <p>👤 User: ${alert.user_id}</p>
                <p>📅 Days remaining: <strong>${alert.days_remaining}</strong></p>
                <p>💉 Dosage: ${alert.dosage_per_day}/day</p>
                <p>📦 Last quantity: ${alert.last_quantity}</p>
                <p><em>${alert.recommended_action}</em></p>
                <span class="alert-priority">${alert.alert_priority}</span>
            `;
            container.appendChild(card);
        });

    } catch (error) {
        container.innerHTML = '<p class="loading">Failed to load refill alerts</p>';
        console.error('Error loading refill alerts:', error);
    }
}

/**
 * Load and display agent traces
 */
async function loadTraces() {
    const container = document.getElementById('tracesContainer');
    container.innerHTML = '<p class="loading">Loading traces...</p>';

    try {
        const response = await fetch('/api/traces/grouped?limit=20');
        const traces = await response.json();

        displayTraces(traces);

    } catch (error) {
        container.innerHTML = '<p class="loading">Failed to load traces</p>';
        console.error('Error loading traces:', error);
    }
}

/**
 * Display traces grouped by workflow
 */
function displayTraces(traces) {
    const container = document.getElementById('tracesContainer');

    if (!traces || traces.length === 0) {
        container.innerHTML = '<p class="loading">No traces available</p>';
        return;
    }

    container.innerHTML = '';

    traces.forEach(trace => {
        const traceGroup = document.createElement('div');
        traceGroup.className = 'trace-group';

        // Header
        const header = document.createElement('div');
        header.className = 'trace-header';
        header.innerHTML = `
            <div>
                <div class="trace-id">Trace ID: ${trace.trace_id}</div>
                <div class="trace-time">${formatTimestamp(trace.start_time)}</div>
            </div>
            <div class="trace-time">${trace.actions.length} actions</div>
        `;
        traceGroup.appendChild(header);

        // Actions
        const actionsDiv = document.createElement('div');
        actionsDiv.className = 'trace-actions';

        trace.actions.forEach(action => {
            const actionDiv = document.createElement('div');
            actionDiv.className = `trace-action status-${action.status}`;
            actionDiv.innerHTML = `
                <div class="trace-agent">🤖 ${action.agent_name} › ${action.action}</div>
                <div class="trace-reason">${action.decision_reason}</div>
            `;
            actionsDiv.appendChild(actionDiv);
        });

        traceGroup.appendChild(actionsDiv);
        container.appendChild(traceGroup);
    });
}

/**
 * Format timestamp for display
 */
function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}
