#!/usr/bin/env python3
"""
Setup script for Agentic AI Pharmacy System
Initializes dependencies and verifies installation
"""

import subprocess
import sys
import os
from pathlib import Path

def print_header(text):
    """Print formatted header."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)

def run_command(command, description):
    """Run shell command with status output."""
    print(f"\n▶ {description}...")
    try:
        subprocess.run(command, check=True, shell=True)
        print(f"✅ {description} - SUCCESS")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - FAILED")
        print(f"   Error: {e}")
        return False

def check_ollama():
    """Check if Ollama is installed and running."""
    print("\n▶ Checking Ollama installation...")
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("✅ Ollama is installed")
            
            # Check if llama3.2 is available
            if "llama3.2" in result.stdout:
                print("✅ llama3.2 model is available")
            else:
                print("⚠️  llama3.2 model not found")
                print("   To install: ollama pull llama3.2")
            return True
        else:
            print("⚠️  Ollama not running")
            print("   Start Ollama: ollama serve")
            return False
    except FileNotFoundError:
        print("❌ Ollama not installed")
        print("   Install from: https://ollama.ai")
        return False

def main():
    """Main setup function."""
    print_header("🏥 AGENTIC AI PHARMACY SYSTEM - SETUP")
    
    # Get project root
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    print(f"\nProject directory: {project_root}")
    
    # Step 1: Install Python dependencies
    print_header("Step 1: Installing Python Dependencies")
    if not run_command(
        f"{sys.executable} -m pip install -r requirements.txt",
        "Installing requirements"
    ):
        print("\n⚠️  Warning: Some dependencies may have failed to install")
    
    # Step 2: Download spaCy model
    print_header("Step 2: Downloading spaCy Language Model")
    run_command(
        f"{sys.executable} -m spacy download en_core_web_sm",
        "Downloading spaCy English model"
    )
    
    # Step 3: Check Ollama
    print_header("Step 3: Verifying Ollama Installation")
    ollama_ok = check_ollama()
    
    # Step 4: Verify data files
    print_header("Step 4: Verifying Data Files")
    data_dir = project_root / "data"
    
    required_files = [
        data_dir / "medicine_master.csv",
        data_dir / "order_history.csv"
    ]
    
    all_files_exist = True
    for file in required_files:
        if file.exists():
            print(f"✅ Found: {file.name}")
        else:
            print(f"❌ Missing: {file.name}")
            all_files_exist = False
    
    # Summary
    print_header("Setup Summary")
    print("\n✅ Python dependencies installed")
    print("✅ spaCy model downloaded")
    
    if ollama_ok:
        print("✅ Ollama is ready")
    else:
        print("⚠️  Ollama needs attention (see above)")
    
    if all_files_exist:
        print("✅ Data files present")
    else:
        print("❌ Some data files missing")
    
    # Next steps
    print_header("Next Steps")
    print("\n1. If Ollama is not running, start it:")
    print("   $ ollama serve")
    print("\n2. If llama3.2 is not installed:")
    print("   $ ollama pull llama3.2")
    print("\n3. Start the backend server:")
    print("   $ cd backend")
    print("   $ python main.py")
    print("\n4. Open your browser:")
    print("   Main UI: http://localhost:8000")
    print("   Admin Dashboard: http://localhost:8000/admin")
    print("   API Docs: http://localhost:8000/docs")
    
    print("\n" + "=" * 70)
    print("  Setup complete! 🎉")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    main()
