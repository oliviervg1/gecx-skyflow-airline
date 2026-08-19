# SkyFlow Airlines: Customer Presentation & Demo Playbook

**Target Audience**: Enterprise Architects, Head of Conversational AI, Contact Center Technical Leaders, Product Managers.  
**Session Duration**: 25 - 35 minutes  
**Goal**: Demonstrate how Google Cloud GECX Agent Studio achieves **99.9% routing precision**, **sub-second latency**, and **deterministic session control** using the **Tool-First Intent Router Architecture**.

---

## 🎯 Executive Storyline: Why Tool-First Router Matters

Enterprise contact centers face a common failure pattern when deploying generative AI routers:
1. **The "Prompt Soup" Trap**: As business requirements grow from 5 intents to 30+, embedding decision logic into LLM prompt instructions causes routing ambiguity, hallucinated answers, and counter drift.
2. **The "Stateless Chat" Trap**: Prompt-only bots cannot manage state machines (e.g. 2 retry limits, domain handoffs), causing repetitive loops and customer frustration.
3. **The SkyFlow Solution**: We separate **semantic understanding** (what the LLM does best) from **business logic & state execution** (what deterministic Python code does best).

---

## 🎬 Live Demonstration Script (Step-by-Step)

### Preparation
1. Run the interactive terminal demo driver:
   ```bash
   uv run python scripts/drive_session.py
   # Or run a preset scenario directly:
   uv run python scripts/drive_session.py --scenario day_of_travel
   ```
2. Explain the architecture trace printed for each turn:
   - **Active Agent & Agent Transfers**: Displays real-time multi-agent routing.
   - **Tool Executions**: Exact parameters and deterministic Python controller envelope (`status`, `next_step`, `agent_action`).
   - **Session Variables (`context.state`)**: Authoritative session state variables.

---

### 🌟 Scenario 1: Day of Travel Routing & Silent Handover
**Customer Pitch**: *"Watch how a day-of-travel query is instantly classified and silently routed to the day_of_travel_agent, which responds with its under-construction notice and concludes the session cleanly."*

1. **User Prompt**:
   > *"What gate does flight SK101 leave from and is it on time?"*
2. **What Happens Under the Hood**:
   - `intent_router_agent` invokes `classify_airline_intent(intent_id="DAY_OF_TRAVEL")`.
   - Tool sets `intent_id="DAY_OF_TRAVEL"`, `domain="DAY_OF_TRAVEL"`, and `target_agent="day_of_travel_agent"` in `context.state`.
   - Tool returns `agent_action: ""` for silent transfer.
   - Router emits `{@AGENT: day_of_travel_agent}` without speaking a redundant preamble.
   - `day_of_travel_agent` responds: *"You've reached the Day of Travel agent. I am currently under construction and will now terminate the conversation."*
   - Sub-agent's `end_chat` callback attaches `Part.from_end_session(reason="UNDER_CONSTRUCTION")` and concludes the chat.

---

### 🌟 Scenario 2: Ancillary Sales Routing & Silent Handover
**Customer Pitch**: *"When an upsell request arrives, the router classifies SALES and hands off to sales_agent."*

1. **User Prompt**:
   > *"I would like to add fast track security and an extra checked bag to my flight"*
2. **What Happens**:
   - Router classifies intent as `SALES` and transfers to `sales_agent`.
   - `sales_agent` responds: *"You've reached the Sales agent. I am currently under construction and will now terminate the conversation."*
   - Sub-agent's `end_chat` callback attaches `Part.from_end_session(reason="UNDER_CONSTRUCTION")` and concludes the chat.

---

### 🌟 Scenario 3: General Policy & FAQ Knowledge Routing
**Customer Pitch**: *"When customers ask policy questions, the router seamlessly delegates to general_faq_agent."*

1. **User Prompt**:
   > *"What are your carry on luggage dimension limits and weight restrictions?"*
2. **What Happens**:
   - Router classifies intent as `GENERAL_FAQ` and transfers to `general_faq_agent`.
   - `general_faq_agent` responds: *"You've reached the General FAQ agent. I am currently under construction and will now terminate the conversation."*
   - Sub-agent's `end_chat` callback attaches `Part.from_end_session(reason="UNDER_CONSTRUCTION")` and concludes the chat.

---

### 🌟 Scenario 4: Ambiguity Guardrails & 2-Turn Clarification
**Customer Pitch**: *"What happens when a customer is vague? Traditional bots either guess wildly or fail. Watch how SkyFlow handles ambiguity with a bounded 2-turn retry counter."*

1. **User Prompt 1**:
   > *"I need some help with my trip"*
2. **What Happens**:
   - Tool classifies empty intent `intent_id=""`.
   - Tool checks `unclear_retry_count` (which is `0`), increments to `1` in `context.state`, and returns `CLARIFY_UNCLEAR`.
   - Agent prompts: *"Certainly! Could you please let me know what you need help with today, such as flight status, travel extras like baggage, or general airline policies?"*
3. **User Prompt 2**:
   > *"Is my flight SK204 delayed today?"*
4. **What Happens**:
   - Router classifies `DAY_OF_TRAVEL` and transfers to `day_of_travel_agent`.
   - `day_of_travel_agent` responds with its under-construction notice and ends session.

---

### 🌟 Scenario 5: Out-of-Scope Boundary Protection
**Customer Pitch**: *"Contact centers cannot have their airline bot answering recipes or ordering pizzas. Watch the deterministic scope guardrail."*

1. **User Prompt**:
   > *"Can you order a pepperoni pizza to terminal 2?"*
2. **What Happens**:
   - Router classifies `OUT_OF_SCOPE`.
   - Tool returns `CLARIFY_OUT_OF_SCOPE` with spoken guidance: *"I'm sorry, I can only assist with SkyFlow Airlines flights, day-of-travel information, travel add-ons, and airline policies. How may I assist you with your flight today?"*
   - Zero hallucination.

---

## 💡 Key Architectural Q&A for Technical Leads

**Q: Why not use a single agent with all tools?**  
*A: Sub-agent specialization isolates prompt instructions, reduces token context, prevents tool selection confusion when scaling to 50+ tools, and enables distributed team development.*

**Q: How do we prevent intent catalog drift across environments?**  
*A: All intents reside in `sources/intents.yaml`. The compiler script (`scripts/generate_intents.py`) syncs the code and enforces a `--check` CI gate in continuous integration.*

**Q: How does session conclusion work across Digital Chat and API integrations?**  
*A: Built-in `end_chat` after-model callbacks attach `Part.from_end_session` when a terminal response is emitted (either via tool completion or sub-agent under-construction notice) to cleanly close the session across web widgets and messaging channels.*
