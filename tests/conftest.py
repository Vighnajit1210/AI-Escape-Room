import os
import sys

# Make the v2 modules importable as top-level modules (same as when Streamlit runs v2/app.py).
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "v2"))
os.environ.setdefault("GEMINI_API_KEY", "")
