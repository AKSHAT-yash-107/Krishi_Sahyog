import json
from pathlib import Path
from functools import lru_cache

import torch
from PIL import Image, UnidentifiedImageError
from torchvision import models, transforms


BACKEND_DIR = Path(__file__).resolve().parents[2]
MODEL_DIR = BACKEND_DIR / "models"
MODEL_PATH = MODEL_DIR / "plant_disease_mobilenetv2.pth"
LABELS_PATH = MODEL_DIR / "class_names.json"

MEAN = [0.485, 0.456, 0.406]
STD = [0.229, 0.224, 0.225]
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


@lru_cache(maxsize=1)
def load_local_model():
    if not MODEL_PATH.exists() or not LABELS_PATH.exists():
        raise RuntimeError(
            "Local disease model is not trained yet. Run "
            "python training/train_disease_model.py from the backend folder."
        )

    metadata = json.loads(LABELS_PATH.read_text(encoding="utf-8"))
    labels = metadata["class_names"]

    model = models.mobilenet_v2(weights=None)
    model.classifier[1] = torch.nn.Linear(model.last_channel, len(labels))
    state = torch.load(MODEL_PATH, map_location=DEVICE)
    model.load_state_dict(state)
    model.to(DEVICE)
    model.eval()

    preprocess = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])
    return model, labels, preprocess, metadata


async def classify_leaf(image_bytes: bytes, content_type: str) -> dict:
    if not image_bytes:
        raise RuntimeError("The uploaded image is empty.")

    try:
        from io import BytesIO
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
    except (UnidentifiedImageError, OSError):
        raise RuntimeError("Could not read this image. Try a JPG or PNG leaf photo.")

    model, labels, preprocess, metadata = load_local_model()
    tensor = preprocess(image).unsqueeze(0).to(DEVICE)

    with torch.inference_mode():
        logits = model(tensor)
        probabilities = torch.softmax(logits, dim=1)[0]
        scores, indices = torch.topk(
            probabilities, k=min(4, len(labels))
        )

    best_idx = int(indices[0].item())
    confidence = float(scores[0].item())
    prediction = labels[best_idx]

    # Low confidence is explicitly surfaced rather than presented as a diagnosis.
    uncertain = confidence < 0.55
    return {
        "prediction": prediction if not uncertain else "Uncertain — retake image or seek expert review",
        "predicted_class": prediction,
        "confidence": round(confidence, 4),
        "uncertain": uncertain,
        "alternatives": [
            {
                "label": labels[int(idx.item())],
                "confidence": round(float(score.item()), 4)
            }
            for score, idx in zip(scores[1:], indices[1:])
        ],
        "model": "HAL Local MobileNetV2",
        "model_type": "locally trained transfer-learning classifier",
        "dataset": "PlantVillage",
        "test_accuracy": metadata.get("test_accuracy"),
        "disclaimer": (
            "Preliminary image-based screening only. PlantVillage images are largely "
            "controlled-condition images; field performance may be lower. Do not apply "
            "pesticides or make treatment decisions from this prediction alone. "
            "Confirm with a qualified agricultural expert."
        )
    }
