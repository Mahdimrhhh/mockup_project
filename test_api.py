"""
Quick test script for Mockup Generator API
Run this after starting Django server and Celery worker
"""
import requests  # type: ignore[import]
import time
import json
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_generate_mockup():
    """Test POST /api/v1/mockups/generate/"""
    print("\n" + "=" * 50)
    print("1. Testing POST /api/v1/mockups/generate/")
    print("=" * 50)
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/mockups/generate/",
            json={"text": "Hello World", "shirt_color": ["white", "black", "blue", "yellow"]},
            timeout=30
        )
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 202:
            result = response.json()
            print(f"✅ Task created successfully!")
            print(f"Response: {json.dumps(result, indent=2)}")
            return result.get("task_id")
        else:
            print(f"❌ Failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Is Django running on port 8000?")
        print("   Start it with: python manage.py runserver")
        return None
    except requests.exceptions.Timeout:
        print("❌ Request timed out. The server may be slow or hanging.")
        print("   Check Django server terminal for errors.")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_task_status(task_id):
    """Test GET /api/v1/tasks/{task_id}/"""
    if not task_id:
        return
    
    print("\n" + "=" * 50)
    print("2. Testing GET /api/v1/tasks/{task_id}/")
    print("=" * 50)
    
    print("Waiting 5 seconds for task to complete...")
    time.sleep(5)
    
    try:
        response = requests.get(f"{BASE_URL}/api/v1/tasks/{task_id}/", timeout=30)
        print(f"Status Code: {response.status_code}")
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        
        status = result.get("status")
        if status == "SUCCESS":
            results = result.get("results", [])
            print(f"\n✅ Task completed successfully!")
            print(f"Generated {len(results)} images")
            for i, img in enumerate(results, 1):
                print(f"  {i}. {img.get('image_url')}")
        elif status == "PENDING":
            print(f"\n⚠️ Task still processing. Check Celery worker.")
        else:
            print(f"\n⚠️ Task status: {status}")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_mockup_history():
    """Test GET /api/mockups/"""
    print("\n" + "=" * 50)
    print("3. Testing GET /api/mockups/")
    print("=" * 50)
    
    try:
        response = requests.get(f"{BASE_URL}/api/mockups/", timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            results = result.get("results", [])
            print(f"Total mockups: {len(results)}")
            
            if results:
                print(f"\nFirst mockup:")
                print(json.dumps(results[0], indent=2))
            else:
                print("No mockups found yet.")
        else:
            print(f"❌ Failed: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("Mockup Generator API Test")
    print("=" * 50)
    print("\nMake sure:")
    print("  1. Django server is running: python manage.py runserver")
    print("  2. Celery worker is running: celery -A mockup_project worker --pool=solo")
    print("  3. Redis is running")
    
    # Test 1: Generate mockup
    task_id = test_generate_mockup()
    
    # Test 2: Check task status
    test_task_status(task_id)
    
    # Test 3: Get history
    test_mockup_history()
    
    print("\n" + "=" * 50)
    print("Testing complete!")
    print("=" * 50)

