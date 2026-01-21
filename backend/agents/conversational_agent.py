"""
Conversational Agent: Natural Language Understanding
Converts messy human text into structured intent using local LLM (Ollama) with regex fallback.
"""

import re
import json
from typing import Dict, Optional, Any
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

from database import Database


class ConversationalAgent:
    """
    Extracts structured intent from natural language input.
    Uses hybrid approach: Ollama LLM + regex patterns.
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
    
    def extract_intent(self, message: str, user_id: str = None) -> Dict[str, Any]:
        """
        Main entry point: extract intent from user message.
        
        Returns:
            {
                "medicine_name": str,
                "quantity": int,
                "dosage_per_day": int,
                "extraction_method": "ollama" | "regex",
                "confidence": float,
                "raw_message": str
            }
        """
        # Try Ollama first if available
        if self.ollama_available:
            try:
                result = self._extract_with_ollama(message, user_id)
                if result and result.get("medicine_name"):
                    result["extraction_method"] = "ollama"
                    return result
            except Exception as e:
                print(f"Ollama extraction failed: {e}, falling back to regex")
        
        # Fallback to regex
        result = self._extract_with_regex(message, user_id)
        result["extraction_method"] = "regex"
        return result
    
    def _extract_with_ollama(self, message: str, user_id: str = None) -> Optional[Dict]:
        """Extract intent using Ollama local LLM."""
        
        # Get user context if available
        context = ""
        if user_id:
            history = Database.get_user_history(user_id)
            if history:
                recent_medicines = [h['medicine_name'] for h in history[-3:]]
                context = f"\nUser's recent medicines: {', '.join(recent_medicines)}"
        
        prompt = f"""You are a pharmacy assistant. Extract medicine order details from the user's message.

User message: "{message}"{context}

Extract the following information as JSON:
- medicine_name: The name of the medicine (use common names, abbreviations like "BP tablets" should be expanded to likely medicine like "Lisinopril" or kept as mentioned)
- quantity: Number of units requested (tablets, capsules, ml, etc.)
- dosage_per_day: How many units per day (default to 1 if not specified)

If the user mentions "refill" or "again", use context from their history.
If quantity is mentioned as "30 days worth" with dosage 2 per day, calculate quantity as 60.

Respond ONLY with valid JSON, no additional text:
{{"medicine_name": "...", "quantity": ..., "dosage_per_day": ...}}"""

        try:
            response = self.ollama_client.chat(
                model='llama3.2',  # or 'mistral', 'phi3'
                messages=[{'role': 'user', 'content': prompt}],
                stream=False
            )
            
            # Parse response
            content = response['message']['content'].strip()
            
            # Extract JSON from response (handle cases where LLM adds extra text)
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                result["confidence"] = 0.9
                result["raw_message"] = message
                return result
            
        except Exception as e:
            print(f"Ollama error: {e}")
            return None
    
    def _extract_with_regex(self, message: str, user_id: str = None) -> Dict:
        """
        Extract intent using regex patterns and heuristics.
        Fallback method when Ollama is unavailable.
        """
        
        message_lower = message.lower()
        
        # Initialize result
        result = {
            "medicine_name": None,
            "quantity": 1,
            "dosage_per_day": 1,
            "confidence": 0.5,
            "raw_message": message
        }
        
        # Pattern 1: Extract quantity
        quantity_patterns = [
            r'(\d+)\s*(?:tablets?|capsules?|pills?|units?)',
            r'(\d+)\s*(?:of|x)',
            r'quantity[:\s]+(\d+)',
            r'(\d+)\s*days?\s*worth'
        ]
        
        for pattern in quantity_patterns:
            match = re.search(pattern, message_lower)
            if match:
                result["quantity"] = int(match.group(1))
                break
        
        # Pattern 2: Extract dosage per day
        dosage_patterns = [
            r'(\d+)\s*(?:per day|daily|times a day|times daily)',
            r'(\d+)\s*(?:times?|x)\s*(?:per day|daily)',
            r'dosage[:\s]+(\d+)'
        ]
        
        for pattern in dosage_patterns:
            match = re.search(pattern, message_lower)
            if match:
                result["dosage_per_day"] = int(match.group(1))
                break
        
        # Pattern 3: Extract medicine name
        # First check for refill/again keywords
        if any(word in message_lower for word in ['refill', 'again', 'same', 'usual']):
            if user_id:
                history = Database.get_user_history(user_id)
                if history:
                    # Get most recent medicine
                    result["medicine_name"] = history[-1]['medicine_name']
                    result["confidence"] = 0.7
                    # Ensure integers
                    result["quantity"] = int(result["quantity"])
                    result["dosage_per_day"] = int(result["dosage_per_day"])
                    return result
        
        # Try to match exact medicine names from database first
        # Sort by length descending to match longest names first (e.g., "Paracetamol Extra" before "Paracetamol")
        all_medicines = Database.load_medicine_master()['medicine_name'].tolist()
        all_medicines.sort(key=len, reverse=True)
        
        for medicine in all_medicines:
            if medicine.lower() in message_lower:
                result["medicine_name"] = medicine
                result["confidence"] = 0.8
                # Ensure integers
                result["quantity"] = int(result["quantity"])
                result["dosage_per_day"] = int(result["dosage_per_day"])
                return result
        
        # Try partial/fuzzy matching
        # Clean message: remove extra punctuation and common words
        cleaned_message = message.lower()
        cleaned_message = re.sub(r'\s*,\s*', ' ', cleaned_message)  # Replace commas with spaces
        cleaned_message = re.sub(r'\s+', ' ', cleaned_message)  # Normalize spaces
        
        # Remove numbers and common phrases from the cleaned message to extract medicine name
        # Extract words that could be medicine names
        words = cleaned_message.split()
        
        # Common words to skip
        skip_words = {
            'i', 'me', 'my', 'the', 'a', 'an', 'some', 'need', 'want', 'order', 
            'buy', 'get', 'please', 'for', 'of', 'to', 'in', 'on', 'at',
            'days', 'day', 'tablets', 'tablet', 'capsules', 'capsule', 'pills', 'pill',
            'worth', 'again', 'and', 'or'
        }
        
        # Find potential medicine names (skip common words and numbers)
        potential_names = []
        for word in words:
            # Clean the word of punctuation
            word = word.strip('.,!?')
            # Skip if it's a number, too short, or a skip word
            if word and not word.isdigit() and len(word) > 2 and word not in skip_words:
                potential_names.append(word)
        
        # Try each potential name with fuzzy matching
        for potential_name in potential_names:
            matches = Database.search_medicine_fuzzy(potential_name)
            if matches:
                result["medicine_name"] = matches[0]
                result["confidence"] = 0.6
                # Ensure integers
                result["quantity"] = int(result["quantity"])
                result["dosage_per_day"] = int(result["dosage_per_day"])
                return result
        
        # If we found potential names but no matches, use the first one
        if potential_names:
            result["medicine_name"] = potential_names[0].capitalize()
            result["confidence"] = 0.3
            # Ensure integers
            result["quantity"] = int(result["quantity"])
            result["dosage_per_day"] = int(result["dosage_per_day"])
            return result
        
        # No medicine name found
        result["medicine_name"] = None
        result["confidence"] = 0.0
        result["quantity"] = int(result["quantity"])
        result["dosage_per_day"] = int(result["dosage_per_day"])
        
        return result
    
    def get_decision_reason(self, intent: Dict) -> str:
        """Generate human-readable explanation of extraction."""
        method = intent.get("extraction_method", "unknown")
        confidence = intent.get("confidence", 0.0)
        
        if method == "ollama":
            return f"Extracted using local LLM (Ollama) with {confidence:.0%} confidence"
        elif method == "regex":
            return f"Extracted using regex patterns with {confidence:.0%} confidence"
        else:
            return "Extraction method unknown"
