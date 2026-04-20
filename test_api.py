import requests
import base64
import json
from pathlib import Path

SPACE_URL = "https://mohamedhamdey-odometer-detector.hf.space"
IMAGE_PATH = "test_image.jpg"  # 

def encode_image(path):
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    ext = Path(path).suffix.lstrip(".")
    return f"data:image/{ext};base64,{b64}"

# STEP 1: Send image to correct endpoint
print("Sending image...")
r = requests.post(
    f"{SPACE_URL}/gradio_api/call/detect_and_show",  
    headers={"Content-Type": "application/json"},
    json={
        "data": [
            {
                "url": encode_image(IMAGE_PATH),  
                "path": None,
                "size": None,
                "orig_name": Path(IMAGE_PATH).name,
                "mime_type": "image/jpeg"
            }
        ]
    },
    timeout=60
)

print(f"Status : {r.status_code}")
print(f"Response: {r.text[:300]}\n")

if r.status_code != 200:
    print("Failed at Step 1")
    exit()

event_id = r.json().get("event_id")
print(f"Event ID: {event_id}\n")

# STEP 2: Get result
print("Fetching result...")
r2 = requests.get(
    f"{SPACE_URL}/gradio_api/call/detect_and_show/{event_id}",
    timeout=60
)

print(f"Status: {r2.status_code}")
print(f"Raw:\n{r2.text[:1000]}\n")

# Parse SSE response
for line in r2.text.splitlines():
    if line.startswith("data:"):
        data_str = line[len("data:"):].strip()
        try:
            data = json.loads(data_str)
            print("Final Result:")
            print(json.dumps(data, indent=2))
        except:
            pass