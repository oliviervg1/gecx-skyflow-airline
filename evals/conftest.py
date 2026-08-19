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

"""Shared pytest fixtures for the SkyFlow Airlines GECX unit tests."""

import builtins
import os
import sys

sys.dont_write_bytecode = True

import pytest
from cxas_scrapi.utils.callback_libs import (
    Blob,
    CallbackContext,
    Content,
    Event,
    LlmRequest,
    LlmResponse,
    Part,
    ToolContext,
)

_HERE = os.path.abspath(os.path.dirname(__file__))
_APP_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
_APP = os.path.join(_APP_ROOT, "cxas_app", "SkyFlowAirlineApp")

if _APP_ROOT not in sys.path:
    sys.path.insert(0, _APP_ROOT)

sys.path.insert(0, os.path.join(_APP, "tools"))
sys.path.insert(0, os.path.join(_APP, "agents"))

# Inject platform classes into builtins
builtins.Part = Part
builtins.Content = Content
builtins.Blob = Blob
builtins.Event = Event
builtins.LlmRequest = LlmRequest
builtins.LlmResponse = LlmResponse
builtins.CallbackContext = CallbackContext


@pytest.fixture(autouse=True)
def inject_tool_context():
    """Inject a fresh ToolContext before each test."""
    ctx = ToolContext(state={})
    builtins.context = ctx
    yield ctx
    if hasattr(builtins, "context"):
        delattr(builtins, "context")


def make_event(author: str, parts, index: int = 1) -> Event:
    """Build a session event."""
    return Event(
        id=f"event-{index}",
        author=author,
        timestamp=index,
        invocation_id="invocation-1",
        content=Content(parts=parts, role=author),
    )


def text_part(value: str) -> Part:
    return Part.from_text(text=value)


def audio_part(transcript: str) -> Part:
    """A part carrying only an audio transcript, as in a live voice call."""
    return Part(inline_data=Blob(transcript=transcript))


def make_request(*texts: str) -> LlmRequest:
    return LlmRequest(
        contents=[
            Content(parts=[text_part(value)], role="user") for value in texts
        ]
    )
