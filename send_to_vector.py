#!/usr/bin/env python3
"""Send test_data.json to Vector and display response"""

import json
import requests
import os

VECTOR_URL = "http://vector:8080"

if os.path.exists("/streamguard"):
    INPUT_FILE = "/streamguard/input.json"
else:
    INPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "input.json")

def save_to_input_file(data):
    """Append data to input.json file"""
    existing_data = []
    
    if os.path.exists(INPUT_FILE):
        try:
            with open(INPUT_FILE, "r") as f:
                content = f.read()
                if content:
                    existing_data = json.loads(content)
                    if not isinstance(existing_data, list):
                        existing_data = [existing_data]
        except json.JSONDecodeError:
            pass
            
    existing_data.append(data)
    
    with open(INPUT_FILE, "w") as f:
        json.dump(existing_data, f, indent=2)

def send_to_vector():
    with open("camera_logs.json", "r") as f:
        events = json.load(f)
    
    print(f"Sending {len(events)} events to Vector at {VECTOR_URL}...")
    print("-" * 50)
    
    for i, event in enumerate(events):
        response = requests.post(
            VECTOR_URL,
            json=event,
            headers={"Content-Type": "application/json"}
        )
        print(f"Event {i+1} ({event.get('type')}): Status {response.status_code}")
        if response.text:
            print(f"Response: {response.text}")
            
        if response.status_code == 200:
            save_to_input_file(event)
    
    print("-" * 50)
    print("Done!")

if __name__ == "__main__":
    send_to_vector()
