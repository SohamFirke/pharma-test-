"""
Prescription Upload Agent: File Handling
Manages prescription file uploads, validation, and storage.
"""

import os
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple, Optional
import shutil

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
PRESCRIPTIONS_DIR = BASE_DIR / "data" / "prescriptions"
UPLOADS_DIR = PRESCRIPTIONS_DIR / "uploads"

# Ensure directories exist
PRESCRIPTIONS_DIR.mkdir(exist_ok=True, parents=True)
UPLOADS_DIR.mkdir(exist_ok=True, parents=True)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.pdf'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


class PrescriptionUploadAgent:
    """
    Handles prescription file uploads and storage.
    """
    
    def __init__(self):
        self.uploads_dir = UPLOADS_DIR
    
    def validate_file(self, filename: str, file_size: int) -> Tuple[bool, str]:
        """
        Validate uploaded file.
        
        Args:
            filename: Original filename
            file_size: File size in bytes
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        
        # Check file extension
        file_ext = Path(filename).suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            return False, f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        
        # Check file size
        if file_size > MAX_FILE_SIZE:
            max_mb = MAX_FILE_SIZE / (1024 * 1024)
            return False, f"File too large. Maximum size: {max_mb}MB"
        
        return True, ""
    
    def save_prescription_file(self, file_content: bytes, original_filename: str,
                              user_id: str) -> Tuple[bool, str, Dict]:
        """
        Save uploaded prescription file.
        
        Args:
            file_content: File binary content
            original_filename: Original filename
            user_id: User ID
        
        Returns:
            Tuple of (success, prescription_id, metadata)
        """
        
        try:
            # Validate file size
            file_size = len(file_content)
            is_valid, error_msg = self.validate_file(original_filename, file_size)
            
            if not is_valid:
                return False, "", {"error": error_msg}
            
            # Generate unique prescription ID
            prescription_id = self._generate_prescription_id()
            
            # Get file extension
            file_ext = Path(original_filename).suffix.lower()
            
            # Create new filename
            new_filename = f"{prescription_id}{file_ext}"
            file_path = self.uploads_dir / new_filename
            
            # Save file
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            # Create metadata
            metadata = {
                "prescription_id": prescription_id,
                "user_id": user_id,
                "original_filename": original_filename,
                "file_path": str(file_path),
                "file_type": file_ext[1:],  # Remove dot
                "file_size": file_size,
                "upload_date": datetime.now().isoformat(),
                "status": "uploaded"
            }
            
            return True, prescription_id, metadata
            
        except Exception as e:
            return False, "", {"error": f"File save failed: {str(e)}"}
    
    def _generate_prescription_id(self) -> str:
        """
        Generate unique prescription ID.
        
        Format: rx_YYYYMMDD_HHMMSS_XXX (XXX = random 3 chars)
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        random_suffix = str(uuid.uuid4())[:3]
        return f"rx_{timestamp}_{random_suffix}"
    
    def get_file_path(self, prescription_id: str) -> Optional[str]:
        """Get file path for a prescription ID."""
        
        # Find file with this prescription ID
        for file_path in self.uploads_dir.glob(f"{prescription_id}.*"):
            return str(file_path)
        
        return None
    
    def delete_prescription_file(self, prescription_id: str) -> bool:
        """Delete prescription file."""
        
        file_path = self.get_file_path(prescription_id)
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                return True
            except Exception:
                return False
        
        return False
    
    def get_decision_reason(self, action: str, success: bool, metadata: Dict) -> str:
        """Generate decision reasoning for observability."""
        
        if action == "validate_file":
            if success:
                return f"File validation passed: {metadata.get('original_filename')}"
            else:
                return f"File validation failed: {metadata.get('error')}"
        
        elif action == "save_file":
            if success:
                return (
                    f"Prescription file saved successfully: {metadata.get('prescription_id')} "
                    f"({metadata.get('file_type')}, {metadata.get('file_size')} bytes)"
                )
            else:
                return f"File save failed: {metadata.get('error')}"
        
        return "Unknown action"
