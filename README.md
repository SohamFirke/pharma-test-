# 🏥 Agentic AI Pharmacy System

**An offline-first, privacy-focused, autonomous pharmacy system powered by local AI agents.**

---

## 🎯 Overview

This system transforms traditional pharmacy operations into an intelligent, agent-based platform that:

- ✅ **Understands natural language** - Order medicines conversationally without rigid forms
- ✅ **Enforces safety rules** - Deterministic prescription validation (no probabilistic decisions)
- ✅ **Predicts refill needs** - Proactively alerts users when running low on medicine
- ✅ **Automates inventory** - Triggers warehouse orders when stock is low
- ✅ **Provides full observability** - Every agent decision is traceable and auditable

**🔒 100% Offline-Capable | 🆓 Zero API Costs | 🔐 Privacy-First**

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      USER INTERFACE                          │
│         Chat Interface + Voice Input + Admin Dashboard       │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    AGENTIC LAYER                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │Conversational│  │    Safety    │  │  Inventory   │      │
│  │    Agent     │  │    Agent     │  │    Agent     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌────────────────────────────────┐      │
│  │  Predictive  │  │   Orchestrator Agent           │      │
│  │    Agent     │  │   (Workflow Coordinator)       │      │
│  └──────────────┘  └────────────────────────────────┘      │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                   BACKEND SERVICES                           │
│        FastAPI + CSV/SQLite + Trace Logger                   │
└──────────────────────────────────────────────────────────────┘
```

### 🤖 Agent Responsibilities

| Agent | Role | Technology |
|-------|------|------------|
| **Conversational** | Extract intent from natural language | Ollama (LLM) + regex fallback |
| **Safety** | Validate prescription requirements | Rule-based (deterministic) |
| **Inventory** | Manage stock & trigger procurement | Python logic + webhook |
| **Predictive** | Calculate refill predictions | Algorithm-based |
| **Orchestrator** | Coordinate workflow & state | Python OOP |

---

## 🚀 Quick Start

### Prerequisites

1. **Python 3.9+**
2. **Ollama** (for local LLM)
   ```bash
   # Install from https://ollama.ai
   # Then pull model:
   ollama pull llama3.2
   ```

### Installation

1. **Clone/Navigate to project**
   ```bash
   cd "new project"
   ```

2. **Run setup script**
   ```bash
   python setup.py
   ```

3. **Start Ollama** (in a separate terminal)
   ```bash
   ollama serve
   ```

4. **Start the backend**
   ```bash
   cd backend
   python main.py
   ```

5. **Open your browser**
   - **Main UI**: http://localhost:8000
   - **Admin Dashboard**: http://localhost:8000/admin
   - **API Docs**: http://localhost:8000/docs

---

## 💡 How It Works

### Example User Flow

**User Input:**
```
"I need my BP tablets again, 30 days worth"
```

**Agent Pipeline:**

1. **Conversational Agent**
   - Extracts: `medicine_name="Lisinopril"`, `quantity=30`, `dosage_per_day=1`
   - Uses Ollama LLM with regex fallback

2. **Safety Agent**
   - Checks: Is prescription required? ✅ Yes
   - Decision: REJECT (prescription required)
   - Output: "PRESCRIPTION REQUIRED: Lisinopril requires a valid prescription"

3. **Inventory Agent** *(if safety passes)*
   - Checks stock availability
   - Deducts inventory
   - Triggers warehouse webhook if low stock

4. **Database Update**
   - Saves order to `order_history.csv`

5. **Predictive Agent** *(background)*
   - Analyzes past orders
   - Calculates days remaining
   - Generates refill alert if ≤ 3 days

---

## 🔍 Why No API Keys?

### Design Philosophy

This system is built for:
- **Privacy**: Medical data never leaves your machine
- **Offline capability**: Works without internet (after initial setup)
- **Cost**: Zero recurring API fees
- **Control**: You own the entire stack

### Technology Choices

| Need | Solution | Why |
|------|----------|-----|
| NLU | Ollama (local LLM) | Runs on your hardware, fully offline |
| Fallback NLP | spaCy + regex | Deterministic, no external calls |
| Database | CSV + pandas | Human-readable, portable |
| Voice input | Web Speech API | Browser-native, client-side |
| Observability | Custom JSON logger | Full control, no vendor lock-in |

---

## 📊 Agent Observability

Every agent decision is logged with:
- `trace_id` - Groups related actions
- `agent_name` - Which agent acted
- `decision_reason` - Why the decision was made
- `input/output` - Complete context
- `timestamp` - When it happened

**View traces in Admin Dashboard → Agent Traces tab**

Example trace:
```json
{
  "trace_id": "abc-123",
  "agent_name": "SafetyAgent",
  "action": "validate_order",
  "decision_reason": "REJECTED: Lisinopril requires prescription (deterministic rule)",
  "status": "success"
}
```

---

## 🧠 Predictive Refill Algorithm

```python
# Calculate remaining medicine days
total_days_supply = quantity / dosage_per_day
days_elapsed = (today - purchase_date).days
days_remaining = total_days_supply - days_elapsed

# Trigger alert if ≤ 3 days
if days_remaining <= 3:
    generate_refill_alert()
```

**Proactive Alerts:**
- CRITICAL: Medicine depleted (0 days)
- HIGH: ≤ 1 day remaining
- MEDIUM: ≤ 3 days remaining

---

## 📁 Project Structure

```
new project/
├── backend/
│   ├── main.py                    # FastAPI application
│   ├── database.py                # CSV/SQLite utilities
│   ├── agents/
│   │   ├── conversational_agent.py
│   │   ├── safety_agent.py
│   │   ├── inventory_agent.py
│   │   ├── predictive_agent.py
│   │   └── orchestrator_agent.py
│   └── observability/
│       ├── trace_logger.py        # Custom trace logging
│       └── middleware.py          # HTTP observability
├── frontend/
│   ├── index.html                 # User chat UI
│   ├── admin.html                 # Admin dashboard
│   ├── style.css                  # Modern dark mode styling
│   ├── app.js                     # Chat client logic
│   └── admin.js                   # Dashboard logic
├── data/
│   ├── medicine_master.csv        # Medicine inventory (source of truth)
│   ├── order_history.csv          # Purchase history
│   └── traces.jsonl               # Agent decision logs
├── requirements.txt
├── setup.py
└── README.md
```

---

## 🛠️ API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/order` | Process medicine order |
| `GET` | `/api/inventory` | Get all medicines |
| `GET` | `/api/inventory/{medicine}` | Get specific medicine |
| `GET` | `/api/user-history/{user_id}` | User order history |
| `GET` | `/api/alerts/refills` | Refill predictions |
| `GET` | `/api/alerts/low-stock` | Low stock warnings |
| `POST` | `/webhook/warehouse` | Warehouse procurement |
| `GET` | `/api/traces` | Agent decision traces |
| `GET` | `/api/traces/grouped` | Grouped workflows |
| `GET` | `/api/statistics` | System statistics |

**Full API documentation**: http://localhost:8000/docs (when server is running)

---

## 🎨 Features

### User Interface
- 🎤 **Voice Input** - Web Speech API for hands-free ordering
- 🌙 **Dark Mode** - Modern glassmorphism design
- 📱 **Responsive** - Works on desktop and mobile
- 🔔 **Real-time Alerts** - Proactive refill notifications

### Admin Dashboard
- 📊 **Statistics Cards** - Key metrics at a glance
- 📦 **Inventory Management** - Real-time stock levels
- ⚠️ **Alert Monitoring** - Low stock & refill predictions
- 🕵️ **Trace Viewer** - Complete agent decision history

### Safety Features
- ✅ **Deterministic Validation** - No AI decisions for safety
- 📋 **Prescription Checking** - Rule-based enforcement
- 💊 **Dosage Limits** - Configurable safety thresholds
- 📝 **Audit Trail** - Every decision is logged

---

## 🧪 Testing the System

### Basic Order Flow

1. Open http://localhost:8000
2. Enter user ID: `user001`
3. Type: "I need paracetamol, 20 tablets"
4. Observe:
   - ✅ Order approved (no prescription required)
   - 📦 Inventory deducted
   - 📋 Order saved to history

### Prescription Test

1. Type: "I need amoxicillin, 10 tablets"
2. Observe:
   - ❌ Order rejected (prescription required)
   - Safety agent blocks the order deterministically

### Refill Prediction Test

1. Check Admin Dashboard → Alerts tab
2. See proactive refill alerts for medicines running low
3. Alerts based on purchase history and consumption rate

---

## 🔧 Configuration

### Customize Stock Threshold

Edit `backend/agents/inventory_agent.py`:
```python
def __init__(self, low_stock_threshold: int = 50):  # Change threshold
```

### Change Refill Alert Timing

Edit `backend/agents/predictive_agent.py`:
```python
def __init__(self, alert_threshold_days: int = 3):  # Change days
```

### Use Different LLM Model

Edit `backend/agents/conversational_agent.py`:
```python
response = self.ollama_client.chat(
    model='mistral',  # Change model
    ...
)
```

---

## 🚨 Troubleshooting

### "Ollama not available"
```bash
# Make sure Ollama is running
ollama serve

# Pull the model if not downloaded
ollama pull llama3.2
```

### "Module not found" errors
```bash
# Reinstall dependencies
pip install -r requirements.txt
```

### System uses regex instead of LLM
- Check if Ollama is running: `ollama list`
- Verify model is installed: `ollama pull llama3.2`
- The system will work fine with regex fallback, just less flexible

---

## 📈 Future Enhancements

Potential improvements (not implemented):
- 🔐 User authentication system
- 📸 Prescription upload & OCR
- 📧 Email/SMS notifications (mock → real)
- 🗄️ PostgreSQL migration for scale
- 🔍 Advanced medicine search (fuzzy matching)
- 📱 Mobile app (React Native)
- 🌐 Multi-language support
- 📊 Analytics dashboard (order trends)

---

## 📝 License

This is a demonstration project for educational purposes.

---

## 💬 Support

For issues or questions:
1. Check the API docs: http://localhost:8000/docs
2. Review agent traces in Admin Dashboard
3. Check `data/traces.jsonl` for detailed logs

---

## 🌟 Key Takeaways

**Why This Architecture?**

1. **Agent Autonomy**: Each agent has a single responsibility and makes independent decisions
2. **Observability**: Every decision is traceable for debugging and compliance
3. **Offline-First**: Works without internet after setup
4. **Privacy**: Medical data stays on your machine
5. **Deterministic Safety**: Critical decisions use rules, not AI
6. **Predictive Intelligence**: Proactive refills improve user experience

**This is how modern AI systems should be built:**
- Transparent
- Auditable  
- Privacy-respecting
- Cost-effective
- Explainable

---

**Built with ❤️ for autonomous, trustworthy AI systems**
