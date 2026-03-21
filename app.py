import gradio as gr
from ultralytics import YOLO
from PIL import Image
import numpy as np

# Load your trained model
model = YOLO('E:/Desktop/OdoVision/runs/detect/odometer_project/exp12/weights/best.pt')

def extract_odometer(results):
    """
    Extract odometer reading from YOLO detection results
    
    Classes:
    - 1-10: Digits 0-9
    - 0, 11, 12: '-', 'X', 'odometer' (ignored)
    """
    detections = []

    for box in results.boxes:
        cls = int(box.cls[0])
        conf = float(box.conf[0])
        x1, y1, x2, y2 = box.xyxy[0]

        x_center = float((x1 + x2) / 2)

        # 🚨 Ignore unwanted classes
        if cls in [0, 11, 12]:  # '-', 'X', 'odometer'
            continue

        # 🚨 Confidence filter (tuneable)
        if conf < 0.4:
            continue

        digit = cls - 1  # shift to 0–9

        detections.append({
            "digit": digit,
            "x": x_center,
            "conf": conf
        })

    # 🚨 If nothing detected
    if len(detections) == 0:
        return {
            "reading": None,
            "confidence": 0,
            "status": "no_digits_detected"
        }

    # 🔹 STEP 1 — Sort left → right
    detections = sorted(detections, key=lambda d: d["x"])

    # 🔹 STEP 2 — Remove duplicates (overlapping digits)
    filtered = []
    MIN_DISTANCE = 10  # pixels (tune if needed)

    for d in detections:
        if not filtered:
            filtered.append(d)
        else:
            if abs(d["x"] - filtered[-1]["x"]) > MIN_DISTANCE:
                filtered.append(d)
            else:
                # keep higher confidence one
                if d["conf"] > filtered[-1]["conf"]:
                    filtered[-1] = d

    detections = filtered

    # 🔹 STEP 3 — Build number
    number = "".join(str(d["digit"]) for d in detections)

    # 🔹 STEP 4 — Confidence score
    avg_conf = sum(d["conf"] for d in detections) / len(detections)

    # 🔹 STEP 5 — Validation rules
    if len(number) < 4:
        status = "low_confidence_short_number"
    elif avg_conf < 0.6:
        status = "low_confidence"
    else:
        status = "ok"

    return {
        "reading": number,
        "confidence": round(avg_conf, 3),
        "digits_detected": len(detections),
        "status": status
    }


def detect_and_read_odometer(image):
    """
    Main API function: Detect and read odometer from dashboard image
    
    Args:
        image: PIL Image or numpy array
    
    Returns:
        dict: {
            "success": bool,
            "odometer": str,
            "confidence": float,
            "message": str
        }
    """
    try:
        # Convert to numpy array if needed
        if isinstance(image, Image.Image):
            image_array = np.array(image)
        else:
            image_array = image
        
        # Run YOLO detection
        results = model.predict(
            image_array,
            conf=0.3,  # Lower threshold since we filter in extract_odometer
            iou=0.45,
            verbose=False
        )[0]  # Get first result
        
        # Extract odometer reading
        extraction = extract_odometer(results)
        
        # Format response based on status
        if extraction["status"] == "ok":
            return {
                "success": True,
                "odometer": extraction["reading"],
                "confidence": extraction["confidence"],
                "digits_detected": extraction["digits_detected"],
                "message": "Odometer reading extracted successfully"
            }
        
        elif extraction["status"] == "low_confidence":
            return {
                "success": False,
                "odometer": extraction["reading"],
                "confidence": extraction["confidence"],
                "digits_detected": extraction["digits_detected"],
                "message": "Low confidence. Please verify or enter manually."
            }
        
        elif extraction["status"] == "low_confidence_short_number":
            return {
                "success": False,
                "odometer": extraction["reading"],
                "confidence": extraction["confidence"],
                "digits_detected": extraction["digits_detected"],
                "message": f"Only {len(extraction['reading'])} digits detected. Expected 4-7 digits."
            }
        
        else:  # no_digits_detected
            return {
                "success": False,
                "odometer": None,
                "confidence": 0.0,
                "digits_detected": 0,
                "message": "No odometer digits detected in image"
            }
        
    except Exception as e:
        return {
            "success": False,
            "odometer": None,
            "confidence": 0.0,
            "digits_detected": 0,
            "message": f"Error: {str(e)}"
        }


# Create Gradio Interface
iface = gr.Interface(
    fn=detect_and_read_odometer,
    inputs=gr.Image(type="pil", label="Upload Dashboard Image"),
    outputs=gr.JSON(label="Detection Result"),
    title="🚗 Odometer Detection & Reading API",
    description="""
    Upload a dashboard image to automatically detect and read the odometer.
    
    **How it works:**
    1. Detects individual digits (0-9) in the odometer
    2. Sorts digits left-to-right
    3. Removes duplicate/overlapping detections
    4. Validates reading (4-7 digits expected)
    
    **Model Performance:**
    - Detection accuracy: 91.2% mAP
    - Precision: 92.9%
    - Recall: 85.4%
    
    **API Response Format:**
```json""")