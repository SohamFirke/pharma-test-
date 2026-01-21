"""
FastAPI Backend for Agentic AI Pharmacy System
Main application with all REST endpoints.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List
from pathlib import Path
import sys

# Add current directory to path
sys.path.append(str(Path(__file__).resolve().parent))

from database import Database
from agents.orchestrator_agent import OrchestratorAgent
from observability.trace_logger import TraceLogger
from observability.middleware import ObservabilityMiddleware

# Initialize FastAPI app
app = FastAPI(
    title="Agentic AI Pharmacy System",
    description="Offline, privacy-first pharmacy with autonomous agents",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize trace logger
trace_logger = TraceLogger()

# Add observability middleware
app.add_middleware(ObservabilityMiddleware, trace_logger=trace_logger)

# Initialize orchestrator
orchestrator = OrchestratorAgent(use_ollama=True)
orchestrator.set_trace_logger(trace_logger)

# Mount static files
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class OrderRequest(BaseModel):
    user_id: str
    message: str

class OrderResponse(BaseModel):
    status: str
    message: str
    trace_id: Optional[str] = None
    order_id: Optional[str] = None

class WebhookRequest(BaseModel):
    medicine_name: str
    current_stock: int
    requested_quantity: int
    priority: str = "normal"


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve main chat interface."""
    index_path = frontend_dir / "index.html"
    if index_path.exists():
        return index_path.read_text()
    return "<h1>Agentic AI Pharmacy System</h1><p>Frontend not found. Check /frontend/index.html</p>"


@app.get("/admin", response_class=HTMLResponse)
async def admin():
    """Serve admin dashboard."""
    admin_path = frontend_dir / "admin.html"
    if admin_path.exists():
        return admin_path.read_text()
    return "<h1>Admin Dashboard</h1><p>Frontend not found. Check /frontend/admin.html</p>"


@app.get("/api/inventory")
async def get_inventory():
    """
    Get all medicine inventory with current stock levels.
    
    Returns:
        List of all medicines with stock information
    """
    try:
        medicines = Database.load_medicine_master()
        return medicines.to_dict('records')
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/inventory/{medicine_name}")
async def get_medicine(medicine_name: str):
    """
    Get specific medicine details.
    
    Args:
        medicine_name: Name of the medicine
    
    Returns:
        Medicine details including stock level
    """
    medicine = Database.get_medicine(medicine_name)
    
    if not medicine:
        raise HTTPException(status_code=404, detail=f"Medicine '{medicine_name}' not found")
    
    return medicine


@app.post("/api/order", response_model=OrderResponse)
async def create_order(request: OrderRequest):
    """
    Process medicine order through agent pipeline.
    
    Request body:
        - user_id: Unique user identifier
        - message: Natural language order message
    
    Returns:
        Order status with trace ID and order ID if successful
    """
    try:
        result = orchestrator.process_order(request.user_id, request.message)
        
        return OrderResponse(
            status=result["status"],
            message=result["message"],
            trace_id=result["trace_id"],
            order_id=result.get("order_id")
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Order processing failed: {str(e)}")


@app.get("/api/user-history/{user_id}")
async def get_user_history(user_id: str):
    """
    Get order history for a specific user.
    
    Args:
        user_id: User identifier
    
    Returns:
        List of user's past orders
    """
    try:
        history = Database.get_user_history(user_id)
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhook/warehouse")
async def warehouse_webhook(request: WebhookRequest):
    """
    Mock warehouse procurement webhook.
    In production, this would integrate with actual warehouse system.
    
    Request body:
        - medicine_name: Medicine to order
        - current_stock: Current inventory level
        - requested_quantity: Amount to order
        - priority: "normal" or "high"
    
    Returns:
        Confirmation of warehouse order
    """
    
    # Log webhook receipt
    trace_logger.log_trace(
        trace_id=f"warehouse-{request.medicine_name}",
        agent_name="WarehouseWebhook",
        action="procurement_request",
        input_data=request.dict(),
        output_data={"status": "received"},
        decision_reason=f"Warehouse procurement requested for {request.medicine_name} ({request.requested_quantity} units)"
    )
    
    return {
        "status": "success",
        "message": f"Warehouse order initiated for {request.medicine_name}",
        "order_details": {
            "medicine": request.medicine_name,
            "quantity": request.requested_quantity,
            "priority": request.priority,
            "estimated_delivery": "2-3 business days"
        }
    }


@app.get("/api/alerts/refills")
async def get_refill_alerts(user_id: Optional[str] = None):
    """
    Get proactive refill alerts generated by Predictive Agent.
    
    Query params:
        - user_id: Optional, filter alerts for specific user
    
    Returns:
        List of refill alerts with prediction details
    """
    try:
        alerts = orchestrator.get_refill_alerts(user_id)
        return alerts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/alerts/low-stock")
async def get_low_stock_alerts():
    """
    Get medicines with low stock levels.
    
    Returns:
        List of medicines below stock threshold
    """
    try:
        low_stock = Database.get_low_stock_medicines(threshold=50)
        return low_stock
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/traces")
async def get_traces(limit: int = 100, trace_id: Optional[str] = None):
    """
    Get agent execution traces for observability.
    
    Query params:
        - limit: Maximum number of traces to return
        - trace_id: Optional, filter by specific trace ID
    
    Returns:
        List of trace logs
    """
    try:
        if trace_id:
            traces = trace_logger.get_trace_by_id(trace_id)
        else:
            traces = trace_logger.get_traces(limit=limit)
        return traces
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/traces/grouped")
async def get_grouped_traces(limit: int = 20):
    """
    Get traces grouped by workflow (trace_id).
    Useful for displaying complete order workflows.
    
    Returns:
        List of grouped trace workflows
    """
    try:
        grouped = trace_logger.get_recent_traces_grouped(limit=limit)
        return grouped
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/statistics")
async def get_statistics():
    """
    Get system statistics and agent performance metrics.
    
    Returns:
        Statistics about agent activity and system health
    """
    try:
        stats = trace_logger.get_agent_statistics()
        
        # Add inventory statistics
        inventory = Database.load_medicine_master()
        stats["inventory"] = {
            "total_medicines": len(inventory),
            "low_stock_count": len(Database.get_low_stock_medicines(50)),
            "prescription_required_count": int(inventory['prescription_required'].sum())
        }
        
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        System status
    """
    return {
        "status": "healthy",
        "service": "Agentic AI Pharmacy System",
        "agents": {
            "conversational": "active",
            "safety": "active",
            "inventory": "active",
            "predictive": "active",
            "orchestrator": "active"
        }
    }


# ============================================================================
# STARTUP
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 70)
    print("🏥 AGENTIC AI PHARMACY SYSTEM")
    print("=" * 70)
    print("Starting server...")
    print("Main UI: http://localhost:8000")
    print("Admin Dashboard: http://localhost:8000/admin")
    print("API Docs: http://localhost:8000/docs")
    print("=" * 70)
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
