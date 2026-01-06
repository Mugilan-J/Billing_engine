import requests
import json
import random
import uuid
from datetime import datetime

# Configuration
URL = "http://localhost:8080/events"

def print_result(name, response, expected_code):
    """Helper to print colorful results"""
    is_success = response.status_code == expected_code
    
    # ANSI colors for terminal
    GREEN = '\033[92m'
    RED = '\033[91m'
    RESET = '\033[0m'
    
    status_color = GREEN if is_success else RED
    print(f"Test: {name}")
    print(f"Sent: {response.request.body}")
    print(f"{status_color}Result: {response.status_code} {response.text}{RESET}")
    print("-" * 50)

def generate_valid_event():
    return {
        "event_id": str(uuid.uuid4()),
        "user_id": f"user_{random.randint(1, 100)}",
        "action": random.choice(["login", "logout", "purchase", "click"]),
        "quantity": random.randint(1, 5),
        "request_id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat()
    }

# ==========================================
# TEST 1: The Happy Path (Valid Data)
# ==========================================
print("\n--- TEST 1: Valid Data ---")
data = generate_valid_event()
resp = requests.post(URL, json=data)
print_result("Happy Path", resp, 200)

# ==========================================
# TEST 2: Logical Errors (Missing Fields)
# ==========================================
print("\n--- TEST 2: Missing Required Fields ---")
# Missing 'user_id'
bad_data = generate_valid_event()
bad_data["user_id"] = "" # Empty string
resp = requests.post(URL, json=bad_data)
print_result("Empty UserID", resp, 400)

# Missing 'action'
bad_data = generate_valid_event()
del bad_data["action"] # Key doesn't exist
resp = requests.post(URL, json=bad_data)
print_result("Missing Action Key", resp, 400)

# ==========================================
# TEST 3: Data Type Errors (Int vs String)
# ==========================================
print("\n--- TEST 3: Wrong Data Types ---")
bad_type_data = generate_valid_event()
# quantity should be Int, we send String "Five"
bad_type_data["quantity"] = "Five" 
resp = requests.post(URL, json=bad_type_data)
# Go's decoder will fail immediately here
print_result("String instead of Int", resp, 400)

# ==========================================
# TEST 4: Malformed JSON (The "Garbage" Test)
# ==========================================
print("\n--- TEST 4: Not Even JSON ---")
# Sending raw text instead of JSON
resp = requests.post(URL, data="This is just raw text, not json")
print_result("Raw Text Body", resp, 400)