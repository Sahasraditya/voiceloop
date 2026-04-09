import os
import json
import google.generativeai as genai
from prompts import (
    AGENT_SYSTEM_PROMPT,
    PROSPECT_SYSTEM_PROMPT,
    ANALYZER_PROMPT,
    OPTIMIZER_PROMPT,
    GENERATE_V0_PROMPT,
)

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Analysis schema — enforced at the API level so we don't need to parse freeform text
ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "outcome": {
            "type": "string",
            "enum": ["converted", "no_conversion", "callback_scheduled"],
        },
        "objections_raised": {
            "type": "array",
            "items": {"type": "string"},
        },
        "objection_outcomes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "objection": {"type": "string"},
                    "outcome": {"type": "string"}
                },
                "required": ["objection", "outcome"]
            }
        },
        "recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "section": {"type": "string"},
                    "issue": {"type": "string"},
                    "suggestion": {"type": "string"},
                },
                "required": ["section", "issue", "suggestion"],
            },
        },
        "duration_turns": {"type": "integer"},
    },
    "required": [
        "outcome",
        "objections_raised",
        "objection_outcomes",
        "recommendations",
        "duration_turns",
    ],
}


def agent_reply(conversation_history: list, current_script: dict, context: dict) -> str:
    sections = current_script["sections"]
    kwargs = {**sections, **context}
    system_prompt = AGENT_SYSTEM_PROMPT.format(**kwargs)

    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=system_prompt,
    )

    # Convert our history format to Gemini's format
    gemini_history = []
    for turn in conversation_history[:-1]:  # all but the last turn
        role = "user" if turn["role"] == "prospect" else "model"
        gemini_history.append({"role": role, "parts": [turn["text"]]})

    chat = model.start_chat(history=gemini_history)
    last_message = conversation_history[-1]["text"]
    response = chat.send_message(last_message)
    return response.text.strip()


def prospect_reply(conversation_history: list, context: dict) -> str:
    system_prompt = PROSPECT_SYSTEM_PROMPT.format(**context)
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=system_prompt,
    )

    gemini_history = []
    for turn in conversation_history[:-1]:
        # From the prospect's perspective, agent is "user" and prospect is "model"
        role = "user" if turn["role"] == "agent" else "model"
        gemini_history.append({"role": role, "parts": [turn["text"]]})

    chat = model.start_chat(history=gemini_history)
    last_message = conversation_history[-1]["text"]
    response = chat.send_message(last_message)
    return response.text.strip()


def _text_contains_any(text: str, phrases: list[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def _infer_outcome_from_transcript(transcript: dict) -> str:
    prospect_lines = [
        turn["text"].lower()
        for turn in transcript["turns"]
        if turn["role"] == "prospect"
    ]
    joined = " ".join(prospect_lines)

    callback_markers = [
        "tuesday", "wednesday", "thursday", "friday", "monday",
        "next week", "this week", "afternoon", "morning", "pm", "am",
        "schedule", "book it", "book that", "let's do", "lets do",
        "that works", "works for me", "i'm available", "im available",
        "see you then", "talk then", "sounds good", "set it up",
    ]
    converted_markers = [
        "yes, let's move forward", "yes lets move forward", "sign me up",
        "we'll move forward", "we will move forward", "let's proceed",
        "lets proceed", "we're in", "we are in", "go ahead",
    ]

    if _text_contains_any(joined, converted_markers):
        return "converted"
    if _text_contains_any(joined, callback_markers):
        return "callback_scheduled"
    return "no_conversion"


def analyze_call(transcript: dict, context: dict) -> dict:
    # Format transcript as readable text for the prompt
    turns_text = "\n".join(
        f"{t['role'].upper()}: {t['text']}" for t in transcript["turns"]
    )
    prompt = ANALYZER_PROMPT.format(
        transcript=turns_text,
        call_goal=context.get("call_goal", "achieve the stated next step"),
    )

    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=ANALYSIS_SCHEMA,
        ),
    )

    response = model.generate_content(prompt)
    analysis = json.loads(response.text)

    heuristic_outcome = _infer_outcome_from_transcript(transcript)
    if analysis.get("outcome") == "callback_scheduled" and heuristic_outcome == "no_conversion":
        analysis["outcome"] = "no_conversion"

    return analysis


def optimize_script(current_script: dict, all_analyses: list) -> dict:
    prompt = OPTIMIZER_PROMPT.format(
        current_script=json.dumps(current_script, indent=2),
        num_analyses=len(all_analyses),
        analyses=json.dumps(all_analyses, indent=2),
    )

    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
        ),
    )

    response = model.generate_content(prompt)
    new_script = json.loads(response.text)

    # Sanity check: make sure version incremented and structure is intact
    if "version" not in new_script or "sections" not in new_script:
        raise ValueError("Gemini returned a malformed script")

    return new_script


def generate_base_script(context: dict) -> dict:
    prompt = GENERATE_V0_PROMPT.format(**context)
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
        ),
    )
    response = model.generate_content(prompt)
    script = json.loads(response.text)
    if "version" not in script or "sections" not in script:
        raise ValueError("Gemini returned a malformed script")
    return script
