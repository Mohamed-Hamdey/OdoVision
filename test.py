import gradio as gr
from ultralytics import YOLO
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os
import cv2

# Load your trained model with error handling
MODEL_PATH = 'E:/Desktop/OdoVision/runs/detect/odometer_project/exp12/weights/best.pt'

def load_model():
    """Load YOLO model with fallback options"""
    if os.path.exists(MODEL_PATH):
        return YOLO(MODEL_PATH)
    else:
        # Try to download from Hugging Face if not found
        print(f"Model {MODEL_PATH} not found, attempting to download...")
        from huggingface_hub import hf_hub_download
        model_path = hf_hub_download(
            repo_id="mohamedhamdey/odometer-detector",  # Update with your HF repo
            filename="best.pt"
        )
        return YOLO(model_path)

try:
    model = load_model()
    print("✅ Model loaded successfully")
except Exception as e:
    print(f"❌ Failed to load model: {e}")
    model = None

def extract_odometer(results):
    """
    Extract odometer reading from YOLO detection results
    
    Classes:
    - 1-10: Digits 0-9
    - 0, 11, 12: '-', 'X', 'odometer' (ignored)
    """
    detections = []

    # Check if there are any detections
    if results.boxes is None:
        return {
            "reading": None,
            "confidence": 0,
            "status": "no_digits_detected"
        }

    for box in results.boxes:
        cls = int(box.cls[0])
        conf = float(box.conf[0])
        x1, y1, x2, y2 = box.xyxy[0]

        x_center = float((x1 + x2) / 2)

        # Ignore unwanted classes
        if cls in [0, 11, 12]:  # '-', 'X', 'odometer'
            continue

        # Confidence filter
        if conf < 0.4:
            continue

        digit = cls - 1  # shift to 0–9

        detections.append({
            "digit": digit,
            "x": x_center,
            "y": float((y1 + y2) / 2),  # Add y coordinate for filtering
            "conf": conf,
            "bbox": [float(x1), float(y1), float(x2), float(y2)]
        })

    # If nothing detected
    if len(detections) == 0:
        return {
            "reading": None,
            "confidence": 0,
            "status": "no_digits_detected"
        }

    # Sort left → right
    detections = sorted(detections, key=lambda d: d["x"])

    # Remove duplicates (overlapping digits)
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

    # Build number
    number = "".join(str(d["digit"]) for d in detections)

    # Confidence score
    avg_conf = sum(d["conf"] for d in detections) / len(detections)

    # Validation rules
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
        "detections": detections,  # Store for visualization
        "status": status
    }

def draw_detections(image_array, extraction):
    """Draw bounding boxes and digits on the image"""
    if isinstance(image_array, np.ndarray):
        img = image_array.copy()
    else:
        img = np.array(image_array)
    
    # Convert to PIL for drawing
    img_pil = Image.fromarray(img)
    draw = ImageDraw.Draw(img_pil)
    
    # Try to load a font, fallback to default
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 20)
    except:
        font = ImageFont.load_default()
    
    # Draw each detection
    if "detections" in extraction and extraction["detections"]:
        for d in extraction["detections"]:
            x1, y1, x2, y2 = d["bbox"]
            digit = d["digit"]
            conf = d["conf"]
            
            # Draw box
            draw.rectangle([x1, y1, x2, y2], outline="red", width=3)
            
            # Draw label
            label = f"{digit} ({conf:.2f})"
            draw.text((x1, y1-25), label, fill="red", font=font)
    
    return np.array(img_pil)

def detect_and_read_odometer(image):
    """
    Main API function: Detect and read odometer from dashboard image
    
    Args:
        image: PIL Image or numpy array
    
    Returns:
        tuple: (json_result, annotated_image)
    """
    # Check if model loaded
    if model is None:
        return {
            "success": False,
            "odometer": None,
            "confidence": 0.0,
            "digits_detected": 0,
            "message": "Model not loaded. Please check model file."
        }, None
    
    try:
        # Convert to numpy array if needed
        if isinstance(image, Image.Image):
            image_array = np.array(image)
        else:
            image_array = image
        
        # Run YOLO detection
        results = model.predict(
            image_array,
            conf=0.3,
            iou=0.45,
            verbose=False
        )[0]
        
        # Extract odometer reading
        extraction = extract_odometer(results)
        
        # Draw annotations if detections exist
        annotated_image = None
        if extraction["status"] != "no_digits_detected":
            annotated_image = draw_detections(image_array, extraction)
        else:
            annotated_image = image_array
        
        # Format response based on status
        if extraction["status"] == "ok":
            return {
                "success": True,
                "odometer": extraction["reading"],
                "confidence": extraction["confidence"],
                "digits_detected": extraction["digits_detected"],
                "message": "Odometer reading extracted successfully"
            }, annotated_image
        
        elif extraction["status"] == "low_confidence":
            return {
                "success": False,
                "odometer": extraction["reading"],
                "confidence": extraction["confidence"],
                "digits_detected": extraction["digits_detected"],
                "message": "Low confidence reading. Please verify or enter manually."
            }, annotated_image
        
        elif extraction["status"] == "low_confidence_short_number":
            return {
                "success": False,
                "odometer": extraction["reading"],
                "confidence": extraction["confidence"],
                "digits_detected": extraction["digits_detected"],
                "message": f"Only {len(extraction['reading'])} digits detected. Expected 4-7 digits."
            }, annotated_image
        
        else:  # no_digits_detected
            return {
                "success": False,
                "odometer": None,
                "confidence": 0.0,
                "digits_detected": 0,
                "message": "No odometer digits detected in image"
            }, annotated_image
        
    except Exception as e:
        import traceback
        error_msg = f"Error: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)  # Log for debugging
        return {
            "success": False,
            "odometer": None,
            "confidence": 0.0,
            "digits_detected": 0,
            "message": f"Error: {str(e)}"
        }, None

# Create Gradio Interface with better UI
with gr.Blocks(title="Odometer Detection System") as demo:
    gr.Markdown("""
    # 🚗 Automatic Odometer Reading System
    
    Upload a dashboard image to automatically detect and read the odometer using YOLOv8 object detection.
    
    ### How it works:
    1. **Detection**: YOLOv8 detects individual digits (0-9) in the odometer
    2. **Sorting**: Digits are sorted left-to-right based on their position
    3. **Filtering**: Duplicate/overlapping detections are removed
    4. **Validation**: The reading is validated (4-7 digits expected)
    5. **Confidence**: Each digit has a confidence score, averaged for the final reading
    
    ### Model Performance:
    - **Detection Accuracy**: 91.2% mAP
    - **Precision**: 92.9%
    - **Recall**: 85.4%
    """)
    
    with gr.Row():
        with gr.Column():
            input_image = gr.Image(type="pil", label="Upload Dashboard Image")
            submit_btn = gr.Button("🔍 Detect Odometer", variant="primary")
        
        with gr.Column():
            output_json = gr.JSON(label="Detection Result")
    
    with gr.Row():
        output_image = gr.Image(label="Annotated Image with Detected Digits")
    
    # Example images (optional)
    gr.Examples(
        examples=[
            ["sample_dashboard1.jpg"],
            ["sample_dashboard2.jpg"],
        ],
        inputs=input_image,
        label="Try these examples"
    )
    
    # Connect the button
    submit_btn.click(
        fn=detect_and_read_odometer,
        inputs=input_image,
        outputs=[output_json, output_image]
    )
    
    # Add instructions
    gr.Markdown("""
    ### 📋 Instructions:
    - Upload a clear image of the vehicle dashboard showing the odometer
    - Ensure the odometer digits are visible and not blurry
    - The system will detect digits and attempt to read the number
    - Results include confidence score and annotated image
    
    ### ⚠️ Notes:
    - Works best with clear, well-lit images
    - Supports odometers with 4-7 digits
    - Low confidence readings should be manually verified
    """)

# Launch the app
if __name__ == "__main__":
    demo.launch()