
import json
from pathlib import Path
from functools import lru_cache
from io import BytesIO

import numpy as np
import torch

from PIL import Image, UnidentifiedImageError
from torchvision import models, transforms


# ============================================================
# PATHS AND CONFIGURATION
# ============================================================

BACKEND_DIR = Path(__file__).resolve().parents[2]
MODEL_DIR = BACKEND_DIR / "models"

MODEL_PATH = MODEL_DIR / "plant_disease_mobilenetv2.pth"
LABELS_PATH = MODEL_DIR / "class_names.json"

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

IMAGE_SIZE = 224

MEAN = [0.485, 0.456, 0.406]
STD = [0.229, 0.224, 0.225]

CONFIDENCE_THRESHOLD = 0.55


# ============================================================
# CUSTOM EXCEPTIONS
# ============================================================

class ImageValidationError(ValueError):
    pass


# ============================================================
# LOAD CLASS NAMES
# ============================================================

def load_class_names():

    if not LABELS_PATH.exists():
        raise FileNotFoundError(
            f"Class names file not found: {LABELS_PATH}"
        )

    metadata = json.loads(
        LABELS_PATH.read_text(encoding="utf-8")
    )

    labels = metadata.get("class_names")

    if not isinstance(labels, list) or not labels:
        raise RuntimeError(
            "Invalid MobileNetV2 class names."
        )

    if len(labels) != 38:
        raise RuntimeError(
            f"Expected 38 classes, found {len(labels)}."
        )

    return labels, metadata


# ============================================================
# IMAGE PREPROCESSING
# ============================================================

def build_preprocessing():

    return transforms.Compose([

        transforms.Resize(256),

        transforms.CenterCrop(IMAGE_SIZE),

        transforms.ToTensor(),

        transforms.Normalize(
            mean=MEAN,
            std=STD
        )

    ])


# ============================================================
# LOAD MOBILENETV2 MODEL
# ============================================================

@lru_cache(maxsize=1)
def load_mobilenet_model():

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"MobileNetV2 checkpoint not found: {MODEL_PATH}"
        )

    labels, metadata = load_class_names()

    # Create MobileNetV2 architecture.
    # weights=None because we load our trained checkpoint.
    model = models.mobilenet_v2(weights=None)

    # Replace original classification layer with 38 classes.
    model.classifier[1] = torch.nn.Linear(
        model.last_channel,
        len(labels)
    )

    # Load trained weights.
    state = torch.load(
        MODEL_PATH,
        map_location=DEVICE
    )

    model.load_state_dict(state)

    model.to(DEVICE)

    model.eval()

    preprocess = build_preprocessing()

    return model, labels, preprocess, metadata


# ============================================================
# IMAGE QUALITY VALIDATION
# ============================================================

def image_quality_check(image):

    width, height = image.size

    if width < 128 or height < 128:
        raise ImageValidationError(
            "Image resolution is too small. "
            "Upload an image of at least 128 x 128 pixels."
        )

    gray = np.asarray(
        image.convert("L").resize((256, 256)),
        dtype=np.float32
    )

    brightness = float(np.mean(gray))

    if brightness < 20:
        raise ImageValidationError(
            "Image is too dark. Take another photograph "
            "in better lighting."
        )

    if brightness > 245:
        raise ImageValidationError(
            "Image is overexposed. Retake it without "
            "direct glare."
        )

    # Variance of Laplacian for blur detection.
    laplacian = (
        -4 * gray
        + np.roll(gray, 1, axis=0)
        + np.roll(gray, -1, axis=0)
        + np.roll(gray, 1, axis=1)
        + np.roll(gray, -1, axis=1)
    )

    blur_score = float(np.var(laplacian))

    if blur_score < 20:
        raise ImageValidationError(
            "Image appears blurry. Hold the camera steady "
            "and upload a sharper photograph."
        )

    return {
        "width": width,
        "height": height,
        "brightness": round(brightness, 2),
        "blur_score": round(blur_score, 2),
        "quality_check": "passed"
    }


# ============================================================
# FORMAT MODEL RESPONSE
# ============================================================

def make_response(
    prediction,
    confidence,
    alternatives,
    metadata,
    uncertain,
    quality
):

    display_prediction = prediction

    if uncertain:
        display_prediction = (
            "Uncertain — retake image or seek expert review."
        )

    return {

        "prediction": display_prediction,

        "predicted_class": prediction,

        "confidence": round(float(confidence), 4),

        "uncertain": uncertain,

        "alternatives": alternatives,

        "model": "HAL Local MobileNetV2",

        "model_type": (
            "Locally trained MobileNetV2 "
            "transfer-learning classifier"
        ),

        "dataset": metadata.get(
            "dataset",
            "PlantVillage"
        ),

        "test_accuracy": metadata.get(
            "test_accuracy"
        ),

        "image_quality": quality,

        "disclaimer": (
            "Preliminary image-based screening only. "
            "PlantVillage images are largely controlled-condition "
            "images; field performance may be lower. "
            "Do not apply pesticides or make treatment decisions "
            "from this prediction alone. Confirm with a qualified "
            "agricultural expert."
        )

    }


# ============================================================
# MAIN DISEASE CLASSIFICATION FUNCTION
# ============================================================

async def classify_leaf(
    image_bytes: bytes,
    content_type: str
) -> dict:

    # Validate empty upload.
    if not image_bytes:
        raise ImageValidationError(
            "The uploaded image is empty."
        )

    # Read uploaded image.
    try:

        image = Image.open(
            BytesIO(image_bytes)
        ).convert("RGB")

    except (
        UnidentifiedImageError,
        OSError
    ):

        raise ImageValidationError(
            "Could not read this image. "
            "Upload a valid JPG, PNG or WEBP."
        )

    # Check image quality.
    quality = image_quality_check(image)

    # Always load MobileNetV2.
    # Custom CNN is deliberately excluded from production.
    model, labels, preprocess, metadata = (
        load_mobilenet_model()
    )

    # Apply exactly the same preprocessing used during training.
    tensor = (
        preprocess(image)
        .unsqueeze(0)
        .to(DEVICE)
    )

    # Run inference.
    with torch.inference_mode():

        logits = model(tensor)

        probabilities = torch.softmax(
            logits,
            dim=1
        )[0].cpu().numpy()

    # Validate model output.
    if len(probabilities) != len(labels):
        raise RuntimeError(
            "Model output count does not match class names."
        )

    if not np.all(np.isfinite(probabilities)):
        raise RuntimeError(
            "Model produced invalid prediction scores."
        )

    # Get top four predictions.
    top_indices = np.argsort(
        probabilities
    )[::-1][:min(4, len(labels))]

    best_idx = int(top_indices[0])

    prediction = labels[best_idx]

    confidence = float(
        probabilities[best_idx]
    )

    # Other predictions.
    alternatives = [

        {
            "label": labels[int(idx)],

            "confidence": round(
                float(probabilities[int(idx)]),
                4
            )

        }

        for idx in top_indices[1:]

    ]

    # Confidence-based uncertainty.
    uncertain = (
        confidence < CONFIDENCE_THRESHOLD
    )

    return make_response(
        prediction=prediction,
        confidence=confidence,
        alternatives=alternatives,
        metadata=metadata,
        uncertain=uncertain,
        quality=quality
    )
