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
    tableBody.innerHTML = '<tr><td colspan="6" class="loading">Loading inventory...</td></tr>';

    try {
        const response = await fetch('/api/inventory');
        const inventory = await response.json();

        displayInventory(inventory);

    } catch (error) {
        tableBody.innerHTML = '<tr><td colspan="6" class="loading">Failed to load inventory</td></tr>';
        console.error('Error loading inventory:', error);
    }
}

/**
 * Display inventory in table
 */
function displayInventory(inventory) {
    const tableBody = document.getElementById('inventoryTableBody');

    if (!inventory || inventory.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="6" class="loading">No medicines in inventory</td></tr>';
        return;
    }

    tableBody.innerHTML = '';

    inventory.forEach(medicine => {
        const row = document.createElement('tr');

        const stockLevel = medicine.stock_level;
        const threshold = medicine.stock_threshold || 50;
        let stockStatus, stockClass;

        if (stockLevel < threshold / 2) {
            stockStatus = 'Critical';
            stockClass = 'critical';
        } else if (stockLevel < threshold) {
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
            <td>
                <button onclick="openRefillModal('${medicine.medicine_name}', ${stockLevel})" 
                        style="padding: 6px 16px; background: #667eea; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 500;">
                    Refill
                </button>
            </td>
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

// ============================================================================
// REFILL FUNCTIONALITY
// ============================================================================

let selectedMedicine = null;

/**
 * Open refill modal
 */
function openRefillModal(medicineName, currentStock) {
    selectedMedicine = medicineName;

    document.getElementById('refillMedicineName').value = medicineName;
    document.getElementById('refillCurrentStock').value = `${currentStock} units`;
    document.getElementById('refillQuantity').value = '';
    document.getElementById('refillReason').value = '';

    const modal = document.getElementById('refillModal');
    modal.style.display = 'flex';
}

/**
 * Close refill modal
 */
function closeRefillModal() {
    const modal = document.getElementById('refillModal');
    modal.style.display = 'none';
    selectedMedicine = null;
}

/**
 * Confirm refill and execute
 */
async function confirmRefill() {
    const quantity = parseInt(document.getElementById('refillQuantity').value);
    const reason = document.getElementById('refillReason').value || 'Manual refill by admin';

    if (!quantity || quantity <= 0) {
        alert('❌ Please enter a valid quantity');
        return;
    }

    // Prompt for admin credentials (simple auth for now)
    const username = prompt('Enter admin username:');
    const password = prompt('Enter admin password:');

    if (!username || !password) {
        alert('Authentication cancelled');
        return;
    }

    try {
        // Login to get token
        const loginResponse = await fetch('/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });

        if (!loginResponse.ok) {
            alert('❌ Invalid credentials');
            return;
        }

        const loginData = await loginResponse.json();
        const token = loginData.access_token;

        // Execute refill
        const refillResponse = await fetch('/admin/refill', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                medicine_name: selectedMedicine,
                quantity: quantity,
                reason: reason
            })
        });

        if (refillResponse.ok) {
            const data = await refillResponse.json();
            alert(`✅ ${data.message}`);

            // Close modal and refresh inventory
            closeRefillModal();
            loadInventory();
            loadStatistics();
        } else {
            const error = await refillResponse.json();
            alert(`❌ Refill failed: ${error.detail}`);
        }
    } catch (error) {
        alert(`❌ Network error: ${error.message}`);
    }
}

/**
 * Excel Export Functions
 */

// Add event listeners for export buttons (called from DOMContentLoaded)
function setupExportButtons() {
    const exportProductsBtn = document.getElementById('exportProductsBtn');
    const exportOrdersBtn = document.getElementById('exportOrdersBtn');
    
    if (exportProductsBtn) {
        exportProductsBtn.addEventListener('click', exportProductList);
    }
    
    if (exportOrdersBtn) {
        exportOrdersBtn.addEventListener('click', exportOrderHistory);
    }
}

/**
 * Export Product List as Excel
 */
async function exportProductList() {
    const btn = document.getElementById('exportProductsBtn');
    const originalText = btn.textContent;
    
    try {
        btn.disabled = true;
        btn.textContent = '⏳ Generating Excel...';
        
        // Check if we're on admin_stock.html (with authentication)
        const token = localStorage.getItem('admin_token');
        if (!token) {
            alert('❌ Authentication required. Please log in to the admin dashboard.');
            return;
        }
        
        const response = await fetch('/admin/export/product-list', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            if (response.status === 401 || response.status === 403) {
                throw new Error('Unauthorized. Please log in again.');
            }
            throw new Error(`Export failed: ${response.status}`);
        }
        
        // Download the file
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'product_list.xlsx';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        btn.textContent = '✅ Downloaded!';
        setTimeout(() => {
            btn.textContent = originalText;
            btn.disabled = false;
        }, 2000);
        
    } catch (error) {
        console.error('Export error:', error);
        alert(`❌ Export failed: ${error.message}`);
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

/**
 * Export Order History as Excel
 */
async function exportOrderHistory() {
    const btn = document.getElementById('exportOrdersBtn');
    const originalText = btn.textContent;
    
    try {
        btn.disabled = true;
        btn.textContent = '⏳ Generating Excel...';
        
        // Check if we're on admin_stock.html (with authentication)
        const token = localStorage.getItem('admin_token');
        if (!token) {
            alert('❌ Authentication required. Please log in to the admin dashboard.');
            return;
        }
        
        const response = await fetch('/admin/export/order-history', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            if (response.status === 401 || response.status === 403) {
                throw new Error('Unauthorized. Please log in again.');
            }
            throw new Error(`Export failed: ${response.status}`);
        }
        
        // Download the file
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'consumer_order_history.xlsx';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        btn.textContent = '✅ Downloaded!';
        setTimeout(() => {
            btn.textContent = originalText;
            btn.disabled = false;
        }, 2000);
        
    } catch (error) {
        console.error('Export error:', error);
        alert(`❌ Export failed: ${error.message}`);
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

// Call setup function when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    setupExportButtons();
});
