import os
import sys

# Add the parent directory to the Python path so it can import server.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import app
