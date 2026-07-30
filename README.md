# Citizen Complaint Prioritization System

A lightweight AI-driven civic complaint solution with a FastAPI backend and Streamlit user interface. The project analyzes complaint images, maps ward location, prioritizes issues, and returns structured output for decision-making.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  Complaint Prioritization System                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐          ┌──────────────────────────┐      │
│  │   Streamlit UI   │  ↔ HTTP  │     FastAPI AI Backend   │      │
│  │  (Local frontend)│          │   (Port 8080)            │      │
│  │                  │          │                          │      │
│  │  • Image upload  │          │  • Image analysis        │      │
│  │  • Location form │          │  • Ward mapping          │      │
│  │  • Result display│          │  • Priority scoring      │
│  └──────────────────┘          └──────────────────────────┘      │
│                                                                 │
│                                 │                               │
│                                 ▼                               │
│                           ┌──────────────┐                      │
│                           │  GeoJSON Ward │                      │
│                           │  mapping data │                      │
│                           └──────────────┘                      │
└─────────────────────────────────────────────────────────────────┘
```

## 🌟 Features

- 📸 Upload civic complaint images
- 🧠 AI-based issue detection and categorization
- 📍 Ward mapping using geographic coordinates
- 🔥 Priority scoring for faster issue handling
- 🧾 Streamlit frontend for easy interaction
- 📊 Predictive output with structured response fields

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Git
- Google AI API Key

### 1. Clone & Setup

```bash
git clone <repository-url>
cd Autonomous_Hacks_Finale
```

### 2. Start the AI Backend (FastAPI)

```bash
cd ai_backend
copy .env.example .env
:: Add your GOOGLE_API_KEY to .env
uv sync
uv run uvicorn main:app --reload --port 8080
```

### 3. Start the Streamlit Frontend

```bash
cd ..\steamlit_frontend
streamlit run app.py
```

---

## 📡 API Endpoints

Base URL: `http://localhost:8080/api/v1`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/analyze/complaint` | POST | Analyze complaint image and return issue details |
| `/analyze/combined` | POST | Analyze image, map ward, and compute priority score |
| `/analyze/prioritize` | POST | Compute priority from dropdown inputs |
| `/verify/completion` | POST | Verify before/after work completion |
| `/analyze/health` | GET | Health check for analysis service |
| `/docs` | GET | Swagger UI documentation |

---

## 🗂️ Project Structure

```
Autonomous_Hacks_Finale/
├── ai_backend/               # FastAPI AI services
│   ├── app/
│   │   ├── agents/           # AI agents and workflow logic
│   │   ├── api/routes/       # FastAPI routers
│   │   ├── api/schemas/      # Pydantic request/response models
│   │   ├── config/           # Settings management
│   │   ├── data/             # GeoJSON ward boundaries
│   │   ├── services/         # Ward mapping and utility services
│   │   └── utils/            # Priority calculation and rules
│   ├── main.py
│   ├── pyproject.toml
│   └── README.md
│
├── steamlit_frontend/        # Streamlit user interface
│   └── app.py
├── README.md                 # Project overview
└── convert_img.py            # Utility script for image conversion
```

---

## 🎯 How It Works

1. User uploads an image in the Streamlit UI.
2. The frontend sends the image and location data to the FastAPI backend.
3. The backend runs image analysis, detects issues, and maps the ward.
4. Priority scoring is computed and returned as structured output.
5. The UI displays detected issues, ward number, and priority results.

---

## 🔧 Technology Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI |
| Frontend | Streamlit |
| AI / Logic | Local vision agents and priority engine |
| Geospatial | GeoJSON ward mapping |
| Package Manager | uv |

---

## 📚 Documentation

- **AI Backend**: `ai_backend/README.md`
- **Streamlit Frontend**: `steamlit_frontend/app.py`
- **API Documentation**: `http://localhost:8080/docs`

---

## 👤 Notes

- This project does not use a Django backend.
- Add your `GOOGLE_API_KEY` to `ai_backend/.env` before running.
- The frontend is configured to call `http://127.0.0.1:8000/api/v1/analyze/combined` by default; update `steamlit_frontend/app.py` if your backend runs on a different port.

---

**Made with ❤️ for AI-first civic complaint prioritization**
 
