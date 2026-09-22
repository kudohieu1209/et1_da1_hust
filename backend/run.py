import uvicorn
import os
import sys

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

if __name__ == "__main__":
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    print(f"Starting HUST Course Advisor Backend at http://{host}:{port}...")
    print(f"Swagger API Docs: http://localhost:{port}/docs")
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
