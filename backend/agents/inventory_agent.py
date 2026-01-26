"""
Inventory Agent: Stock Management
Handles inventory checking, stock deduction, and warehouse procurement triggers.
"""

import sys
from pathlib import Path
from typing import Dict, Tuple, Optional

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

from database import Database


class InventoryAgent:
    """
    Manages medicine inventory and triggers procurement when needed.
    """
    
    def __init__(self, low_stock_threshold: int = 50):
        self.low_stock_threshold = low_stock_threshold
        self.warehouse_webhook_url = "http://localhost:8000/webhook/warehouse"
    
    def check_availability(self, medicine_name: str, quantity: int) -> Tuple[bool, str, Dict]:
        """
        Check if sufficient stock is available.
        
        Returns:
            Tuple of (is_available, message, metadata)
        """
        
        # Ensure quantity is an integer
        quantity = int(quantity)
        
        medicine = Database.get_medicine(medicine_name)
        
        if not medicine:
            return False, f"Medicine '{medicine_name}' not found", {
                "error": "medicine_not_found"
            }
        
        current_stock = int(medicine['stock_level'])  # Explicit conversion
        
        metadata = {
            "medicine_name": medicine['medicine_name'],
            "current_stock": current_stock,
            "requested_quantity": quantity,
            "unit_type": medicine['unit_type']
        }
        
        if current_stock < quantity:
            message = (
                f"Insufficient stock: Only {current_stock} {medicine['unit_type']}(s) "
                f"available, but {quantity} requested"
            )
            metadata["shortage"] = quantity - current_stock
            return False, message, metadata
        
        message = f"Stock available: {current_stock} {medicine['unit_type']}(s) in inventory"
        return True, message, metadata
    
    def deduct_stock(self, medicine_name: str, quantity: int) -> Tuple[bool, str, Dict]:
        """
        Deduct stock after order confirmation.
        Triggers warehouse webhook if stock falls below threshold.
        
        Returns:
            Tuple of (success, message, metadata)
        """
        
        # Ensure quantity is an integer
        quantity = int(quantity)
        
        # Get current stock before deduction
        medicine = Database.get_medicine(medicine_name)
        if not medicine:
            return False, f"Medicine '{medicine_name}' not found", {}
        
        initial_stock = int(medicine['stock_level'])  # Explicit conversion
        
        # Deduct stock
        success = Database.update_stock(medicine_name, -quantity)
        
        if not success:
            return False, f"Failed to deduct stock for {medicine_name}", {
                "error": "stock_update_failed"
            }
        
        # Get updated stock
        updated_medicine = Database.get_medicine(medicine_name)
        new_stock = int(updated_medicine['stock_level'])  # Explicit conversion
        
        metadata = {
            "medicine_name": medicine_name,
            "initial_stock": initial_stock,
            "deducted": quantity,
            "new_stock": new_stock,
            "threshold": self.low_stock_threshold
        }
        
        # Check if warehouse procurement needed
        if new_stock < self.low_stock_threshold:
            procurement_triggered = self._trigger_warehouse_procurement(
                medicine_name, new_stock
            )
            metadata["warehouse_triggered"] = procurement_triggered
            metadata["procurement_quantity"] = self._calculate_procurement_quantity(new_stock)
        
        message = f"Stock deducted: {medicine_name} - {initial_stock} → {new_stock} {medicine['unit_type']}(s)"
        
        return True, message, metadata
    
    def _trigger_warehouse_procurement(self, medicine_name: str, current_stock: int) -> bool:
        """
        Trigger warehouse webhook for low stock items.
        In production, this would make actual HTTP request to warehouse system.
        """
        
        procurement_quantity = self._calculate_procurement_quantity(current_stock)
        
        # Mock webhook payload
        webhook_payload = {
            "medicine_name": medicine_name,
            "current_stock": current_stock,
            "requested_quantity": procurement_quantity,
            "priority": "high" if current_stock < 20 else "normal",
            "requester": "inventory_agent"
        }
        
        # In production, this would be:
        # import httpx
        # response = httpx.post(self.warehouse_webhook_url, json=webhook_payload)
        
        # For now, just log and return success
        print(f"[WAREHOUSE WEBHOOK] Procurement triggered: {webhook_payload}")
        
        return True
    
    def _calculate_procurement_quantity(self, current_stock: int) -> int:
        """
        Calculate how much to order from warehouse.
        Simple logic: order enough to reach 200 units.
        """
        target_stock = 200
        return max(100, target_stock - current_stock)
    
    def get_low_stock_items(self) -> list:
        """Get list of medicines with low stock."""
        return Database.get_low_stock_medicines(self.low_stock_threshold)
    
    def get_decision_reason(self, action: str, success: bool, metadata: Dict) -> str:
        """Generate decision reasoning for observability."""
        
        if action == "check_availability":
            if success:
                return (
                    f"Stock check PASSED: {metadata.get('current_stock')} units available "
                    f"for {metadata.get('requested_quantity')} requested"
                )
            else:
                return (
                    f"Stock check FAILED: Only {metadata.get('current_stock')} units available, "
                    f"shortage of {metadata.get('shortage')} units"
                )
        
        elif action == "deduct_stock":
            reason = (
                f"Stock deducted: {metadata.get('initial_stock')} → {metadata.get('new_stock')} "
                f"({metadata.get('deducted')} units)"
            )
            
            if metadata.get('warehouse_triggered'):
                reason += f" | WAREHOUSE TRIGGERED: Stock below threshold ({metadata.get('threshold')}), " \
                         f"requested {metadata.get('procurement_quantity')} units"
            
            return reason
        
        return "Unknown action"
