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

"""Unit tests for end_chat after_model_callbacks across root router and spoke sub-agents."""

import importlib
import pytest
from cxas_scrapi.utils.callback_libs import CallbackContext, LlmResponse, Part

from conftest import text_part

SUB_AGENTS = (
    "day_of_travel_agent",
    "sales_agent",
    "general_faq_agent",
)


def spoken(*parts):
    return LlmResponse.from_parts(parts=list(parts))


def end_sessions(response):
    return [
        dict(part.function_call.args)
        for part in response.content.parts
        if part.function_call and part.function_call.name == "end_session"
    ]


def run(callback, state, *parts):
    context = CallbackContext(state=dict(state), events=[])
    response = callback.after_model_callback(context, spoken(*parts))
    return response, context.state


# 1. Router Agent Tests
def test_router_open_chat_is_left_alone():
    module = importlib.import_module(
        "cxas_app.SkyFlowAirlineApp.agents.intent_router_agent.after_model_callbacks.end_chat.python_code"
    )
    response, _ = run(module, {}, text_part("How can I help you today?"))
    assert response is None


def test_router_completed_request_concludes_chat():
    module = importlib.import_module(
        "cxas_app.SkyFlowAirlineApp.agents.intent_router_agent.after_model_callbacks.end_chat.python_code"
    )
    response, state = run(
        module, {"chat_complete": "true"}, text_part("Goodbye!")
    )
    assert response is not None
    assert end_sessions(response) == [
        {"reason": "REQUEST_COMPLETED", "session_escalated": False}
    ]
    assert state["chat_complete"] == "concluded"


# 2. Sub-Agent Tests
@pytest.fixture(params=SUB_AGENTS)
def subagent_callback(request):
    return importlib.import_module(
        f"cxas_app.SkyFlowAirlineApp.agents.{request.param}.after_model_callbacks.end_chat.python_code"
    )


def test_subagent_terminates_with_under_construction(subagent_callback):
    """Sub-agent automatically terminates conversation when outputting under construction response."""
    msg = "You've reached the agent. I am currently under construction and will now terminate the conversation."
    response, state = run(subagent_callback, {}, text_part(msg))
    assert response is not None
    assert end_sessions(response) == [
        {"reason": "UNDER_CONSTRUCTION", "session_escalated": False}
    ]
    assert state["chat_complete"] == "concluded"
    assert state["end_reason"] == "UNDER_CONSTRUCTION"


def test_subagent_ignores_empty_message(subagent_callback):
    """If no text output was generated, do not append end_session."""
    context = CallbackContext(state={}, events=[])
    empty_resp = LlmResponse.from_parts(parts=[])
    response = subagent_callback.after_model_callback(context, empty_resp)
    assert response is None
