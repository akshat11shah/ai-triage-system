# Agentic AI Support Triage System 🚀

An industry-grade, autonomous Customer Support Triage system powered by **Llama 3** (via Groq). This application doesn't just wrap an LLM; it acts as an **Agentic AI** capable of dynamic function calling, real-time Knowledge Base retrieval, and robust fallback heuristics. 

Designed to seamlessly ingest, classify, and resolve noisy customer support pipelines at enterprise scale.

## 🌟 Key Features

1. **Agentic Tool Execution:** 
   The core engine uses advanced function calling. Before classifying a ticket, the AI autonomously searches the internal Knowledge Base (KB) or looks up customer tiers to make policy-accurate decisions.
2. **Dynamic Knowledge Base Manager:**
   A fully integrated AJAX dashboard for administrators to add, edit, or delete custom KB policies. The AI's "brain" dynamically updates instantly based on these policies.
3. **Resilient Rate-Limit Handling:** 
   Built for high-volume pipelines. Incorporates automatic exponential backoff, API rate-limit sleep thresholds, and a hard-coded fallback heuristic engine if the API goes completely offline.
4. **Seamless UI/UX:**
   Dark-mode UI built with Vanilla CSS, featuring instant AJAX pagination, dynamic badging, statistical aggregates, and zero-reload architecture.
5. **Robust Excel Data Ingestion:**
   Import thousands of tickets instantly via Excel. Built with `io.BytesIO` memory streaming and fuzzy-header matching to parse messy spreadsheets flawlessly.
6. **Built-in Ground-Truth Evaluation Suite:**
   A dedicated CLI and UI testing framework (`evaluator.py`) to benchmark the AI's accuracy, latency, and cost-per-token against hand-labeled edge cases.

## 🛠️ Technology Stack
* **Backend:** Python, Django
* **AI Engine:** Groq API (Llama-3.1-8B-Instant) for 14,400+ Requests Per Minute speed.
* **Frontend:** HTML5, Vanilla JavaScript (AJAX/Fetch), CSS3 (Dark/Glassmorphism UI)
* **Database:** SQLite (Scalable to PostgreSQL)
* **Data Processing:** OpenPyXL

## 📁 Core Architecture (File Structure)

* `triage_app/triage_engine.py` - **The Brain.** Contains the Llama 3 integration, strict JSON-schema enforcement, function calling tools (`search_knowledge_base`), and fallback rules.
* `triage_app/evaluator.py` - **The Testing Suite.** Seeds the database with edge-case datasets (e.g. Sarcasm, Multi-Language, Vague) and evaluates the AI's classification accuracy.
* `triage_app/views.py` - **The Controllers.** Handles the robust Excel data streams and AJAX JSON endpoints for the dashboard.
* `triage_app/models.py` - **The Schema.** Defines `CustomerMessage`, `TriageResult`, `KBArticle`, and `GroundTruth`.
* `triage_app/templates/triage_app/` - **The UI.** Contains the highly polished, asynchronous HTML/JS templates (`dashboard.html`, `detail.html`).

## 🚀 Quick Start

1. **Environment Setup:**
   Ensure you have activated your virtual environment.
   ```bash
   .venv\Scripts\activate
   ```
2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Environment Variables:**
   Add your Groq API key to a `.env` file in the project root:
   ```env
   GROQ_API_KEY=gsk_your_key_here
   ```
4. **Run the Application:**
   ```bash
   python manage.py runserver
   ```
5. **Access the Dashboard:** 
   Navigate to `http://127.0.0.1:8000/`

## 🧪 Running the Evaluation Suite
To benchmark the AI's accuracy against the Ground Truth dataset:
```bash
python manage.py run_triage --eval
```
This triggers a pacing algorithm to test the model against edge cases, scoring Category, Priority, and Human-Review accuracy.

---
*Built for the Hackathon. Ready for Production.*
