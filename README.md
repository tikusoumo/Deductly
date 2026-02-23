# Deductly — AI-Powered Indian Tax Guidance Agent
> **Deductly** (branded as **TaxSaver AI** in the UI) is a full-stack, RAG-powered tax guidance platform built specifically for Indian individual taxpayers. It combines a multi-collection Qdrant vector database — seeded with the Income Tax Act, Income Tax Rules 1962, CBDT notifications, capital-gain case laws, and ITR forms — with a LangGraph agentic pipeline that interactively collects missing information from the user, retrieves the most relevant legal context, runs deterministic calculations, and delivers a structured, citation-backed tax deduction report.

---
https://github.com/user-attachments/assets/4af7d4b5-6666-4bea-89fe-1d126205aa47



## Table of Contents

1. [Key Features](#key-features)  
2. [Architecture Overview](#architecture-overview)  
3. [RAG Knowledge Base](#rag-knowledge-base)  
4. [LangGraph Agentic Pipeline](#langgraph-agentic-pipeline)  
5. [Tax Deductions Supported](#tax-deductions-supported)  
6. [Guardrail System](#guardrail-system)  
7. [Tech Stack](#tech-stack)  
8. [Project Structure](#project-structure)  
9. [API Reference](#api-reference)  
10. [Frontend Pages](#frontend-pages)  
11. [Data Models](#data-models)  
12. [Environment Variables](#environment-variables)  
13. [Getting Started](#getting-started)  
14. [Chunking / Ingestion Pipeline](#chunking--ingestion-pipeline)  
15. [Security Notes](#security-notes)  

---

## Key Features

| Feature | Description |
|---|---|
| **RAG-Grounded Answers** | Every deduction explanation is backed by retrieved passages from actual Indian tax law documents — minimising hallucinations. |
| **Agentic Human-in-the-Loop** | LangGraph interrupts the graph and asks the user for any missing financial fields before proceeding. |
| **Deterministic Tax Calculator** | A `TaxCalculator` Python class calculates ten major deductions using hard-coded statutory limits for FY 2024-25 / AY 2025-26. |
| **Multi-Collection Retrieval** | Five Qdrant collections are queried in parallel with metadata-filtered (section / rule) and semantic (fallback) search tiers. |
| **Conversation Memory** | LangGraph checkpoints are persisted in MongoDB so users can resume interrupted sessions and review history. |
| **Strict Topic Guardrails** | System prompts and LLM behaviour are locked to Indian Income Tax and financial queries only; all other topics are politely rejected. |
| **Persistent Chat Sessions** | Users can create multiple named chat sessions, each with a full message history stored in MongoDB. |
| **Structured Onboarding Form** | A rich tax-calculator form (validated with Zod) collects all required user details before starting the LangGraph conversation. |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React / Vite)                  │
│   Landing → LoginForm / SignupForm → TaxCalculator Form         │
│   → ChatInterface → ChatSessions → History / Dashboard          │
└────────────────────────┬────────────────────────────────────────┘
                         │  REST (JSON) + X-User-ID header
┌────────────────────────▼────────────────────────────────────────┐
│                  BACKEND  (FastAPI + Uvicorn)                    │
│  /signup  /login  /chats  /tax/submit                           │
│  Auth Controller │ Chat Controller │ Tax Controller             │
│  AuthService     │ ChatService     │ DatabaseService            │
└────────────────────────┬────────────────────────────────────────┘
                         │
          ┌──────────────▼──────────────┐
          │    LangGraph Tax Pipeline   │  ← async graph with
          │  (main_graph.py)            │    MongoDB checkpointer
          │                             │
          │ plan → clarify → ask ──► (interrupt / resume)
          │         ↓                   │
          │ parse_input → filter        │
          │         ↓                   │
          │ analyze_query → RAG         │
          │         ↓                   │
          │ reason → calc_totals        │
          │         ↓                   │
          │ summary → verdict           │
          └──────┬──────────────────────┘
                 │ similarity search
    ┌────────────▼──────────────────────┐
    │   Qdrant Vector DB (cloud)        │
    │  • tax_law_chunks                 │
    │  • tax_rules_chunks               │
    │  • capital_gain_cases             │
    │  • cbdt_notifications             │
    │  • itr_forms                      │
    └───────────────────────────────────┘
                 │ state persistence
    ┌────────────▼──────────────────────┐
    │         MongoDB (Motor async)     │
    │  collections: users, sessions     │
    └───────────────────────────────────┘
```

---

## RAG Knowledge Base

The knowledge base is built by the scripts in the `chunking/` directory and stored as vector embeddings in Qdrant using **Google `text-embedding-004`**.

### Collections

| Collection Name | Source Document(s) | Ingestion Method | Chunk Strategy |
|---|---|---|---|
| `tax_law_chunks` | `Income-tax-bill-2025.pdf` | `PyPDFLoader` | Split by `Section \d+`, then `RecursiveCharacterTextSplitter` (1 000 chars / 150 overlap) |
| `tax_rules_chunks` | `Income_Tax_Rules_1962.pdf` | `PyPDFLoader` | Split by `Rule \d+`, then fine-grained chunking |
| `capital_gain_cases` | `Capital_Gain_Tax_Exemption[1-3].pdf`, `Recent_Tribunal_Rullings[1-3].pdf` | `PyPDFLoader` | Page-level + section metadata extraction |
| `cbdt_notifications` | `CBDT-Notification-7-2024.pdf`, `-9-DV-2016.pdf`, `-70-2022.pdf` | **OCR via PyMuPDF + Tesseract** | 1 000-char chunks; section / clause metadata |
| `itr_forms` | `ITR1(Sahaj).pdf`, `ITR1-Form.pdf` | **OCR via PyMuPDF + Tesseract** | 1 000-char chunks; schedule / section metadata |

### Metadata Schema (per chunk)

```json
{
  "source": "Income-tax-bill-2025",
  "type": "law | rule | case | notification | form",
  "section": "80C",          // extracted via regex if present
  "rule": "11DD",            // for rules collection
  "schedule": "SCHEDULE-IV", // for ITR forms
  "jurisdiction": "INDIA"
}
```

### Retrieval Strategy (in `rag_node`)

1. **Tier 1 — Metadata-filtered (high precision):** If the LLM query-analyser extracts explicit section/rule identifiers from the deduction query, the retriever applies a `FieldCondition` filter on `metadata.section` or `metadata.rule` in `tax_law_chunks` and `tax_rules_chunks` (top-3 hits each).  
2. **Tier 2 — Broad semantic (fallback):** An additional unfiltered similarity search (top-2) is always run on the law and rules collections.  
3. **Tier 3 — Supporting docs:** CBDT notifications and capital-gain case laws are searched with section filters where available (top-2 each).  
4. All results are **deduplicated by content** before being passed to the reasoning node.

---

## LangGraph Agentic Pipeline

The pipeline is defined in `backend/rag_pipeline/main_graph.py` as a `StateGraph` operating on a typed state (`TaxState`).

### State Schema (`TaxState`)

| Key | Type | Purpose |
|---|---|---|
| `messages` | `list[BaseMessage]` | Full chat history (auto-merged via `add_messages`) |
| `user_details` | `dict` | All user financial / personal data |
| `deduction_plan` | `dict` | LLM-generated plan of applicable deductions |
| `missing_data_questions` | `dict` | Fields still required from user, per deduction |
| `rag_results` | `dict` | Retrieved legal chunks per deduction |
| `reasoning` | `dict` | Calculated or LLM-reasoned deduction results |
| `summary` | `str` | Formatted deduction summary |
| `verdict` | `str` | Final human-readable tax report |

### Graph Nodes

```
START
  └─► plan_node            — LLM generates a deduction plan from user_details
        └─► clarify_node   — identifies missing required fields
              ├─(missing)─► ask_for_data_node  — LLM formats friendly questions
              │               └─► [INTERRUPT] human_assistance_tool
              │                       └─► parse_human_input_node
              │                               └─► (loops back to clarify)
              └─(complete)─► filter_node       — runs TaxCalculator for eligible deductions
                               └─► analyze_query_node  — extracts section IDs from queries
                                     └─► rag_node       — parallel multi-collection retrieval
                                           └─► reason_node  — dispatches to TaxCalculator or LLM
                                                 └─► calculate_totals_node
                                                       └─► summary_node
                                                             └─► verdict_node
                                                                   └─► END
```

### Human-in-the-Loop Mechanism

When missing data is detected, `ask_for_data_node` emits an `AIMessage` containing a `ToolCall` to `human_assistance_tool`. LangGraph's `ToolNode` executes the tool, which calls `interrupt(query)` — **pausing the graph**. The session state is checkpointed to MongoDB. When the user replies via `/chats/{id}/send_message`, the service resumes the graph with `Command(resume=...)`, feeding the answer into `parse_human_input_node`. This loop continues until all required fields are collected.

### Key LLM Chains

| Chain | Model | Purpose |
|---|---|---|
| `plan_chain` | Gemini 1.5 Flash | Identifies all applicable deductions and required fields from user details |
| `question_formatter_chain` | Gemini 1.5 Flash | Converts technical field names to friendly conversational questions |
| `query_analyzer_chain` | Gemini 1.5 Flash | Extracts Indian IT section/rule references from deduction queries |
| `reason_chain` | Gemini 1.5 Flash | Falls back to LLM reasoning for deductions without calculator methods |
| `parse_human_input_chain` | Gemini 1.5 Flash | Parses free-text user answers into structured `ParsedHumanInput` Pydantic model |
| `conversation_chain` | Gemini 2.0 Flash | Handles free-form conversational follow-up after deduction analysis |

---

## Tax Deductions Supported

All calculations use statutory limits for **FY 2024-25 (AY 2025-26)**.

| Deduction | Section | Limit | Notes |
|---|---|---|---|
| Standard Deduction | 16(ia) | ₹50,000 | For salaried individuals |
| Investments (EPF, PPF, LIC, ELSS, etc.) | 80C | ₹1,50,000 | Aggregate cap |
| Additional NPS Contribution | 80CCD(1B) | ₹50,000 | Over and above 80C |
| Health Insurance — Self/Family | 80D | ₹25,000 (₹50,000 if senior citizen) | |
| Health Insurance — Parents | 80D | ₹25,000 (₹50,000 if senior citizen parents) | |
| Home Loan Interest | 24(b) | ₹2,00,000 (self-occupied); no limit (let-out) | |
| Charitable Donations | 80G | 50% or 100% depending on institution | |
| Education Loan Interest | 80E | No monetary cap; allowed for 8 years | |
| Disability (Self) | 80DD | ₹75,000 / ₹1,25,000 (severe) | |
| Savings Account Interest — Non-Senior | 80TTA | ₹10,000 | |
| Interest from Deposits — Senior Citizens | 80TTB | ₹50,000 | Mutually exclusive with 80TTA |

---

## Guardrail System

Deductly enforces strict topic boundaries through multiple layers:

1. **System Prompt (Conversational Chain):**  
   The `conversation_chain` system prompt explicitly instructs the model:
   - *"Do not entertain anything other than financial queries related to Indian Income Tax laws."*
   - *"If you're asked with something else rather than financial queries, politely inform the user that you are unable to provide that information."*
   - *"Do not hallucinate by any chance."*

2. **Scoped LLM Chains (RAG Pipeline):**  
   Every chain in `main_graph.py` is purpose-built and tightly templated — the plan chain only identifies tax deductions, the reason chain only reasons about specific tax deductions, etc. There is no general-purpose free-form LLM call in the pipeline.

3. **Structured Input Parsing:**  
   The `parse_human_input_chain` uses a strict Pydantic schema (`ParsedHumanInput`) and is instructed *"Do not assume any values"* — only extracting explicitly mentioned fields, defaulting to `null` otherwise.

4. **Backend Validation:**  
   `Depends(get_current_user_id)` on all authenticated routes prevents unauthenticated access. The TaxCalculator applies hard-coded statutory caps, ignoring any LLM-computed amounts that exceed legal limits.

---

## Tech Stack

### Backend

| Technology | Version | Role |
|---|---|---|
| Python | 3.11+ | Runtime |
| FastAPI | 0.115 | REST API framework |
| Uvicorn | 0.34 | ASGI server |
| LangChain | 0.3.25 | LLM orchestration / chains |
| LangGraph | latest | Stateful agentic graph with checkpointing |
| `langchain-google-genai` | 2.1 | Gemini LLM + embedding integration |
| `langchain-qdrant` | 0.2 | Qdrant vector store integration |
| Qdrant Cloud | — | Vector database |
| Motor (AsyncIOMotorClient) | — | Async MongoDB driver |
| MongoDB | — | User + session persistence, LangGraph checkpoints |
| Pydantic | 2.x | Data validation |
| `sentence-transformers` | 4.1 | Local embedding fallback |
| `PyMuPDF` + `pytesseract` | — | PDF OCR for scanned government documents |
| python-dotenv | 1.1 | Environment variable management |
| bcrypt (passlib) | — | Password hashing |

### Frontend

| Technology | Version | Role |
|---|---|---|
| React | 18.3 | UI framework |
| TypeScript | 5.x | Type safety |
| Vite | 5.x | Build tool / dev server |
| Tailwind CSS | 3.x | Utility-first styling |
| shadcn/ui + Radix UI | — | Accessible component library |
| React Hook Form + Zod | — | Form validation |
| React Router DOM | — | Client-side routing |
| Lucide React | — | Icon set |

---

## Project Structure

```
Deductly/
├── backend/
│   ├── main.py                   # FastAPI app: CORS, routers, startup/shutdown
│   ├── dependencies.py           # get_current_user_id dependency (X-User-ID header)
│   ├── config/
│   │   └── settings.py           # Environment-based config (MongoDB, Google API key, LLM model)
│   ├── controllers/
│   │   ├── auth_controller.py    # POST /signup, POST /login
│   │   └── chat_controller.py    # GET /chats, GET /chats/:id, POST /chats/start_new_tax_session, POST /chats/:id/send_message
│   ├── routes/
│   │   └── tax_routes.py         # POST /tax/submit
│   ├── models/
│   │   ├── chat_message_model.py # Pydantic models: UserCreate, UserLogin, ChatMessage, ChatSessionResponse, etc.
│   │   └── tax_model.py          # TaxFormRequest
│   ├── services/
│   │   ├── auth_service.py       # signup_user, login_user, get_user_by_id
│   │   ├── chat_service.py       # start_new_tax_session, send_message_to_chat, get_user_chat_sessions
│   │   └── database_service.py   # AsyncIOMotorClient singleton; users + sessions collections
│   ├── rag_pipeline/
│   │   ├── main_graph.py         # LangGraph graph definition, all nodes, all LLM chains, retriever setup
│   │   ├── llm_setup.py          # Conversational chain (Gemini 2.0 Flash) + system prompt
│   │   └── tax_deductions.py     # TaxCalculator class: 10 deterministic deduction methods
│   └── utils/
│       └── password_utils.py     # hash_password, verify_password (bcrypt)
│
├── chunking/                     # One-time ingestion scripts (run offline to populate Qdrant)
│   ├── law_chunking.py           # Income Tax Bill 2025 → tax_law_chunks
│   ├── rule_chunking.py          # Income Tax Rules 1962 → tax_rules_chunks
│   ├── case_laws.py              # Capital gain cases + tribunal rulings → capital_gain_cases
│   ├── CBDT_notification_chunking.py  # OCR → cbdt_notifications
│   ├── ITR1_chunking.py          # OCR → itr_forms
│   ├── amended_rule_chunking.py  # Amended rules ingestion
│   ├── webscrapper.py            # Web scraping utilities
│   └── data/                     # Source PDFs (not committed to VCS)
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx               # Router, layout wrapper
│   │   ├── pages/
│   │   │   ├── Landing.tsx       # Marketing landing page
│   │   │   ├── Dashboard.tsx     # User dashboard
│   │   │   ├── Chat.tsx          # Tax consultation chat page
│   │   │   ├── TaxCalculator.tsx # Onboarding form (Zod-validated, starts LangGraph session)
│   │   │   ├── History.tsx       # Chat session history
│   │   │   ├── Settings.tsx      # User settings
│   │   │   └── Submissions.tsx   # Past tax submissions
│   │   ├── components/
│   │   │   ├── auth/             # LoginForm, SignupForm
│   │   │   ├── chat/             # ChatInterface, ChatSessions
│   │   │   ├── layout/           # Header, Sidebar, Layout
│   │   │   └── ui/               # Full shadcn/ui component library
│   │   ├── contexts/
│   │   │   └── AuthContext.tsx   # Auth state: user_id, login/logout helpers
│   │   └── types/
│   │       └── index.ts          # Shared TypeScript interfaces
│   ├── package.json
│   └── vite.config.ts
│
├── requirements.txt              # Python dependencies (pinned)
└── README.md
```

---

## API Reference

All endpoints run on `http://localhost:8000` by default.  
Authenticated endpoints require the header `X-User-ID: <user_id>`.

### Authentication

| Method | Path | Auth | Request Body | Description |
|---|---|---|---|---|
| `POST` | `/signup` | No | `{ username, email, password }` | Register a new user |
| `POST` | `/login` | No | `{ username, password }` | Login; returns `user_id` |

### Chat Sessions

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/chats` | Yes | List all chat sessions for the authenticated user |
| `GET` | `/chats/{session_id}` | Yes | Get full chat history for a specific session |
| `POST` | `/chats/start_new_tax_session` | Yes | Create a new LangGraph session; triggers initial tax analysis |
| `POST` | `/chats/{session_id}/send_message` | Yes | Send a follow-up message; resumes an interrupted graph if needed |

#### `POST /chats/start_new_tax_session` — Request Body

```json
{
  "user_details": {
    "salary": 1200000,
    "user_age": 32,
    "is_senior_citizen": false,
    "investments": {
      "80C_investments": 100000,
      "nps_contribution": 50000
    },
    "health_insurance_premium": 20000,
    "parents_health_insurance_premium": 30000,
    "medical_expenses": 0,
    "parents_age": 62,
    "housing_loan_interest": 180000,
    "property_status": "self_occupied",
    "donation_amount": 5000,
    "education_loan_interest": 0,
    "disability_details": { "is_disabled": false },
    "other_income": {
      "interest_from_savings": 8000,
      "fixed_deposit_interest": 0
    },
    "tax_regime": "old"
  }
}
```

#### `POST /chats/{session_id}/send_message` — Request Body

```json
{
  "message": "My NPS contribution is 50000 and my age is 35",
  "is_interruption_response": true
}
```

### Tax Submission

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/tax/submit` | No | Submit tax form data for processing |

---

## Frontend Pages

| Route | Page | Description |
|---|---|---|
| `/` | `Landing` | Marketing page with feature overview and CTA buttons |
| `/login` | `LoginForm` | Username + password authentication |
| `/signup` | `SignupForm` | New user registration |
| `/dashboard` | `Dashboard` | Overview cards and quick navigation |
| `/tax-calculator` | `TaxCalculator` | Multi-step Zod-validated form collecting all tax details; submits to `/chats/start_new_tax_session` and redirects to chat |
| `/chat` | `Chat` | Full-page chat interface with LangGraph-powered AI advisor; supports session resumption |
| `/history` | `History` | List of past chat sessions |
| `/settings` | `Settings` | User preferences |
| `/submissions` | `Submissions` | History of tax form submissions |

---

## Data Models

### `users` Collection (MongoDB)

```json
{
  "_id": "ObjectId",
  "username": "string (lowercase)",
  "email": "string (lowercase)",
  "password": "string (bcrypt hash)",
  "created_at": "ISODate"
}
```

### `sessions` Collection (MongoDB)

```json
{
  "_id": "ObjectId (= LangGraph thread_id)",
  "user_id": "ObjectId",
  "title": "Tax Chat 2026-02-24 14:30",
  "created_at": "ISODate",
  "updated_at": "ISODate",
  "chat_history": [
    { "role": "user | assistant", "content": "string", "timestamp": "ISODate", "tool_call_id": "string | null" }
  ],
  "initial_tax_details": { /* user_details dict */ },
  "awaiting_human_input": false,
  "langgraph_thread_id": "string"
}
```

---

## Environment Variables

Create a `.env` file inside the `backend/` directory (or project root):

```env
# MongoDB
MONGODB_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/
DB_NAME=tax_helper_db

# Google AI (Gemini + Embeddings)
GOOGLE_API_KEY=your_google_api_key_here

# Qdrant Cloud
QDRANT_URL=https://<cluster-id>.cloud.qdrant.io
QDRANT_API_KEY=your_qdrant_api_key_here
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+ and npm / pnpm
- A MongoDB instance (Atlas free tier works)
- A Qdrant Cloud cluster (free tier available at [cloud.qdrant.io](https://cloud.qdrant.io))
- A Google AI Studio API key (for Gemini and embeddings)

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/deductly.git
cd deductly
```

### 2. Backend Setup

```bash
# Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate     # Windows
# source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Copy and fill in the .env file
cp .env.example backend/.env
# Edit backend/.env with your keys
```

### 3. Populate the Qdrant Knowledge Base (One-Time)

Before running the backend for the first time, ingest the tax documents into Qdrant:

```bash
cd chunking

# Ingest Income Tax Act 2025
python law_chunking.py

# Ingest Income Tax Rules 1962
python rule_chunking.py

# Ingest CBDT Notifications (requires Tesseract OCR installed)
python CBDT_notification_chunking.py

# Ingest Capital Gain Cases + Tribunal Rulings
python case_laws.py

# Ingest ITR-1 Forms (requires Tesseract OCR)
python ITR1_chunking.py
```

> **Note:** Place the source PDFs in `chunking/data/` before running the scripts. Tesseract must be installed system-wide for OCR-based ingestion (`sudo apt install tesseract-ocr` / `brew install tesseract` / Windows installer from GitHub).

### 4. Run the Backend

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.  
Interactive docs: `http://localhost:8000/docs`.

### 5. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:5173`.

---

## Chunking / Ingestion Pipeline

Each script in `chunking/` follows the same four-step pattern:

```
1. LOAD  — PyPDFLoader (text PDF) or PyMuPDF + Tesseract (scanned PDF)
2. SPLIT — Regex split on "Section \d+" or "Rule \d+"; then RecursiveCharacterTextSplitter
           (chunk_size=1000, chunk_overlap=150)
3. TAG   — Metadata enrichment: section, rule, jurisdiction, type, source
4. INGEST— GoogleGenerativeAIEmbeddings (text-embedding-004) → QdrantVectorStore
```

The metadata tags (`section`, `rule`, `jurisdiction`) are critical — the RAG node uses them for precision-filtered retrieval before falling back to semantic search.

---

## Security Notes

- Passwords are hashed with **bcrypt** before storage; raw passwords are never persisted.
- Authentication relies on the `X-User-ID` header resolved via `get_current_user_id` dependency. For production, replace this with a proper JWT / OAuth 2.0 flow.
- CORS is currently set to `allow_origins=["*"]`. Restrict this to the frontend origin in production.
- Google API keys are present in plain text in some chunking scripts for development convenience — **move these to environment variables before committing or deploying**.
- The Qdrant API key and MongoDB URI should never be committed to version control. Use `.env` files (added to `.gitignore`).

---

## Contributing

1. Fork the repository and create a feature branch.
2. Install pre-commit hooks: `pip install pre-commit && pre-commit install`.
3. Follow the existing code style (PEP 8 for Python, ESLint config for TypeScript).
4. Open a pull request with a clear description of the change.

---

## License


MIT © Deductly Team

