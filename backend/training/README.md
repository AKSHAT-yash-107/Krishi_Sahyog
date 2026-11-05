# HAL Local Disease Detector

This module replaces the unavailable Hugging Face inference endpoint with a model
trained locally using MobileNetV2 transfer learning.

## 1. Install dependencies

Open PowerShell in the `backend` folder (the same folder containing `requirements.txt`):

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements-ml.txt
```

If you do not have a virtual environment yet:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-ml.txt
```

## 2. Train a quick first model

```powershell
python training\train_disease_model.py --max-per-class 120 --test-per-class 60 --epochs 2
```

This trains a 38-class model using up to 120 training images and 60 test images per class.
The first run downloads the PlantVillage dataset and ImageNet MobileNetV2 weights.
Allow several GB of free disk space.

For a stronger run after the quick demo:

```powershell
python training\train_disease_model.py --max-per-class 500 --test-per-class 150 --epochs 4
```

Use `--max-per-class 0 --test-per-class 0` to use every available image, if your machine
has enough RAM, disk space and time.

## 3. Start HAL

After training, these files should exist:

- `models/plant_disease_mobilenetv2.pth`
- `models/class_names.json`
- `models/evaluation_report.json`

Start the backend as usual:

```powershell
uvicorn app.main:app --reload --port 8000
```

The existing `POST /api/disease/classify` route and frontend response keys remain compatible.
No `HF_TOKEN` is required for disease detection anymore.

## Notes

- This is transfer learning: ImageNet-pretrained MobileNetV2 features plus a disease
  classification head trained on PlantVillage.
- The script preserves the dataset's official train/test split when provided.
- The printed held-out test accuracy is the measured result for this run. Do not claim
  a number before training completes.
- PlantVillage has controlled-background images. Good benchmark performance does not
  prove performance on real farm photos. Validate with field images before real use.
- PlantVillage attribution: Mohanty, Hughes & Salathé (2016), "Using Deep Learning for
  Image-Based Plant Disease Detection", Frontiers in Plant Science, DOI:
  10.3389/fpls.2016.01419. Review the dataset's current licence before redistribution.
