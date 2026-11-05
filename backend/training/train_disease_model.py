
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np
import torch
from datasets import load_dataset
from PIL import Image
from sklearn.metrics import accuracy_score, classification_report
from torch import nn
from torch.utils.data import Dataset, DataLoader
from torchvision import models, transforms


BACKEND_DIR = Path(__file__).resolve().parents[1]
MODEL_DIR = BACKEND_DIR / "models"
MODEL_PATH = MODEL_DIR / "plant_disease_mobilenetv2.pth"
LABELS_PATH = MODEL_DIR / "class_names.json"


class LeafDataset(Dataset):

    def __init__(self, hf_dataset, transform):
        self.dataset = hf_dataset
        self.transform = transform

    def __len__(self):
        return len(self.dataset)

    def __getitem__(self, index):
        row = self.dataset[index]

        image = row["image"]

        if not isinstance(image, Image.Image):
            image = Image.fromarray(np.asarray(image))

        image = image.convert("RGB")

        return self.transform(image), int(row["label"])


def balanced_indices(dataset, label_column, max_per_class, seed):

    labels = dataset[label_column]
    grouped = {}

    for idx, label in enumerate(labels):
        grouped.setdefault(int(label), []).append(idx)

    rng = random.Random(seed)
    chosen = []

    for label in sorted(grouped):
        indices = grouped[label]
        rng.shuffle(indices)

        if max_per_class > 0:
            chosen.extend(indices[:max_per_class])
        else:
            chosen.extend(indices)

    rng.shuffle(chosen)

    return chosen


def build_model(num_classes):

    weights = models.MobileNet_V2_Weights.DEFAULT

    model = models.mobilenet_v2(weights=weights)

    model.classifier[1] = nn.Linear(
        model.last_channel,
        num_classes
    )

    return model


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--max-per-class",
        type=int,
        default=120
    )

    parser.add_argument(
        "--test-per-class",
        type=int,
        default=60
    )

    parser.add_argument(
        "--epochs",
        type=int,
        default=2
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=16
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42
    )

    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

    print("\n===================================")
    print(" HAL LOCAL DISEASE DETECTOR")
    print("===================================")
    print(f"Device: {device}")

    # STEP 1: Download dataset

    print("\n[1/6] Loading PlantVillage dataset...")

    ds = load_dataset(
        "geraldmc/plantvillage-full",
        revision="v0.1.0",
        split="train"
    )

    print(f"Total images: {len(ds)}")

    # STEP 2: Recover class names

    print("\n[2/6] Preparing disease classes...")

    class_map = {}

    for idx, label in zip(
        ds["class_idx"],
        ds["class_label"]
    ):
        class_map[int(idx)] = str(label)

    num_classes = len(class_map)

    if num_classes != 38:
        raise RuntimeError(
            f"Expected 38 classes, found {num_classes}"
        )

    class_names = [
        class_map[index]
        for index in range(num_classes)
    ]

    print(f"Number of classes: {num_classes}")

    # STEP 3: Preserve official train/test split

    print("\n[3/6] Creating train and test datasets...")

    split_values = ds["split"]

    train_indices = [
        i for i, value in enumerate(split_values)
        if value == "train"
    ]

    test_indices = [
        i for i, value in enumerate(split_values)
        if value == "test"
    ]

    train_hf = ds.select(train_indices)
    test_hf = ds.select(test_indices)

    train_ids = balanced_indices(
        train_hf,
        "class_idx",
        args.max_per_class,
        args.seed
    )

    test_ids = balanced_indices(
        test_hf,
        "class_idx",
        args.test_per_class,
        args.seed
    )

    train_hf = train_hf.select(train_ids)
    test_hf = test_hf.select(test_ids)

    train_hf = train_hf.rename_column(
        "class_idx", "label"
    )

    test_hf = test_hf.rename_column(
        "class_idx", "label"
    )

    print(f"Training images: {len(train_hf)}")
    print(f"Testing images: {len(test_hf)}")

    # STEP 4: Image preprocessing

    print("\n[4/6] Preparing image transformations...")

    train_transform = transforms.Compose([

        transforms.RandomResizedCrop(
            224,
            scale=(0.75, 1.0)
        ),

        transforms.RandomHorizontalFlip(),

        transforms.ColorJitter(
            brightness=0.15,
            contrast=0.15,
            saturation=0.12
        ),

        transforms.ToTensor(),

        transforms.Normalize(
            [0.485, 0.456, 0.406],
            [0.229, 0.224, 0.225]
        )
    ])

    test_transform = transforms.Compose([

        transforms.Resize(256),

        transforms.CenterCrop(224),

        transforms.ToTensor(),

        transforms.Normalize(
            [0.485, 0.456, 0.406],
            [0.229, 0.224, 0.225]
        )
    ])

    train_loader = DataLoader(
        LeafDataset(train_hf, train_transform),
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=0
    )

    test_loader = DataLoader(
        LeafDataset(test_hf, test_transform),
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=0
    )

    # STEP 5: Build and train MobileNetV2

    print("\n[5/6] Loading pretrained MobileNetV2...")

    model = build_model(num_classes).to(device)

    # Freeze pretrained feature extraction layers.

    for param in model.features.parameters():
        param.requires_grad = False

    optimizer = torch.optim.AdamW(
        model.classifier.parameters(),
        lr=0.001
    )

    criterion = nn.CrossEntropyLoss()

    print("\nStarting training...")

    for epoch in range(args.epochs):

        model.train()

        total_loss = 0.0
        correct = 0
        total = 0

        for batch_number, (images, labels) in enumerate(
            train_loader
        ):

            images = images.to(device)
            labels = labels.to(device)

            optimizer.zero_grad()

            outputs = model(images)

            loss = criterion(outputs, labels)

            loss.backward()

            optimizer.step()

            total_loss += loss.item() * labels.size(0)

            predictions = outputs.argmax(dim=1)

            correct += (
                predictions == labels
            ).sum().item()

            total += labels.size(0)

            if (batch_number + 1) % 20 == 0:
                print(
                    f"Epoch {epoch + 1}/{args.epochs} | "
                    f"Batch {batch_number + 1}/{len(train_loader)}"
                )

        epoch_loss = total_loss / max(total, 1)
        epoch_accuracy = correct / max(total, 1)

        print(
            f"\nEpoch {epoch + 1}/{args.epochs} "
            f"| Loss: {epoch_loss:.4f} "
            f"| Training accuracy: {epoch_accuracy:.4f}"
        )

    # STEP 6: Evaluate on held-out test images

    print("\n[6/6] Evaluating model...")

    model.eval()

    y_true = []
    y_pred = []

    with torch.inference_mode():

        for images, labels in test_loader:

            images = images.to(device)

            outputs = model(images)

            predictions = outputs.argmax(
                dim=1
            ).cpu().tolist()

            y_pred.extend(predictions)
            y_true.extend(labels.tolist())

    accuracy = accuracy_score(y_true, y_pred)

    report = classification_report(
        y_true,
        y_pred,
        labels=list(range(num_classes)),
        target_names=class_names,
        zero_division=0,
        output_dict=True
    )

    print("\n===================================")
    print(" MODEL EVALUATION")
    print("===================================")

    print(f"Held-out test accuracy: {accuracy:.4f}")

    print(
        classification_report(
            y_true,
            y_pred,
            labels=list(range(num_classes)),
            target_names=class_names,
            zero_division=0
        )
    )

    # Save model and metadata

    MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    torch.save(
        model.cpu().state_dict(),
        MODEL_PATH
    )

    metadata = {
        "class_names": class_names,
        "image_size": 224,
        "normalization": {
            "mean": [0.485, 0.456, 0.406],
            "std": [0.229, 0.224, 0.225]
        },
        "test_accuracy": float(accuracy),
        "training_images": len(train_hf),
        "test_images": len(test_hf),
        "backbone": "MobileNetV2",
        "training_method": "Transfer learning",
        "dataset": "geraldmc/plantvillage-full"
    }

    LABELS_PATH.write_text(
        json.dumps(metadata, indent=4),
        encoding="utf-8"
    )

    report_path = MODEL_DIR / "evaluation_report.json"

    report_path.write_text(
        json.dumps({
            "accuracy": float(accuracy),
            "classification_report": report
        }, indent=4),
        encoding="utf-8"
    )

    print("\n===================================")
    print(" TRAINING COMPLETE")
    print("===================================")

    print(f"Model saved: {MODEL_PATH}")
    print(f"Classes saved: {LABELS_PATH}")
    print(f"Evaluation saved: {report_path}")


if __name__ == "__main__":
    main()
