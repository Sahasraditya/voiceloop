import json
import os
from glob import glob

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
SCRIPTS_DIR = os.path.join(DATA_DIR, "scripts")
TRANSCRIPTS_DIR = os.path.join(DATA_DIR, "transcripts")
ANALYSES_DIR = os.path.join(DATA_DIR, "analyses")


def get_current_script():
    files = sorted(glob(os.path.join(SCRIPTS_DIR, "script_v*.json")))
    if not files:
        raise FileNotFoundError("No script files found in data/scripts/")
    with open(files[-1]) as f:
        return json.load(f)


def save_script(script: dict):
    version = script["version"]
    path = os.path.join(SCRIPTS_DIR, f"script_v{version}.json")
    with open(path, "w") as f:
        json.dump(script, f, indent=2)
    return path


def save_transcript(call_id: str, transcript: dict):
    path = os.path.join(TRANSCRIPTS_DIR, f"call_{call_id}.json")
    with open(path, "w") as f:
        json.dump(transcript, f, indent=2)
    return path


def get_transcript(call_id: str):
    path = os.path.join(TRANSCRIPTS_DIR, f"call_{call_id}.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def save_analysis(call_id: str, analysis: dict):
    path = os.path.join(ANALYSES_DIR, f"analysis_{call_id}.json")
    with open(path, "w") as f:
        json.dump(analysis, f, indent=2)
    return path


def get_all_analyses():
    files = sorted(glob(os.path.join(ANALYSES_DIR, "analysis_*.json")))
    analyses = []
    for path in files:
        with open(path) as f:
            analyses.append(json.load(f))
    return analyses


def get_campaign_context():
    path = os.path.join(DATA_DIR, "context.json")
    if not os.path.exists(path):
        # Default fallback
        return {
            "company_name": "Acme SaaS",
            "product_description": "A workflow automation platform for operations teams.",
            "target_persona": "Alex, a mid-level operations manager at a 200-person company.",
            "call_goal": "Book a 30-minute technical walkthrough."
        }
    with open(path) as f:
        return json.load(f)


def save_campaign_context(context: dict):
    path = os.path.join(DATA_DIR, "context.json")
    with open(path, "w") as f:
        json.dump(context, f, indent=2)


def clear_campaign_data():
    for d in [SCRIPTS_DIR, TRANSCRIPTS_DIR, ANALYSES_DIR]:
        files = glob(os.path.join(d, "*.json"))
        for f in files:
            os.remove(f)
