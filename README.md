<div align="center">

# WATHEEQ - وثيق
### AI-Powered Arabic Meeting Documentation System

Watheeq is a meeting documentation system that automatically joins online meetings, transcribes Arabic (and mixed-language) audio, and generates professional Business Requirements Documents (BRD) and Minutes of Meeting (MOM) in Word format. All in compliance with international documentation standards.

</div>

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Setup - Running on Railway](#setup---running-on-railway)
  - [Prerequisites](#prerequisites)
  - [Steps](#steps)
- [Project Structure](#project-structure)
- [Team](#team)
- [License](#license)

## Overview

Watheeq solves a critical pain point in Arabic-speaking organizations: the time-consuming and error-prone process of manually documenting meeting outcomes. The system:

1. Automatically **joins** online meetings (Google Meet, Zoom, Teams) via a bot
2. **Transcribes** the audio using a state-of-the-art speech-to-text model
3. **Cleans and preprocesses** the transcript
4. **Chunks, translates, and embeds** the text for semantic search
5. **Extracts** key information using Retrieval-Augmented Generation (RAG)
6. **Generates** structured BRD and MOM `.docx` files

Generated documents conform to **ISO/IEC/IEEE 29148:2018** (BRD) and **ISO 15489-1:2016 + Robert's Rules of Order** (MOM).


## Features

- **Automatic meeting bot** — joins meetings without manual intervention via Recall.ai
- **Arabic-English transcription** — powered by Groq Whisper large-v3, handles Arabic with embedded English technical terms
- **Intelligent RAG extraction** — uses semantic search with natural-language queries to bridge the gap between schema fields and spoken language
- **Single-call document generation** — one LLM call with full schema context ensures coherent, non-repetitive output
- **ISO-compliant documents** — BRD and MOM structured per international standards
- **Approve / Regenerate workflow** — users can accept a document or request regeneration (up to 3 attempts, versioned 1.0 → 1.1 → 1.2)
- **Multilingual support** — handles Arabic-dominant speech with English technical terminology

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Django + Django REST Framework (API docs via `drf-spectacular`) |
| **Static files** | WhiteNoise |
| **Database** | PostgreSQL |
| **Frontend** | HTML, CSS, JavaScript (Django templates) |
| **Meeting Agent** | Recall.ai (Zoom, Microsoft Teams, Google Meet) |
| **Speech-to-Text** | Faster-Whisper `large-v3` (served via Groq) |
| **LLM** | Llama3.3 (served via Groq) — used for cleaning, translation, extraction, and generation |
| **Embeddings** | Ollama — `mxbai-embed-large` (1024-dim) |
| **Document rendering** | `python-docx` |
| **Containerization** | Docker |
| **Deployment** | Railway (Docker-based) |


## Setup - Running on Railway

Watheeq runs on **[Railway](https://railway.app/)**, a cloud platform that builds and runs the project's Docker configuration directly from the repository. The sections below walk through everything needed to get a working instance live. 
As you follow the steps below, you'll create **three services** inside one Railway project:

| Service | Role |
|---------|------|
| **Watheeq** | The Django application — the main service. Environment variables (API keys, secrets) are set here. |
| **PostgreSQL** | The managed database. Provides the `DATABASE_URL` that the backend connects to. |
| **Ollama** | Serves the `mxbai-embed-large` embedding model used by the Processing stage. |


### Prerequisites

**Operating System:** Windows or macOS

**Hardware:**
- RAM: 16 GB
- Processor: Intel Core i7 or Apple M2 equivalent

Ollama runs the embedding model locally inside Docker, which is memory-intensive. Less than 16 GB RAM may cause slow performance.

**Software:**
- A [GitHub](https://github.com/) account
- A [Railway](https://railway.app/) account

**API Keys (obtain before setup):**
- 4 Groq API keys — one per pipeline task, to avoid rate limits. Get them at [console.groq.com](https://console.groq.com)
- 1 Recall.ai API key — for agent joining .Get one at [recall.ai](https://www.recall.ai)

### Steps

1. **Fork the repository**
   Go to [`shaimasaud5/watheeq`](https://github.com/shaimasaud5/watheeq) and click the **Fork** button in the top-right corner of the page. This creates your own copy of the repository under your GitHub account.

   Once the fork is created, clone **your copy** (not the original):
```bash
   git clone https://github.com/<your-username>/watheeq.git
```
   Replace `<your-username>` with your GitHub username.

2. **Create a Railway project and connect your fork**
   - Go to [railway.app](https://railway.app) and create a new project
   - Select **Deploy from GitHub repo**
   - Choose your forked repository

3. **Add the PostgreSQL service**
   - Inside your Railway project, click **Add Service**
   - Select **Database → PostgreSQL**
   - Railway will automatically provide `DATABASE_URL` to your app — no extra configuration needed

4. **Add the Ollama service**
   - Inside your Railway project, click **Add Service**
   - Select **Docker Image** and enter: `ollama/ollama`
   - Once the service is created, go to **Settings → Deploy → Pre-deploy command** and paste:
```bash
   sh -c "ollama serve & sleep 10 && ollama pull mxbai-embed-large && wait"
```
   This starts the Ollama server and automatically downloads the embedding model on startup

5. **Set environment variables**

   In the **Watheeq** service you connected in step 2, go to **Variables** and add the following at minimum:
   ```
   SECRET_KEY=<a strong, unique production secret>
   DEBUG=True
   RECALL_API_KEY=<your key>     # For agent joining 
   GROQ_API_KEY_TASK1=<your key> # For Speech-to-Text using Faster-Wisper
   GROQ_API_KEY_TASK2=<your key> # For semantic English translation
   GROQ_API_KEY_TASK3=<your key> # For RAG information extraction
   GROQ_API_KEY_TASK4=<your key> # For full document generation
   ```
  - Each task uses its own Groq API key because Groq rate limits are per account — using separate keys prevents one task from blocking another.
  - `DATABASE_URL` is provided by the Railway Postgres plugin, so you don't set it manually.

6. **Run migrations**

   In the Watheeq service, go to **Settings → Deploy → Pre-deploy Command** and paste:
   ```bash
   python manage.py migrate
   ```

7. **Connect Recall.ai to your Railway URL**
   - Copy your Railway public URL: `https://<your-app>.railway.app`
   - Go to your [Recall.ai dashboard](https://www.recall.ai)
   - Navigate to **Webhooks → Add Endpoint**
   - Paste the following as the webhook URL:
   ```bash
   https://<your-app>.railway.app/api/preprocessing/webhook/
   ```
   - Under **Subscribed Events**, check the following:
     - `bot.call_ended`
     - `bot.in_call_recording`
     - `bot.joining_call`
     - `recording.done`




## Project Structure

```
watheeq/
│
├── railway.toml                 # Railway deployment configuration
├── docker-compose.yml           # Defines the three containers: Django, PostgreSQL, Ollama
├── .env.example                 # Template showing all required variables
├── Dockerfile
├── manage.py
├── requirements.txt
│
├── backend/
│   ├── core/                    # Django project settings and main URL routing
│   ├── project/                 # Meeting and document models; main API entry point
│   ├── accounts/                # User authentication
│   ├── preprocessing/           # Task 1: downloads recording, transcribes with Whisper, cleans transcript
│   │   ├── services.py
│   │   ├── merge_speakers.py
│   │   ├── cleaner.py
│   │   ├── whisper_service.py
│   │   └── recall_media.py
│   ├── processing/              # Task 2: chunks, translates, and embeds the transcript
│   │   ├── pipeline.py
│   │   ├── services.py
│   │   └── signals.py
│   ├── extract/                 # Task 3: RAG-based information extraction
│   │   ├── embedding_service.py
│   │   ├── extractor.py
│   │   ├── llm_service.py
│   │   ├── retrieval_service.py
│   │   ├── schemas.py
│   │   └── signals.py
│   └── generation/              # Task 4: generates BRD and MOM Word files
│       ├── signals.py
│       └── services/
│           ├── docx_renderer.py
│           ├── llm_client.py
│           ├── orchestrator.py
│           └── prompting.py
│
├── frontend/                    # Django templates and static files (HTML, CSS, JS)
│   ├── templates/
│   └── static/
│
└── docker/
    ├── backend.Dockerfile
    └── frontend.Dockerfile
```

## Team

Developed as a graduation project at **Imam Mohammad Ibn Saud Islamic University**.

- Shaima Saud Alrewaished
- Norah Saad Alayyaf 
- Afra Hudhairi Alharbi
- Atheer Ali Alsaghair

**Supervisor:** Dr. Basma Al-Qadi


## License

This project was developed as an academic graduation project at Imam Mohammed ibn Saud Islamic Univercity. All rights reserved.