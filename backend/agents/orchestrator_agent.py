"""
Orchestrator Agent: Workflow Coordination
Coordinates all agents and maintains workflow state.
"""

import sys
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import uuid

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

from database import Database
from agents.conversational_agent import ConversationalAgent
from agents.safety_agent import SafetyAgent
from agents.inventory_agent import InventoryAgent
from agents.predictive_agent import PredictiveAgent


class OrchestratorAgent:
    """
    Main coordinator agent that orchestrates the workflow across all agents.
    Maintains state and ensures actions happen in the correct order.
    """
    
    def __init__(self, use_ollama: bool = True):
        # Initialize all agents
        self.conversational_agent = ConversationalAgent(use_ollama=use_ollama)
        self.safety_agent = SafetyAgent()
        self.inventory_agent = InventoryAgent()
        self.predictive_agent = PredictiveAgent()
        
        # Workflow state
        self.current_trace_id = None
        self.trace_logger = None  # Will be set by main.py
    
    def set_trace_logger(self, logger):
        """Set the trace logger instance."""
        self.trace_logger = logger
    
    def process_order(self, user_id: str, message: str) -> Dict[str, Any]:
        """
        Main entry point: Process a user order message through the agent pipeline.
        
        Workflow:
        1. Conversational Agent: Extract intent
        2. Safety Agent: Validate prescription requirements
        3. Inventory Agent: Check stock and deduct
        4. Save order to database
        5. Trigger Predictive Agent asynchronously
        
        Returns:
            Response dictionary with status, message, and metadata
        """
        
        # Generate trace ID for this order
        trace_id = str(uuid.uuid4())
        self.current_trace_id = trace_id
        
        workflow_result = {
            "trace_id": trace_id,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "status": "pending",
            "message": "",
            "agent_decisions": [],
            "order_id": None
        }
        
        try:
            # Step 1: Conversational Agent - Extract Intent
            intent = self.conversational_agent.extract_intent(message, user_id)
            
            self._log_agent_action(
                agent_name="ConversationalAgent",
                action="extract_intent",
                input_data={"message": message, "user_id": user_id},
                output_data=intent,
                decision_reason=self.conversational_agent.get_decision_reason(intent)
            )
            
            workflow_result["agent_decisions"].append({
                "agent": "ConversationalAgent",
                "action": "extract_intent",
                "result": intent
            })
            
            # Check if extraction was successful
            if not intent.get("medicine_name") or intent.get("medicine_name") is None:
                workflow_result["status"] = "failed"
                workflow_result["message"] = (
                    "❌ Could not understand medicine request.\n\n"
                    "Please specify the medicine name clearly. For example:\n"
                    "• 'I need Paracetamol, 20 tablets'\n"
                    "• 'I want Ibuprofen for 10 days'\n"
                    "• 'Refill my usual medicine'"
                )
                return workflow_result
            
            medicine_name = intent["medicine_name"]
            quantity = intent.get("quantity", 1)
            dosage_per_day = intent.get("dosage_per_day", 1)
            
            # Ensure they are integers
            try:
                quantity = int(quantity) if quantity is not None else 1
                dosage_per_day = int(dosage_per_day) if dosage_per_day is not None else 1
            except (ValueError, TypeError):
                quantity = 1
                dosage_per_day = 1
            
            # Step 2: Safety Agent - Validate Prescription
            is_valid, safety_reason, safety_metadata = self.safety_agent.validate_order(
                medicine_name, user_id
            )
            
            self._log_agent_action(
                agent_name="SafetyAgent",
                action="validate_order",
                input_data={"medicine_name": medicine_name, "user_id": user_id},
                output_data={"is_valid": is_valid, "reason": safety_reason, "metadata": safety_metadata},
                decision_reason=self.safety_agent.get_decision_reason(is_valid, safety_reason, safety_metadata)
            )
            
            workflow_result["agent_decisions"].append({
                "agent": "SafetyAgent",
                "action": "validate_order",
                "result": {"is_valid": is_valid, "reason": safety_reason}
            })
            
            if not is_valid:
                workflow_result["status"] = "rejected"
                workflow_result["message"] = safety_reason
                return workflow_result
            
            # Check dosage safety
            dosage_safe, dosage_warning = self.safety_agent.check_dosage_safety(
                medicine_name, dosage_per_day
            )
            
            if not dosage_safe:
                workflow_result["status"] = "rejected"
                workflow_result["message"] = dosage_warning
                return workflow_result
            
            # Step 3: Inventory Agent - Check Availability
            is_available, availability_msg, availability_metadata = self.inventory_agent.check_availability(
                medicine_name, quantity
            )
            
            self._log_agent_action(
                agent_name="InventoryAgent",
                action="check_availability",
                input_data={"medicine_name": medicine_name, "quantity": quantity},
                output_data={"is_available": is_available, "message": availability_msg, "metadata": availability_metadata},
                decision_reason=self.inventory_agent.get_decision_reason("check_availability", is_available, availability_metadata)
            )
            
            workflow_result["agent_decisions"].append({
                "agent": "InventoryAgent",
                "action": "check_availability",
                "result": {"is_available": is_available, "message": availability_msg}
            })
            
            if not is_available:
                workflow_result["status"] = "rejected"
                workflow_result["message"] = availability_msg
                return workflow_result
            
            # Step 4: Inventory Agent - Deduct Stock
            deduct_success, deduct_msg, deduct_metadata = self.inventory_agent.deduct_stock(
                medicine_name, quantity
            )
            
            self._log_agent_action(
                agent_name="InventoryAgent",
                action="deduct_stock",
                input_data={"medicine_name": medicine_name, "quantity": quantity},
                output_data={"success": deduct_success, "message": deduct_msg, "metadata": deduct_metadata},
                decision_reason=self.inventory_agent.get_decision_reason("deduct_stock", deduct_success, deduct_metadata)
            )
            
            workflow_result["agent_decisions"].append({
                "agent": "InventoryAgent",
                "action": "deduct_stock",
                "result": {"success": deduct_success, "message": deduct_msg}
            })
            
            if not deduct_success:
                workflow_result["status"] = "failed"
                workflow_result["message"] = "Failed to process order: Stock deduction error"
                return workflow_result
            
            # Step 5: Save Order to Database
            order_id = Database.save_order(
                user_id=user_id,
                medicine_name=medicine_name,
                quantity=quantity,
                dosage_per_day=dosage_per_day
            )
            
            workflow_result["order_id"] = order_id
            
            # Step 6: Success Response
            workflow_result["status"] = "success"
            workflow_result["message"] = (
                f"✅ Order confirmed!\n\n"
                f"Medicine: {medicine_name}\n"
                f"Quantity: {quantity} {availability_metadata.get('unit_type', 'unit')}(s)\n"
                f"Order ID: {order_id}\n\n"
            )
            
            if dosage_warning:
                workflow_result["message"] += f"⚠️ {dosage_warning}\n\n"
            
            if deduct_metadata.get("warehouse_triggered"):
                workflow_result["message"] += (
                    f"📦 Low stock alert: Automatic warehouse order initiated\n"
                )
            
            # Step 7: Trigger Predictive Agent (async simulation)
            # In production, this would be a background task
            self._check_refill_prediction(user_id, medicine_name)
            
            return workflow_result
            
        except Exception as e:
            workflow_result["status"] = "error"
            workflow_result["message"] = f"System error: {str(e)}"
            
            self._log_agent_action(
                agent_name="OrchestratorAgent",
                action="process_order",
                input_data={"user_id": user_id, "message": message},
                output_data={"error": str(e)},
                decision_reason=f"Workflow failed with error: {str(e)}"
            )
            
            return workflow_result
    
    def _check_refill_prediction(self, user_id: str, medicine_name: str):
        """Check if user needs refill alert for this medicine."""
        
        prediction = self.predictive_agent.check_user_medicine(user_id, medicine_name)
        
        if prediction:
            self._log_agent_action(
                agent_name="PredictiveAgent",
                action="check_refill",
                input_data={"user_id": user_id, "medicine_name": medicine_name},
                output_data=prediction,
                decision_reason=f"Refill prediction: {prediction['days_remaining']} days remaining"
            )
    
    def _log_agent_action(self, agent_name: str, action: str, input_data: Dict, 
                          output_data: Dict, decision_reason: str):
        """Log agent action to trace logger."""
        
        if self.trace_logger:
            self.trace_logger.log_trace(
                trace_id=self.current_trace_id,
                agent_name=agent_name,
                action=action,
                input_data=input_data,
                output_data=output_data,
                decision_reason=decision_reason
            )
    
    def get_refill_alerts(self, user_id: str = None) -> List[Dict]:
        """Get proactive refill alerts."""
        
        alerts = self.predictive_agent.predict_refill_needs(user_id)
        
        # Log this prediction run
        self._log_agent_action(
            agent_name="PredictiveAgent",
            action="generate_refill_alerts",
            input_data={"user_id": user_id or "all"},
            output_data={"alert_count": len(alerts)},
            decision_reason=f"Generated {len(alerts)} refill alerts"
        )
        
        return alerts
