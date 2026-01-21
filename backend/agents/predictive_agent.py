"""
Predictive Intelligence Agent: Proactive Refill Prediction
Analyzes order history to predict when users need refills.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

from database import Database


class PredictiveAgent:
    """
    Predicts when users will run out of medicine and generates proactive refill alerts.
    """
    
    def __init__(self, alert_threshold_days: int = 3):
        """
        Args:
            alert_threshold_days: Trigger alert when medicine days remaining <= this value
        """
        self.alert_threshold_days = alert_threshold_days
    
    def predict_refill_needs(self, user_id: Optional[str] = None) -> List[Dict]:
        """
        Analyze order history and predict upcoming refill needs.
        
        Args:
            user_id: Specific user to analyze, or None for all users
        
        Returns:
            List of refill alerts with prediction details
        """
        
        order_history = Database.load_order_history()
        
        if user_id:
            order_history = order_history[order_history['user_id'] == user_id]
        
        alerts = []
        today = datetime.now()
        
        # Group by user and medicine
        grouped = order_history.groupby(['user_id', 'medicine_name'])
        
        for (uid, medicine), group in grouped:
            # Get most recent order
            most_recent = group.sort_values('purchase_date').iloc[-1]
            
            # Calculate days remaining
            prediction = self._calculate_days_remaining(most_recent, today)
            
            if prediction['days_remaining'] <= self.alert_threshold_days:
                alert = {
                    "user_id": uid,
                    "medicine_name": medicine,
                    "days_remaining": prediction['days_remaining'],
                    "last_purchase_date": most_recent['purchase_date'].isoformat(),
                    "last_quantity": int(most_recent['quantity']),
                    "dosage_per_day": int(most_recent['dosage_per_day']),
                    "predicted_runout_date": prediction['runout_date'].isoformat(),
                    "alert_priority": self._get_alert_priority(prediction['days_remaining']),
                    "recommended_action": self._get_recommended_action(prediction['days_remaining'])
                }
                alerts.append(alert)
        
        # Sort by urgency (lowest days remaining first)
        alerts.sort(key=lambda x: x['days_remaining'])
        
        return alerts
    
    def _calculate_days_remaining(self, order: Dict, current_date: datetime) -> Dict:
        """
        Calculate how many days of medicine remain for a user.
        
        Formula:
            total_days_supply = quantity / dosage_per_day
            days_elapsed = current_date - purchase_date
            days_remaining = total_days_supply - days_elapsed
        """
        
        quantity = order['quantity']
        dosage_per_day = order['dosage_per_day']
        purchase_date = order['purchase_date']
        
        # Total days the medicine should last
        total_days_supply = quantity / dosage_per_day
        
        # Days since purchase
        days_elapsed = (current_date - purchase_date).days
        
        # Days remaining
        days_remaining = total_days_supply - days_elapsed
        
        # Predicted runout date
        runout_date = purchase_date + timedelta(days=total_days_supply)
        
        return {
            "days_remaining": round(days_remaining, 1),
            "days_elapsed": days_elapsed,
            "total_days_supply": round(total_days_supply, 1),
            "runout_date": runout_date
        }
    
    def _get_alert_priority(self, days_remaining: float) -> str:
        """Determine alert priority based on days remaining."""
        if days_remaining <= 0:
            return "CRITICAL"
        elif days_remaining <= 1:
            return "HIGH"
        elif days_remaining <= 3:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _get_recommended_action(self, days_remaining: float) -> str:
        """Generate recommended action message."""
        if days_remaining <= 0:
            return "URGENT: Medicine supply depleted. Order immediately."
        elif days_remaining <= 1:
            return "Order refill today to avoid running out."
        elif days_remaining <= 3:
            return "Consider ordering refill soon."
        else:
            return "Monitor supply."
    
    def check_user_medicine(self, user_id: str, medicine_name: str) -> Optional[Dict]:
        """
        Check refill status for a specific user's medicine.
        
        Returns:
            Prediction details or None if no history found
        """
        
        history = Database.get_user_medicine_history(user_id, medicine_name)
        
        if not history:
            return None
        
        # Get most recent order
        most_recent = max(history, key=lambda x: x['purchase_date'])
        
        # Handle purchase_date - could be datetime object or string
        purchase_date = most_recent['purchase_date']
        if isinstance(purchase_date, str):
            purchase_date = datetime.fromisoformat(purchase_date)
        elif hasattr(purchase_date, 'to_pydatetime'):
            # Pandas Timestamp
            purchase_date = purchase_date.to_pydatetime()
        
        prediction = self._calculate_days_remaining({
            'quantity': int(most_recent['quantity']),
            'dosage_per_day': int(most_recent['dosage_per_day']),
            'purchase_date': purchase_date
        }, datetime.now())
        
        return {
            "user_id": user_id,
            "medicine_name": medicine_name,
            "days_remaining": prediction['days_remaining'],
            "runout_date": prediction['runout_date'].isoformat(),
            "needs_refill": prediction['days_remaining'] <= self.alert_threshold_days
        }
    
    def get_decision_reason(self, alert: Dict) -> str:
        """Generate decision reasoning for observability."""
        
        return (
            f"Predictive alert generated for {alert['user_id']} - {alert['medicine_name']}: "
            f"{alert['days_remaining']} days remaining "
            f"(purchased {alert['last_quantity']} units on {alert['last_purchase_date'][:10]}, "
            f"consuming {alert['dosage_per_day']}/day). "
            f"Priority: {alert['alert_priority']}"
        )
