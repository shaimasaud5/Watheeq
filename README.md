<div align="center">

# Watheeq (وثيق)

### AI-Powered Meeting Documentation Assistant

*Automatically join Arabic business meetings, transcribe code-switched Arabic–English speech, and generate formal BRD and MOM documents — end to end.*

</div>

---

## Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [System Architecture](#-system-architecture)
- [Data Model](#-data-model)
- [Tech Stack](#-tech-stack)
- [Environment Variables](#-environment-variables)
- [🚀 Running on Railway](#-running-on-railway)
- [Team](#-team)
- [License](#-license)

---

## 📖 Overview

Software projects rely heavily on meetings to define requirements, make decisions, and assign responsibilities — yet documenting those meetings is still mostly manual, slow, and error-prone. The problem is harder in Arabic business meetings, where speakers naturally **code-switch** between Arabic and English technical terms mid-sentence.

**Watheeq** addresses this gap as a unified, end-to-end system. It pairs an **external AI meeting agent** (for automatic meeting attendance and recording) with an **internal AI pipeline** that combines Speech-to-Text, semantic embeddings, Retrieval-Augmented Generation (RAG), and Large Language Models to identify key meeting elements — requirements, decisions, and action items — and turn them into structured formal documents:

- **BRD** — *Business Requirements Document*, following the **ISO/IEC/IEEE 29148:2018** order.
- **MOM** — *Minutes of Meeting*, following **Robert's Rules of Order**.

The system also provides an interactive **Arabic web interface** where users can review, regenerate, manage, and download the generated documents.

---

## ✨ Key Features

- **Automated meeting attendance** — a bot joins meetings on Zoom, Microsoft Teams, and Google Meet via Recall.ai.
- **Code-switched transcription** — accurately handles mixed Arabic–English speech using Faster-Whisper (large-v3).
- **Semantic pipeline with RAG** — chunks transcripts, generates embeddings, and retrieves the most relevant content for each document section.
- **Structured document generation** — produces professional BRD and MOM Word documents that follow recognized documentation standards.
- **Interactive Arabic web interface** — review, regenerate, manage, and download documents, with a live progress bar for meeting and processing status.

---

## 🏗️ System Architecture

A meeting flows through Watheeq as a pipeline: Recall.ai captures the recording, and the Django backend processes it in stages to produce the final BRD and MOM documents. Each stage passes its result to the next automatically via **Django Signals**.

```
  Recall.ai          ┌──────────────────────── Django Backend ────────────────────────┐
  (meeting bot) ───>  │  Preprocessing → Processing → Extract → Generation             │ ──> Word docs
   Zoom/Teams/Meet    │       (Project app coordinates · Frontend app serves the UI)   │     (BRD / MOM)
                      └────────────────────────────────────────────────────────────────┘
                              │                  │                │
                          Groq (STT)         Ollama           Groq (LLM)
                       Faster-Whisper     mxbai-embed-large    Llama3.3
```

The Django backend is organized into **six applications**:

| App | Responsibility |
|-----|----------------|
| **Preprocessing** | Receives the recording from Recall.ai, transcribes the audio with **Groq Faster-Whisper**, and cleans the resulting transcript. |
| **Processing** | Splits the transcript into chunks, translates them into English, and generates **1024-dimensional vector embeddings** using Ollama (`mxbai-embed-large`). |
| **Extract** | Uses **RAG** to retrieve the most relevant chunks and extract structured information into a JSON schema using **Groq Llama3.3**. |
| **Generation** | Expands the JSON schema into professional document content (Groq Llama3.3) and renders it into a Word document via `python-docx`. |
| **Project** | Coordinator app — handles project creation, sends recording requests to Recall.ai, and monitors pipeline progress for the frontend. |
| **Accounts** | Manages users and authentication via a custom user model (`accounts.User`). |

The user-facing pages are served as **Django templates** (HTML/CSS/JS under `frontend/`), not as a separate Django app. Two services run **outside** the Railway environment: **Recall.ai** (on its own infrastructure) and **Groq** (cloud LLM/STT inference).

---

## 🗄️ Data Model

Data is stored in **PostgreSQL** across eight interconnected tables, accessed through Django's ORM:

`User` · `Project` · `Meeting` · `Document` · `Transcript` · `TranscriptChunk` · `Extraction` · `GeneratedDocument`

---

## 🛠️ Tech Stack

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

---

## 🔐 Environment Variables

These are configured on the **Watheeq backend** service in Railway (**Variables** tab). The table lists every variable, what it's for, and where its value comes from.

| Variable | Purpose | Set by |
|----------|---------|--------|
| `DATABASE_URL` | PostgreSQL connection string, read by Django via `dj_database_url`. | **Auto-injected by Railway** when you add the Postgres plugin — you don't set this manually. |
| `SECRET_KEY` | Django cryptographic secret. Use a strong, unique value. | You |
| `DEBUG` | Django debug mode. **Must be `False` in production.** | You |
| `RECALL_API_KEY` | Authenticates the meeting bot with Recall.ai. | You |
| `GROQ_API_KEY` | Groq inference (Faster-Whisper STT + Llama3.3 LLM). | You |
| `GROQ_API_KEY_TASK1` | Additional Groq key for distributing requests across pipeline stages. | You |
| `GROQ_API_KEY_TASK3` | Additional Groq key for distributing requests across pipeline stages. | You |
| `GROQ_API_KEY_TASK4` | Additional Groq key for distributing requests across pipeline stages. | You |

> **Variable names matter:** `settings.py` reads `SECRET_KEY`, `DEBUG`, and `DATABASE_URL` — use these exact names (not `DJANGO_SECRET_KEY` / `DJANGO_DEBUG`), otherwise Django falls back to its insecure defaults.

> ⚠️ **Never commit your real `.env` file.** Keep it in `.gitignore` and commit only a `.env.example` with placeholder values.

---

## 🚀 Running on Railway

Watheeq runs on **[Railway](https://railway.app/)**, a cloud platform that builds and runs the project's Docker configuration directly from the repository. The sections below walk through everything needed to get a working instance live. 
As you follow the steps below, you'll create **three services** inside one Railway project:

| Service | Role |
|---------|------|
| **Watheeq** | The Django application — the main service. Environment variables (API keys, secrets) are set here. |
| **PostgreSQL** | The managed database. Provides the `DATABASE_URL` that the backend connects to. |
| **Ollama** | Serves the `mxbai-embed-large` embedding model used by the Processing stage. |

### Prerequisites

- A [GitHub](https://github.com/) account
- A [Railway](https://railway.app/) account
- API keys for **Recall.ai** and **Groq**

### Steps

1. **Fork the repository**
   Fork [`shaimasaud5/watheeq`](https://github.com/shaimasaud5/watheeq) into your own GitHub account. The fork is your own copy of the code — your deployment, database, and API keys are entirely separate from the original project.

2. **Create the project and connect your fork**
   Create a new Railway project and link it to **your fork** so Railway builds from its Docker configuration.

3. **Add the PostgreSQL service**
   Add the Railway PostgreSQL plugin. Railway exposes its connection string as `DATABASE_URL`, which Django picks up automatically via `dj_database_url` — no manual database config required.

4. **Add the Ollama service**
   In the same Railway project, create a new service from the `ollama/ollama` Docker image. This runs the embedding-model server that the Processing stage depends on. (You'll load the actual model into it in step 9.)

5. **Set environment variables** (on the **Watheeq** service → *Variables*)
   In Railway, variables are set per service, so add these on the **Watheeq** service (not the PostgreSQL or Ollama service). Use the keys from the [Environment Variables](#-environment-variables) section. At minimum:
   ```
   SECRET_KEY=<a strong, unique production secret>
   DEBUG=True
   RECALL_API_KEY=<your key>
   GROQ_API_KEY_TASK1=<your key>
   GROQ_API_KEY_TASK2=<your key>
   GROQ_API_KEY_TASK3=<your key>
   GROQ_API_KEY_TASK4=<your key>
   ```
   `DATABASE_URL` is provided by the Railway Postgres plugin, so you don't set it manually.


6. **Allowed hosts & CSRF are already configured**
   `settings.py` already trusts Railway:
   - `ALLOWED_HOSTS` includes `.railway.app`
   - `CSRF_TRUSTED_ORIGINS` includes `https://*.railway.app`

7. **Collect static files and run migrations**
   Static files are served by **WhiteNoise**, so run `collectstatic`, then apply migrations against the Railway database:
   ```bash
   python manage.py collectstatic --noinput
   python manage.py migrate
   ```

8. **Serve the app**
   The backend is served through its WSGI entry point (`core.wsgi.application`) using a production WSGI server (e.g. **gunicorn**).

9. **Pull the Ollama embedding model**
   The Ollama service from step 4 starts empty. Pull `mxbai-embed-large` into it so the Processing stage can generate embeddings.

10. **Point Recall.ai at the Railway URL**
    Take the public `https://<your-app>.railway.app` URL and configure it as the webhook endpoint in Recall.ai, so meeting recordings are delivered to the deployed backend.

---

## 👥 Team

Developed as a graduation project at **Imam Mohammad Ibn Saud Islamic University**.

- Shaima Saud Abdullah Alrewaished
- Noura
- Afra
- Atheer

**Supervisor:** Dr. Basma Al-Qadi

---

## 📄 License

This is an academic graduation project and is not licensed for redistribution.

---

<div align="center">

*Turning meetings into documents — automatically.*

</div>
