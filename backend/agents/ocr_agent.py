"""
OCR Agent: Text Extraction from Prescriptions
Extracts text from prescription images/PDFs using Tesseract OCR and pdfplumber.
"""

import sys
from pathlib import Path
from typing import Dict, Tuple, Optional
import os

# Add parent directory to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

try:
    from PIL import Image
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    print("Warning: pytesseract/Pillow not available")

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    print("Warning: pdfplumber not available")


class OCRAgent:
    """
    Extracts text from prescription images and PDFs using local OCR.
    NO cloud APIs - completely offline.
    """
    
    def __init__(self):
        self.tesseract_available = TESSERACT_AVAILABLE
        self.pdfplumber_available = PDFPLUMBER_AVAILABLE
        
        # Try to detect Tesseract binary
        if self.tesseract_available:
            self._check_tesseract_installation()
    
    def _check_tesseract_installation(self):
        """Check if Tesseract binary is installed."""
        try:
            pytesseract.get_tesseract_version()
        except Exception as e:
            print(f"Warning: Tesseract not found. Install with: brew install tesseract")
            print(f"Error: {e}")
            self.tesseract_available = False
    
    def extract_text(self, file_path: str, file_type: str) -> Tuple[bool, str, Dict]:
        """
        Extract text from prescription file.
        
        Args:
            file_path: Path to the prescription file
            file_type: File type (jpg, png, pdf)
        
        Returns:
            Tuple of (success, extracted_text, metadata)
        """
        
        if not os.path.exists(file_path):
            return False, "", {"error": "File not found"}
        
        try:
            if file_type.lower() == 'pdf':
                return self._extract_from_pdf(file_path)
            else:
                return self._extract_from_image(file_path)
        
        except Exception as e:
            return False, "", {"error": f"OCR failed: {str(e)}"}
    
    def _extract_from_image(self, image_path: str) -> Tuple[bool, str, Dict]:
        """Extract text from image using Tesseract OCR."""
        
        if not self.tesseract_available:
            return False, "", {
                "error": "Tesseract OCR not available. Install: brew install tesseract"
            }
        
        try:
            # Open image
            image = Image.open(image_path)
            
            #Preprocess image for better OCR
            # Convert to grayscale
            image = image.convert('L')
            
            # Extract text
            text = pytesseract.image_to_string(image)
            
            # Get confidence data
            try:
                data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
                confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            except:
                avg_confidence = 0
            
            # Clean text
            text = text.strip()
            
            metadata = {
                "method": "tesseract_ocr",
                "average_confidence": round(avg_confidence, 2),
                "text_length": len(text),
                "preprocessing": "grayscale"
            }
            
            if not text:
                return False, "", {"error": "No text extracted from image"}
            
            return True, text, metadata
        
        except Exception as e:
            return False, "", {"error": f"Image OCR failed: {str(e)}"}
    
    def _extract_from_pdf(self, pdf_path: str) -> Tuple[bool, str, Dict]:
        """Extract text from PDF using pdfplumber."""
        
        if not self.pdfplumber_available:
            return False, "", {
                "error": "pdfplumber not available. Install: pip install pdfplumber"
            }
        
        try:
            text_parts = []
            page_count = 0
            
            with pdfplumber.open(pdf_path) as pdf:
                page_count = len(pdf.pages)
                
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            
            full_text = "\n".join(text_parts).strip()
            
            metadata = {
                "method": "pdfplumber",
                "page_count": page_count,
                "text_length": len(full_text)
            }
            
            if not full_text:
                return False, "", {"error": "No text extracted from PDF"}
            
            return True, full_text, metadata
        
        except Exception as e:
            return False, "", {"error": f"PDF extraction failed: {str(e)}"}
    
    def get_decision_reason(self, success: bool, metadata: Dict) -> str:
        """Generate decision reasoning for observability."""
        
        if success:
            method = metadata.get('method', 'unknown')
            length = metadata.get('text_length', 0)
            
            if method == "tesseract_ocr":
                conf = metadata.get('average_confidence', 0)
                return (
                    f"Text extracted using Tesseract OCR: {length} characters, "
                    f"average confidence: {conf}%"
                )
            elif method == "pdfplumber":
                pages = metadata.get('page_count', 0)
                return f"Text extracted from PDF using pdfplumber: {pages} pages, {length} characters"
        else:
            return f"OCR failed: {metadata.get('error', 'unknown error')}"
        
        return "Unknown OCR result"
