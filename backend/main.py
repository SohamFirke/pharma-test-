"""
FastAPI Backend for Agentic AI Pharmacy System
Main application with all REST endpoints.
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from pathlib import Path
import sys
import json
import uuid

# Add current directory to path
sys.path.append(str(Path(__file__).resolve().parent))

from database import Database
from agents.orchestrator_agent import OrchestratorAgent
from observability.trace_logger import TraceLogger
from observability.middleware import ObservabilityMiddleware

# Authentication
import auth

# Prescription agents
from agents.prescription_upload_agent import PrescriptionUploadAgent
from agents.ocr_agent import OCRAgent
from agents.prescription_parsing_agent import PrescriptionParsingAgent
from agents.prescription_safety_agent import PrescriptionSafetyAgent
from agents.order_execution_agent import OrderExecutionAgent

# New agents for intent routing and chat
from agents.router_agent import RouterAgent
from agents.general_chat_agent import GeneralChatAgent
from agents.symptom_analysis_agent import SymptomAnalysisAgent
from agents.prescription_vision_agent import PrescriptionVisionAgent
from agents.stock_refill_agent import StockRefillAgent

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

# Initialize prescription agents
upload_agent = PrescriptionUploadAgent()
ocr_agent = OCRAgent()
parsing_agent = PrescriptionParsingAgent(use_ollama=True)
safety_agent = PrescriptionSafetyAgent()
execution_agent = OrderExecutionAgent(orchestrator=orchestrator)

# Initialize new agents
router_agent = RouterAgent()
general_chat_agent = GeneralChatAgent(use_ollama=True)
symptom_analysis_agent = SymptomAnalysisAgent()
vision_agent = PrescriptionVisionAgent()
stock_refill_agent = StockRefillAgent()

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


class LoginRequest(BaseModel):
    username: str
    password: str


class RefillRequest(BaseModel):
    medicine_name: str
    quantity: int
    reason: str


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


@app.get("/prescription", response_class=HTMLResponse)
async def prescription_page():
    """Serve prescription upload page."""
    prescription_path = frontend_dir / "prescription.html"
    if prescription_path.exists():
        return prescription_path.read_text()
    return "<h1>Prescription Upload</h1><p>Frontend not found. Check /frontend/prescription.html</p>"


@app.get("/admin-stock", response_class=HTMLResponse)
async def admin_stock_page():
    """Serve admin stock management dashboard."""
    admin_stock_path = frontend_dir / "admin_stock.html"
    if admin_stock_path.exists():
        return admin_stock_path.read_text()
    return "<h1>Admin Stock Management</h1><p>Frontend not found. Check /frontend/admin_stock.html</p>"


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


# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@app.post("/auth/login")
async def login(request: LoginRequest):
    """
    Admin login endpoint.
    
    Request body:
        - username: Admin username
        - password: Admin password
    
    Returns:
        JWT token for authenticated session
    """
    try:
        # Authenticate user
        user = auth.authenticate_user(request.username, request.password)
        
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Invalid username or password"
            )
        
        # Generate JWT token
        token = auth.create_access_token(user["username"], user["role"])
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "username": user["username"],
            "role": user["role"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")


@app.post("/auth/logout")
async def logout(credentials: HTTPAuthorizationCredentials = Depends(auth.security)):
    """
    Logout endpoint - invalidates current token.
    
    Requires:
        Authorization header with Bearer token
    
    Returns:
        Success message
    """
    try:
        token = credentials.credentials
        auth.invalidate_token(token)
        
        return {"message": "Logged out successfully"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/auth/validate")
async def validate_token(credentials: HTTPAuthorizationCredentials = Depends(auth.security)):
    """
    Validate current token.
    
    Requires:
        Authorization header with Bearer token
    
    Returns:
        User info if token is valid
    """
    try:
        token = credentials.credentials
        payload = auth.decode_token(token)
        
        if not payload:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired token"
            )
        
        return {
            "valid": True,
            "username": payload.get("sub"),
            "role": payload.get("role")
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ADMIN-ONLY PROTECTED ENDPOINTS
# ============================================================================

@app.get("/admin/inventory")
async def get_admin_inventory(credentials: HTTPAuthorizationCredentials = Depends(auth.security)):
    """
    Get full inventory with stock status (ADMIN ONLY).
    
    Requires:
        Authorization header with Bearer token
    
    Returns:
        List of all medicines with stock levels and status
    """
    # Validate admin token
    await auth.get_current_admin(credentials)
    
    try:
        medicines_df = Database.load_medicine_master()
        medicines = medicines_df.to_dict('records')
        
        # Add stock status to each medicine
        for medicine in medicines:
            current_stock = medicine.get('stock_level', 0)
            threshold = medicine.get('stock_threshold', 50)
            
            if current_stock < threshold / 2:
                medicine['stock_status'] = 'CRITICAL'
            elif current_stock < threshold:
                medicine['stock_status'] = 'LOW'
            else:
                medicine['stock_status'] = 'OK'
        
        return {"medicines": medicines, "total_count": len(medicines)}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/refill-alerts")
async def get_refill_alerts(credentials: HTTPAuthorizationCredentials = Depends(auth.security)):
    """
    Get rule-based refill alerts (ADMIN ONLY).
    Alerts generated via deterministic threshold monitoring (AI-assisted orchestration).
    
    Requires:
        Authorization header with Bearer token
    
    Returns:
        List of active refill alerts
    """
    # Validate admin token
    current_admin = await auth.get_current_admin(credentials)
    
    try:
        # Monitor inventory and generate fresh alerts
        alerts = stock_refill_agent.monitor_inventory()
        
        # Log monitoring action
        trace_id = f"monitor_{uuid.uuid4().hex[:8]}"
        trace_logger.log_trace(
            trace_id=trace_id,
            agent_name="StockRefillAgent",
            action="monitor_inventory",
            input_data={"requested_by": current_admin['username']},
            output_data={"alert_count": len(alerts)},
            decision_reason=stock_refill_agent.get_decision_reason(
                "monitor_inventory", True, {"alerts": alerts}
            )
        )
        
        return {"alerts": alerts, "count": len(alerts), "trace_id": trace_id}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/refill")
async def trigger_refill(
    request: RefillRequest,
    credentials: HTTPAuthorizationCredentials = Depends(auth.security)
):
    """
    Manually trigger stock refill (ADMIN ONLY).
    
    Requires:
        Authorization header with Bearer token
    
    Request body:
        - medicine_name: Medicine to refill
        - quantity: Quantity to add
        - reason: Reason for refill
    
    Returns:
        Refill execution result
    """
    # Validate admin token
    current_admin = await auth.get_current_admin(credentials)
    
    try:
        trace_id = f"refill_{uuid.uuid4().hex[:8]}"
        
        # Execute refill
        success, message, refill_data = stock_refill_agent.execute_refill(
            medicine_name=request.medicine_name,
            quantity=request.quantity,
            triggered_by="ADMIN",
            admin_username=current_admin['username'],
            reason=request.reason
        )
        
        # Log refill action
        trace_logger.log_trace(
            trace_id=trace_id,
            agent_name="StockRefillAgent",
            action="execute_refill",
            input_data={
                "medicine_name": request.medicine_name,
                "quantity": request.quantity,
                "admin": current_admin['username']
            },
            output_data=refill_data if success else {"error": message},
            decision_reason=stock_refill_agent.get_decision_reason(
                "execute_refill", success, refill_data if success else {"error": message}
            ),
            status="success" if success else "failed"
        )
        
        if not success:
            raise HTTPException(status_code=400, detail=message)
        
        return {
            "status": "success",
            "message": message,
            "refill_data": refill_data,
            "trace_id": trace_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Refill failed: {str(e)}")


@app.get("/admin/refill-history")
async def get_refill_history(
    limit: int = 50,
    credentials: HTTPAuthorizationCredentials = Depends(auth.security)
):
    """
    Get refill history audit trail (ADMIN ONLY).
    
    Query params:
        - limit: Maximum number of records (default: 50)
    
    Requires:
        Authorization header with Bearer token
    
    Returns:
        List of historical refill actions
    """
    # Validate admin token
    await auth.get_current_admin(credentials)
    
    try:
        history = stock_refill_agent.get_refill_history(limit=limit)
        
        return {
            "history": history,
            "count": len(history)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/export/product-list")
async def export_product_list(
    credentials: HTTPAuthorizationCredentials = Depends(auth.security)
):
    """
    Export product list as Excel file (ADMIN ONLY).
    
    For administrative and inventory management purposes only.
    No medical decision-making logic involved.
    
    Requires:
        Authorization header with Bearer token
    
    Returns:
        Excel file download (product_list.xlsx)
    """
    # Validate admin token
    current_admin = await auth.get_current_admin(credentials)
    
    try:
        # Generate Excel file
        from utils.excel_generator import ExcelGenerator
        excel_bytes = ExcelGenerator.generate_product_list()
        
        # Log export action
        trace_id = f"export_products_{uuid.uuid4().hex[:8]}"
        trace_logger.log_trace(
            trace_id=trace_id,
            agent_name="ExcelGenerator",
            action="export_product_list",
            input_data={"admin_user": current_admin['username']},
            output_data={"file_size_bytes": len(excel_bytes)},
            decision_reason=f"Product list exported by admin: {current_admin['username']}"
        )
        
        # Return Excel file
        return Response(
            content=excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": "attachment; filename=product_list.xlsx"
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@app.get("/admin/export/order-history")
async def export_order_history(
    credentials: HTTPAuthorizationCredentials = Depends(auth.security)
):
    """
    Export consumer order history as Excel file (ADMIN ONLY).
    
    For administrative and inventory management purposes only.
    No medical decision-making logic involved.
    
    Note: Patient demographic data (age, gender) and dosage frequencies 
    are placeholder values for demonstration purposes.
    
    Requires:
        Authorization header with Bearer token
    
    Returns:
        Excel file download (consumer_order_history.xlsx)
    """
    # Validate admin token
    current_admin = await auth.get_current_admin(credentials)
    
    try:
        # Generate Excel file
        from utils.excel_generator import ExcelGenerator
        excel_bytes = ExcelGenerator.generate_order_history()
        
        # Log export action
        trace_id = f"export_orders_{uuid.uuid4().hex[:8]}"
        trace_logger.log_trace(
            trace_id=trace_id,
            agent_name="ExcelGenerator",
            action="export_order_history",
            input_data={"admin_user": current_admin['username']},
            output_data={"file_size_bytes": len(excel_bytes)},
            decision_reason=f"Order history exported by admin: {current_admin['username']}"
        )
        
        # Return Excel file
        return Response(
            content=excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": "attachment; filename=consumer_order_history.xlsx"
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


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


@app.post("/api/chat")
async def chat(request: OrderRequest):
    """
    Handle general chat and symptom queries with intent routing.
    
    Uses RouterAgent to classify intent and route to appropriate agent:
    - GENERAL_CHAT → GeneralChatAgent
    - SYMPTOM_QUERY → SymptomAnalysisAgent
    - ORDER_RELATED → Redirects to order processing
    
    Request body:
        - user_id: Unique user identifier
        - message: User message
    
    Returns:
        Response from appropriate agent with intent classification
    """
    try:
        import uuid
        trace_id = f"chat_{uuid.uuid4().hex[:8]}"
        
        # Step 1: Classify intent using RouterAgent
        intent_result = router_agent.classify_intent(request.message)
        
        trace_logger.log_trace(
            trace_id=trace_id,
            agent_name="RouterAgent",
            action="classify_intent",
            input_data={"message": request.message, "user_id": request.user_id},
            output_data=intent_result,
            decision_reason=router_agent.get_decision_reason(intent_result)
        )
        
        intent = intent_result.get("intent")
        confidence = intent_result.get("confidence", 0.0)
        
        # Step 2: Route to appropriate agent based on intent
        if intent == router_agent.GENERAL_CHAT:
            # Handle general conversation
            chat_result = general_chat_agent.respond(request.message, request.user_id)
            
            trace_logger.log_trace(
                trace_id=trace_id,
                agent_name="GeneralChatAgent",
                action="respond",
                input_data={"message": request.message},
                output_data=chat_result,
                decision_reason=general_chat_agent.get_decision_reason(chat_result)
            )
            
            return {
                "status": "success",
                "response": chat_result["response"],
                "intent_detected": intent,
                "confidence": confidence,
                "trace_id": trace_id,
                "agent_used": "GeneralChatAgent"
            }
        
        elif intent == router_agent.SYMPTOM_QUERY:
            # Handle symptom analysis
            symptom_result = symptom_analysis_agent.analyze_and_recommend(
                request.message, request.user_id
            )
            
            trace_logger.log_trace(
                trace_id=trace_id,
                agent_name="SymptomAnalysisAgent",
                action="analyze_and_recommend",
                input_data={"message": request.message},
                output_data=symptom_result,
                decision_reason=symptom_analysis_agent.get_decision_reason(symptom_result)
            )
            
            return {
                "status": "success",
                "response": symptom_result["response"],
                "intent_detected": intent,
                "confidence": confidence,
                "symptoms_detected": symptom_result.get("symptoms_detected", []),
                "recommendations": symptom_result.get("recommendations", []),
                "trace_id": trace_id,
                "agent_used": "SymptomAnalysisAgent"
            }
        
        elif intent == router_agent.ORDER_RELATED:
            # Redirect to order processing
            result = orchestrator.process_order(request.user_id, request.message)
            
            return {
                "status": result["status"],
                "response": result["message"],
                "intent_detected": intent,
                "confidence": confidence,
                "trace_id": result["trace_id"],
                "order_id": result.get("order_id"),
                "agent_used": "OrderProcessing"
            }
        
        else:
            # Unknown intent
            return {
                "status": "unknown_intent",
                "response": "I'm not sure how to help with that. Try ordering a medicine, asking about symptoms, or just say hi!",
                "intent_detected": intent,
                "confidence": confidence,
                "trace_id": trace_id
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")



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
    Get predictive refill alerts based on usage patterns (Predictive Agent).
    Uses historical order data to generate proactive reminders.
    
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
            "orchestrator": "active",
            "prescription_upload": "active",
            "ocr": "active"
        }
    }


# ============================================================================
# PRESCRIPTION UPLOAD ENDPOINTS
# ============================================================================

@app.post("/api/upload-prescription")
async def upload_prescription(
    file: UploadFile = File(...),
    user_id: str = Form(...)
):
    """
    Upload prescription image/PDF and automatically extract medicine details.
    
    Request:
        - file: Prescription image (JPG/PNG) or PDF
        - user_id: User identifier
    
    Returns:
        Prescription data with extracted medicines
    """
    trace_id = None
    
    try:
        # Generate trace ID
        import uuid
        trace_id = f"rx_{uuid.uuid4().hex[:8]}"
        
        # Step 1: Upload Agent - Save file
        file_content = await file.read()
        success, prescription_id, upload_metadata = upload_agent.save_prescription_file(
            file_content, file.filename, user_id
        )
        
        trace_logger.log_trace(
            trace_id=trace_id,
            agent_name="PrescriptionUploadAgent",
            action="save_file",
            input_data={"filename": file.filename, "user_id": user_id},
            output_data=upload_metadata,
            decision_reason=upload_agent.get_decision_reason("save_file", success, upload_metadata),
            status="success" if success else "failed"
        )
        
        if not success:
            raise HTTPException(status_code=400, detail=upload_metadata.get('error'))
        
        # Step 2: OCR Agent - Extract text
        file_path = upload_metadata['file_path']
        file_type = upload_metadata['file_type']
        
        success, ocr_text, ocr_metadata = ocr_agent.extract_text(file_path, file_type)
        
        trace_logger.log_trace(
            trace_id=trace_id,
            agent_name="OCRAgent",
            action="extract_text",
            input_data={"file_path": file_path, "file_type": file_type},
            output_data={"text_length": len(ocr_text), **ocr_metadata},
            decision_reason=ocr_agent.get_decision_reason(success, ocr_metadata),
            status="success" if success else "failed"
        )
        
        if not success:
            return JSONResponse({
                "status": "failed",
                "prescription_id": prescription_id,
                "message": "Text extraction failed. " + ocr_metadata.get('error', ''),
                "trace_id": trace_id
            }, status_code=400)
        
        # Step 3: Parsing Agent - Extract medicines
        success, medicines, parsing_metadata = parsing_agent.parse_prescription(ocr_text)
        
        trace_logger.log_trace(
            trace_id=trace_id,
            agent_name="PrescriptionParsingAgent",
            action="parse_prescription",
            input_data={"text_preview": ocr_text[:200]},
            output_data={"medicines": medicines, **parsing_metadata},
            decision_reason=parsing_agent.get_decision_reason(success, medicines, parsing_metadata),
            status="success" if success else "failed"
        )
        
        if not success:
            return JSONResponse({
                "status": "failed",
                "prescription_id": prescription_id,
                "message": "Prescription parsing failed. " + parsing_metadata.get('error', ''),
                "extracted_text": ocr_text,
                "trace_id": trace_id
            }, status_code=400)
        
        # Step 4: Safety Agent - Validate medicines
        parsing_confidence = parsing_metadata.get('confidence', 0.5)
        is_valid, safety_reason, validated_medicines = safety_agent.validate_prescription(
            medicines, parsing_confidence
        )
        
        trace_logger.log_trace(
            trace_id=trace_id,
            agent_name="PrescriptionSafetyAgent",
            action="validate_prescription",
            input_data={"medicines_count": len(medicines)},
            output_data={"validated_count": len(validated_medicines), "is_valid": is_valid},
            decision_reason=safety_agent.get_decision_reason(is_valid, safety_reason, validated_medicines),
            status="success" if is_valid else "rejected"
        )
        
        # Save prescription to database
        prescription_data = {
            "prescription_id": prescription_id,
            "user_id": user_id,
            "file_path": file_path,
            "upload_date": upload_metadata['upload_date'],
            "status": "validated" if is_valid else "rejected",
            "ocr_text": ocr_text[:500],  # Truncate for storage
            "parsed_medicines": json.dumps(validated_medicines if is_valid else medicines),
            "safety_status": "approved" if is_valid else "rejected",
            "order_ids": "",
            "trace_id": trace_id
        }
        
        Database.save_prescription(prescription_data)
        
        # Return response
        return {
            "status": "success" if is_valid else "validation_failed",
            "prescription_id": prescription_id,
            "trace_id": trace_id,
            "extracted_text": ocr_text,
            "parsed_medicines": validated_medicines if is_valid else medicines,
            "safety_validation": {
                "is_valid": is_valid,
                "reason": safety_reason
            },
            "message": safety_reason if not is_valid else "Prescription validated. Review medicines and confirm order."
        }
    
    except HTTPException:
        raise
    except Exception as e:
        if trace_id:
            trace_logger.log_trace(
                trace_id=trace_id,
                agent_name="PrescriptionUploadWorkflow",
                action="process_upload",
                input_data={"filename": file.filename},
                output_data={"error": str(e)},
                decision_reason=f"Prescription upload failed: {str(e)}",
                status="error"
            )
        raise HTTPException(status_code=500, detail=f"Upload processing failed: {str(e)}")


@app.post("/api/vision-prescription")
async def vision_prescription_upload(
    file: UploadFile = File(...),
    user_id: str = Form(...)
):
    """
    Upload prescription image and extract using LLaMA 3.2 Vision model.
    
    This uses vision AI instead of OCR + parsing for better accuracy.
    
    Request:
        - file: Prescription image (JPG/PNG)
        - user_id: User identifier
    
    Returns:
        Prescription data with vision-extracted medicines
    """
    trace_id = None
    
    try:
        import uuid
        trace_id = f"vision_{uuid.uuid4().hex[:8]}"
        
        # Step 1: Save file
        file_content = await file.read()
        success, prescription_id, upload_metadata = upload_agent.save_prescription_file(
            file_content, file.filename, user_id
        )
        
        trace_logger.log_trace(
            trace_id=trace_id,
            agent_name="PrescriptionUploadAgent",
            action="save_file",
            input_data={"filename": file.filename, "user_id": user_id},
            output_data=upload_metadata,
            decision_reason="Saved prescription file for vision processing",
            status="success" if success else "failed"
        )
        
        if not success:
            raise HTTPException(status_code=400, detail=upload_metadata.get('error'))
        
        file_path = upload_metadata['file_path']
        
        # Step 2: Vision Agent - Extract from image directly
        success, medicines, vision_metadata = vision_agent.extract_from_image(file_path)
        
        trace_logger.log_trace(
            trace_id=trace_id,
            agent_name="PrescriptionVisionAgent",
            action="extract_from_image",
            input_data={"file_path": file_path},
            output_data={"medicines": medicines, **vision_metadata},
            decision_reason=vision_agent.get_decision_reason(success, medicines, vision_metadata),
            status="success" if success else "failed"
        )
        
        if not success:
            error_msg = vision_metadata.get('error', 'Vision extraction failed')
            return JSONResponse({
                "status": "failed",
                "prescription_id": prescription_id,
                "message": error_msg,
                "trace_id": trace_id
            }, status_code=400)
        
        # Save prescription to database
        prescription_data = {
            "prescription_id": prescription_id,
            "user_id": user_id,
            "file_path": file_path,
            "upload_date": upload_metadata['upload_date'],
            "status": "vision_processed",
            "ocr_text": f"Vision model extraction (confidence: {vision_metadata.get('confidence', 0.0):.0%})",
            "parsed_medicines": json.dumps(medicines),
            "safety_status": "pending_review",
            "order_ids": "",
            "trace_id": trace_id
        }
        
        Database.save_prescription(prescription_data)
        
        return {
            "status": "success",
            "prescription_id": prescription_id,
            "trace_id": trace_id,
            "medicines": medicines,
            "vision_metadata": vision_metadata,
            "message": f"Vision extraction successful. Found {len(medicines)} medicine(s). Review and confirm to order."
        }
    
    except HTTPException:
        raise
    except Exception as e:
        if trace_id:
            trace_logger.log_trace(
                trace_id=trace_id,
                agent_name="VisionPrescriptionWorkflow",
                action="process_vision_upload",
                input_data={"filename": file.filename},
                output_data={"error": str(e)},
                decision_reason=f"Vision prescription processing failed: {str(e)}",
                status="error"
            )
        raise HTTPException(status_code=500, detail=f"Vision processing failed: {str(e)}")



@app.post("/api/confirm-prescription-order")
async def confirm_prescription_order(
    prescription_id: str = Form(...),
    user_id: str = Form(...)
):
    """
    Confirm and execute orders from validated prescription.
    
    Request:
        - prescription_id: Prescription ID to process
        - user_id: User identifier
    
    Returns:
        Order execution results
    """
    
    try:
        # Get prescription
        prescription = Database.get_prescription(prescription_id)
        
        if not prescription:
            raise HTTPException(status_code=404, detail="Prescription not found")
        
        if prescription['user_id'] != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized")
        
        if prescription['safety_status'] != 'approved':
            raise HTTPException(status_code=400, detail="Prescription not approved for ordering")
        
        # Parse medicines
        try:
            medicines = json.loads(prescription['parsed_medicines'])
        except:
            raise HTTPException(status_code=400, detail="Invalid prescription data")
        
        # Execute orders
        trace_id = prescription['trace_id']
        success, order_results, summary = execution_agent.execute_prescription_orders(
            user_id, medicines, prescription_id
        )
        
        trace_logger.log_trace(
            trace_id=trace_id,
            agent_name="OrderExecutionAgent",
            action="execute_orders",
            input_data={"prescription_id": prescription_id, "medicines_count": len(medicines)},
            output_data={"orders": order_results, "success": success},
            decision_reason=execution_agent.get_decision_reason(success, order_results),
            status="success" if success else "partial_failure"
        )
        
        # Update prescription status
        order_ids = ",".join([r.get('order_id', '') for r in order_results if r.get('order_id')])
        Database.update_prescription_status(
            prescription_id,
            "fulfilled" if success else "partial",
            order_ids
        )
        
        return {
            "status": "success" if success else "partial_success",
            "prescription_id": prescription_id,
            "orders_created": order_results,
            "summary": summary,
            "trace_id": trace_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Order execution failed: {str(e)}")


@app.get("/api/prescription/{prescription_id}/trace")
async def get_prescription_trace(prescription_id: str):
    """
    Get complete agent decision trace for a prescription.
    
    Args:
        prescription_id: Prescription ID
    
    Returns:
        Complete trace of agent decisions
    """
    
    try:
        prescription = Database.get_prescription(prescription_id)
        
        if not prescription:
            raise HTTPException(status_code=404, detail="Prescription not found")
        
        trace_id = prescription.get('trace_id')
        if not trace_id:
            return {"prescription_id": prescription_id, "traces": [], "message": "No trace found"}
        
        traces = trace_logger.get_trace_by_id(trace_id)
        
        return {
            "prescription_id": prescription_id,
            "trace_id": trace_id,
            "traces": traces,
            "prescription_status": prescription.get('status')
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/prescriptions")
async def get_prescriptions(user_id: Optional[str] = None):
    """
    Get all prescriptions, optionally filtered by user.
    
    Query params:
        - user_id: Optional filter by user
    
    Returns:
        List of prescriptions
    """
    
    try:
        prescriptions = Database.get_all_prescriptions(user_id)
        return prescriptions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
