# PackCheck (SIH26034)

An evidence-driven Legal Metrology compliance checker for physical packaged commodities.

---

## Project Overview

PackCheck automates and assists in verifying packaged goods compliance against the Legal Metrology (Packaged Commodities) Rules in India. It combines high-accuracy text/feature extraction, deterministic statutory rule checking, and human-in-the-loop review.

---

## Architecture Principle

The core processing pipeline is strictly staged:

```
CAPTURE ──> EXTRACT ──> CHECK ──> REVIEW ──> RESULT
```

| Pipeline Stage | Responsibility | Role |
| :--- | :--- | :--- |
| **CAPTURE** | Image ingestion, framing, and quality assessment | Input Gate |
| **EXTRACT** | **AI / OCR**: Extracts text, bounding boxes, labels, and declares | *Proposes* |
| **CHECK** | **Deterministic Rules Engine**: Statutory compliance verification | *Decides* |
| **REVIEW** | **Human Reviewer**: Resolves uncertainty and flags edge cases | *Resolves* |
| **RESULT** | Verifiable compliance audit report and evidence export | Output |

> **Core Axiom**: AI/OCR only *extracts and proposes*; deterministic rules *decide*; humans *resolve uncertainty*.

---

## Development Strategy & Provider Independence

PackCheck is designed with a provider-independent AI/OCR abstraction to support seamless phase transitions:

```
OCRProvider
├── CloudOCRProvider (Phase 1: Gemini & Groq Vision APIs)
└── LocalOCRProvider (Phase 2: Local inference on NVIDIA RTX 4050 6GB)
```

The rest of the application interacts exclusively with the `OCRProvider` abstract contract, ensuring zero coupling to specific AI backends or cloud vendors.

---

## Project Structure

```
PackCheck/
├── backend/                  # FastAPI backend
│   ├── app/
│   │   ├── api/              # API endpoints and routers (POST /api/extract)
│   │   ├── core/             # Application configuration and settings (Pydantic BaseSettings)
│   │   ├── models/           # Domain models
│   │   ├── schemas/          # Pydantic schemas / DTOs (ExtractionResult, ExtractedField)
│   │   ├── services/         # Business logic and provider interfaces
│   │   │   ├── interfaces/   # Abstract contracts (OCR, Quality, Rules, Evidence, Report)
│   │   │   └── providers/    # Concrete providers (GeminiOCRProvider)
│   │   └── main.py           # FastAPI entrypoint and CORS middleware
│   ├── tests/                # Backend unit and integration test suite
│   └── requirements.txt      # Backend Python dependencies
├── frontend/                 # React + Vite frontend test UI
│   ├── src/
│   │   ├── App.jsx           # Main application wrapper with live backend ping
│   │   ├── ExtractTest.jsx   # Image upload, extraction trigger, and results table
│   │   └── index.css         # Custom dark-theme styling
│   ├── package.json          # Node dependencies and scripts
│   └── package-lock.json     # Locked dependency tree
├── rules/                    # Deterministic statutory compliance rule definitions
├── data/
│   ├── samples/              # Compliant and non-compliant package image samples
│   └── seeded_defects/       # Synthetic and annotated defect datasets
├── tests/                    # Cross-system and end-to-end integration tests
├── docs/                     # Technical specifications and architectural documentation
├── .env.example              # Environment variables template (placeholders only)
├── .gitignore                # Git ignore rules for secrets, caches, and dependencies
└── README.md                 # Project documentation and onboarding guide
```

---

## Prerequisites

Ensure you have the following installed on your machine:

- **Python**: 3.10, 3.11, or 3.12 (`python --version`)
- **Node.js**: 18, 20, or 22+ and `npm` (`node --version`, `npm --version`)
- **Git**: (`git --version`)
- A **Google Gemini API Key** (from [Google AI Studio](https://aistudio.google.com/))

---

## Setup & Installation Guide

Follow these steps to set up and run PackCheck locally from scratch:

### 1. Clone the Repository

```bash
git clone <repository-url>
cd PackCheck
```

### 2. Configure Environment Variables

Create your local `.env` file from the provided `.env.example`:

**Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

**macOS / Linux (Bash):**
```bash
cp .env.example .env
```

Open `.env` in your editor and insert your API credentials:
```ini
# AI & OCR Cloud Provider Keys
GEMINI_API_KEY=
GEMINI_MODEL=gemini-flash-latest
GROQ_API_KEY=

# Application Environment
ENVIRONMENT=development
HOST=127.0.0.1
PORT=8000
FRONTEND_URL=http://localhost:5173
```

> **Security Note**: Never commit `.env` to Git. It is automatically ignored by `.gitignore`.

### 3. Backend Setup

1. Create and activate a Python virtual environment:

   **Windows (PowerShell):**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   **macOS / Linux (Bash):**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install backend dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```

3. Run automated tests to verify your setup:
   ```bash
   pytest backend/tests -v
   ```

4. Start the backend development server:
   ```bash
   uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
   ```

### 4. Frontend Setup

In a new terminal window:

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the Vite development server:
   ```bash
   npm run dev
   ```

---

## Local URLs & Endpoints

| Service / Tool | URL | Description |
| :--- | :--- | :--- |
| **Frontend UI** | [http://localhost:5173](http://localhost:5173) | Interactive package extraction test UI |
| **Backend API** | [http://127.0.0.1:8000](http://127.0.0.1:8000) | FastAPI application root |
| **Interactive Docs** | [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) | Swagger UI for API exploration and testing |
| **Health Check** | [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health) | Verifies backend connectivity (`{"status": "ok"}`) |
| **Extraction Endpoint** | `POST http://127.0.0.1:8000/api/extract` | Multipart upload accepting JPEG, PNG, or WEBP |

---

## Running Automated Tests

Run backend tests at any time using:

```bash
# Run all tests with verbose output
pytest backend/tests -v

# Run a specific test suite
pytest backend/tests/test_extract_api.py -v
pytest backend/tests/test_gemini_provider.py -v
```

All backend tests use mocked providers and mock Gemini responses. No active API key or network access is required to run the test suite.

To verify frontend code:

```bash
cd frontend
npm run lint
npm run build
```

---

## TEAM DEVELOPMENT WORKFLOW

To maintain code quality, avoid merge conflicts, and protect credentials, all team members must follow this workflow:

1. **`main` is the Stable Branch**:
   - `main` must always remain buildable, deployable, and passing all tests.
   - Never commit experimental or broken code directly to `main`.

2. **Feature Branching**:
   - Always create a dedicated branch for your task or feature:
     ```bash
     git checkout main
     git pull origin main
     git checkout -b feat/your-feature-name
     ```
   - Branch naming convention:
     - `feat/<feature-name>` for new capabilities
     - `fix/<bug-name>` for bug fixes
     - `test/<test-name>` for test additions
     - `docs/<doc-name>` for documentation updates

3. **Never Commit Secrets**:
   - Do **NOT** commit `.env` or hard-code API keys, tokens, or passwords anywhere in the codebase.
   - Always verify what you are committing using `git status` and `git diff` before adding files.

4. **Pull Before Starting Work**:
   - Always rebase or pull from `main` before writing code to stay up to date:
     ```bash
     git pull origin main
     ```

5. **Commit with Meaningful Messages**:
   - Write clear, conventional commit messages describing the change:
     - `feat: add quality check interface for label blur`
     - `fix: handle missing mrp field in extraction parser`
     - `test: add unit tests for net quantity validation`

6. **Run Tests Before Committing**:
   - Ensure the full test suite passes locally before pushing:
     ```bash
     pytest backend/tests -v
     cd frontend && npm run build
     ```

7. **Open a Pull Request (PR)**:
   - Push your branch to GitHub and open a Pull Request targeting `main`.
   - Provide a clear PR description detailing what was changed and how to test it.
   - Obtain at least one teammate review before merging.
