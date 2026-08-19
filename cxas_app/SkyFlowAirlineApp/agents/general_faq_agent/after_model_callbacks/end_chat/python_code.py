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

"""end_chat — concludes the conversation after stating under construction."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def after_model_callback(
    callback_context: CallbackContext,
    llm_response: LlmResponse,
) -> Optional[LlmResponse]:
    """Append end_session to reliably terminate the conversation."""
    try:
        # Prevent infinite reasoning loops if already concluded
        if callback_context.state.get("chat_complete") == "concluded":
            return None

        content = getattr(llm_response, "content", None)
        parts = list(getattr(content, "parts", None) or [])

        # Do not terminate if no text was generated
        if not any(part.text_or_transcript() for part in parts):
            return None

        # Do not append if the model already made a tool call (e.g. end_session)
        if any(part.function_call for part in parts):
            return None

        callback_context.state["chat_complete"] = "concluded"
        callback_context.state["end_reason"] = "UNDER_CONSTRUCTION"
        logger.info("Sub-agent terminating conversation: UNDER_CONSTRUCTION")

        return LlmResponse.from_parts(
            parts=parts
            + [Part.from_end_session(reason="UNDER_CONSTRUCTION", escalated=False)]
        )

    except Exception:
        logger.exception("end_chat callback failed")
        return None
