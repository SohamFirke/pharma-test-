"""
Router Agent: Intent Classification ONLY (No Medical/Safety Decisions)

This agent classifies user messages into intent categories using embeddings.
It does NOT make medical, safety, or prescription validation decisions.

Decision Authority: Intent classification only
- Determines message category (chat, symptom, order, prescription)
- Routes to appropriate agent
- Does NOT approve medications
- Does NOT override safety rules
"""

import numpy as np
from typing import Dict, Any, Tuple, List
from sklearn.metrics.pairwise import cosine_similarity
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).resolve().parent.parent))


class RouterAgent:
    """
    Routes user messages to appropriate agents based on intent classification.
    
    AUTHORITY SCOPE:
    - Intent classification ONLY
    - Does NOT make medical diagnoses
    - Does NOT make safety/prescription decisions
    - Routes messages to specialized agents for actual processing
    
    Uses nomic-embed-text embeddings with cosine similarity matching.
    """
    
    # Intent categories
    GENERAL_CHAT = "GENERAL_CHAT"
    SYMPTOM_QUERY = "SYMPTOM_QUERY"
    ORDER_RELATED = "ORDER_RELATED"
    PRESCRIPTION_UPLOAD = "PRESCRIPTION_UPLOAD"
    
    def __init__(self):
        self.ollama_available = False
        self.embeddings_cache = {}
        
        # Try to initialize Ollama
        try:
            import ollama
            self.ollama_client = ollama
            # Test if server is accessible
            try:
                self.ollama_client.list()
                self.ollama_available = True
                print("✓ Ollama available for intent routing")
            except Exception:
                print("⚠ Ollama server not responding, using keyword fallback")
                self.ollama_available = False
        except ImportError:
            print("⚠ Ollama not installed, using keyword fallback")
            self.ollama_available = False
        
        # Predefined intent examples for embedding-based classification
        self.intent_examples = {
            self.GENERAL_CHAT: [
                "hi",
                "hello",
                "thank you",
                "thanks",
                "how are you",
                "what can you do",
                "help",
                "how does this work",
                "goodbye",
                "bye"
            ],
            self.SYMPTOM_QUERY: [
                "I have fever",
                "my head hurts",
                "I have headache",
                "cold and cough",
                "feeling sick",
                "my throat hurts",
                "I have pain",
                "stomach ache",
                "body ache",
                "runny nose"
            ],
            self.ORDER_RELATED: [
                "order medicine",
                "I need paracetamol",
                "buy ibuprofen",
                "refill my tablets",
                "I want to order",
                "get me medicine",
                "purchase aspirin",
                "I need tablets",
                "order 20 tablets",
                "refill prescription"
            ]
        }
        
        # Keyword-based fallback patterns
        self.keyword_patterns = {
            self.GENERAL_CHAT: [
                "hi", "hello", "hey", "thank", "help", "what", "how", "who", 
                "goodbye", "bye", "thanks"
            ],
            self.SYMPTOM_QUERY: [
                "fever", "headache", "pain", "ache", "sick", "cold", "cough", 
                "throat", "stomach", "hurt", "symptom", "feeling"
            ],
            self.ORDER_RELATED: [
                "order", "need", "want", "buy", "purchase", "get", "refill",
                "tablet", "capsule", "medicine", "quantity"
            ]
        }
        
        # Precompute embeddings if Ollama is available
        if self.ollama_available:
            self._precompute_intent_embeddings()
    
    def _precompute_intent_embeddings(self):
        """Precompute embeddings for all intent examples."""
        for intent, examples in self.intent_examples.items():
            self.embeddings_cache[intent] = []
            for example in examples:
                embedding = self._get_embedding(example)
                if embedding is not None:
                    self.embeddings_cache[intent].append(embedding)
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """Get embedding vector for text using nomic-embed-text."""
        if not self.ollama_available:
            return None
        
        try:
            response = self.ollama_client.embeddings(
                model='nomic-embed-text',
                prompt=text
            )
            return np.array(response['embedding'])
        except Exception as e:
            print(f"Embedding generation failed: {e}")
            return None
    
    def classify_intent(self, message: str) -> Dict[str, Any]:
        """
        Classify user message intent using embeddings or keyword fallback.
        
        IMPORTANT: This method performs INTENT CLASSIFICATION ONLY.
        It does NOT make medical diagnoses, safety decisions, or prescription validations.
        The classification result is used ONLY for routing to specialized agents.
        
        Args:
            message: User input message
        
        Returns:
            {
                "intent": str (GENERAL_CHAT, SYMPTOM_QUERY, ORDER_RELATED),
                "confidence": float (0.0-1.0),
                "method": "embedding" | "keyword",
                "reasoning": str
            }
        """
        message_lower = message.lower().strip()
        
        # Try embedding-based classification first
        # NOTE: Router Agent performs intent classification ONLY - no medical/safety authority
        if self.ollama_available and self.embeddings_cache:
            result = self._classify_with_embeddings(message)
            if result:
                return result
        
        # Fallback to keyword-based classification
        # NOTE: Keywords used for routing only - does NOT diagnose or make safety decisions
        return self._classify_with_keywords(message_lower)
    
    def _classify_with_embeddings(self, message: str) -> Dict[str, Any]:
        """Classify using embedding similarity."""
        try:
            # Get embedding for user message
            message_embedding = self._get_embedding(message)
            if message_embedding is None:
                return None
            
            # Calculate similarities with each intent category
            intent_scores = {}
            
            for intent, example_embeddings in self.embeddings_cache.items():
                if not example_embeddings:
                    continue
                
                # Calculate similarity with all examples for this intent
                similarities = []
                for example_emb in example_embeddings:
                    sim = cosine_similarity(
                        message_embedding.reshape(1, -1),
                        example_emb.reshape(1, -1)
                    )[0][0]
                    similarities.append(sim)
                
                # Use max similarity as intent score
                intent_scores[intent] = max(similarities)
            
            # Get best matching intent
            best_intent = max(intent_scores, key=intent_scores.get)
            confidence = intent_scores[best_intent]
            
            return {
                "intent": best_intent,
                "confidence": float(confidence),
                "method": "embedding",
                "reasoning": f"Embedding similarity: {confidence:.2f} to {best_intent} examples",
                "all_scores": {k: float(v) for k, v in intent_scores.items()}
            }
        
        except Exception as e:
            print(f"Embedding classification error: {e}")
            return None
    
    def _classify_with_keywords(self, message_lower: str) -> Dict[str, Any]:
        """Fallback: classify using keyword matching."""
        
        intent_scores = {
            self.GENERAL_CHAT: 0,
            self.SYMPTOM_QUERY: 0,
            self.ORDER_RELATED: 0
        }
        
        # Count keyword matches for each intent
        for intent, keywords in self.keyword_patterns.items():
            for keyword in keywords:
                if keyword in message_lower:
                    intent_scores[intent] += 1
        
        # Get best match
        best_intent = max(intent_scores, key=intent_scores.get)
        max_score = intent_scores[best_intent]
        
        # If no keywords matched, default to general chat
        if max_score == 0:
            return {
                "intent": self.GENERAL_CHAT,
                "confidence": 0.3,
                "method": "keyword",
                "reasoning": "No specific keywords matched, defaulting to general chat",
                "all_scores": intent_scores
            }
        
        # Calculate confidence based on keyword matches
        total_keywords = sum(intent_scores.values())
        confidence = max_score / max(total_keywords, 1)
        
        return {
            "intent": best_intent,
            "confidence": float(min(confidence * 0.8, 0.9)),  # Cap at 0.9 for keyword method
            "method": "keyword",
            "reasoning": f"Matched {max_score} keyword(s) for {best_intent}",
            "all_scores": intent_scores
        }
    
    def get_decision_reason(self, classification_result: Dict) -> str:
        """Generate human-readable explanation of routing decision."""
        intent = classification_result.get("intent", "UNKNOWN")
        confidence = classification_result.get("confidence", 0.0)
        method = classification_result.get("method", "unknown")
        
        reason = f"Classified as {intent} with {confidence:.0%} confidence using {method} method"
        
        if method == "embedding":
            reason += " (nomic-embed-text embeddings)"
        elif method == "keyword":
            reason += " (keyword pattern matching)"
        
        return reason
