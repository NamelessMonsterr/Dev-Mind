import asyncio
import json
import time
from fastapi.testclient import TestClient
from devmind.api.app import create_app

# ASCII Colors
GREEN = "\033[92m"
BLUE = "\033[94m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def print_step(step, message):
    print(f"\n{BLUE}=== Step {step}: {message} ==={RESET}")

def print_user(message):
    print(f"{GREEN}👤 User:{RESET} {message}")

def print_system(message, data=None):
    print(f"{CYAN}🤖 DevMind:{RESET} {message}")
    if data:
        print(f"{YELLOW}{json.dumps(data, indent=2)}{RESET}")

async def run_demo():
    print(f"{BLUE}🚀 Starting DevMind User Journey Simulation...{RESET}")
    
    # 1. Initialize App
    print_step(1, "System Startup")
    print_system("Initializing DevMind API...")
    app = create_app()
    client = TestClient(app)
    print_system("System Online ✅")

    # 2. Health Check
    print_step(2, "Health Check")
    print_user("Is the system healthy?")
    response = client.get("/health")
    print_system("Health Status:", response.json())

    # 3. Ingestion
    print_step(3, "Ingesting Code")
    code_content = """
def calculate_fibonacci(n):
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

def authenticate_user(username, password):
    # TODO: Implement secure auth
    if username == "admin" and password == "secret":
        return True
    return False
"""
    print_user("Uploading 'utils.py' with Fibonacci and Auth functions...")
    
    # Mocking ingestion endpoint behavior since we don't have a real file upload in TestClient easily without files
    # We will simulate the "ingestion" by directly using the embedding/indexing logic if possible, 
    # but for this demo, we can assume the API is mocked or we use the real endpoint.
    # Since we can't easily upload files in this script without creating them, let's create a temp file.
    
    with open("utils.py", "w") as f:
        f.write(code_content)
        
    with open("utils.py", "rb") as f:
        response = client.post(
            "/ingest/start", 
            files={"files": ("utils.py", f, "text/x-python")},
            data={"languages": ["python"]}
        )
    
    print_system("Ingestion Job Started:", response.json())
    job_id = response.json().get("job_id")
    
    # Simulate waiting for ingestion (mocked or real)
    # In a real test we'd poll, but here we assume it's fast or async. 
    # For the purpose of this demo script using mocks might be safer if services aren't running.
    # However, let's assume the integration tests set up the mocks.
    # Wait, the integration tests use mocks. This script runs against the REAL app factory.
    # If the real app requires Qdrant/Redis, checking health might fail if they aren't running.
    # The user asked to "run and use it". 
    # I should try to run it. If dependencies are missing, I'll catch that.
    
    # 4. Search
    print_step(4, "Semantic Search")
    query = "How to authenticate user?"
    print_user(f"Searching for: '{query}'")
    
    # We might need to mock the search if Qdrant isn't up.
    # But let's try real call. If it fails, we know we need infrastructure.
    try:
        response = client.post("/search", json={"query": query, "top_k": 2})
        if response.status_code == 200:
            print_system("Search Results:", response.json())
        else:
            print_system(f"Search failed (likely due to missing DB connection): {response.status_code}")
            # Mock success for demo purposes if infra is down
            print_system("(Mocked) Found match in 'utils.py': def authenticate_user...")
    except Exception as e:
        print_system(f"Search failed: {e}")

    # 5. Chat
    print_step(5, "AI Chat")
    chat_message = "Explain the auth function"
    print_user(f"Chat: '{chat_message}'")
    
    try:
        # Stream chat
        # TestClient doesn't support websockets easily, use synchronous endpoint if available or mock
        # DevMind has /chat endpoint
        response = client.post("/chat", json={"messages": [{"role": "user", "content": chat_message}]})
        if response.status_code == 200:
             print_system("AI Response:", response.json())
        else:
             print_system(f"Chat failed: {response.status_code}")
             print_system("(Mocked) AI: The authenticate_user function checks if username is 'admin'...")
    except Exception as e:
        print_system(f"Chat failed: {e}")

    print(f"\n{BLUE}=== Demo Complete ==={RESET}")

if __name__ == "__main__":
    asyncio.run(run_demo())
