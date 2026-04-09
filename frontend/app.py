import os
import json
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

API = os.getenv("BACKEND_URL", "http://localhost:8000")
N8N_WEBHOOK_BASE = os.getenv("N8N_WEBHOOK_BASE", "http://localhost:5678/webhook")

st.set_page_config(page_title="Call Agent", layout="wide")
st.title("Self-Improving Call Agent")
st.caption("Run a sales call, save the transcript, and review how the script improves after each analyzed interaction.")

# ── Sidebar: Campaign Setup ───────────────────────────────────────────────────
with st.sidebar:
    st.header("Campaign Setup")
    try:
        current_ctx = requests.get(f"{API}/context").json()
    except Exception:
        current_ctx = {}

    st.caption("Define the active company, target persona, and call objective.")
    c_name = st.text_input("Company Name", value=current_ctx.get("company_name", "Acme SaaS"))
    c_desc = st.text_area(
        "Product Description",
        value=current_ctx.get("product_description", "A workflow automation platform for operations teams."),
        height=110,
    )
    c_targ = st.text_area(
        "Target Persona",
        value=current_ctx.get("target_persona", "Alex, a mid-level operations manager at a 200-person company."),
        height=110,
    )
    c_goal = st.text_input("Call Goal", value=current_ctx.get("call_goal", "Book a 30-minute technical walkthrough."))

    if st.button("Generate Sandbox", use_container_width=True):
        with st.spinner("Wiping data and generating new base script..."):
            payload = {
                "company_name": c_name,
                "product_description": c_desc,
                "target_persona": c_targ,
                "call_goal": c_goal
            }
            resp = requests.post(f"{API}/setup-campaign", json=payload)
            if resp.ok:
                st.success("New sandbox ready.")
                st.session_state.history = []
                st.session_state.call_active = False
                st.rerun()
            else:
                st.error(f"Failed to setup campaign: {resp.text}")

    st.divider()
    st.subheader("Current Campaign")
    st.write(f"**Company:** {current_ctx.get('company_name', 'Acme SaaS')}")
    st.write(f"**Goal:** {current_ctx.get('call_goal', 'Book a 30-minute technical walkthrough.')}")
    st.caption("Generating a new sandbox clears the current transcripts, analyses, and scripts.")


# ── Session state init ────────────────────────────────────────────────────────

if "history" not in st.session_state:
    st.session_state.history = []
if "call_active" not in st.session_state:
    st.session_state.call_active = False
if "script_version" not in st.session_state:
    st.session_state.script_version = 0
if "last_call_id" not in st.session_state:
    st.session_state.last_call_id = None
if "last_audio" not in st.session_state:
    st.session_state.last_audio = None  # mp3 bytes for the most recent agent reply


# ── Helpers ───────────────────────────────────────────────────────────────────

def fetch_tts(text: str):
    """Fetch audio bytes using gTTS as a lightweight mock TTS layer for the demo."""
    try:
        from gtts import gTTS
        from io import BytesIO
        mp3_fp = BytesIO()
        tts = gTTS(text=text, lang='en', tld='com')
        tts.write_to_fp(mp3_fp)
        return mp3_fp.getvalue(), None
    except Exception as e:
        return None, f"gTTS Error: {e}"


def get_agent_reply(history):
    resp = requests.post(f"{API}/call/turn", json={"conversation_history": history})
    resp.raise_for_status()
    return resp.json()["reply"]


def get_prospect_reply(history):
    resp = requests.post(f"{API}/prospect/respond", json={"conversation_history": history})
    resp.raise_for_status()
    return resp.json()["reply"]


def get_script():
    resp = requests.get(f"{API}/script/current")
    resp.raise_for_status()
    return resp.json()


def end_call_and_analyze():
    """Save transcript and delegate analysis and optimization to n8n."""
    # 1. Save transcript
    resp = requests.post(
        f"{API}/call/end",
        json={
            "conversation_history": st.session_state.history,
            "script_version": st.session_state.script_version,
        },
    )
    resp.raise_for_status()
    call_id = resp.json()["call_id"]
    st.session_state.last_call_id = call_id

    # 2. Delegate to n8n Webhook
    # n8n is strictly required for the orchestration layer
    try:
        n8n_resp = requests.post(
            f"{N8N_WEBHOOK_BASE}/call-end",
            json={"call_id": call_id},
            timeout=120,
        )
        if not n8n_resp.ok:
            st.error(f"n8n Webhook returned error: {n8n_resp.status_code} {n8n_resp.text}")
            return call_id, 0, False
    except Exception as e:
        st.error(f"Could not reach n8n workflow. Make sure it is Active. Error: {e}")
        return call_id, 0, False

    # Return call_id, and 0 for len(all_analyses) because n8n runs async in the background
    return call_id, 0, True


# ── Layout ────────────────────────────────────────────────────────────────────

try:
    current_script = get_script()
except Exception:
    current_script = None

try:
    analyses = requests.get(f"{API}/analysis/all").json()
except Exception:
    analyses = []

metric_1, metric_2, metric_3 = st.columns(3)
with metric_1:
    st.metric("Script Version", current_script["version"] if current_script else "—")
with metric_2:
    st.metric("Calls Analyzed", len(analyses))
with metric_3:
    st.metric("Active Turns", len(st.session_state.history))

st.divider()

col_call, col_script, col_log = st.columns([2, 2, 2], gap="large")

# ── Left: Live Call ───────────────────────────────────────────────────────────

with col_call:
    st.subheader("Live Call")
    st.caption("Use manual mode to roleplay the prospect, or let the simulator generate the next turn.")

    auto_mode = st.toggle("Auto-run with prospect simulator", value=False)

    if st.session_state.last_audio:
        st.audio(st.session_state.last_audio, format="audio/mp3", autoplay=True)

    if not st.session_state.call_active:
        if st.button("Start Call", type="primary"):
            script = get_script()
            st.session_state.script_version = script["version"]
            st.session_state.history = []
            st.session_state.call_active = True

            opener = script["sections"]["opener"]
            st.session_state.history.append({"role": "agent", "text": opener})
            audio, err = fetch_tts(opener)
            if err:
                st.warning(f"TTS: {err}")
            st.session_state.last_audio = audio
            st.rerun()
    else:
        if st.button("End Call", type="secondary"):
            st.session_state.last_audio = None
            success = False
            with st.spinner("Saving transcript and running analysis..."):
                call_id, num_analyses, success = end_call_and_analyze()

            if success:
                st.session_state.call_active = False
                msg = f"Call ended (ID: {call_id}). Analysis saved."
                if num_analyses >= 2:
                    msg += " Script optimized — see Current Script panel."
                st.success(msg)
                st.rerun()
            else:
                st.warning("Analysis failed. Please fix n8n to continue.")

    # Render transcript — audio player appears inline after the last agent message
    for turn in st.session_state.history:
        if turn["role"] == "agent":
            with st.chat_message("assistant"):
                st.write(turn["text"])
        else:
            with st.chat_message("user"):
                st.write(turn["text"])

    # Input area
    if st.session_state.call_active:
        if auto_mode:
            if st.button("Next Turn (Prospect)"):
                with st.spinner("Prospect responding..."):
                    prospect_text = get_prospect_reply(st.session_state.history)
                st.session_state.history.append({"role": "prospect", "text": prospect_text})

                with st.spinner("Agent responding..."):
                    agent_text = get_agent_reply(st.session_state.history)
                st.session_state.history.append({"role": "agent", "text": agent_text})
                audio, err = fetch_tts(agent_text)
                if err:
                    st.warning(f"TTS: {err}")
                st.session_state.last_audio = audio
                st.rerun()
        else:
            user_input = st.chat_input("Your message (as prospect)...")
            if user_input:
                st.session_state.history.append({"role": "prospect", "text": user_input})
                with st.spinner("Agent responding..."):
                    agent_text = get_agent_reply(st.session_state.history)
                st.session_state.history.append({"role": "agent", "text": agent_text})
                audio, err = fetch_tts(agent_text)
                if err:
                    st.warning(f"TTS: {err}")
                st.session_state.last_audio = audio
                st.rerun()


# ── Center: Current Script ────────────────────────────────────────────────────

with col_script:
    st.subheader("Current Script")
    st.caption("The live script used by the agent on this run. Updated sections are highlighted softly.")

    try:
        script = current_script if current_script else get_script()
        version = script["version"]
        sections = script["sections"]

        st.markdown(f"**Version {version}**")

        prev_sections = {}
        if version > 0:
            try:
                scripts_dir = os.path.join(os.path.dirname(__file__), "..", "data", "scripts")
                with open(os.path.join(scripts_dir, f"script_v{version - 1}.json")) as f:
                    prev_sections = json.load(f)["sections"]
            except Exception:
                pass

        for section_name, text in sections.items():
            changed = prev_sections.get(section_name) != text and bool(prev_sections)
            label = f"**{section_name.replace('_', ' ').title()}**"
            if changed:
                st.markdown(label)
                st.markdown(
                    f"<div style='background:#f3f8f2;color:#111;padding:10px 12px;border-radius:6px;border-left:3px solid #7aa874'>{text}</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(label)
                st.markdown(
                    f"<div style='background:#f8f9fa;color:#111;padding:10px 12px;border-radius:6px'>{text}</div>",
                    unsafe_allow_html=True,
                )
            st.markdown("")

    except Exception as e:
        st.error(f"Could not load script: {e}")


# ── Right: Improvement Log ────────────────────────────────────────────────────

with col_log:
    st.subheader("Improvement Log")
    st.caption("Saved analyses from completed calls, plus the change log for the active script.")

    if st.button("Refresh"):
        st.rerun()

    if not analyses:
        st.info("No analyses yet. End a call to trigger analysis.")
    else:
        st.markdown(f"**{len(analyses)} call(s) analyzed**")
        for a in reversed(analyses):
            outcome_text = a["outcome"].replace("_", " ").title()
            st.markdown(f"**Call {a['call_id']}**")
            st.write(f"Outcome: {outcome_text}")
            if a.get("objections_raised"):
                st.markdown(f"Objections: `{'`, `'.join(a['objections_raised'])}`")
            for rec in a.get("recommendations", []):
                with st.expander(f"Fix: {rec['section']}"):
                    st.markdown(f"**Issue:** {rec['issue']}")
                    st.markdown(f"**Suggestion:** {rec['suggestion']}")
            st.divider()

    try:
        script = get_script()
        change_log = script.get("change_log", [])
        if change_log:
            st.subheader("Script Change Log")
            for entry in reversed(change_log):
                with st.expander(f"v{entry.get('version', '?')} — {entry.get('section', '')}"):
                    st.markdown(entry.get("reason", "") or entry.get("description", ""))
    except Exception:
        pass
