"""
Order Execution Agent: Auto-Order Creation from Prescriptions
Automatically creates orders based on validated prescription data.
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Add parent directory to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from database import Database
from agents.orchestrator_agent import OrchestratorAgent


class OrderExecutionAgent:
    """
    Executes automatic order creation from validated prescriptions.
    Integrates with existing order pipeline.
    """
    
    def __init__(self, orchestrator: OrchestratorAgent = None):
        self.orchestrator = orchestrator or OrchestratorAgent(use_ollama=False)
    
    def execute_prescription_orders(self, user_id: str, validated_medicines: List[Dict],
                                   prescription_id: str) -> Tuple[bool, List[Dict], str]:
        """
        Execute orders for all medicines in prescription.
        
        Args:
            user_id: User ID
            validated_medicines: List of validated medicine dictionaries
            prescription_id: Prescription ID for tracking
        
        Returns:
            Tuple of (success, order_results, summary_message)
        """
        
        if not validated_medicines:
            return False, [], "No medicines to order"
        
        order_results = []
        successful_orders = []
        failed_orders = []
        
        for medicine in validated_medicines:
            medicine_name = medicine['medicine_name']
            quantity = medicine['quantity_calculated']
            dosage_per_day = medicine.get('frequency_per_day', 1)
            
            # Create order message
            order_message = (
                f"Prescription order ({prescription_id}): {medicine_name}, "
                f"{quantity} {medicine.get('unit_type', 'unit')}(s)"
            )
            
            try:
                # Use existing orchestrator to process order
                result = self.orchestrator.process_order(user_id, order_message)
                
                order_info = {
                    "medicine_name": medicine_name,
                    "quantity": quantity,
                    "dosage_per_day": dosage_per_day,
                    "order_id": result.get('order_id'),
                    "status": result['status'],
                    "message": result['message'],
                    "prescription_id": prescription_id
                }
                
                order_results.append(order_info)
                
                if result['status'] == 'success':
                    successful_orders.append(medicine_name)
                else:
                    failed_orders.append(f"{medicine_name}: {result['message']}")
            
            except Exception as e:
                order_info = {
                    "medicine_name": medicine_name,
                    "quantity": quantity,
                    "status": "error",
                    "message": str(e)
                }
                order_results.append(order_info)
                failed_orders.append(f"{medicine_name}: {str(e)}")
        
        # Generate summary
        if failed_orders:
            success = False
            summary = (
                f"Partial success: {len(successful_orders)}/{len(validated_medicines)} orders placed.\n"
                f"Failed: {'; '.join(failed_orders)}"
            )
        else:
            success = True
            summary = (
                f"✅ All orders placed successfully!\n"
                f"{len(successful_orders)} medicine(s) ordered from prescription {prescription_id}"
            )
        
        return success, order_results, summary
    
    def get_decision_reason(self, success: bool, order_results: List[Dict]) -> str:
        """Generate decision reasoning for observability."""
        
        total = len(order_results)
        successful = sum(1 for r in order_results if r['status'] == 'success')
        
        if success:
            return (
                f"Prescription orders executed successfully: {successful}/{total} orders placed "
                f"(medicines: {', '.join(r['medicine_name'] for r in order_results if r['status'] == 'success')})"
            )
        else:
            failed = total - successful
            return (
                f"Prescription order execution partial: {successful} succeeded, {failed} failed"
            )
