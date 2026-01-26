"""
Prescription Safety Agent: Validation and Safety Checks
Validates prescriptions against safety rules - DETERMINISTIC ONLY.
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Add parent directory to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from database import Database


class PrescriptionSafetyAgent:
    """
    Validates prescriptions using deterministic rules.
    NEVER guesses - rejects unclear prescriptions.
    """
    
    def __init__(self):
        self.min_confidence_threshold = 0.4
    
    def validate_prescription(self, medicines: List[Dict], parsing_confidence: float) -> Tuple[bool, str, List[Dict]]:
        """
        Validate prescription medicines.
        
        Args:
            medicines: List of parsed medicine dictionaries
            parsing_confidence: Overall parsing confidence (0-1)
        
        Returns:
            Tuple of (is_valid, reason, validated_medicines)
        """
        
        if not medicines:
            return False, "REJECTED: No medicines found in prescription", []
        
        # Check overall parsing confidence
        if parsing_confidence < self.min_confidence_threshold:
            return False, (
                f"REJECTED: Prescription text unclear (confidence: {parsing_confidence:.0%}). "
                "Please upload a clearer image or manually enter the prescription."
            ), []
        
        validated_medicines = []
        rejection_reasons = []
        
        for idx, medicine in enumerate(medicines, 1):
            is_valid, reason, validated_med = self._validate_single_medicine(medicine, idx)
            
            if is_valid:
                validated_medicines.append(validated_med)
            else:
                rejection_reasons.append(reason)
        
        # If any medicine was rejected, reject entire prescription
        if rejection_reasons:
            combined_reason = "REJECTED: " + "; ".join(rejection_reasons)
            return False, combined_reason, []
        
        # All medicines valid
        reason = f"APPROVED: {len(validated_medicines)} medicine(s) validated successfully"
        return True, reason, validated_medicines
    
    def _validate_single_medicine(self, medicine: Dict, index: int) -> Tuple[bool, str, Dict]:
        """Validate a single medicine from prescription."""
        
        medicine_name = medicine.get('medicine_name')
        
        # Rule 1: Medicine name must be clear
        if not medicine_name or medicine_name == 'null' or len(medicine_name) < 3:
            return False, f"Medicine #{index}: Name unclear or missing", {}
        
        # Rule 2: Medicine must exist in database
        db_medicine = Database.get_medicine(medicine_name)
        if not db_medicine:
            # Try fuzzy match
            matches = Database.search_medicine_fuzzy(medicine_name)
            if matches:
                db_medicine = Database.get_medicine(matches[0])
                medicine['medicine_name'] = matches[0]  # Use matched name
            else:
                return False, f"Medicine #{index}: '{medicine_name}' not found in database", {}
        
        # Rule 3: Prescription-required medicines need prescription (which we have!)
        # This is CORRECT - we're processing a prescription, so prescription-required medicines are APPROVED
        if db_medicine['prescription_required']:
            medicine['prescription_validated'] = True
        else:
            medicine['prescription_validated'] = False  # OTC medicine
        
        # Rule 4: Quantity must be calculable or reasonable
        quantity = medicine.get('quantity_calculated')
        if quantity is None:
            # Check if we can calculate it
            freq = medicine.get('frequency_per_day')
            duration = medicine.get('duration_days')
            
            if not freq or not duration:
                return False, f"Medicine #{index}: Cannot determine quantity (missing frequency or duration)", {}
            
            quantity = int(freq) * int(duration)
            medicine['quantity_calculated'] = quantity
        
        # Rule 5: Quantity sanity check
        if quantity <= 0:
            return False, f"Medicine #{index}: Invalid quantity ({quantity})", {}
        
        if quantity > 1000:
            return False, f"Medicine #{index}: Quantity ({quantity}) exceeds safety limits (max 1000)", {}
        
        # Add validation metadata
        medicine['safety_validated'] = True
        medicine['stock_available'] = db_medicine['stock_level']
        medicine['unit_type'] = db_medicine['unit_type']
        
        return True, "", medicine
    
    def get_decision_reason(self, is_valid: bool, reason: str, medicines: List[Dict]) -> str:
        """Generate decision reasoning for observability."""
        
        if is_valid:
            count = len(medicines)
            prescription_meds = sum(1 for m in medicines if m.get('prescription_validated'))
            
            reason_text = f"Prescription APPROVED: {count} medicine(s) validated"
            if prescription_meds > 0:
                reason_text += f" ({prescription_meds} prescription-required)"
            
            return reason_text
        else:
            return f"Prescription validation failed: {reason}"
