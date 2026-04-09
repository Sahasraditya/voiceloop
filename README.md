# Self-Improving Call Agent

This project is a prototype sales call agent that can run a conversation, save the transcript, analyze what happened, and rewrite its own script after repeated failures. The goal is to demonstrate a tight feedback loop between call execution and script optimization rather than a production-ready call center stack.

The implementation uses Gemini for agent behavior, prospect simulation, post-call analysis, and script optimization. Voice is handled with lightweight mock TTS via `gTTS`, and orchestration is handled through `n8n`.

---

## What It Does

- Runs a simulated sales call through a Streamlit UI
- Persists transcripts, analyses, and versioned scripts as JSON files
- Uses Gemini to analyze objections, outcomes, and script weaknesses
- Rewrites underperforming script sections after enough call data is collected
- Lets the user switch campaigns dynamically by changing the company, product, persona, and call goal

---

## Architecture

```text
┌─────────────┐     turn-by-turn      ┌──────────────────┐
│  Streamlit  │ ◄──────────────────► │  FastAPI Backend  │
│  Frontend   │                       │  (main.py)        │
└──────┬──────┘                       └────────┬─────────┘
       │                                        │
       │ POST /n8n/call-end                     │ Gemini 2.5 Flash
       ▼                                        │ (agent, analyzer,
┌─────────────┐   webhook chain                 │  optimizer,
│  n8n        │ ──────────────────►             │  prospect sim)
│ Orchestrator│   analyze → optimize            └──────────────────
└─────────────┘
       │
       ▼
  data/
  ├── scripts/      ← versioned script JSON
  ├── transcripts/  ← one file per call
  └── analyses/     ← one file per analysis
```

Core files:
- `frontend/app.py`: Streamlit operator UI
- `backend/main.py`: FastAPI endpoints for turns, transcripts, analysis, and optimization
- `backend/gemini.py`: Gemini calls for generation, simulation, analysis, and rewrite logic
- `backend/storage.py`: flat-file persistence
- `n8n/VoiceLoop_Orchestrator.json`: webhook-driven post-call automation

---

## Setup

1. Install dependencies

```bash
pip install -r requirements.txt
```

2. Configure environment

```bash
cp .env.example .env
```

Required env vars:
- `GOOGLE_API_KEY`

Optional env vars:
- `BACKEND_URL` defaults to `http://localhost:8000`
- `N8N_WEBHOOK_BASE` defaults to `http://localhost:5678/webhook`

3. Start the backend

```bash
cd backend
uvicorn main:app --reload
```

4. Start the frontend

```bash
cd frontend
streamlit run app.py
```

5. Start `n8n` for the full automation loop

```bash
npx n8n
```

Then import or recreate the workflow described in `n8n/workflows.md` or use the checked-in `n8n/VoiceLoop_Orchestrator.json`.

---

## Demo Flow

1. Open Streamlit at `http://localhost:8501`
2. Review or change the campaign in the sidebar
3. Click `Generate Sandbox` if you want a fresh `v0` script for a new campaign
4. Toggle `Auto-run with prospect simulator` on if you want the prospect handled automatically
5. Click `Start Call`
6. Advance the conversation until the agent has handled objections and attempted a close
7. Click `End Call`
8. Repeat for a second call
9. After the second saved analysis, `n8n` triggers script optimization
10. Refresh the UI and inspect the updated script version and improvement log

---

## Success Criteria Mapping

- **Agent can simulate a sales conversation (voice)**  
  The Streamlit UI runs the conversation loop and plays agent responses with mock TTS via `gTTS`.

- **Implements a feedback loop: outcome → analysis → script adjustment**  
  Each completed call is saved, analyzed by Gemini, and eventually used to rewrite underperforming script sections.

- **Documents the improvement logic**  
  Improvement reasoning is documented in `IMPROVEMENT_LOGIC.md` and mirrored in versioned script `change_log` entries.

- **Handles at least 2 iteration cycles in the demo**  
  The repository includes saved analyses and script versions (`script_v0`, `script_v1`, `script_v2`) showing multiple optimization passes.

---

## How the Self-Improvement Loop Works

After each call ends, the frontend saves the transcript and notifies `n8n`. The orchestrator triggers Gemini analysis, stores the structured output, checks whether enough analyses exist, and then calls the optimizer. The optimizer rewrites only the script sections supported by evidence in the analysis history, increments the version number, and appends a machine-readable change log entry.

This keeps the demo simple while still exposing the full workflow:
- conversation history acts as short-term call memory
- saved analyses act as cross-call memory
- versioned script files make changes auditable

---

## Design Choices And Tradeoffs

### Flat-file storage instead of a database

I intentionally used JSON files instead of a relational database. For a take-home prototype, this keeps setup fast, makes the state easy to inspect, and avoids unnecessary infrastructure. The tradeoff is that it is single-tenant and not appropriate for scale.

### Mock TTS instead of a production voice stack

I used `gTTS` as a lightweight mock voice layer. This keeps the demo cheap, simple to reproduce, and aligned with the prompt’s allowance for mock STT/TTS. In production, I would replace this with a lower-latency streaming voice provider and real speech recognition.

### `n8n` for orchestration

I used `n8n` to separate the post-call automation from the turn-by-turn UI loop. That keeps the interactive path simple while still demonstrating workflow orchestration, thresholds, and chained actions.

### Dynamic campaign sandbox

The UI allows the reviewer to redefine the company, product, persona, and call goal. When this changes, the backend resets prior data and regenerates `v0`. This is intentionally opinionated: it prevents cross-campaign contamination in the optimization history and makes the app easier for a non-technical operator to explore.

---

## Known Limitations

- No authentication or tenant separation
- Flat-file persistence only
- Prospect simulator relies on prompt behavior rather than a hard state machine
- Optimization threshold is intentionally low for demo purposes
- `n8n` webhooks are fire-and-forget with limited retry handling
- Voice is mock TTS only, not production telephony

---

## What I Would Improve Next

- Move persistence to a proper database with per-campaign isolation
- Add stronger validation around analyzer and optimizer outputs
- Add evaluation metrics across runs rather than relying only on qualitative recommendations
- Replace mock TTS with a streaming voice stack and real STT
- Add tests around storage, routing, and optimization thresholds
