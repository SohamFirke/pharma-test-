"""
General Chat Agent: Handles casual conversation
Responds to greetings, questions, and general inquiries about the system.
"""

import sys
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).resolve().parent.parent))


class GeneralChatAgent:
    """
    Handles general conversation and system information queries.
    Uses Ollama LLM for natural responses.
    """
    
    def __init__(self, use_ollama: bool = True):
        self.use_ollama = use_ollama
        self.ollama_available = False
        
        if use_ollama:
            try:
                import ollama
                self.ollama_client = ollama
                # Test if server is accessible
                try:
                    self.ollama_client.list()
                    self.ollama_available = True
                except Exception:
                    self.ollama_available = False
            except ImportError:
                self.ollama_available = False
        
        # System information for responses
        self.system_info = {
            "name": "AI Pharmacy Assistant",
            "capabilities": [
                "Order medicines using natural language",
                "Upload prescriptions for automatic processing",
                "Get medicine recommendations for common symptoms",
                "Track refill alerts and inventory",
                "View order history"
            ],
            "features": [
                "100% offline capable",
                "Privacy-first design",
                "Deterministic safety validation",
                "Full agent observability"
            ]
        }
    
    def respond(self, message: str, user_id: str = None) -> Dict[str, Any]:
        """
        Generate a response to user message.
        
        Args:
            message: User's message
            user_id: Optional user identifier
        
        Returns:
            {
                "response": str,
                "method": "ollama" | "template",
                "confidence": float
            }
        """
        message_lower = message.lower().strip()
        
        # Try Ollama first for natural responses
        if self.ollama_available:
            llm_response = self._respond_with_ollama(message)
            if llm_response:
                return {
                    "response": llm_response,
                    "method": "ollama",
                    "confidence": 0.9
                }
        
        # Fallback to template-based responses
        return self._respond_with_template(message_lower)
    
    def _respond_with_ollama(self, message: str) -> str:
        """Generate response using Ollama LLM."""
        try:
            system_prompt = f"""You are a helpful pharmacy assistant chatbot for an AI-powered pharmacy system.

Your role is to:
- Greet users warmly
- Answer questions about the pharmacy system
- Provide helpful information about features
- Be friendly and professional

System capabilities:
{chr(10).join('- ' + cap for cap in self.system_info['capabilities'])}

IMPORTANT RULES:
- DO NOT provide medical advice or diagnose conditions
- DO NOT recommend specific medicines (tell users to ask about symptoms or place an order)
- Keep responses brief and friendly
- If asked about medicines for symptoms, tell them to describe their symptoms
- If they want to order, direct them to place an order

Respond naturally to the user's message."""

            response = self.ollama_client.chat(
                model='llama3.2',
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': message}
                ],
                stream=False
            )
            
            return response['message']['content'].strip()
        
        except Exception as e:
            print(f"Ollama chat failed: {e}")
            return None
    
    def _respond_with_template(self, message_lower: str) -> Dict[str, Any]:
        """Generate response using predefined templates."""
        
        # Greeting patterns
        if any(word in message_lower for word in ['hi', 'hello', 'hey']):
            response = (
                "👋 Hello! I'm your AI Pharmacy Assistant.\n\n"
                "I can help you:\n"
                "• Order medicines by telling me what you need\n"
                "• Upload prescriptions for automatic processing\n"
                "• Get medicine recommendations for common symptoms\n"
                "• View your order history and refill alerts\n\n"
                "How can I assist you today?"
            )
            return {
                "response": response,
                "method": "template",
                "confidence": 0.95
            }
        
        # Thank you
        if any(word in message_lower for word in ['thank', 'thanks']):
            response = (
                "You're welcome! If you need anything else, just let me know. 😊"
            )
            return {
                "response": response,
                "method": "template",
                "confidence": 0.95
            }
        
        # Help/What can you do
        if any(word in message_lower for word in ['help', 'what can', 'how do', 'capabilities']):
            response = (
                "🏥 **AI Pharmacy System Features**\n\n"
                "**Order Medicines:**\n"
                "Simply tell me what you need, like: \"I need Paracetamol, 20 tablets\"\n\n"
                "**Upload Prescription:**\n"
                "Click the 'Upload Prescription' button to automatically extract medicines from your prescription image.\n\n"
                "**Symptom Help:**\n"
                "Describe your symptoms and I'll suggest over-the-counter medicines.\n\n"
                "**Safety Features:**\n"
                "• Prescription validation\n"
                "• Stock checking\n"
                "• Refill predictions\n"
                "• Full audit trail\n\n"
                "What would you like to do?"
            )
            return {
                "response": response,
                "method": "template",
                "confidence": 0.95
            }
        
        # Goodbye
        if any(word in message_lower for word in ['bye', 'goodbye', 'see you']):
            response = "Goodbye! Stay healthy! 👋"
            return {
                "response": response,
                "method": "template",
                "confidence": 0.95
            }
        
        # Default response
        response = (
            "I'm here to help with your pharmacy needs!\n\n"
            "You can:\n"
            "• Order medicines (e.g., \"I need Paracetamol\")\n"
            "• Ask about symptoms (e.g., \"I have fever\")\n"
            "• Upload a prescription\n\n"
            "What would you like to do?"
        )
        return {
            "response": response,
            "method": "template",
            "confidence": 0.6
        }
    
    def get_decision_reason(self, result: Dict) -> str:
        """Generate human-readable explanation of response generation."""
        method = result.get("method", "unknown")
        confidence = result.get("confidence", 0.0)
        
        if method == "ollama":
            return f"Generated natural response using LLM with {confidence:.0%} confidence"
        elif method == "template":
            return f"Used template-based response with {confidence:.0%} confidence"
        else:
            return "Response generation method unknown"
