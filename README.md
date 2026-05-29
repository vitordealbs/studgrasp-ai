# 🧠 StudGrasp AI

> AI microservice powering the StudGrasp learning platform — flashcard generation, personalized insights, and roadmap scraping.

*IMAGEM QUE AINDA VOU COLOCAR AQUI*

---

## 📖 Overview

**StudGrasp AI** is a Python microservice built with **FastAPI** that acts as the intelligence layer of the StudGrasp platform. It communicates exclusively with the [Java Spring Boot backend](https://github.com/vitordealbs/studgrasp-api) via HTTP — the frontend never talks to this service directly.

*IMAGEM QUE AINDA VOU COLOCAR AQUI*

### What it does

- 🃏 **Flashcard generation** — uses any OpenAI-compatible LLM to generate question/answer pairs for a given topic
- 🤖 **Personalized insights** — analyzes a student's spaced repetition data and returns actionable study recommendations
- 🏫 **Class insights** — aggregates class-wide performance and generates advisor-facing analytics
- 🗺️ **Roadmap scraper** — crawls [roadmap.sh](https://roadmap.sh) and populates all learning tracks into the Java backend

---

## 🏗️ Architecture

```
Frontend  →  Java Spring Boot API  →  studgrasp-ai (this service)
                    ↑
           studgrasp-ai (scraper writes data via Java API)
```

*IMAGEM QUE AINDA VOU COLOCAR AQUI*

The Java backend calls this service for all AI operations. This service calls the Java API to read performance data and persist generated content.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI 0.115 + Uvicorn |
| LLM Client | OpenAI SDK (provider-agnostic) |
| HTTP Client | httpx (async) |
| Task Queue | Celery + Redis |
| Scraping | Playwright (Chromium) |
| Validation | Pydantic v2 + pydantic-settings |
| Testing | pytest + pytest-asyncio |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Redis (for the Celery scraper task)
- The [studgrasp-api](https://github.com/vitordealbs/studgrasp-api) Java backend running
- An API key for any OpenAI-compatible LLM provider

### 1. Clone the repository

```bash
git clone https://github.com/vitordealbs/studgrasp-ai.git
cd studgrasp-ai
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate      # Linux/macOS
# venv\Scripts\activate       # Windows
pip install -r requirements.txt
```

### 3. Install Playwright browser

```bash
playwright install chromium
```

### 4. Set up environment variables

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
LLM_API_KEY=your-key-here
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat

JAVA_API_URL=http://localhost:8080
SCRAPER_API_KEY=studgrasp-scraper-dev-key-change-in-production
REDIS_URL=redis://localhost:6379
```

### 5. Run the service

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Interactive docs available at **http://localhost:8000/docs**

---

## 🐳 Running with Docker

This service is designed to run alongside the Java backend on a shared Docker network.

Make sure the Java backend is running first with `studgrasp_network` created, then:

```bash
docker compose up --build
```

---

## 🤖 LLM Providers

The service uses the OpenAI-compatible API — swap providers without changing any code:

| Provider | `LLM_BASE_URL` | `LLM_MODEL` | Cost |
|---|---|---|---|
| DeepSeek | `https://api.deepseek.com` | `deepseek-chat` | ~$0.14/1M tokens |
| Groq | `https://api.groq.com/openai/v1` | `llama-3.3-70b-versatile` | Free* |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` | ~$0.15/1M tokens |
| Ollama | `http://localhost:11434/v1` | `llama3.2` | Free (local) |

\* Groq has rate limits on the free tier.

---

## 📡 API Endpoints

All endpoints are prefixed with `/ai`. The Java backend is the only caller — except for `/health`.

| Method | Route | Description | Called by |
|---|---|---|---|
| `GET` | `/health` | Service health check | Anyone |
| `POST` | `/ai/flashcards/generate` | Generate flashcards via LLM | Java |
| `POST` | `/ai/attempts` | Record a flashcard attempt | Java |
| `POST` | `/ai/insights/{userId}` | Generate student study insights | Java |
| `POST` | `/ai/insights/class/{classId}` | Generate class insights for advisor | Java |
| `POST` | `/ai/scrape` | Scrape roadmap.sh and populate tracks | Java |

---

## 🧪 Tests

No database, Redis, or Java backend required — everything is mocked.

```bash
# Run all tests
pytest tests/ -v

# Quick pass check
pytest tests/ -q
```

| File | Covers |
|---|---|
| `test_health.py` | Health endpoint |
| `test_flashcards.py` | Flashcard generation and review |
| `test_attempts.py` | Attempt recording and error handling |
| `test_insights.py` | Student and class AI insights |
| `test_analysis.py` | Weak topics analysis |
| `test_spaced_repetition.py` | HTTP client wrappers for spaced repetition |
| `test_llm_service.py` | LLM service (mocked), JSON parsing |
| `test_scraper_service.py` | Slug discovery, React Flow parser, HTTP save |

---

## 📁 Project Structure

```
studgrasp-ai/
├── app/
│   ├── main.py              # FastAPI app + global error handler
│   ├── config.py            # Settings via pydantic-settings
│   ├── routers/             # HTTP layer
│   │   ├── flashcards.py
│   │   ├── attempts.py
│   │   ├── insights.py
│   │   ├── analysis.py
│   │   └── scraper.py
│   ├── services/            # Business logic
│   │   ├── llm_service.py         # Flashcard + insight generation
│   │   ├── spaced_repetition.py   # HTTP client wrappers for SM-2 data
│   │   └── scraper_service.py     # roadmap.sh scraper
│   └── schemas/             # Pydantic models
│       ├── flashcard.py
│       ├── analysis.py
│       └── insights.py
├── tasks/
│   └── scraper_task.py      # Celery async scraper task
├── tests/
├── .env.example
└── docker-compose.yml
```

---

## 📄 License

MIT
