# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""classify_airline_intent — Root Router Controller Tool.

Owns the SkyFlow Airlines intent catalogue, scope validation, and spoke-agent
routing decisions. The model classifies customer requests into an intent_id,
and this tool deterministically updates session state, increments retry
counters in Python, and returns guided agent_action instructions.

PLATFORM CONTRACT:
`context` is a platform-injected global in CX Agent Studio and must never be
declared as a function parameter.
"""

import logging
from typing import Literal, NamedTuple

logger = logging.getLogger(__name__)


class Intent(NamedTuple):
    """Routing target and domain parameters for an airline intent."""

    target_agent: str
    domain: str = ""


# --- generated from sources/intents.yaml (catalogue) — do not edit ---
# SkyFlow Airlines Intent Routing Table
# (target_agent, domain)
_INTENT_BASE = {
    "DAY_OF_TRAVEL": Intent(
        target_agent="day_of_travel_agent", domain="DAY_OF_TRAVEL",
    ),
    "SALES": Intent(
        target_agent="sales_agent", domain="SALES",
    ),
    "GENERAL_FAQ": Intent(
        target_agent="general_faq_agent", domain="GENERAL_FAQ",
    ),
}
# --- end generated ---


# --- generated from sources/intents.yaml (signature) — do not edit ---
def classify_airline_intent(
    intent_id: Literal[
        "",
        "DAY_OF_TRAVEL",
        "SALES",
        "GENERAL_FAQ",
    ] = "",
) -> dict:
    # --- end generated ---
    """Classify customer intent and compute destination sub-agent routing.

    Call this tool as soon as the customer expresses what they need help with.
    If the customer is vague or ambiguous, ask one clarifying question first.
    If they remain vague on the second turn, pass an empty string "".

    Args:
        intent_id: The matched intent. Must be exactly one of:
            DAY_OF_TRAVEL:
                flight status, delays, gates, terminal directions, baggage claim
                carousels, boarding passes
                Customer requests related to day-of-departure operations including
                flight status and delays, gate assignments, concourse and terminal
                navigation, baggage reclaim carousels, boarding times and groups,
                and airport check-in desks.
            SALES:
                fast track security, checked bags, seat upgrades, lounge passes,
                comfort bundles
                Customer requests related to purchasing add-ons and upgrades
                including Fast Track priority security passes, additional checked
                luggage allowance, extra legroom seat selection, Executive Lounge
                day passes, and all-in-one comfort bundles.
            GENERAL_FAQ:
                baggage size/weight limits, name changes, ticket cancellations,
                refunds, pet travel, policies
                General airline policy and rule inquiries including cabin and
                checked baggage dimensions and weight limits, ticket spelling
                corrections and name change fees, cancellations and refund policies,
                traveling with pets, infants, and special mobility assistance.

    Returns:
        dict containing:
            status:       "success" or "error"
            next_step:    ROUTE_DAY_OF_TRAVEL  — transfer to day_of_travel_agent
                          ROUTE_SALES          — transfer to sales_agent
                          ROUTE_GENERAL_FAQ    — transfer to general_faq_agent
                          CLARIFY_UNCLEAR      — ask clarifying question with domain options
                          END_SESSION          — polite farewell and close session
                          RETRY                — re-prompt customer
            agent_action: Spoken guidance and next question for the customer
            data:         Dictionary with classified intent and destination metadata
            error_code:   Present only when status is "error"
    """
    try:
        raw_intent = (intent_id or "").strip().upper()
        matched_intent = _INTENT_BASE.get(raw_intent)

        data = {
            "intent_id": raw_intent,
            "domain": matched_intent.domain if matched_intent else "",
            "target_agent": matched_intent.target_agent if matched_intent else "",
        }

        # 1. Active Sub-Agent Domain Transfer (silent transfer, sub-agent handles the turn)
        if matched_intent and matched_intent.target_agent:
            context.state["intent_id"] = raw_intent
            context.state["domain"] = matched_intent.domain
            context.state["target_agent"] = matched_intent.target_agent

            return _response(
                status="success",
                next_step=f"ROUTE_{matched_intent.domain}",
                agent_action="",
                data=data,
            )

        # 2. Vague, Unclear, or Missing Intent Handling (2-turn retry guardrail)
        return _handle_unclear_help(data=data)

    except Exception:  # noqa: BLE001 - tool must never raise unhandled exceptions
        logger.exception("classify_airline_intent encountered an error")
        return _end_chat(
            reason="SYSTEM_ERROR",
            agent_action=(
                "Apologise sincerely and inform the customer that a technical issue occurred. "
                "Please send another message shortly. Thank you for contacting SkyFlow Airlines, goodbye."
            ),
            data=data,
        )


def _response(
    status: str,
    next_step: str,
    agent_action: str,
    data: dict | None = None,
    error_code: str | None = None,
) -> dict:
    """Build a uniform return envelope."""
    res = {
        "status": status,
        "next_step": next_step,
        "agent_action": agent_action,
        "data": data or {},
    }
    if error_code:
        res["error_code"] = error_code
    return res


def _end_chat(reason: str, agent_action: str, data: dict) -> dict:
    """Record chat termination reason and mark chat session complete."""
    context.state["end_reason"] = reason
    context.state["chat_complete"] = "true"
    data["end_reason"] = reason
    return _response(
        status="success",
        next_step="END_SESSION",
        agent_action=agent_action,
        data=data,
    )


def _get_retry_count(key: str) -> int:
    """Safely parse integer retry counter from context.state."""
    try:
        return int(context.state.get(key, "0") or "0")
    except (ValueError, TypeError):
        return 0


def _handle_unclear_help(data: dict) -> dict:
    """Handle vague requests: clarify once with options, terminate on 2nd attempt."""
    count = _get_retry_count("unclear_retry_count")
    if count == 0:
        context.state["unclear_retry_count"] = "1"
        return _response(
            status="success",
            next_step="CLARIFY_UNCLEAR",
            agent_action=(
                "Ask the customer politely what specific service or topic they need help with today "
                "(such as day-of-travel flight info, purchasing extras like bags or Fast Track, or general airline FAQ)."
            ),
            data=data,
        )

    return _end_chat(
        reason="UNCLEAR_INTENT_GIVE_UP",
        agent_action=(
            "Politely explain that since the request is still unclear, you will conclude the chat. "
            "Thank them for contacting SkyFlow Airlines and say goodbye."
        ),
        data=data,
    )

