# 🌾 Krishi Sahyog
### AI-Powered Agricultural Decision Support & Field Intelligence Platform

Krishi Sahyog is an AI-assisted agricultural decision-support platform that brings crop disease detection, soil health analysis, weather advisory, satellite-based vegetation monitoring, mandi price intelligence, and conversational AI into a unified application.

The objective is to help farmers interpret agricultural information and make more informed field-level decisions through an accessible web interface.

---

## ✨ Features

### 1. Crop Disease Detection
- Upload crop leaf images for disease classification.
- Uses a trained PyTorch MobileNetV2 model.
- Performs image preprocessing and quality checks.
- Returns predicted classes, confidence scores, and alternative predictions.

### 2. Soil Health Advisory
- Accepts soil parameters including nitrogen, phosphorus, potassium, and pH.
- Generates soil-based recommendations.
- Supports Soil Health Card image extraction through OCR.
- Allows users to review extracted values before generating an advisory.

### 3. Weather Advisory
- Provides weather-informed agricultural recommendations.
- Uses configured weather service credentials.
- Helps users understand weather-related agricultural risks.

### 4. Satellite Vegetation Analysis
- Accepts agricultural field boundaries in GeoJSON format.
- Uses Sentinel-2 satellite imagery.
- Calculates NDVI and EVI vegetation indices.
- Supports field-level vegetation assessment.

### 5. Mandi Price Intelligence
- Provides mandi price information and filtering.
- Supports nearby mandi discovery.
- Generates selling-strategy recommendations using available market information.

### 6. Intelligence Core
- Combines available agricultural context from different modules.
- Generates consolidated field intelligence reports.
- Integrates soil, weather, and satellite information where available.

### 7. AI Farmer Assistant
- Provides a conversational interface for agricultural questions.
- Uses configured Gemini AI integration and available farm context.

---

## 🏗️ Architecture

```text
                 FARMER
                    |
                    v
              REACT FRONTEND
                    |
                    v
              FASTAPI BACKEND
                    |
        +-----------+-----------+
        |           |           |
        v           v           v
     Disease      Soil       Weather
    Detection   Advisory    Advisory
        |           |           |
        v           v           v
    MobileNetV2   OCR       Weather API

        +-----------+-----------+
                    |
             +------+------+
             |             |
             v             v
        Satellite        Mandi
        Analysis       Intelligence
             |             |
             v             v
         Sentinel-2    Mandi Database

                    |
                    v
             INTELLIGENCE CORE
                    |
                    v
            AI FARMER ASSISTANT
                    |
                    v
             REPORTS & RESULTS
```

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | React, JavaScript, CSS |
| Frontend tooling | Vite, npm |
| Backend | Python, FastAPI |
| API server | Uvicorn |
| Machine Learning | PyTorch, Torchvision, MobileNetV2 |
| Image processing | Pillow |
| OCR | RapidOCR ONNX Runtime |
| Data processing | NumPy, Scikit-learn |
| AI integration | Google Gemini |
| Weather integration | OpenWeather |
| Model ecosystem | Hugging Face |
| Geospatial input | GeoJSON |
| Satellite data | Sentinel-2 |
| Database | SQLite |

---

## 📁 Project Structure

```text
Krishi_Sahyog/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── routes/
│   │   └── services/
│   │
│   ├── models/
│   ├── scripts/
│   ├── training/
│   │
│   ├── .env.example
│   ├── requirements.txt
│   ├── requirements-ml.txt
│   └── requirements-ocr.txt
│
├── frontend/
│   ├── src/
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   └── vite.config.js
│
├── INSTALL.txt
├── INSTALL-KRS-DISEASE-MODULE.txt
├── .gitignore
└── README.md
```

---

## ⚙️ Installation & Setup

### Prerequisites

- Python and pip
- Node.js and npm
- Git
- Required API credentials for enabled external services

### 1. Clone the repository

```bash
git clone https://github.com/AKSHAT-yash-107/Krishi_Sahyog.git

cd Krishi_Sahyog
```

### 2. Configure the backend

```powershell
cd backend

python -m venv .venv

.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip

pip install -r requirements.txt
pip install -r requirements-ml.txt
pip install -r requirements-ocr.txt
```

### 3. Configure environment variables

Create your environment file:

```powershell
Copy-Item .env.example .env
```

Add your own API credentials to `backend/.env`.

Example configuration:

```env
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
GEMINI_MODEL=gemini-2.0-flash

OPENWEATHER_API_KEY=YOUR_OPENWEATHER_API_KEY

HF_TOKEN=YOUR_HUGGINGFACE_TOKEN
HF_MODEL=linkanjarad/mobilenet_v2_1.0_224-plant-disease
```

Never commit your actual `.env` file or API credentials.

### 4. Start the backend

From the `backend` directory:

```powershell
uvicorn app.main:app --reload
```

Backend API:

`http://127.0.0.1:8000`

API documentation:

`http://127.0.0.1:8000/docs`

Health check:

`http://127.0.0.1:8000/api/health`

### 5. Start the frontend

Open another terminal:

```powershell
cd frontend

npm install

npm run dev
```

Vite starts the frontend and displays its local URL.

---

## 🔌 API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | GET | Backend health check |
| `/api/disease/classify` | POST | Crop disease classification |
| `/api/soil/advisory` | POST | Soil health advisory |
| `/api/soil/ocr` | POST | Soil card OCR |
| `/api/weather/advisory` | POST | Weather advisory |
| `/api/satellite/analyze` | POST | Satellite vegetation analysis |
| `/api/assistant/ask` | POST | AI farmer assistant |
| `/api/mandi/filters` | GET | Mandi filters |
| `/api/mandi/nearest` | GET | Nearby mandi discovery |
| `/api/mandi/prices` | GET | Mandi price information |
| `/api/mandi/selling-strategy` | POST | Selling strategy |
| `/api/intelligence/analyze` | POST | Consolidated field intelligence |

---

## 🧠 Machine Learning Workflow

The current disease classification service uses a trained MobileNetV2 architecture implemented using PyTorch.

The inference pipeline consists of:

1. Image upload and RGB conversion.
2. Image quality assessment.
3. Image resizing and normalization.
4. MobileNetV2 inference.
5. Softmax-based class scoring.
6. Top predictions and alternative class results.

The model is intended to assist agricultural assessment, not replace professional diagnosis.

---

## 🛰️ Satellite Vegetation Indices

Krishi Sahyog uses vegetation indices to assess vegetation conditions.

**Normalized Difference Vegetation Index (NDVI)**

NDVI = (NIR - Red) / (NIR + Red)

**Enhanced Vegetation Index (EVI)**

EVI = 2.5 × (NIR - Red) / (NIR + 6 × Red - 7.5 × Blue + 1)

These indicators help interpret vegetation conditions. They should not be treated as definitive crop disease diagnoses.

---

## ⚠️ Limitations

- Disease classification results depend on image quality and model training data.
- Real-world field performance may differ from controlled dataset performance.
- OCR extraction can be inaccurate; extracted soil values and units must be verified.
- Satellite vegetation indices provide indirect vegetation observations.
- Weather and AI services depend on external API availability and configuration.
- Mandi recommendations depend on the quality and freshness of available market data.
- AI-generated recommendations should be independently validated before important agricultural decisions.

---

## 🔮 Future Improvements

- Improved crop disease datasets and model evaluation.
- More robust geospatial analytics.
- Regional-language support.
- Historical vegetation monitoring.
- Expanded agricultural knowledge retrieval.
- Better market intelligence and price forecasting.
- Field validation and farmer feedback integration.

---

## 👨‍💻 Author

**Akshat Shrivastav**

B.Tech — Computer Science and Engineering

GitHub: [AKSHAT-yash-107](https://github.com/AKSHAT-yash-107)

**Repository:** [Krishi Sahyog](https://github.com/AKSHAT-yash-107/Krishi_Sahyog)

---

*Krishi Sahyog — Bringing agricultural intelligence together in one platform.*
