#!/usr/bin/env python3
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

"""Interactive Terminal Simulator and CLI Test Driver for SkyFlow Airlines.

Runs an interactive conversational session simulating the Tool-First Intent Router
and Spoke Sub-Agents with full trace and state inspection.

Usage:
    python scripts/drive_session.py
    python scripts/drive_session.py --scenario day_of_travel
    python scripts/drive_session.py --scenario sales
    python scripts/drive_session.py --scenario faq
    python scripts/drive_session.py --scenario ambiguity
"""

import argparse
import builtins
import json
import os
import sys
import time
from typing import Dict, Any

sys.dont_write_bytecode = True

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from cxas_scrapi.utils.callback_libs import ToolContext

# Import tools
from cxas_app.SkyFlowAirlineApp.tools.classify_airline_intent.python_function.python_code import (
    classify_airline_intent,
)

SUBAGENT_RESPONSES = {
    "day_of_travel_agent": "You've reached the Day of Travel agent. I am currently under construction and will now terminate the conversation.",
    "sales_agent": "You've reached the Sales agent. I am currently under construction and will now terminate the conversation.",
    "general_faq_agent": "You've reached the General FAQ agent. I am currently under construction and will now terminate the conversation.",
}


class AirlineSessionDriver:
    """Drives multi-agent session state and simulated conversational turns."""

    def __init__(self):
        self.context = ToolContext(state={})
        builtins.context = self.context
        self.active_agent = "intent_router_agent"
        self.history = []

    def reset(self):
        self.context = ToolContext(state={})
        builtins.context = self.context
        self.active_agent = "intent_router_agent"
        self.history = []

    def match_intent_heuristics(self, user_text: str) -> str:
        """Heuristic matcher mapping user input to 1 of 3 sub-agent domain intents."""
        text = user_text.lower()
        if any(w in text for w in ["pizza", "hotel", "weather", "car rental", "taxi", "burger"]):
            return ""
        if text.strip() in ["hello", "hi", "hey", "good morning", "good afternoon"]:
            return ""
        if any(w in text for w in ["bye", "goodbye", "thanks that is all", "thank you bye"]):
            return ""
        if any(w in text for w in ["dont understand", "what do you mean", "confused", "pardon"]):
            return ""
        if text.strip() in ["help", "i need help", "can you help", "support"]:
            return ""

        # 1. Day of Travel
        if any(w in text for w in [
            "gate", "concourse", "terminal", "where is flight", "depart from",
            "delayed", "on time", "delay", "flight status", "status of flight",
            "baggage claim", "carousel", "luggage pickup", "boarding pass", "boarding group",
        ]):
            return "DAY_OF_TRAVEL"

        # 2. Sales & Ancillaries
        if any(w in text for w in [
            "fast track", "priority security", "skip security queue", "extra bag",
            "checked bag", "add luggage", "23kg", "32kg", "extra legroom",
            "seat upgrade", "reserve seat", "lounge", "lounge pass", "executive lounge",
            "bundle", "comfort bundle",
        ]):
            return "SALES"

        # 3. General FAQ & Policy
        if any(w in text for w in [
            "dimension", "bag size", "carry on limit", "cabin bag limit", "weight limit",
            "name change", "typo", "spelling mistake", "marriage name", "transfer ticket",
            "cancel", "refund", "cooling off", "money back", "voucher", "pet", "dog",
            "cat", "animal", "guide dog", "infant", "baby", "stroller", "wheelchair",
        ]):
            return "GENERAL_FAQ"

        return ""

    def execute_turn(self, user_text: str) -> Dict[str, Any]:
        """Process one conversational turn."""
        trace = {
            "user_input": user_text,
            "starting_agent": self.active_agent,
            "tool_executions": [],
            "agent_transfers": [],
            "agent_response": "",
            "state_snapshot": {},
        }

        # 1. If currently at intent router agent:
        if self.active_agent == "intent_router_agent":
            intent_id = self.match_intent_heuristics(user_text)
            tool_res = classify_airline_intent(intent_id=intent_id)
            trace["tool_executions"].append({
                "tool": "classify_airline_intent",
                "args": {"intent_id": intent_id},
                "result": tool_res,
            })

            next_step = tool_res.get("next_step")
            if next_step == "ROUTE_DAY_OF_TRAVEL":
                self.active_agent = "day_of_travel_agent"
                trace["agent_transfers"].append("day_of_travel_agent")
                trace["agent_response"] = SUBAGENT_RESPONSES["day_of_travel_agent"]
                self.context.state["chat_complete"] = "concluded"
                self.context.state["end_reason"] = "UNDER_CONSTRUCTION"

            elif next_step == "ROUTE_SALES":
                self.active_agent = "sales_agent"
                trace["agent_transfers"].append("sales_agent")
                trace["agent_response"] = SUBAGENT_RESPONSES["sales_agent"]
                self.context.state["chat_complete"] = "concluded"
                self.context.state["end_reason"] = "UNDER_CONSTRUCTION"

            elif next_step == "ROUTE_GENERAL_FAQ":
                self.active_agent = "general_faq_agent"
                trace["agent_transfers"].append("general_faq_agent")
                trace["agent_response"] = SUBAGENT_RESPONSES["general_faq_agent"]
                self.context.state["chat_complete"] = "concluded"
                self.context.state["end_reason"] = "UNDER_CONSTRUCTION"

            else:
                trace["agent_response"] = tool_res.get("agent_action", "")

        # 2. If at any sub-agent:
        elif self.active_agent in SUBAGENT_RESPONSES:
            trace["agent_response"] = SUBAGENT_RESPONSES[self.active_agent]
            self.context.state["chat_complete"] = "concluded"
            self.context.state["end_reason"] = "UNDER_CONSTRUCTION"

        trace["active_agent"] = self.active_agent
        trace["state_snapshot"] = dict(self.context.state)
        self.history.append(trace)
        return trace


def print_trace(trace: Dict[str, Any]):
    print("\n" + "=" * 65)
    print(f"👤 USER: {trace['user_input']}")
    print(f"🤖 ACTIVE AGENT: {trace['active_agent']}")
    if trace["agent_transfers"]:
        print(f"🔄 TRANSFERS: -> {' -> '.join(trace['agent_transfers'])}")
    print("-" * 65)
    print("⚙️  TOOL EXECUTIONS:")
    for t in trace["tool_executions"]:
        print(f"   ▶ {t['tool']}({json.dumps(t['args'])})")
        print(f"     Status: {t['result'].get('status')}, Next Step: {t['result'].get('next_step')}")
    print("-" * 65)
    print("💬 AGENT RESPONSE (agent_action):")
    print(f"   \"{trace['agent_response']}\"")
    print("-" * 65)
    print("📊 SESSION VARIABLES (context.state):")
    for k, v in trace["state_snapshot"].items():
        if v:
            print(f"   • {k}: {v}")
    print("=" * 65 + "\n")


def run_scenario(scenario_name: str):
    driver = AirlineSessionDriver()
    scenarios = {
        "day_of_travel": [
            "What gate does flight SK101 leave from and is it delayed?",
        ],
        "sales": [
            "I would like to add fast track security to my flight",
        ],
        "faq": [
            "What are your carry-on baggage dimension limits?",
        ],
        "ambiguity": [
            "I need some help",
            "Is flight SK204 on time today?",
        ],
    }

    steps = scenarios.get(scenario_name, scenarios["day_of_travel"])
    print(f"\n🚀 Running Preset Scenario: {scenario_name.upper()}")
    for user_input in steps:
        time.sleep(0.3)
        trace = driver.execute_turn(user_input)
        print_trace(trace)


def interactive_cli():
    driver = AirlineSessionDriver()
    print("\n" + "=" * 65)
    print("🛫 SkyFlow Airlines — Interactive Multi-Agent Intent Router CLI")
    print("   Type any question or command to test routing and sub-agents.")
    print("   Commands: /reset, /scenario <name>, /quit")
    print("=" * 65 + "\n")

    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            if user_input in ["/quit", "exit", "quit"]:
                print("Exiting simulator. Have a great day!")
                break
            if user_input == "/reset":
                driver.reset()
                print("✨ Session state reset to root intent_router_agent.")
                continue
            if user_input.startswith("/scenario"):
                parts = user_input.split()
                sc_name = parts[1] if len(parts) > 1 else "day_of_travel"
                run_scenario(sc_name)
                continue

            trace = driver.execute_turn(user_input)
            print_trace(trace)

        except (KeyboardInterrupt, EOFError):
            print("\nSession ended.")
            break


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--scenario", choices=["day_of_travel", "sales", "faq", "ambiguity"], help="Run preset scenario")
    args = parser.parse_args()

    if args.scenario:
        run_scenario(args.scenario)
    else:
        interactive_cli()
