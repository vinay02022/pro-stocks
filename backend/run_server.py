"""
Run the StockPro backend server.
"""
import os
import sys

# Set working directory and path
backend_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(backend_dir)
sys.path.insert(0, backend_dir)

# Load environment
from dotenv import load_dotenv
load_dotenv(os.path.join(backend_dir, ".env"))

# Run uvicorn
import uvicorn

if __name__ == "__main__":
    print("Starting StockPro Backend Server...")
    print(f"Working directory: {backend_dir}")
    print("API Docs: http://localhost:8000/docs")
    print("-" * 50)

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
