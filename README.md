# 🌾 Krishi Sahyog — AI-Powered Agricultural Decision Support Platform

Krishi Sahyog is an AI-assisted decision-support web app for farmers. It combines crop disease detection, soil advisory (with Soil Health Card OCR), weather advisory, satellite vegetation analysis, mandi price intelligence, and a conversational farmer assistant behind one React + FastAPI application.

> ⚠️ Decision support only. Outputs are not a replacement for expert agronomic advice. See [Limitations](#️-limitations).

## 🚀 Key Features

### 1. Crop Disease Detection
- Upload a crop or leaf image for disease classification.
- Trained MobileNetV2 model (PyTorch) returns the predicted class, confidence score, and alternative predictions.
- Runs an image-quality check before inference.

### 2. Soil Health Advisory
- Takes nitrogen, phosphorus, potassium and pH values and generates recommendations.
- **Soil Health Card OCR:** upload a clear JPG/PNG/WEBP photo of a card, extract the values, review and correct them, then generate the advisory.
- If the Gemini service is unavailable, the soil endpoint returns a cautious summary of your inputs instead of failing with HTTP 502.

### 3. Weather Advisory
- Weather-informed recommendations and precautions for farm operations.

### 4. Satellite Vegetation Analysis
- Takes a field boundary as GeoJSON and uses Sentinel-2 imagery.
- Computes NDVI and EVI to assess vegetation condition across the field.

### 5. Mandi Price Intelligence
- Price lookup with filtering, nearest-mandi discovery, and selling-strategy suggestions.

### 6. Intelligence Core
- Merges soil, weather and satellite context into one field-level report.

### 7. AI Farmer Assistant
- Chat interface that uses the available farm context to answer agricultural questions.

## 🏗️ System Architecture

```text
                 FARMER
                    |
                    v
             REACT FRONTEND (Vite)
                    |
                    v
              FASTAPI BACKEND
                    |
       +------------+-------------+
       |            |             |
       v            v             v
   Disease       Soil &         Weather
  Detection      Advisory       Advisory
       |            |             |
       v            v             v
  MobileNetV2   Soil data/OCR   Weather data

       +------------+-------------+
                    |
          +---------+---------+
          |                   |
          v                   v
    Satellite Analysis    Mandi Intelligence
          |                   |
          v                   v
     Sentinel-2           Mandi database

                    |
                    v
             INTELLIGENCE CORE
                    |
                    v
            AI FARMER ASSISTANT
                    |
                    v
             RESULTS & REPORTS
```

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | React, JavaScript, CSS, Vite |
| Backend | Python, FastAPI, Uvicorn |
| Machine Learning | PyTorch, Torchvision, MobileNetV2 |
| Image Processing | Pillow (PIL) |
| Generative AI | Google Gemini (advisories and assistant) |
| Satellite Analysis | Sentinel-2, NDVI, EVI |
| Geospatial Input | GeoJSON |
| Database | SQLite |
| API | REST (JSON, multipart for image uploads) |

## 📂 Project Structure

```text
Krishi_Sahyog/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── routes/
│   │   └── services/
│   ├── models/
│   ├── training/
│   └── data/
├── frontend/
│   ├── src/
│   ├── public/
│   └── package.json
├── INSTALL.txt
├── .gitignore
└── README.md
```

## ⚙️ Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm
- Git
- A Google Gemini API key (for advisories and the assistant)

### 1. Clone

```bash
git clone https://github.com/AKSHAT-yash-107/Krishi_Sahyog.git
cd Krishi_Sahyog
```

### 2. Backend

```bash
cd backend
python -m venv .venv
```

Activate the environment:

```bash
# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate
```

Install dependencies and start the API:

```bash
pip install -r requirements.txt
pip install -r requirements-ocr.txt   # needed for Soil Health Card OCR
uvicorn app.main:app --reload
```

The API runs at `http://127.0.0.1:8000`; interactive docs are at `http://127.0.0.1:8000/docs`.

### 3. Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the local URL Vite prints (usually `http://localhost:5173`).

### 4. Configuration

Create a `.env` file in `backend/` with your credentials:

```env
GEMINI_API_KEY=your_key_here
```

Place the trained disease-model checkpoint in `backend/models/` before using the disease module. Modules that depend on missing credentials or files will not work until they are provided.

## 🔌 API Reference

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/disease/classify` | POST | Crop disease classification (image upload) |
| `/api/soil/advisory` | POST | Soil advisory from N, P, K, pH |
| `/api/soil/ocr` | POST | Extract values from a Soil Health Card (multipart field `image`) |
| `/api/weather/advisory` | POST | Weather advisory |
| `/api/satellite/analyze` | POST | NDVI/EVI analysis for a GeoJSON field |
| `/api/mandi/prices` | GET | Mandi prices |
| `/api/mandi/nearest` | GET | Nearby mandis |
| `/api/mandi/selling-strategy` | POST | Selling strategy |
| `/api/intelligence/analyze` | POST | Consolidated field report |
| `/api/assistant/ask` | POST | AI farmer assistant |

## 🧠 Machine Learning

Disease detection uses a MobileNetV2 trained with PyTorch. Inference steps:

1. Load the image and convert to RGB.
2. Assess image quality.
3. Resize and normalize.
4. Run the model.
5. Apply softmax for class scores.
6. Return top predictions and alternatives.

## ⚠️ Limitations

- Accuracy on controlled datasets may not carry over to real field photos.
- NDVI/EVI describe vegetation condition; they are not disease diagnoses.
- OCR is fallible. Always check extracted soil values and units before generating advice.
- Recommendations depend on input quality; mandi insights depend on data freshness and coverage.
- AI-generated advice should be validated before important agricultural decisions.

## 🔮 Future Improvements

- Disease datasets captured in real field conditions
- More robust geospatial analysis
- Expanded agricultural knowledge base
- Regional-language support
- Historical crop-health monitoring
- Broader market intelligence
- Evaluating recommendation accuracy with real-world feedback

## 👨‍💻 Author

**Akshat Shrivastav** — B.Tech, Computer Science and Engineering
GitHub: [AKSHAT-yash-107](https://github.com/AKSHAT-yash-107)

---

*Krishi Sahyog — Bringing agricultural intelligence together in one platform.*
