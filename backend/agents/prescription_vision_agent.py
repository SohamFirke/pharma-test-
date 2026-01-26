"""
Prescription Vision Agent: Image-based Prescription Reading
Uses LLaMA 3.2 Vision to extract medicine details from prescription images.
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import base64
import json
import re

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

from database import Database


class PrescriptionVisionAgent:
    """
    Reads prescription images using LLaMA 3.2 Vision model.
    Extracts medicine names, dosages, frequency, and duration.
    """
    
    def __init__(self):
        self.ollama_available = False
        self.vision_model = "llama3.2-vision"
        
        # Try to initialize Ollama
        try:
            import ollama
            self.ollama_client = ollama
            # Test if server is accessible
            try:
                self.ollama_client.list()
                self.ollama_available = True
                print("✓ Ollama available for vision processing")
            except Exception:
                print("⚠ Ollama server not responding")
                self.ollama_available = False
        except ImportError:
            print("⚠ Ollama not installed")
            self.ollama_available = False
    
    def extract_from_image(self, image_path: str) -> Tuple[bool, List[Dict], Dict]:
        """
        Extract medicine details from prescription image using vision model.
        
        Args:
            image_path: Path to prescription image file
        
        Returns:
            (success, medicines, metadata)
            - success: bool
            - medicines: List of extracted medicine dictionaries
            - metadata: Additional information about extraction
        """
        
        if not self.ollama_available:
            return False, [], {
                "error": "Vision model not available",
                "message": "Ollama server not running or vision model not installed"
            }
        
        try:
            # Read and encode image
            image_data = self._encode_image(image_path)
            if not image_data:
                return False, [], {"error": "Failed to read image file"}
            
            # Use vision model to extract prescription data
            success, extracted_text, confidence = self._vision_extract(image_data)
            
            if not success:
                return False, [], {
                    "error": "Vision extraction failed",
                    "raw_response": extracted_text
                }
            
            # Parse structured data from vision model output
            medicines = self._parse_vision_output(extracted_text)
            
            if not medicines:
                return False, [], {
                    "error": "No medicines found in prescription",
                    "extracted_text": extracted_text,
                    "confidence": confidence
                }
            
            # Validate extracted medicines against database
            validated_medicines = self._validate_medicines(medicines)
            
            return True, validated_medicines, {
                "confidence": confidence,
                "method": "vision_llama",
                "raw_extraction": extracted_text,
                "medicines_found": len(validated_medicines)
            }
        
        except Exception as e:
            return False, [], {
                "error": f"Vision processing error: {str(e)}"
            }
    
    def _encode_image(self, image_path: str) -> Optional[str]:
        """Encode image to base64 for Ollama vision API."""
        try:
            with open(image_path, 'rb') as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            print(f"Image encoding error: {e}")
            return None
    
    def _vision_extract(self, image_data: str) -> Tuple[bool, str, float]:
        """
        Use LLaMA 3.2 Vision to extract prescription details.
        
        Returns:
            (success, extracted_text, confidence)
        """
        try:
            prompt = """You are a medical prescription reader. Extract ALL medicine details from this prescription image.

For EACH medicine found, provide:
1. Medicine name (exact spelling)
2. Dosage (e.g., 500mg, 10ml)
3. Frequency per day (e.g., 2 times daily, 3x daily)
4. Duration in days (e.g., 7 days, 14 days)

Format your response as JSON array:
[
  {
    "medicine_name": "Medicine Name",
    "dosage": "500mg",
    "frequency_per_day": 2,
    "duration_days": 7
  }
]

If you cannot read certain details, use null for that field.
Return ONLY the JSON array, no explanatory text."""

            response = self.ollama_client.chat(
                model=self.vision_model,
                messages=[{
                    'role': 'user',
                    'content': prompt,
                    'images': [image_data]
                }]
            )
            
            content = response['message']['content'].strip()
            
            # Calculate confidence based on response quality
            confidence = 0.8 if content and len(content) > 20 else 0.3
            
            return True, content, confidence
        
        except Exception as e:
            print(f"Vision API error: {e}")
            return False, str(e), 0.0
    
    def _parse_vision_output(self, vision_text: str) -> List[Dict]:
        """Parse JSON output from vision model."""
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\[.*\]', vision_text, re.DOTALL)
            if json_match:
                medicines = json.loads(json_match.group())
                
                # Normalize format
                normalized = []
                for med in medicines:
                    if isinstance(med, dict) and 'medicine_name' in med:
                        # Ensure required fields
                        normalized.append({
                            "medicine_name": med.get('medicine_name', '').strip(),
                            "dosage": med.get('dosage', ''),
                            "frequency_per_day": int(med.get('frequency_per_day', 1)) if med.get('frequency_per_day') else 1,
                            "duration_days": int(med.get('duration_days', 7)) if med.get('duration_days') else 7
                        })
                
                return normalized
            
            return []
        
        except json.JSONDecodeError:
            print("Failed to parse JSON from vision output")
            return []
        except Exception as e:
            print(f"Parsing error: {e}")
            return []
    
    def _validate_medicines(self, medicines: List[Dict]) -> List[Dict]:
        """
        Validate extracted medicines against medicine database.
        Add validation flags and database information.
        """
        validated = []
        
        for med in medicines:
            med_name = med.get('medicine_name', '')
            if not med_name:
                continue
            
            # Check if medicine exists in database
            db_medicine = Database.get_medicine(med_name)
            
            if db_medicine:
                # Exact match found
                med['validation_status'] = 'exact_match'
                med['prescription_required'] = db_medicine.get('prescription_required', True)
                med['stock_level'] = db_medicine.get('stock_level', 0)
                med['unit_type'] = db_medicine.get('unit_type', 'unit')
            else:
                # Try fuzzy matching
                fuzzy_matches = Database.search_medicine_fuzzy(med_name)
                if fuzzy_matches:
                    suggested_name = fuzzy_matches[0]
                    db_medicine = Database.get_medicine(suggested_name)
                    
                    med['validation_status'] = 'fuzzy_match'
                    med['suggested_name'] = suggested_name
                    med['prescription_required'] = db_medicine.get('prescription_required', True)
                    med['stock_level'] = db_medicine.get('stock_level', 0)
                    med['unit_type'] = db_medicine.get('unit_type', 'unit')
                else:
                    # Not found in database
                    med['validation_status'] = 'not_found'
                    med['prescription_required'] = True  # Assume requires prescription if unknown
                    med['stock_level'] = 0
            
            # Calculate total quantity needed
            frequency = med.get('frequency_per_day', 1)
            duration = med.get('duration_days', 7)
            med['quantity_needed'] = frequency * duration
            
            validated.append(med)
        
        return validated
    
    def get_decision_reason(self, success: bool, medicines: List[Dict], metadata: Dict) -> str:
        """Generate human-readable explanation of vision extraction."""
        
        if not success:
            error = metadata.get('error', 'Unknown error')
            return f"Vision extraction failed: {error}"
        
        method = metadata.get('method', 'vision')
        confidence = metadata.get('confidence', 0.0)
        count = len(medicines)
        
        reason = f"Extracted {count} medicine(s) using {method} with {confidence:.0%} confidence. "
        
        # Add validation summary
        exact_matches = sum(1 for m in medicines if m.get('validation_status') == 'exact_match')
        fuzzy_matches = sum(1 for m in medicines if m.get('validation_status') == 'fuzzy_match')
        not_found = sum(1 for m in medicines if m.get('validation_status') == 'not_found')
        
        reason += f"Validation: {exact_matches} exact, {fuzzy_matches} fuzzy, {not_found} not found in database."
        
        return reason
