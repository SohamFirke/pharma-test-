"""
Safety & Policy Agent: Prescription Validation
Deterministic rule-based validation for medicine safety.
NO probabilistic LLM decisions for safety-critical operations.
"""

import sys
from pathlib import Path
from typing import Dict, Tuple

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

from database import Database


class SafetyAgent:
    """
    Validates medicine orders against prescription requirements.
    Uses deterministic rule-based logic only.
    """
    
    def __init__(self):
        self.prescription_override = False  # For testing/demo purposes
    
    def validate_order(self, medicine_name: str, user_id: str = None) -> Tuple[bool, str, Dict]:
        """
        Validate if an order can be fulfilled based on prescription requirements.
        
        Args:
            medicine_name: Name of the medicine to validate
            user_id: User ID (for potential prescription record lookup)
        
        Returns:
            Tuple of (is_valid, reason, metadata)
            - is_valid: Boolean indicating if order is approved
            - reason: Human-readable explanation
            - metadata: Additional context for logging
        """
        
        # Get medicine details
        medicine = Database.get_medicine(medicine_name)
        
        if not medicine:
            return False, f"Medicine '{medicine_name}' not found in database", {
                "error": "medicine_not_found",
                "searched_name": medicine_name
            }
        
        prescription_required = medicine['prescription_required']
        
        metadata = {
            "medicine_name": medicine['medicine_name'],
            "prescription_required": prescription_required,
            "unit_type": medicine['unit_type']
        }
        
        # Rule: If prescription required, reject (unless override for demo)
        if prescription_required and not self.prescription_override:
            reason = (
                f"PRESCRIPTION REQUIRED: {medicine['medicine_name']} is a prescription "
                f"medicine. Please provide a valid prescription or consult with a pharmacist."
            )
            metadata["rejection_reason"] = "prescription_required"
            return False, reason, metadata
        
        # Rule: Non-prescription medicines are automatically approved
        reason = f"Order approved: {medicine['medicine_name']} does not require a prescription"
        metadata["approval_reason"] = "non_prescription_medicine"
        
        return True, reason, metadata
    
    def check_dosage_safety(self, medicine_name: str, dosage_per_day: int) -> Tuple[bool, str]:
        """
        Check if dosage is within safe limits.
        This is a simplified version - real implementation would have dosage limits per medicine.
        
        Args:
            medicine_name: Name of the medicine
            dosage_per_day: Number of units per day
        
        Returns:
            Tuple of (is_safe, warning_message)
        """
        
        # Simplified safety rules
        # In production, this would check against medicine-specific max daily dosages
        
        if dosage_per_day <= 0:
            return False, f"ERROR: Dosage must be at least 1 unit per day."

        if dosage_per_day > 10:
            return False, f"WARNING: Dosage of {dosage_per_day} units/day exceeds typical safe limits. Please consult a doctor."
        
        if dosage_per_day > 6:
            return True, f"NOTICE: High dosage ({dosage_per_day} units/day). Ensure this matches your prescription."
        
        return True, ""
    
    def get_decision_reason(self, is_valid: bool, reason: str, metadata: Dict) -> str:
        """Generate detailed decision reasoning for observability."""
        
        if not is_valid:
            if metadata.get("error") == "medicine_not_found":
                return f"REJECTED: Medicine not found in database (searched: {metadata.get('searched_name')})"
            elif metadata.get("rejection_reason") == "prescription_required":
                return f"REJECTED: {metadata.get('medicine_name')} requires prescription (deterministic rule)"
        else:
            return f"APPROVED: {metadata.get('medicine_name')} - {metadata.get('approval_reason')}"
        
        return reason
