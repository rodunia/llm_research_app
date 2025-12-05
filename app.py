"""
LLM Research App - Hugging Face Entry Point
Runs frontend/app.py for Streamlit deployment
"""

# This file just runs the frontend app
# We do it by executing the file directly so paths work correctly
import subprocess
import sys

subprocess.run([sys.executable, "frontend/app.py"])
