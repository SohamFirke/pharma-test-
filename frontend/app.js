/**
 * Client-side JavaScript for Chat Interface
 * Handles user interaction, voice input, and API calls
 */

// DOM Elements
const messagesArea = document.getElementById('messagesArea');
const messageInput = document.getElementById('messageInput');
const userIdInput = document.getElementById('userIdInput');
const sendBtn = document.getElementById('sendBtn');
const voiceBtn = document.getElementById('voiceBtn');
const refillAlerts = document.getElementById('refillAlerts');
const refreshAlertsBtn = document.getElementById('refreshAlertsBtn');

// Voice Recognition
let recognition = null;
let isRecording = false;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeVoiceRecognition();
    loadRefillAlerts();

    // Event listeners
    sendBtn.addEventListener('click', sendMessage);
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
    voiceBtn.addEventListener('click', toggleVoiceRecognition);
    refreshAlertsBtn.addEventListener('click', loadRefillAlerts);
});

/**
 * Send message to backend
 */
async function sendMessage() {
    const message = messageInput.value.trim();
    const userId = userIdInput.value.trim();

    if (!message) return;
    if (!userId) {
        alert('Please enter a user ID');
        return;
    }

    // Display user message
    addMessage(message, 'user');
    messageInput.value = '';

    // Show loading
    const loadingId = addMessage('Processing your order...', 'bot', true);

    try {
        const response = await fetch('/api/order', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_id: userId,
                message: message
            })
        });

        const data = await response.json();

        // Remove loading message
        removeMessage(loadingId);

        // Display bot response
        addMessage(data.message, 'bot');

        // Refresh alerts if order was successful
        if (data.status === 'success') {
            setTimeout(loadRefillAlerts, 1000);
        }

    } catch (error) {
        removeMessage(loadingId);
        addMessage(`❌ Error: ${error.message}`, 'bot');
    }
}

/**
 * Add message to chat
 */
function addMessage(text, sender, isLoading = false) {
    const messageDiv = document.createElement('div');
    const messageId = `msg-${Date.now()}`;
    messageDiv.id = messageId;
    messageDiv.className = `message ${sender}-message${isLoading ? ' loading-msg' : ''}`;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    // Parse text with line breaks
    const lines = text.split('\n');
    lines.forEach((line, index) => {
        if (line.trim()) {
            const p = document.createElement('p');
            p.textContent = line;
            contentDiv.appendChild(p);
        }
    });

    messageDiv.appendChild(contentDiv);
    messagesArea.appendChild(messageDiv);

    // Scroll to bottom
    messagesArea.scrollTop = messagesArea.scrollHeight;

    return messageId;
}

/**
 * Remove message by ID
 */
function removeMessage(messageId) {
    const element = document.getElementById(messageId);
    if (element) {
        element.remove();
    }
}

/**
 * Initialize Web Speech API for voice input
 */
function initializeVoiceRecognition() {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();

        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            messageInput.value = transcript;
            stopRecording();
        };

        recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            stopRecording();
            if (event.error !== 'no-speech') {
                alert('Voice recognition error: ' + event.error);
            }
        };

        recognition.onend = () => {
            stopRecording();
        };
    } else {
        voiceBtn.style.display = 'none';
        console.log('Speech recognition not supported');
    }
}

/**
 * Toggle voice recognition
 */
function toggleVoiceRecognition() {
    if (!recognition) return;

    if (isRecording) {
        recognition.stop();
    } else {
        recognition.start();
        startRecording();
    }
}

function startRecording() {
    isRecording = true;
    voiceBtn.classList.add('recording');
    voiceBtn.textContent = '🔴';
}

function stopRecording() {
    isRecording = false;
    voiceBtn.classList.remove('recording');
    voiceBtn.textContent = '🎤';
}

/**
 * Load refill alerts from API
 */
async function loadRefillAlerts() {
    try {
        const userId = userIdInput.value.trim();
        const url = userId ? `/api/alerts/refills?user_id=${userId}` : '/api/alerts/refills';

        const response = await fetch(url);
        const alerts = await response.json();

        displayRefillAlerts(alerts);

    } catch (error) {
        refillAlerts.innerHTML = '<p class="loading">Failed to load alerts</p>';
        console.error('Error loading alerts:', error);
    }
}

/**
 * Display refill alerts in sidebar
 */
function displayRefillAlerts(alerts) {
    if (!alerts || alerts.length === 0) {
        refillAlerts.innerHTML = '<p class="loading">No refill alerts at this time ✅</p>';
        return;
    }

    refillAlerts.innerHTML = '';

    alerts.forEach(alert => {
        const card = document.createElement('div');
        card.className = `alert-card priority-${alert.alert_priority.toLowerCase()}`;

        card.innerHTML = `
            <h4>${alert.medicine_name}</h4>
            <p>👤 User: ${alert.user_id}</p>
            <p>📅 Days remaining: <strong>${alert.days_remaining}</strong></p>
            <p>💊 Last order: ${alert.last_quantity} units</p>
            <p>${alert.recommended_action}</p>
            <span class="alert-priority">${alert.alert_priority}</span>
        `;

        refillAlerts.appendChild(card);
    });
}
