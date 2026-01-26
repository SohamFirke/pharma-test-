"""
Symptom Analysis Agent: Safe OTC Medicine Recommendations
Provides over-the-counter medicine suggestions based on symptoms.
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

from database import Database


class SymptomAnalysisAgent:
    """
    Analyzes symptoms and provides informational OTC medicine recommendations.
    
    IMPORTANT LIMITATIONS:
    - This agent does NOT diagnose medical conditions
    - Provides informational content only (NOT MEDICAL ADVICE)
    - Uses deterministic symptom → medicine mapping (NO AI diagnosis)
    - Only recommends OTC medicines (prescription medicines excluded)
    - All responses include medical disclaimers
    """
    
    def __init__(self):
        self.data_path = Path(__file__).resolve().parent.parent.parent / "data"
        self.symptom_mapping_file = self.data_path / "symptom_medicine_mapping.csv"
        
        # Load symptom mapping
        self.symptom_db = self._load_symptom_mapping()
        
        # Common symptom keywords
        self.symptom_keywords = self._extract_symptom_keywords()
    
    def _load_symptom_mapping(self) -> pd.DataFrame:
        """Load symptom to medicine mapping database."""
        try:
            return pd.read_csv(self.symptom_mapping_file)
        except FileNotFoundError:
            print(f"Warning: Symptom mapping file not found at {self.symptom_mapping_file}")
            return pd.DataFrame(columns=['symptom', 'medicine_name', 'category', 'severity', 'disclaimer'])
    
    def _extract_symptom_keywords(self) -> List[str]:
        """Extract list of symptom keywords from database."""
        if self.symptom_db.empty:
            return []
        return self.symptom_db['symptom'].str.lower().unique().tolist()
    
    def analyze_and_recommend(self, message: str, user_id: str = None) -> Dict[str, Any]:
        """
        Analyze user message for symptoms and recommend OTC medicines.
        
        Args:
            message: User's symptom description
            user_id: Optional user identifier
        
        Returns:
            {
                "symptoms_detected": List[str],
                "recommendations": List[Dict],
                "disclaimer_shown": bool,
                "method": "mapping" | "none",
                "response": str (formatted response)
            }
        """
        message_lower = message.lower().strip()
        
        # Detect symptoms in message
        detected_symptoms = self._detect_symptoms(message_lower)
        
        if not detected_symptoms:
            return {
                "symptoms_detected": [],
                "recommendations": [],
                "disclaimer_shown": False,
                "method": "none",
                "response": (
                    "I couldn't identify specific symptoms in your message.\n\n"
                    "Please describe your symptoms clearly, for example:\n"
                    "• \"I have fever\"\n"
                    "• \"My head hurts\"\n"
                    "• \"Cold and cough\"\n\n"
                    "Or you can directly order a medicine if you know what you need."
                )
            }
        
        # Get recommendations for detected symptoms
        recommendations = self._get_recommendations(detected_symptoms)
        
        # Format response
        response = self._format_response(detected_symptoms, recommendations)
        
        return {
            "symptoms_detected": detected_symptoms,
            "recommendations": recommendations,
            "disclaimer_shown": True,
            "method": "mapping",
            "response": response
        }
    
    def _detect_symptoms(self, message_lower: str) -> List[str]:
        """Detect symptoms mentioned in user message."""
        detected = []
        
        for symptom in self.symptom_keywords:
            # Check for exact match or partial match
            if symptom in message_lower:
                detected.append(symptom)
            # Check for common variations
            elif symptom == "headache" and any(word in message_lower for word in ["head hurt", "head pain"]):
                detected.append(symptom)
            elif symptom == "stomach ache" and any(word in message_lower for word in ["stomach pain", "tummy ache"]):
                detected.append(symptom)
        
        return list(set(detected))  # Remove duplicates
    
    def _get_recommendations(self, symptoms: List[str]) -> List[Dict[str, Any]]:
        """Get medicine recommendations for symptoms."""
        recommendations = []
        
        for symptom in symptoms:
            # Get all medicines for this symptom
            matches = self.symptom_db[self.symptom_db['symptom'].str.lower() == symptom.lower()]
            
            for _, row in matches.iterrows():
                medicine_name = row['medicine_name']
                
                # Verify medicine exists in database and is OTC
                medicine_info = Database.get_medicine(medicine_name)
                
                if medicine_info:
                    # SAFETY CHECK: Only recommend if NOT prescription required
                    if medicine_info.get('prescription_required', True):
                        continue  # Skip prescription medicines
                    
                    recommendations.append({
                        "symptom": symptom,
                        "medicine_name": medicine_name,
                        "category": row['category'],
                        "severity": row['severity'],
                        "disclaimer": row['disclaimer'],
                        "prescription_required": False,
                        "stock_available": medicine_info.get('stock_level', 0) > 0
                    })
        
        return recommendations
    
    def _format_response(self, symptoms: List[str], recommendations: List[Dict]) -> str:
        """Format user-friendly response with recommendations."""
        
        # Medical disclaimer (ALWAYS shown)
        response = (
            "⚕️ **IMPORTANT MEDICAL DISCLAIMER**\n"
            "I am not a doctor and this is not medical advice. "
            "This system does not diagnose medical conditions and should not replace "
            "professional medical advice. Please consult a healthcare professional "
            "for proper diagnosis and treatment.\n\n"
        )
        
        # Show detected symptoms
        response += f"**Symptoms detected:** {', '.join(symptoms)}\n\n"
        
        if not recommendations:
            response += (
                "❌ I found these symptoms, but I cannot recommend any medicines.\n\n"
                "**Possible reasons:**\n"
                "• The medicines for these symptoms require a prescription\n"
                "• Medicine not available in our inventory\n\n"
                "Please consult a doctor for proper diagnosis and prescription."
            )
            return response
        
        # Group recommendations by medicine
        medicine_groups = {}
        for rec in recommendations:
            med = rec['medicine_name']
            if med not in medicine_groups:
                medicine_groups[med] = rec
        
        response += "**💊 Over-the-Counter (OTC) Recommendations:**\n\n"
        
        for medicine_name, rec in medicine_groups.items():
            stock_status = "✅ In stock" if rec['stock_available'] else "❌ Out of stock"
            
            response += f"**{medicine_name}** ({stock_status})\n"
            response += f"• For: {rec['symptom']}\n"
            response += f"• ⚠️ {rec['disclaimer']}\n\n"
        
        response += (
            "\n📌 **Next Steps:**\n"
            "If you'd like to order any of these medicines, please send a message like:\n"
            "• \"Order Paracetamol, 20 tablets\"\n"
            "• \"I need Ibuprofen for 10 days\""
        )
        
        return response
    
    def get_decision_reason(self, result: Dict) -> str:
        """Generate human-readable explanation of symptom analysis."""
        symptoms = result.get("symptoms_detected", [])
        recommendations = result.get("recommendations", [])
        method = result.get("method", "none")
        
        if method == "none":
            return "No symptoms detected in user message"
        
        reason = f"Detected {len(symptoms)} symptom(s): {', '.join(symptoms)}. "
        reason += f"Recommended {len(recommendations)} OTC medicine(s) using deterministic symptom mapping. "
        reason += "Medical disclaimer shown to user."
        
        return reason
