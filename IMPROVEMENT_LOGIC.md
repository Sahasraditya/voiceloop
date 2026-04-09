# Script Improvement Logic

This file explains how script changes were produced across iterations in the current demo campaign. The goal is to make the optimization loop human-readable alongside the machine-readable `change_log` entries stored in `data/scripts/`.

Current campaign context:
- Company: Burger King
- Offer: Graduation catering service
- Persona: School principal organizing graduation for a large student cohort
- Goal: Book a tasting menu

---

## v0 → v1

### What happened

The initial script assumed too much too early. In the analyzed calls, the agent jumped into a graduation catering pitch without first validating the prospect’s situation or asking enough discovery questions.

The saved analyses pointed to three recurring weaknesses:
- the opener assumed details like event scale before confirming them
- the value proposition stayed too generic when the prospect asked for specifics
- the close was directionally right but not operationally tight enough for scheduling

### What the analysis recommended

The recommendations in the saved analyses pushed the script toward:
- open-ended discovery earlier in the call
- more concrete examples in the value proposition
- specific scheduling options in the close

### What changed in the script

`script_v1.json` reflects those changes:
- **Opener**: changed from an assumption-led pitch to an opener that asks about student count and the prospect’s biggest challenge
- **Value proposition**: expanded to include specific food items and customizable packages
- **Timing objection**: added a validation step before trying to reschedule
- **Close**: changed from a general invitation to specific tasting time slots

### Why that matters

This is the first meaningful move from a generic cold-call script toward a context-aware sales script. The improvement is not just “better wording”; it is better call structure:
- discover first
- pitch second
- close with concrete options

---

## v1 → v2

### What happened

One analyzed call ended in `no_conversion` after the prospect rejected the interaction almost immediately. The saved recommendation made clear that the agent was still asking discovery questions too early, before earning permission to continue.

Another analysis also noted that the value proposition was still somewhat generic when describing the catering offer.

### What the analysis recommended

The optimization feedback pushed the script toward:
- a micro-commitment before discovery
- a clearer “reason to listen” in the opener
- more concrete packaging and dietary examples in the value proposition

### What changed in the script

`script_v2.json` implements those changes:
- **Opener**: now asks for permission to give a quick overview before starting discovery
- **Value proposition**: now includes concrete examples like the `Grad Feast`, menu breadth, and vegan accommodation

### Why that matters

This iteration improves the script at the top of the funnel. Instead of assuming attention, the agent now earns it first, then uses more specific proof points. That is a better response to the observed failure mode than simply “trying harder to sell.”

---

## How The Loop Decides What To Change

The optimization behavior is intentionally narrow:
- each call transcript is saved
- Gemini analyzes the transcript and returns structured recommendations
- once enough analyses exist, the optimizer reads the full analysis history plus the current script
- only sections with evidence of underperformance should be rewritten
- the output is stored as a new versioned script with a `change_log`

This means the system is not trying to reinvent the whole script after every call. It is trying to make evidence-backed edits to the weakest sections.

---

## What This Demonstrates

- conversation history is used as short-term memory during a call
- saved analyses act as cross-call memory
- optimization is based on accumulated outcomes, objections, and recommendations
- script evolution is inspectable both in JSON and in this narrative log
