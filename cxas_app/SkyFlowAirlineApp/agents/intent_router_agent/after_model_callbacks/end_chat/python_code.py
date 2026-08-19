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

"""end_chat — deterministic chat session conclusion and state telemetry callback.

Fires after the model has produced its response. If chat_complete has been
set by a tool, this callback appends the platform end_session part to conclude
the chat session deterministically.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def after_model_callback(
    callback_context: CallbackContext,
    llm_response: LlmResponse,
) -> Optional[LlmResponse]:
    """Append end_session once, after a tool has marked the conversation complete."""
    try:
        state = callback_context.state

        if state.get("chat_complete", "") != "true":
            return None

        content = getattr(llm_response, "content", None)
        parts = list(getattr(content, "parts", None) or [])

        # If the model is executing a tool call, do not interrupt; wait for output turn
        if any(part.function_call for part in parts):
            return None

        # Nothing to close if model hasn't generated a message yet
        if not any(part.text_or_transcript() for part in parts):
            return None

        reason = state.get("end_reason", "") or "REQUEST_COMPLETED"

        state["chat_complete"] = "concluded"
        logger.info("Concluding chat session: reason=%s", reason)

        return LlmResponse.from_parts(
            parts=parts
            + [Part.from_end_session(reason=reason, escalated=False)]
        )

    except Exception:
        logger.exception("end_chat callback failed")
        return None
