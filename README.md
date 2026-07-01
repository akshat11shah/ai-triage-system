# 1. Project Title
**Agentic AI Customer Message Triage System**

# 2. Overview
The Agentic AI Triage System is an enterprise-grade customer support pipeline designed to process unstructured, sarcastic, angry, and multilingual customer requests. Instead of relying on a simple chatbot, this system uses an **Agentic LLM Architecture** (Llama 3 8B via Groq) to autonomously query local Knowledge Base policies, make priority classification decisions, and draft emails for human-in-the-loop approval. 

# 3. Features
* **Agentic Tool Calling:** The AI autonomously searches the local SQLite Knowledge Base database for company policies before finalizing triage decisions.
* **Human-in-the-Loop Auto-Reply:** Safely generates highly contextual draft email responses based on strict company policies for human agents to review and approve.
* **Self-Healing ML Fallback (k-NN):** If the primary cloud API fails, the system seamlessly degrades to an offline, auto-training Scikit-Learn model (Random Forest + k-Nearest Neighbors) to maintain 100% uptime.
* **Real-Time Telemetry:** Dashboard tracking for latency times, token usage, and fractional-penny API costs.
* **Multilingual Translation:** Automatically detects and translates non-English customer inputs.

# 4. Screenshots
<img width="888" height="860" alt="image" src="https://github.com/user-attachments/assets/49d0e69b-6051-459e-a637-6fb8086dcec8" />
<img width="1152" height="873" alt="image" src="https://github.com/user-attachments/assets/b0dcb493-47c3-4368-94f3-9860c34f08c2" />
<img width="1146" height="711" alt="image" src="https://github.com/user-attachments/assets/23d0b866-399d-43a5-a1b7-52d38d45ac0d" />


# 5. Tech Stack
* **Backend:** Python, Django 4.2+
* **Frontend:** Vanilla JavaScript, HTML5, CSS3 (No heavy frontend frameworks)
* **Database:** SQLite
* **AI Provider:** Groq Cloud API (Model: `llama-3.1-8b-instant`)
* **Machine Learning (Fallback):** Scikit-Learn (TF-IDF, Random Forest, NearestNeighbors)

# 6. Project Structure
```text
ai_triage_system/
│
├── manage.py                   # Django CLI entrypoint
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (Ignored in Git)
│
├── triage_project/             # Main Django Configuration
│   ├── settings.py
│   ├── urls.py
│
├── triage_app/                 # Core Application
│   ├── models.py               # SQLite Database Schema
│   ├── views.py                # HTTP Controllers & AJAX endpoints
│   ├── triage_engine.py        # Connects to Groq & parses Agentic Logic
│   ├── ml_classifier.py        # Scikit-Learn offline fallback logic
│   └── templates/              # HTML Frontend
│
└── ml_models/                  # (Auto-generated) Serialized .pkl ML Models
```

# 7. Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/akshat11shah/ai-triage-system.git
   cd ai-triage-system
   ```
2. Create and activate a Virtual Environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run Database Migrations:
   ```bash
   python manage.py migrate
   ```

# 8. Requirements
Key dependencies include:
* `Django>=4.2`
* `groq>=0.9.0`
* `scikit-learn>=1.0.0`
* `joblib>=1.1.0`
* `openpyxl>=3.1.0` *(For Excel ingestion)*

# 9. Environment Variables
Create a `.env` file in the root directory (same level as `manage.py`) and add your Groq API key:
```env
GROQ_API_KEY=gsk_your_api_key_here
```

# 10. Usage
1. Start the local server:
   ```bash
   python manage.py runserver
   ```
2. Open `http://127.0.0.1:8000/` in your browser.
3. Click **"Seed Mock Dataset"** in the top right to populate the database with realistic customer messages and KB Articles.
4. Click **"Analyze & Triage"** on any message to trigger the Agentic AI flow.

# 11. Workflow
1. **Input:** Customer message arrives via Excel import or UI form.
2. **Analysis:** The `TriageEngine` parses the message and determines if it requires context.
3. **Tool Calling:** The LLM fires a JSON payload requesting to query the `search_knowledge_base` function.
4. **Resolution:** The backend runs the SQL query, injects the policy into the LLM context, and requests a final decision.
5. **Output:** The LLM returns a strict JSON classification (Category, Priority, Summary) which is parsed and displayed on the UI.
6. **Offline Mode:** If Step 2 fails, the `ml_classifier.py` intercepts the text and uses k-NN Vector Retrieval to predict the priority based on historical data.

# 12. Database
* **CustomerMessage:** Stores raw inbound text, source, and timestamps.
* **TriageResult:** Stores AI telemetry, final JSON classifications, cost, latency, and the generated Draft Auto-Reply.
* **KBArticle:** Stores company policies used dynamically by the AI to resolve tickets without hallucinating.

# 13. Future Enhancements
* Implementing a "Multi-Cloud Router" to instantly fallback to OpenAI's GPT-4o-mini before reverting to the local ML model.
* Integrating IMAP/SMTP to fetch real emails directly into the dashboard.

# 14. Known Issues
* Requires a highly reliable internet connection for sub-second latency. If offline, the ML Fallback model requires at least 5 previously triaged messages in the database to train successfully.

# 15. Contributing
Contributions are welcome. Please open an issue first to discuss what you would like to change.
