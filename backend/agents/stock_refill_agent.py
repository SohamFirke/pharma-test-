"""
Stock Refill Agent: Rule-Based Inventory Monitoring & Refill Management

Monitors stock levels using deterministic threshold checks.
AI assists with orchestration only - does NOT make stocking decisions.
All alerts are generated via rule-based threshold comparison.
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta
import pandas as pd
import json

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

from database import Database


class StockRefillAgent:
    """
    Monitors inventory using rule-based thresholds and manages stock refill operations.
    
    Decision Authority: MONITORING ONLY
    - Uses deterministic threshold comparison (NOT AI prediction)
    - Generates alerts when stock < configured threshold
    - AI assists with orchestration (not decision-making)
    - Admin configures thresholds in medicine_master.csv
    
    Features:
    - Auto-detect low stock via threshold checks
    - Generate refill alerts with reasoning
    - Track refill history
    - Prevent duplicate/spam refills
    - Calculate suggested refill quantities (based on threshold)
    """
    
    def __init__(self):
        self.data_path = Path(__file__).resolve().parent.parent.parent / "data"
        self.refill_logs_path = self.data_path / "refill_logs.csv"
        self.alerts_path = self.data_path / "refill_alerts.json"
        
        # Initialize data files if they don't exist
        self._initialize_data_files()
        
        # Refill cooldown (prevent rapid refills for same medicine)
        self.refill_cooldown_minutes = 5
        
        # Max refill quantity multiplier
        self.max_refill_multiplier = 5
    
    def _initialize_data_files(self):
        """Create data files if they don't exist."""
        
        # Create refill logs CSV
        if not self.refill_logs_path.exists():
            refill_logs = pd.DataFrame(columns=[
                'timestamp', 'medicine_name', 'quantity_added', 
                'triggered_by', 'reason', 'admin_username', 'new_stock_level'
            ])
            refill_logs.to_csv(self.refill_logs_path, index=False)
        
        # Create alerts JSON
        if not self.alerts_path.exists():
            with open(self.alerts_path, 'w') as f:
                json.dump([], f)
    
    def monitor_inventory(self) -> List[Dict[str, Any]]:
        """
        Monitor all medicines and generate refill alerts for low stock.
        Uses rule-based threshold comparison (NOT AI prediction).
        
        Returns:
            List of refill alerts (generated via deterministic threshold checks)
        """
        alerts = []
        
        try:
            # Load medicine master
            medicines_df = Database.load_medicine_master()
            
            for _, medicine in medicines_df.iterrows():
                medicine_name = medicine['medicine_name']
                current_stock = medicine['stock_level']
                threshold = medicine.get('stock_threshold', 50)  # Default threshold
                
                # Check if stock is below threshold
                if current_stock < threshold:
                    # Calculate suggested refill quantity
                    suggested_quantity = self._calculate_refill_quantity(
                        current_stock, threshold
                    )
                    
                    # Determine severity
                    if current_stock < threshold / 2:
                        severity = "CRITICAL"
                    elif current_stock < threshold:
                        severity = "LOW"
                    else:
                        severity = "OK"
                    
                    alert = {
                        "medicine_name": medicine_name,
                        "current_stock": int(current_stock),
                        "threshold": int(threshold),
                        "suggested_quantity": int(suggested_quantity),
                        "severity": severity,
                        "reason": self._generate_alert_reason(current_stock, threshold, severity),
                        "timestamp": datetime.now().isoformat(),
                        "alert_id": f"alert_{medicine_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    }
                    
                    alerts.append(alert)
            
            # Save alerts to file
            self._save_alerts(alerts)
            
            return alerts
        
        except Exception as e:
            print(f"Inventory monitoring error: {e}")
            return []
    
    def _calculate_refill_quantity(self, current_stock: int, threshold: int) -> int:
        """Calculate suggested refill quantity using deterministic formula."""
        # Refill to 2x threshold for safety margin (rule-based calculation)
        deficit = threshold - current_stock
        safety_margin = threshold
        return deficit + safety_margin
    
    def _generate_alert_reason(self, current_stock: int, threshold: int, severity: str) -> str:
        """Generate human-readable alert reason."""
        if severity == "CRITICAL":
            return f"CRITICAL: Stock ({current_stock}) is less than 50% of threshold ({threshold}). Immediate refill recommended."
        elif severity == "LOW":
            return f"LOW STOCK: Current stock ({current_stock}) below threshold ({threshold}). Refill recommended."
        else:
            return f"Stock level ({current_stock}) approaching threshold ({threshold})."
    
    def _save_alerts(self, alerts: List[Dict]):
        """Save alerts to JSON file."""
        try:
            with open(self.alerts_path, 'w') as f:
                json.dump(alerts, f, indent=2)
        except Exception as e:
            print(f"Error saving alerts: {e}")
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """
        Get currently active refill alerts.
        
        Returns:
            List of active alerts
        """
        try:
            if self.alerts_path.exists():
                with open(self.alerts_path, 'r') as f:
                    alerts = json.load(f)
                return alerts
            return []
        except Exception as e:
            print(f"Error loading alerts: {e}")
            return []
    
    def execute_refill(
        self, 
        medicine_name: str, 
        quantity: int, 
        triggered_by: str,
        admin_username: str = "system",
        reason: str = ""
    ) -> Tuple[bool, str, Dict]:
        """
        Execute stock refill operation.
        
        Args:
            medicine_name: Medicine to refill
            quantity: Quantity to add
            triggered_by: "ADMIN" (manual) or "SYSTEM" (rule-based alert)
            admin_username: Username of admin (if manual)
            reason: Reason for refill
        
        Returns:
            (success, message, refill_data)
        """
        
        # Validate refill request
        is_valid, validation_msg = self._validate_refill(medicine_name, quantity)
        if not is_valid:
            return False, validation_msg, {}
        
        try:
            # Get current medicine info
            medicine = Database.get_medicine(medicine_name)
            if not medicine:
                return False, f"Medicine '{medicine_name}' not found", {}
            
            current_stock = medicine.get('stock_level', 0)
            
            # Update stock level
            new_stock = current_stock + quantity
            success = Database.update_stock(medicine_name, new_stock)
            
            if not success:
                return False, "Failed to update stock in database", {}
            
            # Log refill action
            refill_data = {
                "timestamp": datetime.now().isoformat(),
                "medicine_name": medicine_name,
                "quantity_added": quantity,
                "triggered_by": triggered_by,
                "reason": reason,
                "admin_username": admin_username,
                "new_stock_level": new_stock,
                "previous_stock": current_stock
            }
            
            self._log_refill(refill_data)
            
            return True, f"Refill successful. Stock updated from {current_stock} to {new_stock}", refill_data
        
        except Exception as e:
            return False, f"Refill execution error: {str(e)}", {}
    
    def _validate_refill(self, medicine_name: str, quantity: int) -> Tuple[bool, str]:
        """
        Validate refill request for safety.
        
        Returns:
            (is_valid, reason)
        """
        # Check medicine exists
        medicine = Database.get_medicine(medicine_name)
        if not medicine:
            return False, f"Medicine '{medicine_name}' not found in database"
        
        # Check quantity is positive
        if quantity <= 0:
            return False, "Quantity must be greater than 0"
        
        # Check quantity not excessive
        threshold = medicine.get('stock_threshold', 50)
        max_quantity = threshold * self.max_refill_multiplier
        if quantity > max_quantity:
            return False, f"Quantity ({quantity}) exceeds maximum allowed ({max_quantity})"
        
        # Check cooldown period
        if self._refill_in_cooldown(medicine_name):
            return False, f"Cooldown period active. Please wait {self.refill_cooldown_minutes} minutes between refills"
        
        return True, "Valid"
    
    def _refill_in_cooldown(self, medicine_name: str) -> bool:
        """Check if medicine is in refill cooldown period."""
        try:
            refill_logs = pd.read_csv(self.refill_logs_path)
            
            if refill_logs.empty:
                return False
            
            # Get last refill for this medicine
            medicine_refills = refill_logs[refill_logs['medicine_name'] == medicine_name]
            
            if medicine_refills.empty:
                return False
            
            last_refill_time = pd.to_datetime(medicine_refills.iloc[-1]['timestamp'])
            time_since_refill = datetime.now() - last_refill_time
            
            return time_since_refill < timedelta(minutes=self.refill_cooldown_minutes)
        
        except Exception as e:
            print(f"Cooldown check error: {e}")
            return False
    
    def _log_refill(self, refill_data: Dict):
        """Log refill action to CSV."""
        try:
            # Load existing logs
            refill_logs = pd.read_csv(self.refill_logs_path)
            
            # Append new log
            new_log = pd.DataFrame([refill_data])
            refill_logs = pd.concat([refill_logs, new_log], ignore_index=True)
            
            # Save
            refill_logs.to_csv(self.refill_logs_path, index=False)
        
        except Exception as e:
            print(f"Error logging refill: {e}")
    
    def get_refill_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get refill history.
        
        Args:
            limit: Maximum number of records to return
        
        Returns:
            List of refill log entries
        """
        try:
            refill_logs = pd.read_csv(self.refill_logs_path)
            
            if refill_logs.empty:
                return []
            
            # Sort by timestamp descending
            refill_logs = refill_logs.sort_values('timestamp', ascending=False)
            
            # Limit results
            refill_logs = refill_logs.head(limit)
            
            return refill_logs.to_dict('records')
        
        except Exception as e:
            print(f"Error loading refill history: {e}")
            return []
    
    def get_decision_reason(self, action: str, success: bool, data: Dict) -> str:
        """Generate human-readable decision reason for observability."""
        
        if action == "monitor_inventory":
            alert_count = len(data.get('alerts', []))
            return f"Rule-based inventory monitoring: {alert_count} alert(s) generated via threshold checks (AI-assisted orchestration)"
        
        elif action == "execute_refill":
            if success:
                medicine = data.get('medicine_name', 'Unknown')
                quantity = data.get('quantity_added', 0)
                triggered = data.get('triggered_by', 'Unknown')
                return f"Refill executed: Added {quantity} units of {medicine} (triggered by: {triggered})"
            else:
                return f"Refill failed: {data.get('error', 'Unknown error')}"
        
        return "Action completed"
