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

"""Clean up orphaned evaluations from the CES App."""

import sys
import yaml
from cxas_scrapi.core.evaluations import Evaluations

APP_NAME = "projects/1097682577517/locations/us/apps/35a3feff-7b7e-4e7e-9504-d279323ba314"
GOLDEN_FILE = "evals/goldens/airline_goldens.yaml"

def main():
    with open(GOLDEN_FILE, "r") as f:
        goldens = yaml.safe_load(f)
    
    keep_names = {c["conversation"] for c in goldens.get("conversations", [])}
    print(f"Canonical evaluations to keep ({len(keep_names)}): {keep_names}")

    eval_client = Evaluations(app_name=APP_NAME)
    existing_evals = list(eval_client.list_evaluations())
    print(f"Found {len(existing_evals)} total evaluation(s) on platform:")

    deleted_count = 0
    kept_count = 0

    for ev in existing_evals:
        display_name = getattr(ev, "display_name", "")
        name = getattr(ev, "name", "")
        if display_name not in keep_names:
            print(f"  [DELETE] {display_name} -> {name}")
            try:
                eval_client.delete_evaluation(name=name, force=True)
                deleted_count += 1
            except Exception as e:
                print(f"    Failed to delete {name}: {e}")
        else:
            print(f"  [KEEP]   {display_name} -> {name}")
            kept_count += 1

    print(f"\nCleanup complete. Kept: {kept_count}, Deleted orphaned: {deleted_count}")

if __name__ == "__main__":
    main()
