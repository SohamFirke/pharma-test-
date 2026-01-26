"""
Prescription Parsing Agent: Text to Structured Data
Converts raw OCR text into structured medicine prescription data.
"""

import re
import json
from typing import Dict, List, Optional, Any, Tuple
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from database import Database


class PrescriptionParsingAgent:
    """
    Parses prescription text to extract medicine details.
    Uses hybrid approach: Ollama LLM + regex fallback.
    """
    
    def __init__(self, use_ollama: bool = True):
        self.use_ollama = use_ollama
        self.ollama_available = False
        
        if use_ollama:
            try:
                import ollama
                self.ollama_client = ollama
                self.ollama_available = True
            except ImportError:
                print("Warning: Ollama not available, using regex fallback")
                self.ollama_available = False
    
    def parse_prescription(self, raw_text: str) -> Tuple[bool, List[Dict], Dict]:
        """
        Parse prescription text to extract medicine details.
        
        Args:
            raw_text: Raw OCR extracted text
        
        Returns:
            Tuple of (success, medicines_list, metadata)
        """
        
        if not raw_text or len(raw_text.strip()) < 10:
            return False, [], {"error": "Text too short or empty"}
        
        # Try Ollama first
        if self.ollama_available:
            try:
                success, medicines, metadata = self._parse_with_ollama(raw_text)
                if success and medicines:
                    return success, medicines, metadata
            except Exception as e:
                print(f"Ollama parsing failed: {e}, falling back to regex")
        
        # Fallback to regex
        return self._parse_with_regex(raw_text)
    
    def _parse_with_ollama(self, raw_text: str) -> Tuple[bool, List[Dict], Dict]:
        """Parse using Ollama local LLM."""
        
        prompt = f"""You are a prescription parser. Extract medicine details from this prescription text.

Prescription Text:
{raw_text}

Extract ONLY medicines with clear details. Output valid JSON with this exact structure:
{{
  "medicines": [
    {{
      "medicine_name": "exact name",
      "dosage": "500mg",
      "frequency_per_day": 2,
      "duration_days": 7
    }}
  ]
}}

Rules:
- If medicine name is unclear, set to null
- frequency_per_day must be a number (e.g., "2 times daily" = 2)
- duration_days should be total days (e.g., "7 days" = 7)
- If "as needed" or unclear duration, set duration_days to null

Respond ONLY with valid JSON, no additional text."""

        try:
            response = self.ollama_client.chat(
                model='llama3.2',
                messages=[{'role': 'user', 'content': prompt}],
                stream=False
            )
            
            content = response['message']['content'].strip()
            
            # Extract JSON
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                medicines = result.get('medicines', [])
                
                # Calculate quantities and validate
                validated_medicines = []
                for med in medicines:
                    if med.get('medicine_name') and med.get('medicine_name') != 'null':
                        # Calculate quantity
                        freq = med.get('frequency_per_day', 1)
                        duration = med.get('duration_days')
                        
                        if freq and duration:
                            med['quantity_calculated'] = int(freq) * int(duration)
                        else:
                            med['quantity_calculated'] = None
                        
                        validated_medicines.append(med)
                
                metadata = {
                    "method": "ollama_llm",
                    "confidence": 0.8,
                    "medicines_found": len(validated_medicines)
                }
                
                return True, validated_medicines, metadata
        
        except Exception as e:
            print(f"Ollama parsing error: {e}")
            return False, [], {"error": str(e)}
        
        return False, [], {"error": "No medicines extracted"}
    
    def _parse_with_regex(self, raw_text: str) -> Tuple[bool, List[Dict], Dict]:
        """Parse using regex patterns - fallback method."""
        
        medicines = []
        lines = raw_text.split('\n')
        
        # Common prescription patterns
        medicine_pattern = r'(?:Rx:|Tab\.|Cap\.|Syrup)\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)'
        dosage_pattern = r'(\d+\s*mg)'
        frequency_pattern = r'(\d+)\s*(?:times?|x)\s*(?:daily|per day|a day)'
        duration_pattern = r'(?:for\s+)?(\d+)\s*days?'
        
        current_medicine = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Try to find medicine name
            med_match = re.search(medicine_pattern, line, re.IGNORECASE)
            if med_match:
                if current_medicine:
                    medicines.append(current_medicine)
                
                current_medicine = {
                    "medicine_name": med_match.group(1).strip(),
                    "dosage": None,
                    "frequency_per_day": 1,
                    "duration_days": None,
                    "quantity_calculated": None
                }
            
            if current_medicine:
                # Extract dosage
                dosage_match = re.search(dosage_pattern, line)
                if dosage_match:
                    current_medicine["dosage"] = dosage_match.group(1).strip()
                
                # Extract frequency
                freq_match = re.search(frequency_pattern, line)
                if freq_match:
                    current_medicine["frequency_per_day"] = int(freq_match.group(1))
                
                # Extract duration
                dur_match = re.search(duration_pattern, line)
                if dur_match:
                    current_medicine["duration_days"] = int(dur_match.group(1))
        
        # Add last medicine
        if current_medicine:
            medicines.append(current_medicine)
        
        # Calculate quantities and fuzzy match medicine names
        validated_medicines = []
        for med in medicines:
            # Try to match medicine name in database
            matches = Database.search_medicine_fuzzy(med['medicine_name'])
            if matches:
                med['medicine_name'] = matches[0]
                med['medicine_name_matched'] = True
            else:
                med['medicine_name_matched'] = False
            
            # Calculate quantity
            if med['frequency_per_day'] and med['duration_days']:
                med['quantity_calculated'] = med['frequency_per_day'] * med['duration_days']
            
            validated_medicines.append(med)
        
        metadata = {
            "method": "regex_patterns",
            "confidence": 0.5,
            "medicines_found": len(validated_medicines)
        }
        
        if not validated_medicines:
            return False, [], {"error": "No medicines found in text"}
        
        return True, validated_medicines, metadata
    
    def get_decision_reason(self, success: bool, medicines: List[Dict], metadata: Dict) -> str:
        """Generate decision reasoning for observability."""
        
        if success:
            method = metadata.get('method', 'unknown')
            count = metadata.get('medicines_found', 0)
            conf = metadata.get('confidence', 0)
            
            return (
                f"Prescription parsed using {method}: {count} medicine(s) extracted "
                f"with {conf:.0%} confidence"
            )
        else:
            return f"Prescription parsing failed: {metadata.get('error', 'unknown error')}"
