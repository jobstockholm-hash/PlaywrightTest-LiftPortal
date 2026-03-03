"""
utils/csv_generator.py
======================
Generates a CSV for bulk-import testing on the LIFT Portal.

Official template columns: First name, Last name

Uniqueness strategy
-------------------
Every First name gets a unique 4-digit suffix (e.g. "Alice3847").
This prevents:
  1. Duplicate rows within the same CSV file.
  2. Name collisions with existing portal users (portal checks full name).

The file is saved in TWO places:
  - output_dir  (pytest tmp_path -- used by the automated test)
  - test-data/  (project root -- permanent copy for manual inspection)

Usage
-----
    from utils.csv_generator import generate_users_csv
    path = generate_users_csv(count=35)
"""

import csv
import random
import shutil
from datetime import datetime
from pathlib import Path

_FIRST = [
    "Alice", "Bob", "Carol", "David", "Eva", "Frank", "Grace", "Henry",
    "Iris", "Jack", "Karen", "Leo", "Maria", "Nils", "Olivia", "Peter",
    "Quinn", "Rosa", "Sam", "Tina", "Ulrik", "Vera", "Walter", "Xena",
    "Yara", "Zoe", "Anders", "Bjorn", "Camilla", "Dag", "Elin", "Finn",
    "Greta", "Hans", "Inga",
]
_LAST = [
    "Hansen", "Nielsen", "Johansen", "Andersen", "Larsen", "Olsen",
    "Rasmussen", "Christensen", "Petersen", "Madsen", "Smith", "Jones",
    "Williams", "Brown", "Davis", "Miller", "Wilson", "Moore", "Taylor",
    "Anderson", "Thomas", "Jackson", "White", "Harris", "Martin",
]

_LOCAL_TESTDATA = Path("test-data")


def generate_users_csv(count=35, output_dir="test-data", filename=None):
    """
    Generate a CSV with unique users for LIFT Portal bulk import.

    Each First name has a unique 4-digit suffix to avoid duplicate errors.
    A copy is saved to test-data/ in the project root for manual testing.

    Returns absolute path to the CSV in output_dir.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    if not filename:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"bulk_users_{count}_{ts}.csv"

    filepath = Path(output_dir) / filename
    fieldnames = ["First name", "Last name"]

    used_tags = set()
    rows = []
    for _ in range(count):
        while True:
            tag = random.randint(1000, 9999)
            if tag not in used_tags:
                used_tags.add(tag)
                break
        rows.append({
            "First name": f"{random.choice(_FIRST)}{tag}",
            "Last name":  random.choice(_LAST),
        })

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    abs_path = filepath.resolve()
    print(f"  ✅ CSV generated: {abs_path} ({count} users)")

    # Permanent copy in test-data/ for manual inspection and replay
    try:
        _LOCAL_TESTDATA.mkdir(parents=True, exist_ok=True)
        local_copy = _LOCAL_TESTDATA / filename
        shutil.copy2(abs_path, local_copy)
        print(f"  📁 Local copy:    {local_copy.resolve()}")
        print(f"  ℹ️  Manual upload: open test-data/{filename}")
    except Exception as e:
        print(f"  ⚠️  Could not save local copy: {e}")

    return str(abs_path)


if __name__ == "__main__":
    import sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 35
    path = generate_users_csv(n, output_dir="test-data")
    print("Done: " + path)