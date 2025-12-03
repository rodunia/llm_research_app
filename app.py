"""
LLM Research App - Hugging Face Entry Point
Redirects to frontend/app.py for Streamlit deployment
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import and run the frontend app
from frontend.app import *
