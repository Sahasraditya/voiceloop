# n8n Workflow Setup Guide

These three workflows implement the call → analyze → improve loop.
Set them up in this order — each one references the next.

---

## Workflow 1 — Call Flow

**Purpose:** Receives notification that a call ended, fetches the transcript, and hands it off to the analyzer.

### Nodes (in order)

**1. Webhook — `call-end`**
- Type: Webhook
- HTTP Method: POST
- Path: `call-end`
- This is the endpoint Streamlit hits when the user clicks "End Call"
- Expected body: `{ "call_id": "abc123" }`

**2. HTTP Request — Fetch Transcript**
- Type: HTTP Request
- Method: GET
- URL: `http://localhost:8000/transcript/{{ $json.call_id }}`
- This fetches the full transcript by call ID

**3. HTTP Request — Trigger Analyzer**
- Type: HTTP Request
- Method: POST
- URL: `http://localhost:5678/webhook/analyze-call`
- Body (JSON):
  ```json
  {
    "call_id": "{{ $json.call_id }}"
  }
  ```
- Send transcript to Workflow 2

---

## Workflow 2 — Post-Call Analyzer

**Purpose:** Runs Gemini analysis on the transcript, saves the result, and conditionally triggers script optimization.

### Nodes (in order)

**1. Webhook — `analyze-call`**
- Type: Webhook
- HTTP Method: POST
- Path: `analyze-call`
- Expected body: `{ "call_id": "abc123" }`

**2. HTTP Request — Run Analysis**
- Type: HTTP Request
- Method: POST
- URL: `http://localhost:8000/call/analyze`
- Body (JSON):
  ```json
  {
    "call_id": "{{ $json.call_id }}"
  }
  ```
- This calls Gemini and returns a structured analysis dict

**3. HTTP Request — Save Analysis**
- Type: HTTP Request
- Method: POST
- URL: `http://localhost:8000/analysis/save`
- Body (JSON):
  ```json
  {
    "call_id": "{{ $json.call_id }}",
    "analysis": {{ $json }}
  }
  ```

**4. HTTP Request — Get All Analyses**
- Type: HTTP Request
- Method: GET
- URL: `http://localhost:8000/analysis/all`
- We need the count to decide whether to optimize

**5. IF Node — Enough Data to Optimize?**
- Condition: `{{ $json.length >= 2 }}`
- True branch → proceed to node 6
- False branch → end workflow

**6. HTTP Request — Trigger Optimizer**
- Type: HTTP Request
- Method: POST
- URL: `http://localhost:5678/webhook/optimize-script`
- Body: `{}` (no payload needed; optimizer fetches its own data)

---

## Workflow 3 — Script Optimizer

**Purpose:** Reads all analyses and the current script, asks Gemini to rewrite underperforming sections, and saves the new version.

### Nodes (in order)

**1. Webhook — `optimize-script`**
- Type: Webhook
- HTTP Method: POST
- Path: `optimize-script`

**2. HTTP Request — Run Optimization**
- Type: HTTP Request
- Method: POST
- URL: `http://localhost:8000/script/optimize`
- Body: `{}` (endpoint fetches analyses and current script internally)
- Returns: new script JSON with incremented version and change_log entry

**3. HTTP Request — Save New Script**
- Type: HTTP Request
- Method: POST
- URL: `http://localhost:8000/script/save`
- Body (JSON):
  ```json
  {
    "script": {{ $json }}
  }
  ```

**4. Respond to Webhook**
- Type: Respond to Webhook
- Response Body: `{ "status": "ok", "new_version": "{{ $json.version }}" }`

---

## Testing the Workflows

1. Start the backend: `uvicorn main:app --reload` (from `backend/`)
2. Import or recreate these three workflows in n8n
3. Activate all three workflows
4. Start Streamlit, run a call, click "End Call"
5. Watch the n8n execution log — you should see Workflow 1 → 2 → (after 2 calls) → 3
6. After Workflow 3 runs, refresh the Streamlit script panel — version should increment

---

## Notes

- The turn-by-turn conversation loop runs directly between Streamlit and the backend.
  n8n only handles the post-call pipeline. This keeps n8n simple and avoids polling.
- If n8n is not running, you can manually trigger analysis and optimization by hitting
  the backend endpoints directly via curl or the Swagger UI at `http://localhost:8000/docs`.
- The IF node threshold (≥2 analyses) is intentionally low for demo purposes.
  In production you'd want more data before optimizing.
