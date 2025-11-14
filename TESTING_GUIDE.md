# Testing Guide for Mockup Generator

## Prerequisites

1. **Activate virtual environment:**
   ```bash
   mpenv\Scripts\activate
   ```

2. **Ensure Redis is running:**
   - Check if Redis is already running on port 6379
   - If not, start Redis server

3. **Start Celery Worker** (in a separate terminal):
   ```bash
   celery -A mockup_project worker --loglevel=info --pool=solo
   ```
   Keep this terminal open - you should see "celery@..." ready to receive tasks.

4. **Start Django Development Server** (in another terminal):
   ```bash
   python manage.py runserver
   ```
   Server should start on `http://127.0.0.1:8000`

---

## Testing the API Endpoints

### 1. Test Mockup Generation Endpoint

**Endpoint:** `POST http://127.0.0.1:8000/api/v1/mockups/generate/`

**Using cURL:**
```bash
curl -X POST http://127.0.0.1:8000/api/v1/mockups/generate/ \
  -H "Content-Type: application/json" \
  -d "{\"text\": \"Hello World\"}"
```

**Using Python requests:**
```python
import requests

response = requests.post(
    'http://127.0.0.1:8000/api/v1/mockups/generate/',
    json={
        "text": "Hello World",
        "font": "arial",  # optional
        "text_color": "#FFFFFF",  # optional
        "shirt_color": ["white", "black", "blue", "yellow"]  # optional
    }
)
print(response.json())
# Expected: {"task_id": "uuid-string", "status": "PENDING", "message": "Image generation started"}
```

**Save the `task_id` from the response** - you'll need it for the next step.

---

### 2. Test Task Result Endpoint

**Endpoint:** `GET http://127.0.0.1:8000/api/v1/tasks/{task_id}/`

**Using cURL:**
```bash
# Replace {task_id} with the UUID from step 1
curl http://127.0.0.1:8000/api/v1/tasks/{task_id}/
```

**Using Python:**
```python
import requests
import time

task_id = "your-task-id-from-step-1"  # Replace with actual task_id

# Wait a few seconds for task to complete
time.sleep(5)

response = requests.get(f'http://127.0.0.1:8000/api/v1/tasks/{task_id}/')
print(response.json())
# Expected: {"task_id": "uuid", "status": "SUCCESS", "results": [...]}
```

**Check the Celery worker terminal** - you should see:
- `Task mockups.tasks.generate_mockup_task[...] received`
- `=== GENERATE MOCKUP STARTED for task ...`
- `=== GENERATE MOCKUP FINISHED for task ...`
- `Task ... succeeded`

**Verify:**
- Status should be `"SUCCESS"` (not `"PENDING"`)
- `results` array should contain 4 image URLs (one for each color)
- Images should be accessible at the URLs provided

---

### 3. Test Mockup History Endpoint

**Endpoint:** `GET http://127.0.0.1:8000/api/mockups/`

**Using cURL:**
```bash
curl http://127.0.0.1:8000/api/mockups/
```

**Using Python:**
```python
import requests

response = requests.get('http://127.0.0.1:8000/api/mockups/')
print(response.json())
# Expected: {"results": [{"id": 1, "text": "...", "image_url": "...", ...}]}
```

**Verify:**
- Returns list of all generated mockups
- Each mockup has: `id`, `text`, `image_url`, `font`, `text_color`, `shirt_color`, `created_at`
- Images are accessible

---

## Quick Test Script

Save this as `test_api.py` in your project root:

```python
import requests
import time
import json

BASE_URL = "http://127.0.0.1:8000"

print("=" * 50)
print("Testing Mockup Generator API")
print("=" * 50)

# Test 1: Generate Mockup
print("\n1. Testing POST /api/v1/mockups/generate/")
response = requests.post(
    f"{BASE_URL}/api/v1/mockups/generate/",
    json={"text": "Test Mockup", "shirt_color": ["white", "black", "blue", "yellow"]}
)
print(f"Status Code: {response.status_code}")
result = response.json()
print(f"Response: {json.dumps(result, indent=2)}")

if response.status_code == 202:
    task_id = result.get("task_id")
    print(f"\n✅ Task created: {task_id}")
    
    # Test 2: Check Task Status
    print("\n2. Testing GET /api/v1/tasks/{task_id}/")
    print("Waiting 5 seconds for task to complete...")
    time.sleep(5)
    
    response = requests.get(f"{BASE_URL}/api/v1/tasks/{task_id}/")
    print(f"Status Code: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")
    
    if result.get("status") == "SUCCESS":
        print(f"\n✅ Task completed successfully!")
        print(f"Generated {len(result.get('results', []))} images")
    else:
        print(f"\n⚠️ Task status: {result.get('status')}")
    
    # Test 3: Get Mockup History
    print("\n3. Testing GET /api/mockups/")
    response = requests.get(f"{BASE_URL}/api/mockups/")
    print(f"Status Code: {response.status_code}")
    result = response.json()
    print(f"Total mockups: {len(result.get('results', []))}")
    if result.get('results'):
        print(f"First mockup: {json.dumps(result['results'][0], indent=2)}")
    
    print("\n" + "=" * 50)
    print("✅ All tests completed!")
else:
    print(f"\n❌ Failed to create task. Status: {response.status_code}")
```

Run it:
```bash
python test_api.py
```

---

## Manual Verification Checklist

- [ ] Django server starts without errors
- [ ] Celery worker starts and shows "ready to accept tasks"
- [ ] POST to `/api/v1/mockups/generate/` returns `task_id` and `status: "PENDING"`
- [ ] Celery worker terminal shows task received and processing
- [ ] GET to `/api/v1/tasks/{task_id}/` returns `status: "SUCCESS"` after processing
- [ ] `results` array contains 4 image URLs
- [ ] Image URLs are accessible in browser
- [ ] GET to `/api/mockups/` returns list of mockups
- [ ] Generated images exist in `media/mockups/` folder
- [ ] Database has records in `Mockup` and `GeneratedImage` tables

---

## Troubleshooting

**If task stays in PENDING:**
- Check Celery worker is running
- Check Redis is running
- Check worker terminal for errors

**If images don't generate:**
- Check `assets/shirts/` folder has: `white.png`, `black.png`, `blu.jpg`, `yellow.png`
- Check worker terminal for error messages
- Verify `media/mockups/` folder exists and is writable

**If API returns 500 error:**
- Check Django server terminal for traceback
- Verify database migrations: `python manage.py migrate`
- Check all dependencies installed: `pip install -r requirements.txt`

