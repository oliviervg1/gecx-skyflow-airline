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

"""Compiles the SkyFlow Airlines intent catalogue from sources/intents.yaml into the router tool.

This script ensures a single source of truth for all intents across the model's
Literal enum, the docstring glosses, and the deterministic Python lookup tables.

Usage:
    python scripts/generate_intents.py           # Update tool code
    python scripts/generate_intents.py --check   # Verify synchronization (CI gate)
"""

import argparse
import difflib
import pathlib
import sys
import textwrap
import yaml

sys.dont_write_bytecode = True

_HERE = pathlib.Path(__file__).resolve().parent.parent
_SOURCE = _HERE / "sources" / "intents.yaml"
_TOOL = (
    _HERE
    / "cxas_app"
    / "SkyFlowAirlineApp"
    / "tools"
    / "classify_airline_intent"
    / "python_function"
    / "python_code.py"
)

_BEGIN = "# --- generated from sources/intents.yaml ({label}) — do not edit ---"
_END = "# --- end generated ---"
_DOC_BEGIN = "        intent_id: The matched intent. Must be exactly one of:\n"
_DOC_END = "    Returns:"



def load_intents() -> list:
    """Load and validate the intents YAML source of truth."""
    if not _SOURCE.exists():
        sys.exit(f"Sources file not found: {_SOURCE}")
    intents = yaml.safe_load(_SOURCE.read_text())
    if not intents:
        sys.exit(f"{_SOURCE} is empty")

    valid_domains = {"DAY_OF_TRAVEL", "SALES", "GENERAL_FAQ", "SYSTEM"}
    seen = set()
    for entry in intents:
        missing = {"id", "gloss", "target_agent", "domain"} - set(entry)
        if missing:
            sys.exit(f"Entry {entry.get('id', entry)} missing fields: {sorted(missing)}")
        if not entry["id"].isidentifier() or entry["id"] != entry["id"].upper():
            sys.exit(f"{entry['id']} is not a valid uppercase identifier")
        if entry["id"] in seen:
            sys.exit(f"Duplicate intent id: {entry['id']}")
        if entry["domain"] not in valid_domains:
            sys.exit(f"Invalid domain for {entry['id']}: {entry['domain']}")
        seen.add(entry["id"])
    return intents


def render_enum(intents: list) -> str:
    """Generate the function signature with Literal enum."""
    lines = [
        "def classify_airline_intent(",
        "    intent_id: Literal[",
        '        "",',
    ]
    lines += [f'        "{i["id"]}",' for i in intents]
    lines += ['    ] = "",', ") -> dict:"]
    return "\n".join(lines)


def render_glosses(intents: list) -> str:
    """Generate the docstring parameter descriptions."""
    out = []
    for intent in intents:
        gloss = intent["gloss"].strip()
        desc = intent.get("description", "").strip()
        out.append(f"            {intent['id']}:")
        for line in textwrap.wrap(gloss, width=68):
            out.append(f"                {line}")
        if desc and desc != gloss:
            for line in textwrap.wrap(desc, width=68):
                out.append(f"                {line}")
    return "\n".join(out)


def render_tables(intents: list) -> str:
    """Generate the Python dictionary mapping intent to target agent and domain."""
    out = [
        "# SkyFlow Airlines Intent Routing Table",
        "# (target_agent, domain)",
        "_INTENT_BASE = {",
    ]
    for intent in intents:
        out.append(f'    "{intent["id"]}": Intent(')
        out.append(
            f'        target_agent="{intent["target_agent"]}", '
            f'domain="{intent["domain"]}",'
        )
        out.append("    ),")
    out.append("}")
    return "\n".join(out)


def replace_region(source: str, label: str, body: str, indent: str = "") -> str:
    """Swap text inside a delimited comment region."""
    begin = _BEGIN.format(label=label)
    if source.count(begin) != 1:
        sys.exit(f"Expected exactly one '{label}' region in {_TOOL}")
    head, rest = source.split(begin, 1)
    if _END not in rest:
        sys.exit(f"'{label}' region in {_TOOL} is not closed")
    _, tail = rest.split(_END, 1)
    return f"{head}{begin}\n{body}\n{indent}{_END}{tail}"


def replace_between(source: str, start: str, end: str, body: str) -> str:
    """Swap text between two explicit string boundaries."""
    if source.count(start) != 1 or source.count(end) != 1:
        sys.exit(f"Could not locate docstring region in {_TOOL}")
    head, rest = source.split(start, 1)
    _, tail = rest.split(end, 1)
    return f"{head}{start}{body}\n\n{end}{tail}"


def render(intents: list, current: str) -> str:
    """Render all generated sections into current file content."""
    out = replace_region(current, "catalogue", render_tables(intents))
    out = replace_region(out, "signature", render_enum(intents), indent="    ")
    return replace_between(out, _DOC_BEGIN, _DOC_END, render_glosses(intents))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if tool code matches sources/intents.yaml without writing.",
    )
    args = parser.parse_args()

    intents = load_intents()
    if not _TOOL.exists():
        sys.exit(f"Target tool file does not exist: {_TOOL}")
    current = _TOOL.read_text()
    updated = render(intents, current)

    if current == updated:
        print(f"{len(intents)} intents; {_TOOL.name} is synchronized.")
        return 0

    if args.check:
        diff = difflib.unified_diff(
            current.splitlines(True),
            updated.splitlines(True),
            fromfile="on disk",
            tofile="from intents.yaml",
        )
        sys.stdout.writelines(diff)
        print(
            f"\n{_TOOL.name} is stale. Run: python scripts/generate_intents.py",
            file=sys.stderr,
        )
        return 1

    _TOOL.write_text(updated)
    print(f"Successfully wrote {len(intents)} intents into {_TOOL.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
