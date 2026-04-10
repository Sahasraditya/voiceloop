import uuid
from datetime import date
from dotenv import load_dotenv
load_dotenv()  # load .env before any os.getenv() calls

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import storage
import gemini

app = FastAPI(title="Call Agent API")

# Allow Streamlit (running on a different port) to hit this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request models ────────────────────────────────────────────────────────────

class TurnRequest(BaseModel):
    conversation_history: list  # [{"role": "agent"|"prospect", "text": "..."}]

class EndCallRequest(BaseModel):
    conversation_history: list
    script_version: int

class AnalyzeRequest(BaseModel):
    call_id: str

class SaveAnalysisRequest(BaseModel):
    call_id: str
    analysis: dict

class SaveScriptRequest(BaseModel):
    script: dict

class ProspectRequest(BaseModel):
    conversation_history: list

class ContextRequest(BaseModel):
    company_name: str
    product_description: str
    target_persona: str
    call_goal: str


def stamp_latest_change_log_entry(script: dict) -> dict:
    change_log = script.get("change_log")
    if not change_log:
        return script

    latest_entry = change_log[-1]
    latest_entry["version"] = script.get("version", latest_entry.get("version"))
    latest_entry["date"] = date.today().isoformat()
    return script


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/context")
def get_context():
    return storage.get_campaign_context()

@app.post("/setup-campaign")
def setup_campaign(req: ContextRequest):
    context = req.model_dump()
    storage.save_campaign_context(context)
    storage.clear_campaign_data()
    # Generate new v0 script based on context
    new_script = gemini.generate_base_script(context)
    storage.save_script(new_script)
    return {"status": "ok", "context": context, "script_version": new_script.get("version", 0)}


@app.get("/script/current")
def get_current_script():
    return storage.get_current_script()


@app.post("/script/save")
def save_script(req: SaveScriptRequest):
    script = stamp_latest_change_log_entry(req.script)
    path = storage.save_script(script)
    return {"saved": path, "version": script["version"]}


@app.post("/script/optimize")
def optimize_script():
    current = storage.get_current_script()
    analyses = storage.get_all_analyses()
    if not analyses:
        raise HTTPException(status_code=400, detail="No analyses to optimize from")
    new_script = gemini.optimize_script(current, analyses)
    return new_script


@app.post("/call/turn")
def call_turn(req: TurnRequest):
    # The last message in history should be from the prospect; agent responds
    script = storage.get_current_script()
    context = storage.get_campaign_context()
    reply = gemini.agent_reply(req.conversation_history, script, context)
    return {"reply": reply}


@app.post("/call/end")
def end_call(req: EndCallRequest):
    call_id = str(uuid.uuid4())[:8]  # short ID is fine for a demo
    transcript = {
        "call_id": call_id,
        "script_version": req.script_version,
        "turns": req.conversation_history,
    }
    storage.save_transcript(call_id, transcript)
    return {"call_id": call_id}


@app.get("/transcript/{call_id}")
def get_transcript(call_id: str):
    transcript = storage.get_transcript(call_id)
    if not transcript:
        raise HTTPException(status_code=404, detail=f"No transcript for call {call_id}")
    return transcript


@app.post("/call/analyze")
def analyze_call(req: AnalyzeRequest):
    transcript = storage.get_transcript(req.call_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    context = storage.get_campaign_context()
    analysis = gemini.analyze_call(transcript, context)
    analysis["call_id"] = req.call_id
    return analysis


@app.post("/analysis/save")
def save_analysis(req: SaveAnalysisRequest):
    path = storage.save_analysis(req.call_id, req.analysis)
    return {"saved": path}


@app.get("/analysis/all")
def get_all_analyses():
    return storage.get_all_analyses()


@app.post("/prospect/respond")
def prospect_respond(req: ProspectRequest):
    context = storage.get_campaign_context()
    reply = gemini.prospect_reply(req.conversation_history, context)
    return {"reply": reply}
