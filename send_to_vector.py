#!/usr/bin/env python3
"""Send test_data.json to Vector and display response"""

import json
import requests

VECTOR_URL = "http://localhost:8080"

def send_to_vector():
    with open("test_data.json", "r") as f:
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
    
    print("-" * 50)
    print("Done!")

if __name__ == "__main__":
    send_to_vector()
