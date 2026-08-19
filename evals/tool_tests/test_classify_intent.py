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

"""Unit tests for classify_airline_intent controller tool matching the 3 sub-agents."""

import builtins
import pytest
from cxas_app.SkyFlowAirlineApp.tools.classify_airline_intent.python_function.python_code import (
    classify_airline_intent,
    _INTENT_BASE,
)


def test_classify_day_of_travel_intent():
    """Verify DAY_OF_TRAVEL routes directly to day_of_travel_agent."""
    builtins.context.state.clear()
    res = classify_airline_intent(intent_id="DAY_OF_TRAVEL")
    assert res["status"] == "success"
    assert res["next_step"] == "ROUTE_DAY_OF_TRAVEL"
    assert res["data"]["target_agent"] == "day_of_travel_agent"
    assert res["data"]["domain"] == "DAY_OF_TRAVEL"
    assert builtins.context.state["intent_id"] == "DAY_OF_TRAVEL"
    assert builtins.context.state["domain"] == "DAY_OF_TRAVEL"
    assert builtins.context.state["target_agent"] == "day_of_travel_agent"
    assert res["agent_action"] == ""


def test_classify_sales_intent():
    """Verify SALES routes directly to sales_agent."""
    builtins.context.state.clear()
    res = classify_airline_intent(intent_id="SALES")
    assert res["status"] == "success"
    assert res["next_step"] == "ROUTE_SALES"
    assert res["data"]["target_agent"] == "sales_agent"
    assert res["data"]["domain"] == "SALES"
    assert builtins.context.state["intent_id"] == "SALES"
    assert builtins.context.state["domain"] == "SALES"
    assert builtins.context.state["target_agent"] == "sales_agent"
    assert res["agent_action"] == ""


def test_classify_general_faq_intent():
    """Verify GENERAL_FAQ routes directly to general_faq_agent."""
    builtins.context.state.clear()
    res = classify_airline_intent(intent_id="GENERAL_FAQ")
    assert res["status"] == "success"
    assert res["next_step"] == "ROUTE_GENERAL_FAQ"
    assert res["data"]["target_agent"] == "general_faq_agent"
    assert res["data"]["domain"] == "GENERAL_FAQ"
    assert builtins.context.state["intent_id"] == "GENERAL_FAQ"
    assert builtins.context.state["domain"] == "GENERAL_FAQ"
    assert builtins.context.state["target_agent"] == "general_faq_agent"
    assert res["agent_action"] == ""


def test_unclear_intent_clarification_and_give_up():
    """Test 2-turn retry bounded clarification for missing or ambiguous inputs."""
    builtins.context.state.clear()

    # Turn 1: Clarify
    res1 = classify_airline_intent(intent_id="")
    assert res1["status"] == "success"
    assert res1["next_step"] == "CLARIFY_UNCLEAR"
    assert builtins.context.state["unclear_retry_count"] == "1"

    # Turn 2: Second unclear input terminates session
    res2 = classify_airline_intent(intent_id="")
    assert res2["status"] == "success"
    assert res2["next_step"] == "END_SESSION"
    assert builtins.context.state["end_reason"] == "UNCLEAR_INTENT_GIVE_UP"
    assert builtins.context.state["chat_complete"] == "true"


def test_unknown_or_unmatched_intent_handling():
    """Verify unmatched intent triggers clarification guardrail."""
    builtins.context.state.clear()
    res = classify_airline_intent(intent_id="UNKNOWN_TOPIC")
    assert res["status"] == "success"
    assert res["next_step"] == "CLARIFY_UNCLEAR"
    assert builtins.context.state["unclear_retry_count"] == "1"
