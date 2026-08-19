# Technical Design Document: GECX Agent Studio Tool-First Intent Routing

## 1. Executive Problem Statement

Enterprise virtual assistants in high-volume contact centers (e.g., airlines, telecommunications, banking) require:
1. **Ultra-low routing latency** (< 800ms response time on digital chat).
2. **Deterministic boundary enforcement** (guaranteed deflection of out-of-scope requests, strict retry thresholds).
3. **Multi-turn state tracking** (resilient PNR, flight number, and domain state persistence).
4. **Session reliability** (deterministic greeting, no-input recovery, clean chat conclusion).

### The Prompt-Heavy Router Anti-Pattern
In traditional LLM chatbot designs, developers encode the entire intent catalog, branch logic, retry counters, and handover conditions into huge system prompts:

```
[Anti-Pattern System Prompt]
You are a router. If the user asks about gates, say X. If the user asks about bags, say Y.
Count how many times they asked something unclear. If count > 2, say goodbye.
Remember to save the PNR if they mentioned it.
```

**Failure Modes of Prompt-Heavy Routers:**
- **State Amnesia & Counter Drift**: LLMs cannot reliably increment integer counters (`count = count + 1`) over multi-turn context windows.
- **Routing Indeterminism**: Small variations in phrasing cause the LLM to hallucinate intermediate answers or skip required handoffs.
- **Maintenance Nightmare**: Adding or updating an intent requires editing multiple prompt markdown files and risking regression.
- **Token Inflation & Latency**: Packing 30+ intent descriptions into every turn inflates input tokens and increases time-to-first-token (TTFT).

---

## 2. The Tool-First Architecture Solution

In the **Tool-First Design Pattern**, the LLM's sole responsibility is **semantic classification** (mapping user text to a strongly-typed enum parameter). All business logic, state machines, retry limits, database lookups, and guidance generation reside in **deterministic Python controller tools**.

```
[User Utterance] ──> [LLM classifies intent_id] ──> [Python Tool Controller]
                                                          │
                                         ┌────────────────┴────────────────┐
                                         ▼                                 ▼
                                 [Updates context.state]          [Returns agent_action]
                                         │                                 │
                                         └────────────────┬────────────────┘
                                                          ▼
                                            [Spoke Agent Routing / Narration]
```

### Core Architecture Pillars

### 1. Root Hub & Spoke Multi-Agent Topology
- **Hub Agent (`intent_router_agent`)**:
  - Direct customer greeting and inquiry classification via `classify_airline_intent(intent_id="...")`.
  - Reads `next_step` from tool response and emits `{@AGENT: <target_agent>}` silently.
- **Spoke 1 (`day_of_travel_agent`)**:
  - Focuses on day-of-travel domain intents (flight status, gates, delays, baggage carousels).
  - Emits under-construction response and terminates via `end_chat` callback.
- **Spoke 2 (`sales_agent`)**:
  - Focuses on ancillary sales domain intents (Fast Track, checked bags, seat selection, lounge).
  - Emits under-construction response and terminates via `end_chat` callback.
- **Spoke 3 (`general_faq_agent`)**:
  - Focuses on policy FAQ domain intents (baggage limits, name changes, refunds, pet rules).
  - Emits under-construction response and terminates via `end_chat` callback.

### 2. Single Source of Truth Intent Generation
All 3 sub-agent domain intents are defined in `sources/intents.yaml`:
```yaml
- id: DAY_OF_TRAVEL
  domain: DAY_OF_TRAVEL
  target_agent: day_of_travel_agent
  gloss: "flight status, delays, gates, terminal directions, baggage claim carousels, boarding passes"
```

The compiler script (`scripts/generate_intents.py`) parses `sources/intents.yaml` and compiles:
1. `Literal["", "DAY_OF_TRAVEL", "SALES", "GENERAL_FAQ"]` enum in tool entry function signature.
2. Exhaustive docstring descriptions combining all sub-agent customer utterances.
3. `_INTENT_BASE` dictionary mapping intent IDs to `Intent(target_agent=..., domain=...)`.
4. `--check` CI gate to enforce zero-drift synchronization.

---

## 3. Conversational Platform Callbacks

### `end_chat` (`after_model_callbacks`)
- Executes after the model has produced its response on terminal turns (`context.state["chat_complete"] == "true"`).
- Automatically appends `Part.from_end_session(reason=..., escalated=False)` to cleanly conclude the chat session.
- Sends deterministic session completion signals to Web UI and API client integrations.
- *Note for Voice vs. Chat*: In text/chat modalities, real-time voice silence detection (`before_model_callbacks`) is omitted as messaging channels are asynchronous and event-driven.

---

## 4. Session State Variable Schema (`app.json`)

All state variables are declared with `"required": []` to guarantee protobuf compatibility with Google Cloud CES:

| Variable Name | Type | Initial Value | Ownership | Description |
| :--- | :--- | :--- | :--- | :--- |
| `intent_id` | STRING | `""` | `classify_airline_intent` | Canonical active intent code |
| `domain` | STRING | `""` | `classify_airline_intent` | Active domain (`DAY_OF_TRAVEL`, `SALES`, `GENERAL_FAQ`) |
| `unclear_retry_count` | STRING | `"0"` | `classify_airline_intent` | Clarification retry counter (max 1) |
| `out_of_scope_retry_count` | STRING | `"0"` | `classify_airline_intent` | Out-of-scope retry counter (max 1) |
| `chat_complete` | STRING | `"false"` | Tools / Callbacks | `true` when turn is terminal |
| `end_reason` | STRING | `""` | Tools / Callbacks | Termination telemetry reason code |

---

## 5. Verification & Quality Gates

- **Static Linter**: `uv run cxas lint --app-dir .` passes with **0 errors, 0 warnings**.
- **Pytest Evals**: 13 passing unit tests verifying 100% of tool methods, exception handling, and callback lifecycles.
- **Golden Evals**: Consolidated golden evaluation suite in `evals/goldens/airline_goldens.yaml` (5/5 PASS in CX Agent Studio).
