"""
LLM Research App - Hugging Face Entry Point
Executes frontend/app.py for Streamlit deployment
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Execute the frontend app
frontend_app = project_root / "frontend" / "app.py"
with open(frontend_app) as f:
    exec(f.read())
