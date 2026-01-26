// Prescription Upload Client Logic

let selectedFile = null;
let currentPrescriptionId = null;
let currentUserId = null;

// DOM Elements
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('file-input');
const filePreview = document.getElementById('file-preview');
const previewImage = document.getElementById('preview-image');
const previewName = document.getElementById('preview-name');
const uploadBtn = document.getElementById('upload-btn');
const userIdInput = document.getElementById('user-id');

// Drag and Drop
dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('dragover');
});

dropzone.addEventListener('dragleave', () => {
    dropzone.classList.remove('dragover');
});

dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');

    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFileSelect(files[0]);
    }
});

// File input change
fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFileSelect(e.target.files[0]);
    }
});

function handleFileSelect(file) {
    // Validate file type
    const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'application/pdf'];
    if (!validTypes.includes(file.type)) {
        alert('Invalid file type. Please upload JPG, PNG, or PDF');
        return;
    }

    // Validate file size (10MB)
    if (file.size > 10 * 1024 * 1024) {
        alert('File too large. Maximum size is 10MB');
        return;
    }

    selectedFile = file;

    // Show preview
    filePreview.style.display = 'block';
    dropzone.style.display = 'none';
    previewName.textContent = file.name;

    // Show image preview if it's an image
    if (file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = (e) => {
            previewImage.src = e.target.result;
            previewImage.style.display = 'block';
        };
        reader.readAsDataURL(file);
    } else {
        previewImage.style.display = 'none';
    }

    // Enable upload button
    uploadBtn.disabled = false;
}

function clearFile() {
    selectedFile = null;
    filePreview.style.display = 'none';
    dropzone.style.display = 'flex';
    fileInput.value = '';
    uploadBtn.disabled = true;
}

async function uploadPrescription() {
    if (!selectedFile) {
        alert('Please select a file first');
        return;
    }

    if (!userIdInput.value) {
        alert('Please enter a user ID');
        return;
    }

    currentUserId = userIdInput.value;

    // Disable button
    uploadBtn.disabled = true;
    uploadBtn.textContent = '⏳ Processing...';

    const statusDiv = document.getElementById('upload-status');
    statusDiv.innerHTML = '<p class="status-info">Uploading and processing prescription...</p>';

    try {
        // Create FormData
        const formData = new FormData();
        formData.append('file', selectedFile);
        formData.append('user_id', currentUserId);

        // Upload
        const response = await fetch('/api/upload-prescription', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.message || 'Upload failed');
        }

        // Store prescription ID
        currentPrescriptionId = result.prescription_id;

        // Show results
        if (result.status === 'success') {
            showReviewStep(result);
        } else {
            statusDiv.innerHTML = `<p class="status-error">❌ ${result.message}</p>`;
            if (result.extracted_text) {
                statusDiv.innerHTML += `<details><summary>View Extracted Text</summary><pre>${result.extracted_text}</pre></details>`;
            }
            uploadBtn.disabled = false;
            uploadBtn.textContent = 'Try Again';
        }

    } catch (error) {
        statusDiv.innerHTML = `<p class="status-error">❌ Error: ${error.message}</p>`;
        uploadBtn.disabled = false;
        uploadBtn.textContent = 'Upload & Process';
    }
}

function showReviewStep(result) {
    // Hide upload section
    document.getElementById('step-upload').style.display = 'none';

    // Show review section
    const reviewSection = document.getElementById('step-review');
    reviewSection.style.display = 'block';

    // Show extracted text
    document.getElementById('extracted-text').textContent = result.extracted_text;

    // Show medicines
    const medicinesList = document.getElementById('medicines-list');
    medicinesList.innerHTML = '';

    result.parsed_medicines.forEach((med, idx) => {
        const medCard = document.createElement('div');
        medCard.className = 'medicine-card';
        medCard.innerHTML = `
            <div class="medicine-header">
                <strong>${idx + 1}. ${med.medicine_name}</strong>
                ${med.prescription_validated ? '<span class="badge">Prescription Required</span>' : '<span class="badge badge-secondary">OTC</span>'}
            </div>
            <div class="medicine-details">
                <p><strong>Dosage:</strong> ${med.dosage || 'Not specified'}</p>
                <p><strong>Frequency:</strong> ${med.frequency_per_day || 1} times per day</p>
                <p><strong>Duration:</strong> ${med.duration_days || 'Not specified'} days</p>
                <p><strong>Quantity:</strong> ${med.quantity_calculated || 'N/A'} ${med.unit_type || 'unit'}(s)</p>
                <p><strong>Stock Available:</strong> ${med.stock_available || 0} ${med.unit_type || 'unit'}(s)</p>
            </div>
        `;
        medicinesList.appendChild(medCard);
    });

    // Show validation result
    const validationDiv = document.getElementById('validation-result');
    if (result.safety_validation.is_valid) {
        validationDiv.innerHTML = `
            <div class="validation-success">
                ✅ ${result.message}
            </div>
        `;
        document.getElementById('confirm-btn').disabled = false;
    } else {
        validationDiv.innerHTML = `
            <div class="validation-error">
                ❌ ${result.safety_validation.reason}
            </div>
        `;
        document.getElementById('confirm-btn').disabled = true;
    }
}

async function confirmOrder() {
    if (!currentPrescriptionId || !currentUserId) {
        alert('Invalid prescription data');
        return;
    }

    const confirmBtn = document.getElementById('confirm-btn');
    confirmBtn.disabled = true;
    confirmBtn.textContent = '⏳ Placing Orders...';

    const statusDiv = document.getElementById('order-status');
    statusDiv.innerHTML = '<p class="status-info">Creating orders...</p>';

    try {
        const formData = new FormData();
        formData.append('prescription_id', currentPrescriptionId);
        formData.append('user_id', currentUserId);

        const response = await fetch('/api/confirm-prescription-order', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.detail || 'Order failed');
        }

        // Show complete step
        showCompleteStep(result);

    } catch (error) {
        statusDiv.innerHTML = `<p class="status-error">❌ Error: ${error.message}</p>`;
        confirmBtn.disabled = false;
        confirmBtn.textContent = '✓ Confirm & Place Order';
    }
}

function showCompleteStep(result) {
    // Hide review section
    document.getElementById('step-review').style.display = 'none';

    // Show complete section
    const completeSection = document.getElementById('step-complete');
    completeSection.style.display = 'block';

    // Show order summary
    const summaryDiv = document.getElementById('order-summary');
    summaryDiv.innerHTML = `
        <div class="summary-card">
            <h3>Order Summary</h3>
            <p class="summary-message">${result.summary}</p>
            <div class="orders-list">
                ${result.orders_created.map(order => `
                    <div class="order-item">
                        <strong>${order.medicine_name}</strong>
                        <span>${order.quantity} unit(s)</span>
                        <span class="status-badge ${order.status}">${order.status.toUpperCase()}</span>
                    </div>
                `).join('')}
            </div>
            <p class="trace-link">
                <a href="/api/prescription/${result.prescription_id}/trace" target="_blank">
                    View Agent Decision Trace →
                </a>
            </p>
        </div>
    `;
}

function resetUpload() {
    // Reset all state
    selectedFile = null;
    currentPrescriptionId = null;
    currentUserId = null;

    // Reset UI
    clearFile();
    document.getElementById('step-upload').style.display = 'block';
    document.getElementById('step-review').style.display = 'none';
    document.getElementById('step-complete').style.display = 'none';

    document.getElementById('upload-status').innerHTML = '';
    document.getElementById('order-status').innerHTML = '';

    uploadBtn.disabled = true;
    uploadBtn.textContent = 'Upload & Process';
}
