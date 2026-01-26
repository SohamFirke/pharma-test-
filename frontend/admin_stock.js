/**
 * Admin Stock Management Dashboard JavaScript
 * Handles authentication, inventory display, and refill operations
 */

// Global state
let authToken = null;
let currentAdmin = null;
let inventory = [];
let selectedMedicine = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    setupEventListeners();
});

function setupEventListeners() {
    // Login form
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }

    // Logout button
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', handleLogout);
    }
}

function checkAuth() {
    // Check if token exists in localStorage
    authToken = localStorage.getItem('admin_token');

    if (authToken) {
        // Validate token
        validateToken();
    } else {
        showLoginPage();
    }
}

async function validateToken() {
    try {
        const response = await fetch('/auth/validate', {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            currentAdmin = data.username;
            showDashboard();
        } else {
            // Token invalid
            localStorage.removeItem('admin_token');
            showLoginPage();
        }
    } catch (error) {
        console.error('Token validation error:', error);
        showLoginPage();
    }
}

async function handleLogin(e) {
    e.preventDefault();

    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const errorDiv = document.getElementById('loginError');

    try {
        const response = await fetch('/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });

        if (response.ok) {
            const data = await response.json();
            authToken = data.access_token;
            currentAdmin = data.username;

            // Store token
            localStorage.setItem('admin_token', authToken);

            // Show dashboard
            showDashboard();
        } else {
            const data = await response.json();
            errorDiv.textContent = data.detail || 'Login failed';
            errorDiv.style.display = 'block';
        }
    } catch (error) {
        errorDiv.textContent = 'Network error. Please try again.';
        errorDiv.style.display = 'block';
    }
}

async function handleLogout() {
    try {
        await fetch('/auth/logout', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
    } catch (error) {
        console.error('Logout error:', error);
    }

    // Clear local data
    localStorage.removeItem('admin_token');
    authToken = null;
    currentAdmin = null;

    // Show login page
    showLoginPage();
}

function showLoginPage() {
    document.getElementById('loginPage').style.display = 'flex';
    document.getElementById('dashboard').classList.remove('active');
}

function showDashboard() {
    document.getElementById('loginPage').style.display = 'none';
    document.getElementById('dashboard').classList.add('active');
    document.getElementById('adminUsername').textContent = currentAdmin;

    // Load dashboard data
    loadInventory();
    loadAlerts();

    // Auto-refresh every 30 seconds
    setInterval(() => {
        loadInventory();
        loadAlerts();
    }, 30000);
}

async function loadInventory() {
    try {
        const response = await fetch('/admin/inventory', {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            inventory = data.medicines || [];
            renderInventory();
            updateStats();
        } else if (response.status === 401) {
            // Token expired
            handleLogout();
        }
    } catch (error) {
        console.error('Error loading inventory:', error);
    }
}

function renderInventory() {
    const container = document.getElementById('inventoryContainer');

    if (inventory.length === 0) {
        container.innerHTML = '<p>No medicines in inventory.</p>';
        return;
    }

    const tableHTML = `
        <table>
            <thead>
                <tr>
                    <th>Medicine Name</th>
                    <th>Current Stock</th>
                    <th>Threshold</th>
                    <th>Status</th>
                    <th>Prescription Required</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>
                ${inventory.map(medicine => `
                    <tr>
                        <td><strong>${medicine.medicine_name}</strong></td>
                        <td>${medicine.stock_level} ${medicine.unit_type}</td>
                        <td>${medicine.stock_threshold || 'N/A'}</td>
                        <td>
                            <span class="stock-badge ${medicine.stock_status.toLowerCase()}">
                                ${medicine.stock_status}
                            </span>
                        </td>
                        <td>${medicine.prescription_required ? 'Yes' : 'No'}</td>
                        <td>
                            <button class="refill-btn" onclick="openRefillModal('${medicine.medicine_name}', ${medicine.stock_level})">
                                Refill
                            </button>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;

    container.innerHTML = tableHTML;
}

function updateStats() {
    const critical = inventory.filter(m => m.stock_status === 'CRITICAL').length;
    const low = inventory.filter(m => m.stock_status === 'LOW').length;
    const ok = inventory.filter(m => m.stock_status === 'OK').length;

    document.getElementById('criticalCount').textContent = critical;
    document.getElementById('lowCount').textContent = low;
    document.getElementById('okCount').textContent = ok;
    document.getElementById('totalCount').textContent = inventory.length;
}

async function loadAlerts() {
    try {
        const response = await fetch('/admin/refill-alerts', {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            renderAlerts(data.alerts || []);
        }
    } catch (error) {
        console.error('Error loading alerts:', error);
    }
}

function renderAlerts(alerts) {
    const container = document.getElementById('alertsContainer');

    if (alerts.length === 0) {
        container.innerHTML = '<p style="color: #666;">No active alerts. All stock levels are OK.</p>';
        return;
    }

    const alertsHTML = alerts.map(alert => `
        <div class="alert-item ${alert.severity.toLowerCase()}">
            <strong>${alert.medicine_name}</strong> - ${alert.severity}
            <div style="margin-top: 5px; font-size: 14px;">
                Current Stock: ${alert.current_stock} | Threshold: ${alert.threshold}
            </div>
            <div style="margin-top: 5px; font-size: 13px; color: #666;">
                ${alert.reason}
            </div>
            <div style="margin-top: 10px;">
                <button class="refill-btn" onclick="openRefillModal('${alert.medicine_name}', ${alert.current_stock}, ${alert.suggested_quantity})">
                    Refill ${alert.suggested_quantity} units
                </button>
            </div>
        </div>
    `).join('');

    container.innerHTML = alertsHTML;
}

function openRefillModal(medicineName, currentStock, suggestedQuantity = null) {
    selectedMedicine = medicineName;

    document.getElementById('refillMedicine').value = medicineName;
    document.getElementById('refillCurrentStock').value = `${currentStock} units`;
    document.getElementById('refillQuantity').value = suggestedQuantity || '';
    document.getElementById('refillReason').value = '';

    document.getElementById('refillModal').classList.add('active');
}

function closeRefillModal() {
    document.getElementById('refillModal').classList.remove('active');
    selectedMedicine = null;
}

async function confirmRefill() {
    const quantity = parseInt(document.getElementById('refillQuantity').value);
    const reason = document.getElementById('refillReason').value || 'Manual refill by admin';

    if (!quantity || quantity <= 0) {
        alert('Please enter a valid quantity');
        return;
    }

    try {
        const response = await fetch('/admin/refill', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({
                medicine_name: selectedMedicine,
                quantity: quantity,
                reason: reason
            })
        });

        if (response.ok) {
            const data = await response.json();
            alert(`✅ ${data.message}`);

            // Close modal and refresh
            closeRefillModal();
            loadInventory();
            loadAlerts();
        } else {
            const data = await response.json();
            alert(`❌ Refill failed: ${data.detail}`);
        }
    } catch (error) {
        alert(`❌ Network error: ${error.message}`);
    }
}

// Make functions global for onclick handlers
window.openRefillModal = openRefillModal;
window.closeRefillModal = closeRefillModal;
window.confirmRefill = confirmRefill;

/**
 * Excel Export Functions
 */

// Add event listeners for export buttons
document.addEventListener('DOMContentLoaded', () => {
    const exportProductsBtn = document.getElementById('exportProductsBtn');
    const exportOrdersBtn = document.getElementById('exportOrdersBtn');
    
    if (exportProductsBtn) {
        exportProductsBtn.addEventListener('click', exportProductList);
    }
    
    if (exportOrdersBtn) {
        exportOrdersBtn.addEventListener('click', exportOrderHistory);
    }
});

/**
 * Export Product List as Excel
 */
async function exportProductList() {
    const btn = document.getElementById('exportProductsBtn');
    const originalText = btn.textContent;
    
    try {
        btn.disabled = true;
        btn.textContent = '⏳ Generating Excel...';
        
        const response = await fetch('/admin/export/product-list', {
            headers: {
                'Authorization': `Bearer ${authToken}`
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
        
        const response = await fetch('/admin/export/order-history', {
            headers: {
                'Authorization': `Bearer ${authToken}`
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
