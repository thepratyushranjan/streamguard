import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_health():
    try:
        r = requests.get(f"{BASE_URL}/health")
        print(f"Health: {r.status_code} {r.json()}")
    except Exception as e:
        print(f"Health check failed: {e}")

def test_ingest():
    print("\nTesting Ingestion...")
    payload = {
        "type": "EVENT",
        "processed_at": time.time(),
        "meta": {
            "cam_id": 101,
            "site": "site_001",
            "status": "WARNING",
            "ts": time.time(),
            "cam_name": "Entrance Cam"
        },
        "data": {
            "people_count": 5,
            "detections": [
                {"class_id": 1, "label": "person", "confidence": 0.95, "bbox": [10, 10, 100, 200]},
                {"class_id": 1, "label": "person", "confidence": 0.88, "bbox": [150, 10, 100, 200]}
            ],
            "triggers": ["loitering"]
        }
    }
    
    try:
        r = requests.post(f"{BASE_URL}/events", json=payload)
        print(f"Ingest Status: {r.status_code}")
        if r.status_code != 200:
            print(r.text)
    except Exception as e:
        print(f"Ingest failed: {e}")

def test_sites_endpoints():
    site_id = "site_001"
    endpoints = [
        f"/api/v1/sites/{site_id}/summary",
        f"/api/v1/sites/{site_id}/events",
        f"/api/v1/sites/{site_id}/analytics/distribution",
        f"/api/v1/sites/{site_id}/analytics/traffic-flow"
    ]
    
    headers = {"X-API-Key": "default_unsafe_key"}
    
    print("\nTesting Sites Endpoints...")
    for ep in endpoints:
        try:
            r = requests.get(f"{BASE_URL}{ep}", headers=headers)
            print(f"GET {ep}: {r.status_code}")
            if r.status_code == 200:
                pass # print(r.json())
            else:
                print(r.text)
        except Exception as e:
            print(f"Failed {ep}: {e}")

if __name__ == "__main__":
    test_health()
    test_ingest()
    time.sleep(1) # Wait for consistent insert
    test_sites_endpoints()
