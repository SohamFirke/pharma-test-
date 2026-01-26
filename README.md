⚠️ Educational Demonstration Project — Not for Clinical Use


# 🏥 Agentic AI Pharmacy System

**An offline-first, privacy-focused, autonomous pharmacy system powered by local AI agents with admin stock management.**

---

## 🎯 Overview

This system transforms traditional pharmacy operations into an intelligent, agent-based platform that:

- ✅ **Understands natural language** - Order medicines conversationally without rigid forms
- ✅ **Intent-based routing** - AI-assisted classification of user requests (general chat, symptom analysis, prescription upload)
- ✅ **Symptom analysis** - Get OTC medicine recommendations based on symptoms (NOT MEDICAL ADVICE - includes comprehensive disclaimers)
- ✅ **Prescription vision processing** - Upload prescription images for automatic extraction
- ✅ **Enforces safety rules** - Deterministic prescription validation (rule-based, not probabilistic)
- ✅ **Admin stock management** - Secure admin dashboard for inventory refills with JWT authentication
- ✅ **Rule-based refill monitoring** - Threshold-based alerts when stock runs low
- ✅ **Inventory monitoring** - Rule-based + predictive refill alerts (AI-assisted monitoring, not decision-making)
- ✅ **Provides full observability** - Every agent decision is traceable and auditable

**🔒 100% Offline-Capable | 🆓 Zero API Costs | 🔐 Privacy-First | 🔐 Admin Authentication**

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      USER INTERFACES                         │
│    Chat + Voice + Prescription Upload + Admin Dashboards     │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                 AUTHENTICATION LAYER                         │
│            JWT-based Admin Authentication                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    AGENTIC LAYER                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Router Agent │  │ General Chat │  │   Symptom    │      │
│  │(Intent Class)│  │    Agent     │  │   Analysis   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Prescription │  │Stock Refill  │  │  Inventory   │      │
│  │Vision Agent  │  │    Agent     │  │    Agent     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌────────────────────────────────┐      │
│  │  Predictive  │  │   Orchestrator Agent           │      │
│  │    Agent     │  │   (Workflow Coordinator)       │      │
│  └──────────────┘  └────────────────────────────────┘      │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                   BACKEND SERVICES                           │
│    FastAPI + JWT Auth + CSV/SQLite + Trace Logger           │
└──────────────────────────────────────────────────────────────┘
```

### 🤖 Agent Responsibilities

| Agent | Role | Technology | Decision Authority |
|-------|------|------------|--------------------|
| **Router** | Classify user intent ONLY (chat, symptom, prescription, order) - Does NOT make medical/safety decisions | Ollama embeddings + cosine similarity | Intent classification only |
| **General Chat** | Handle greetings and general questions | Ollama LLM (llama3.2) | Informational only |
| **Symptom Analysis** | Map symptoms to OTC recommendations (NOT DIAGNOSIS - informational only) | NLP + symptom database | No medical authority |
| **Prescription Vision** | Extract medicine names from images (extraction only, not validation) | Ollama Vision (llama3.2-vision) | Extraction only |
| **Stock Refill** | Monitor inventory using rule-based thresholds | Deterministic algorithm with thresholds | Monitoring only |
| **Inventory** | Manage stock using deterministic rules | Python logic + webhook | Rule-based decisions |
| **Predictive** | Calculate refill predictions | Algorithm-based |
| **Orchestrator** | Coordinate workflow & state | Python OOP |

---

## 🚀 Quick Start

### Prerequisites

1. **Python 3.9+**
2. **Ollama** (for local LLM)
   ```bash
   # Install from https://ollama.ai
   # Then pull required models:
   ollama pull llama3.2
   ollama pull llama3.2-vision
   ollama pull nomic-embed-text
   ```

### Installation

1. **Clone/Navigate to project**
   ```bash
   cd "new project"
   ```

2. **Install dependencies**
   ```bash
   pip3 install -r requirements.txt
   ```

3. **Start Ollama** (in a separate terminal)
   ```bash
   ollama serve
   ```

4. **Start the backend**
   ```bash
   cd backend
   python3 main.py
   ```

5. **Open your browser**
   - **Main Chat UI**: http://localhost:8000
   - **Admin Dashboard**: http://localhost:8000/admin
   - **Admin Stock Management**: http://localhost:8000/admin-stock
   - **Prescription Upload**: http://localhost:8000/prescription
   - **API Docs**: http://localhost:8000/docs

---

## � Admin Stock Management Dashboard

### Overview

Secure admin-only dashboard for managing pharmacy inventory with real-time monitoring, rule-based refill alerts, and manual stock refill capabilities.

### Features

- 🔒 **JWT-based authentication** - Secure login with hardcoded admin credentials
- 📊 **Real-time inventory monitoring** - View all medicines with stock levels
- 🚨 **Rule-based + predictive refill alerts** - Automatic threshold-based alerts when stock falls below configured levels (AI-assisted monitoring for orchestration, not decision-making)
- ⚡ **Manual stock refills** - Trigger refills with quantity and reason tracking
- 📝 **Full audit trail** - All refill actions logged with admin username and timestamp
- 🛡️ **Safety constraints** - Cooldown periods, quantity validation, rate limiting
- 🔄 **Auto-refresh** - Dashboard updates every 30 seconds

### Access

1. Navigate to **http://localhost:8000/admin-stock**
2. Login with admin credentials:
   - **Username**: `admin`
   - **Password**: `pharmacy_admin_2026`

### Admin Endpoints (Protected)

All admin endpoints require JWT token in `Authorization: Bearer <token>` header:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/login` | POST | Login with username/password, returns JWT token |
| `/auth/logout` | POST | Invalidate current token |
| `/auth/validate` | GET | Validate current token |
| `/admin/inventory` | GET | Get full inventory with stock status (CRITICAL/LOW/OK) |
| `/admin/refill-alerts` | GET | Get rule-based refill alerts (threshold monitoring) |
| `/admin/refill` | POST | Trigger manual stock refill (logged) |
| `/admin/refill-history` | GET | View refill audit trail |

### How to Refill Stock

**Option 1: Admin Stock Dashboard** (http://localhost:8000/admin-stock)
1. Login with admin credentials
2. View inventory table with color-coded stock status
3. Click "Refill" button for any medicine
4. Enter quantity and reason
5. Confirm - stock updates immediately

**Option 2: Existing Admin Dashboard** (http://localhost:8000/admin)
1. Go to "Inventory" tab
2. Click "Refill" button in ACTION column
3. Enter admin credentials when prompted
4. Enter quantity and reason
5. Confirm - stock updates immediately

**Option 3: API Call**
```bash
# Login first
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "pharmacy_admin_2026"}'

# Use returned token
curl -X POST http://localhost:8000/admin/refill \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "medicine_name": "Paracetamol",
    "quantity": 100,
    "reason": "Stock depleted - manual restock"
  }'
```

### Safety Features

- **Cooldown Period**: 5 minutes between refills for same medicine
- **Quantity Validation**: Max refill = threshold × 5
- **Authentication Required**: All actions require admin credentials
- **Audit Logging**: Every refill logged with timestamp, admin user, quantity, and reason
- **Rate Limiting**: Max 10 refills per medicine per hour

### Stock Thresholds

Each medicine has a configurable threshold in `data/medicine_master.csv`:

| Medicine | Stock Threshold | Alert Trigger |
|----------|----------------|---------------|
| Paracetamol | 50 | Stock < 50 |
| Ibuprofen | 100 | Stock < 100 |
| Insulin Glargine | 15 | Stock < 15 |

**Stock Status:**
- 🟢 **OK**: Stock >= Threshold
- 🟡 **LOW**: Stock < Threshold
- 🔴 **CRITICAL**: Stock < Threshold / 2

---

## � Chat Interface Features

### Intent-Based Routing

The system automatically classifies user messages into:

1. **GENERAL_CHAT** - Greetings, questions, general conversation
   - Example: "Hi", "Hello", "How are you?"
   - Response: AI-powered conversational agent

2. **SYMPTOM_QUERY** - Health symptoms for medicine recommendations
   - Example: "I have fever", "My head hurts", "I have a cough"
   - Response: OTC medicine recommendations with medical disclaimer

3. **PRESCRIPTION_UPLOAD** - Prescription-related queries
   - Example: "I want to upload prescription", "Upload my prescription"
   - Response: Redirect to prescription upload page

4. **MEDICINE_ORDER** - Direct medicine orders
   - Example: "I need Paracetamol 20 tablets", "Order Ibuprofen"
   - Response: Process order with stock check

### Symptom Analysis

- Maps natural language symptoms to medicines
- Provides OTC recommendations with dosage info
- Includes medical disclaimers
- Checks stock availability
- Handles multiple symptoms

**Example:**
```
User: "I have fever and headache"

Response:
⚕️ IMPORTANT MEDICAL DISCLAIMER
I am not a doctor and this is not medical advice. This system does not 
diagnose medical conditions and should not replace professional medical advice. 
Please consult a healthcare professional for proper diagnosis and treatment.

Symptoms detected: fever, headache

💊 Over-the-Counter (OTC) Recommendations:
(For informational purposes only)

Paracetamol (✅ In stock: 50 units)
• Commonly used for: fever, headache
• ⚠️ Consult doctor if fever persists for more than 3 days

Ibuprofen (✅ In stock: 100 units)
• Commonly used for: fever, headache
• ⚠️ Do not exceed recommended dose. Consult pharmacist.
```

### Prescription Upload

- Upload prescription images (JPEG, PNG, PDF)
- Automatic extraction using Ollama Vision
- Safety checks for prescription-required medicines
- Comprehensive logging

---

## � Project Structure

```
new project/
├── backend/
│   ├── main.py                      # FastAPI server + routes
│   ├── auth.py                      # JWT authentication (NEW)
│   ├── database.py                  # Data access layer
│   ├── agents/
│   │   ├── router_agent.py          # Intent classification (NEW)
│   │   ├── general_chat_agent.py    # General conversation (NEW)
│   │   ├── symptom_analysis_agent.py # Symptom-to-medicine mapping (NEW)
│   │   ├── prescription_vision_agent.py # Vision-based extraction (NEW)
│   │   ├── stock_refill_agent.py    # Inventory monitoring & refills (NEW)
│   │   ├── conversational_agent.py  # Natural language understanding
│   │   ├── inventory_agent.py       # Stock management
│   │   ├── safety_agent.py          # Prescription validation
│   │   ├── predictive_agent.py      # Refill predictions
│   │   └── orchestrator_agent.py    # Workflow coordination
│   └── observability/
│       ├── trace_logger.py          # Action logging
│       └── middleware.py            # FastAPI middleware
├── frontend/
│   ├── index.html                   # Main chat interface
│   ├── app.js                       # Chat logic
│   ├── admin.html                   # Observability dashboard
│   ├── admin.js                     # Admin dashboard logic
│   ├── admin_stock.html             # Admin stock management UI (NEW)
│   ├── admin_stock.js               # Stock management logic (NEW)
│   ├── prescription.html            # Prescription upload UI
│   └── style.css                    # Unified styles
├── data/
│   ├── medicine_master.csv          # Medicine database (with thresholds)
│   ├── orders.csv                   # Order history
│   ├── symptom_medicine_mapping.csv # Symptom database (NEW)
│   ├── refill_logs.csv              # Refill audit trail (NEW)
│   ├── refill_alerts.json           # Active refill alerts (NEW)
│   └── traces.jsonl                 # Agent decision logs
└── requirements.txt                 # Python dependencies
```

---

## 🛠️ API Endpoints

### Public Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main chat interface |
| `/admin` | GET | Admin observability dashboard |
| `/admin-stock` | GET | Admin stock management dashboard |
| `/prescription` | GET | Prescription upload page |
| `/api/chat` | POST | Unified chat endpoint (intent-routed) |
| `/api/inventory` | GET | Get all medicines |
| `/api/inventory/{name}` | GET | Get specific medicine |
| `/api/statistics` | GET | System statistics |
| `/api/alerts/low-stock` | GET | Low stock alerts |
| `/api/alerts/refills` | GET | Refill predictions |
| `/api/traces/grouped` | GET | Agent decision traces |

### Admin Endpoints (Protected)

| Endpoint | Method | Auth Required | Description |
|----------|--------|---------------|-------------|
| `/auth/login` | POST | No | Admin login (returns JWT) |
| `/auth/logout` | POST | Yes | Logout (invalidate token) |
| `/auth/validate` | GET | Yes | Validate token |
| `/admin/inventory` | GET | Yes | Full inventory with stock status |
| `/admin/refill-alerts` | GET | Yes | AI-generated refill alerts |
| `/admin/refill` | POST | Yes | Trigger stock refill |
| `/admin/refill-history` | GET | Yes | Refill audit trail |

---

## 🔧 Troubleshooting

### Refill button not showing

**Cause**: Browser cache not cleared

**Solution**:
1. Hard refresh: ⌘ + Shift + R (Mac) or Ctrl + Shift + R (Windows)
2. Or clear browser cache and reload
3. Check browser console for JavaScript errors

### Login fails (401 Unauthorized)

**Cause**: Incorrect credentials or bcrypt issue

**Solution**:
1. Verify username: `admin`
2. Verify password: `pharmacy_admin_2026`
3. Check backend logs for authentication errors

### Ollama connection errors

**Cause**: Ollama not running

**Solution**:
```bash
# Start Ollama
ollama serve

# Verify models are pulled
ollama list
ollama pull llama3.2
ollama pull llama3.2-vision
ollama pull nomic-embed-text
```

---

## 📈 Features Summary

### ✅ Implemented

- [x] Natural language medicine ordering
- [x] Intent-based routing (GENERAL_CHAT, SYMPTOM_QUERY, PRESCRIPTION_UPLOAD, MEDICINE_ORDER)
- [x] General chat agent with Ollama LLM
- [x] Symptom analysis with OTC recommendations
- [x] Medical disclaimers for health queries
- [x] Prescription image upload (vision-based extraction)
- [x] JWT-based admin authentication
- [x] Admin stock management dashboard
- [x] Real-time inventory monitoring
- [x] Rule-based + predictive refill alerts (AI-assisted monitoring)
- [x] Manual stock refills with audit trail
- [x] Safety constraints (cooldown, validation, rate limiting)
- [x] Prescription requirement enforcement
- [x] Predictive refill alerts
- [x] Low stock detection
- [x] Automated warehouse orders (webhook simulation)
- [x] Full observability (trace logging)
- [x] Admin dashboard with statistics
- [x] Stock status color coding (CRITICAL/LOW/OK)

---

## ⚕️ Safety & Responsibility

### Medical Disclaimer

**THIS SYSTEM IS NOT A MEDICAL DEVICE AND DOES NOT PROVIDE MEDICAL ADVICE.**

#### Symptom Analysis Feature
- The symptom analysis feature provides **informational content only**
- It does NOT diagnose medical conditions
- It does NOT replace professional medical advice, diagnosis, or treatment
- All symptom-related responses include explicit disclaimers
- Users are directed to consult healthcare professionals

#### Decision Authority Boundaries

**What AI Components Do:**
- ✅ Classify user intent (routing)
- ✅ Extract text from prescription images
- ✅ Monitor stock levels against thresholds
- ✅ Orchestrate workflow steps

**What AI Components Do NOT Do:**
- ❌ Make medical diagnoses
- ❌ Override safety rules
- ❌ Make prescription validation decisions (rule-based only)
- ❌ Autonomously approve medications

#### Safety-Critical Decisions

All safety-critical decisions are **deterministic and rule-based**:

1. **Prescription Requirements**: Hardcoded database determines if Rx required
2. **Stock Thresholds**: Admin-configured numeric thresholds
3. **Refill Quantities**: Validated against maximum limits (threshold × 5)
4. **Cooldown Periods**: Time-based constraints (5 minutes)

#### Refill Alert Generation

**Mechanism:**
```
IF current_stock < configured_threshold THEN
    alert_severity = CRITICAL if < threshold/2 else LOW
    suggested_quantity = (threshold - current_stock) + safety_margin
END IF
```

- **NOT AI prediction**: Rule-based threshold comparison
- **AI-assisted**: Monitoring and orchestration (not decision-making)
- **Admin control**: Thresholds configurable in `medicine_master.csv`

### Compliance Notes

- **Privacy**: All data remains local (offline-first)
- **Audit Trail**: Complete logging of all actions
- **Authentication**: Admin functions require JWT authentication
- **Transparency**: All agent decisions traceable via observability system

### Intended Use

This is a **demonstration educational project** for:
- Learning agentic AI architecture
- Understanding offline-first systems
- Exploring healthcare IT concepts

**NOT intended for:**
- Clinical use
- Real patient care
- Production medical environments without proper certification

---

## 🌟 Key Takeaways

**This is how modern AI systems should be built:**
- Transparent
- Auditable  
- Privacy-respecting
- Cost-effective
- Explainable
- Secure (authentication & authorization)
- Observable (full tracing)
- Safe (rate limiting, validation, cooldowns)

---

**Built with ❤️ for autonomous, trustworthy, and secure AI systems**
