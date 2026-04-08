import os
import json
from openai import OpenAI
from prompts import (
    AGENT_SYSTEM_PROMPT,
    PROSPECT_SYSTEM_PROMPT,
    ANALYZER_PROMPT,
    OPTIMIZER_PROMPT,
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-4o-mini"


def agent_reply(conversation_history: list, current_script: dict) -> str:
    sections = current_script["sections"]
    system_prompt = AGENT_SYSTEM_PROMPT.format(**sections)

    messages = [{"role": "system", "content": system_prompt}]
    for turn in conversation_history:
        role = "user" if turn["role"] == "prospect" else "assistant"
        messages.append({"role": role, "content": turn["text"]})

    response = client.chat.completions.create(model=MODEL, messages=messages)
    return response.choices[0].message.content.strip()


def prospect_reply(conversation_history: list) -> str:
    messages = [{"role": "system", "content": PROSPECT_SYSTEM_PROMPT}]
    for turn in conversation_history:
        role = "user" if turn["role"] == "agent" else "assistant"
        messages.append({"role": role, "content": turn["text"]})

    response = client.chat.completions.create(model=MODEL, messages=messages)
    return response.choices[0].message.content.strip()


def analyze_call(transcript: dict) -> dict:
    turns_text = "\n".join(
        f"{t['role'].upper()}: {t['text']}" for t in transcript["turns"]
    )
    prompt = ANALYZER_PROMPT.format(transcript=turns_text)

    # json_object mode guarantees valid JSON back — no manual parsing needed
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


def optimize_script(current_script: dict, all_analyses: list) -> dict:
    prompt = OPTIMIZER_PROMPT.format(
        current_script=json.dumps(current_script, indent=2),
        num_analyses=len(all_analyses),
        analyses=json.dumps(all_analyses, indent=2),
    )

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    new_script = json.loads(response.choices[0].message.content)

    if "version" not in new_script or "sections" not in new_script:
        raise ValueError("LLM returned a malformed script")

    return new_script
